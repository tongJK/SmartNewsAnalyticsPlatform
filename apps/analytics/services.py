from django.db.models import Count, Avg, Sum, F, Q
from django.utils import timezone
from datetime import timedelta, datetime
import pandas as pd
from typing import Dict, List, Optional
import logging

from .models import ArticleMetrics, DailyArticleStats, TrendingTopic, UserEngagement
from apps.articles.models import Article

logger = logging.getLogger('analytics')


class TimeSeriesAnalytics:
    """
    Service for time-series analytics using TimescaleDB features
    """
    
    @staticmethod
    def get_article_views_timeseries(article_id: int, days: int = 30) -> pd.DataFrame:
        """
        Get time-series data for article views
        """
        end_date = timezone.now()
        start_date = end_date - timedelta(days=days)
        
        metrics = ArticleMetrics.objects.filter(
            article_id=article_id,
            timestamp__gte=start_date,
            timestamp__lte=end_date
        ).values('timestamp', 'views_count').order_by('timestamp')
        
        if not metrics:
            return pd.DataFrame(columns=['timestamp', 'views_count'])
        
        df = pd.DataFrame(list(metrics))
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df.set_index('timestamp', inplace=True)
        
        # Resample to daily aggregation
        daily_views = df.resample('D')['views_count'].sum().fillna(0)
        
        return daily_views.reset_index()
    
    @staticmethod
    def get_trending_articles(hours: int = 24, limit: int = 10) -> List[Dict]:
        """
        Get trending articles based on recent engagement
        """
        cutoff_time = timezone.now() - timedelta(hours=hours)
        
        trending = Article.objects.filter(
            articlemetrics__timestamp__gte=cutoff_time
        ).annotate(
            recent_views=Sum('articlemetrics__views_count'),
            recent_shares=Sum('articlemetrics__shares_count'),
            engagement_score=F('recent_views') + F('recent_shares') * 5
        ).order_by('-engagement_score')[:limit]
        
        return [
            {
                'id': article.id,
                'title': article.title,
                'recent_views': article.recent_views or 0,
                'recent_shares': article.recent_shares or 0,
                'engagement_score': article.engagement_score or 0,
                'published_at': article.published_at,
            }
            for article in trending
        ]
    
    @staticmethod
    def get_category_performance(days: int = 7) -> List[Dict]:
        """
        Analyze performance by category
        """
        end_date = timezone.now()
        start_date = end_date - timedelta(days=days)
        
        category_stats = Article.objects.filter(
            published_at__gte=start_date
        ).values('category').annotate(
            article_count=Count('id'),
            total_views=Sum('views'),
            total_shares=Sum('shares'),
            avg_engagement=Avg(F('views') + F('shares') * 5)
        ).order_by('-avg_engagement')
        
        return list(category_stats)
    
    @staticmethod
    def get_hourly_traffic_pattern(days: int = 7) -> pd.DataFrame:
        """
        Analyze traffic patterns by hour of day
        """
        end_date = timezone.now()
        start_date = end_date - timedelta(days=days)
        
        # Get user engagement data grouped by hour
        engagement_data = UserEngagement.objects.filter(
            timestamp__gte=start_date,
            timestamp__lte=end_date
        ).extra(
            select={'hour': 'EXTRACT(hour FROM timestamp)'}
        ).values('hour').annotate(
            total_sessions=Count('session_id', distinct=True),
            avg_time_spent=Avg('time_spent'),
            avg_scroll_depth=Avg('scroll_depth')
        ).order_by('hour')
        
        df = pd.DataFrame(list(engagement_data))
        if df.empty:
            return pd.DataFrame(columns=['hour', 'total_sessions', 'avg_time_spent', 'avg_scroll_depth'])
        
        # Fill missing hours with zeros
        all_hours = pd.DataFrame({'hour': range(24)})
        df = all_hours.merge(df, on='hour', how='left').fillna(0)
        
        return df


class TrendAnalyzer:
    """
    Service for trend detection and analysis
    """
    
    @staticmethod
    def detect_trending_topics(hours: int = 24, min_mentions: int = 5) -> List[Dict]:
        """
        Detect trending topics based on article content and engagement
        """
        cutoff_time = timezone.now() - timedelta(hours=hours)
        
        # Get recent trending topics
        trending = TrendingTopic.objects.filter(
            timestamp__gte=cutoff_time,
            mention_count__gte=min_mentions
        ).order_by('-trend_score')[:20]
        
        return [
            {
                'topic': topic.topic,
                'mention_count': topic.mention_count,
                'article_count': topic.article_count,
                'trend_score': topic.trend_score,
                'velocity': topic.velocity,
                'timestamp': topic.timestamp,
            }
            for topic in trending
        ]
    
    @staticmethod
    def calculate_trend_score(topic: str, current_mentions: int, previous_mentions: int) -> float:
        """
        Calculate trend score based on mention velocity
        """
        if previous_mentions == 0:
            return float(current_mentions)
        
        velocity = (current_mentions - previous_mentions) / previous_mentions
        base_score = current_mentions
        trend_score = base_score * (1 + velocity)
        
        return max(0, trend_score)
    
    @staticmethod
    def predict_engagement(article_id: int) -> Dict:
        """
        Predict article engagement based on historical patterns
        Simple prediction based on category and time patterns
        """
        try:
            article = Article.objects.get(pk=article_id)
            
            # Get historical performance for similar articles
            similar_articles = Article.objects.filter(
                category=article.category,
                published_at__gte=timezone.now() - timedelta(days=30)
            ).exclude(pk=article_id)
            
            if not similar_articles.exists():
                return {'predicted_views': 0, 'predicted_shares': 0, 'confidence': 0.0}
            
            avg_views = similar_articles.aggregate(avg_views=Avg('views'))['avg_views'] or 0
            avg_shares = similar_articles.aggregate(avg_shares=Avg('shares'))['avg_shares'] or 0
            
            # Simple time-based adjustment
            hour = article.published_at.hour
            time_multiplier = 1.2 if 8 <= hour <= 18 else 0.8  # Business hours boost
            
            predicted_views = int(avg_views * time_multiplier)
            predicted_shares = int(avg_shares * time_multiplier)
            confidence = min(similar_articles.count() / 10.0, 1.0)  # More data = higher confidence
            
            return {
                'predicted_views': predicted_views,
                'predicted_shares': predicted_shares,
                'confidence': confidence,
                'based_on_articles': similar_articles.count()
            }
            
        except Article.DoesNotExist:
            return {'error': 'Article not found'}


class DashboardService:
    """
    Service for dashboard data aggregation
    """
    
    @staticmethod
    def get_overview_stats(days: int = 7) -> Dict:
        """
        Get overview statistics for dashboard
        """
        end_date = timezone.now()
        start_date = end_date - timedelta(days=days)
        
        # Article stats
        total_articles = Article.objects.count()
        recent_articles = Article.objects.filter(created_at__gte=start_date).count()
        
        # Engagement stats
        total_views = Article.objects.aggregate(total=Sum('views'))['total'] or 0
        total_shares = Article.objects.aggregate(total=Sum('shares'))['total'] or 0
        
        # Recent engagement
        recent_views = ArticleMetrics.objects.filter(
            timestamp__gte=start_date
        ).aggregate(total=Sum('views_count'))['total'] or 0
        
        # Top categories
        top_categories = Article.objects.values('category').annotate(
            count=Count('id'),
            total_views=Sum('views')
        ).order_by('-total_views')[:5]
        
        return {
            'total_articles': total_articles,
            'recent_articles': recent_articles,
            'total_views': total_views,
            'total_shares': total_shares,
            'recent_views': recent_views,
            'top_categories': list(top_categories),
            'period_days': days,
        }
    
    @staticmethod
    def get_real_time_metrics() -> Dict:
        """
        Get real-time metrics for live dashboard
        """
        # Last hour metrics
        one_hour_ago = timezone.now() - timedelta(hours=1)
        
        recent_views = ArticleMetrics.objects.filter(
            timestamp__gte=one_hour_ago
        ).aggregate(total=Sum('views_count'))['total'] or 0
        
        active_articles = ArticleMetrics.objects.filter(
            timestamp__gte=one_hour_ago,
            views_count__gt=0
        ).values('article').distinct().count()
        
        return {
            'views_last_hour': recent_views,
            'active_articles_last_hour': active_articles,
            'timestamp': timezone.now(),
        }