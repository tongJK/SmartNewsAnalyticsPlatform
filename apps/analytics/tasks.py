from celery import shared_task
from django.db.models import Count, Sum, Avg, F
from django.utils import timezone
from datetime import timedelta, date
import logging

logger = logging.getLogger('analytics')


@shared_task
def generate_daily_stats():
    """
    Generate daily aggregated statistics for all articles
    Runs daily at midnight via Celery Beat
    """
    try:
        from .models import DailyArticleStats, ArticleMetrics
        from apps.articles.models import Article
        
        yesterday = date.today() - timedelta(days=1)
        
        # Get all articles that had activity yesterday
        articles_with_activity = ArticleMetrics.objects.filter(
            timestamp__date=yesterday
        ).values('article').distinct()
        
        stats_created = 0
        
        for item in articles_with_activity:
            article_id = item['article']
            
            # Aggregate metrics for this article on this date
            daily_metrics = ArticleMetrics.objects.filter(
                article_id=article_id,
                timestamp__date=yesterday
            ).aggregate(
                total_views=Sum('views_count'),
                total_shares=Sum('shares_count'),
                total_comments=Sum('comments_count'),
                avg_read_time=Avg('read_time_avg'),
                avg_bounce_rate=Avg('bounce_rate')
            )
            
            # Create or update daily stats
            daily_stat, created = DailyArticleStats.objects.update_or_create(
                article_id=article_id,
                date=yesterday,
                defaults={
                    'total_views': daily_metrics['total_views'] or 0,
                    'total_shares': daily_metrics['total_shares'] or 0,
                    'total_comments': daily_metrics['total_comments'] or 0,
                    'avg_read_time': daily_metrics['avg_read_time'],
                    'avg_bounce_rate': daily_metrics['avg_bounce_rate'],
                }
            )
            
            if created:
                stats_created += 1
        
        # Calculate rankings
        _calculate_daily_rankings(yesterday)
        
        logger.info(f"Generated daily stats for {stats_created} articles on {yesterday}")
        return f"Generated daily stats for {stats_created} articles"
        
    except Exception as exc:
        logger.error(f"Error generating daily stats: {exc}")
        raise


def _calculate_daily_rankings(date_obj):
    """Calculate daily rankings for articles"""
    from .models import DailyArticleStats
    
    # Rank by views
    stats_by_views = DailyArticleStats.objects.filter(
        date=date_obj
    ).order_by('-total_views')
    
    for rank, stat in enumerate(stats_by_views, 1):
        stat.views_rank = rank
        stat.save(update_fields=['views_rank'])
    
    # Rank by engagement (views + shares * 5)
    stats_by_engagement = DailyArticleStats.objects.filter(
        date=date_obj
    ).annotate(
        engagement_score=F('total_views') + F('total_shares') * 5
    ).order_by('-engagement_score')
    
    for rank, stat in enumerate(stats_by_engagement, 1):
        stat.engagement_rank = rank
        stat.save(update_fields=['engagement_rank'])


@shared_task
def detect_trending_topics_task():
    """
    Detect and update trending topics
    Runs every 30 minutes via Celery Beat
    """
    try:
        from .models import TrendingTopic
        from apps.articles.models import Article
        from collections import Counter
        import re
        
        # Get recent articles (last 24 hours)
        cutoff_time = timezone.now() - timedelta(hours=24)
        recent_articles = Article.objects.filter(
            published_at__gte=cutoff_time
        )
        
        # Extract topics/keywords from titles and content
        all_words = []
        for article in recent_articles:
            # Simple keyword extraction (can be improved with NLP)
            text = f"{article.title} {article.content}".lower()
            words = re.findall(r'\b[a-zA-Z]{4,}\b', text)  # Words with 4+ chars
            all_words.extend(words)
        
        # Count word frequencies
        word_counts = Counter(all_words)
        
        # Filter out common words (simple stopwords)
        stopwords = {
            'this', 'that', 'with', 'have', 'will', 'from', 'they', 'been',
            'were', 'said', 'each', 'which', 'their', 'time', 'more', 'very',
            'what', 'know', 'just', 'first', 'into', 'over', 'think', 'also',
            'your', 'work', 'life', 'only', 'can', 'still', 'should', 'after',
            'being', 'now', 'made', 'before', 'here', 'through', 'when', 'where'
        }
        
        trending_words = {
            word: count for word, count in word_counts.most_common(50)
            if word not in stopwords and count >= 3
        }
        
        # Update trending topics
        topics_updated = 0
        current_time = timezone.now()
        
        for word, count in trending_words.items():
            # Get previous mention count for trend calculation
            previous_topic = TrendingTopic.objects.filter(
                topic=word,
                timestamp__gte=current_time - timedelta(hours=1)
            ).first()
            
            previous_count = previous_topic.mention_count if previous_topic else 0
            
            # Calculate trend score
            from .services import TrendAnalyzer
            trend_score = TrendAnalyzer.calculate_trend_score(word, count, previous_count)
            velocity = (count - previous_count) / max(previous_count, 1)
            
            # Create trending topic entry
            trending_topic = TrendingTopic.objects.create(
                topic=word,
                timestamp=current_time,
                mention_count=count,
                article_count=recent_articles.filter(
                    Q(title__icontains=word) | Q(content__icontains=word)
                ).count(),
                trend_score=trend_score,
                velocity=velocity
            )
            
            # Link related articles
            related_articles = recent_articles.filter(
                Q(title__icontains=word) | Q(content__icontains=word)
            )[:10]  # Limit to top 10
            
            trending_topic.related_articles.set(related_articles)
            topics_updated += 1
        
        logger.info(f"Updated {topics_updated} trending topics")
        return f"Updated {topics_updated} trending topics"
        
    except Exception as exc:
        logger.error(f"Error detecting trending topics: {exc}")
        raise


@shared_task
def cleanup_old_metrics():
    """
    Clean up old metrics data to prevent database bloat
    Runs weekly
    """
    try:
        from .models import ArticleMetrics, UserEngagement
        
        # Keep detailed metrics for 90 days
        cutoff_date = timezone.now() - timedelta(days=90)
        
        deleted_metrics = ArticleMetrics.objects.filter(
            timestamp__lt=cutoff_date
        ).delete()
        
        deleted_engagement = UserEngagement.objects.filter(
            timestamp__lt=cutoff_date
        ).delete()
        
        logger.info(f"Cleaned up {deleted_metrics[0]} old metrics and {deleted_engagement[0]} engagement records")
        return f"Cleaned up {deleted_metrics[0]} metrics, {deleted_engagement[0]} engagement records"
        
    except Exception as exc:
        logger.error(f"Error cleaning up old metrics: {exc}")
        raise


@shared_task
def update_article_embeddings():
    """
    Update embeddings for articles that don't have them
    Runs every 6 hours
    """
    try:
        from apps.articles.models import Article
        from apps.articles.tasks import generate_embeddings_batch
        
        # Find articles without embeddings
        articles_without_embeddings = Article.objects.filter(
            embedding__isnull=True
        )[:100]  # Process in batches of 100
        
        if articles_without_embeddings:
            article_ids = list(articles_without_embeddings.values_list('id', flat=True))
            generate_embeddings_batch.delay(article_ids)
            
            logger.info(f"Queued embedding generation for {len(article_ids)} articles")
            return f"Queued embedding generation for {len(article_ids)} articles"
        else:
            return "No articles need embedding updates"
            
    except Exception as exc:
        logger.error(f"Error updating article embeddings: {exc}")
        raise