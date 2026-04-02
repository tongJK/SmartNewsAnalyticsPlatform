"""
Article service layer for business logic
"""
from django.db import transaction
from django.db.models import F, Q
from django.utils import timezone
from apps.articles.models import Article, ArticleView
from apps.services.embedding_service import embedding_manager
import logging

logger = logging.getLogger('articles')


class ArticleService:
    """Service class for article-related business logic"""
    
    @staticmethod
    def create_article(title, content, author=None, category=None, tags=None, **kwargs):
        """
        Create a new article with business logic validation
        """
        # Business logic: Auto-generate summary if not provided
        if not kwargs.get('summary') and content:
            kwargs['summary'] = ArticleService._generate_summary(content)
        
        # Business logic: Set published_at if not provided
        if not kwargs.get('published_at'):
            kwargs['published_at'] = timezone.now()
        
        # Create article
        article = Article.objects.create(
            title=title,
            content=content,
            author=author or '',
            category=category or '',
            tags=tags or [],
            **kwargs
        )
        
        logger.info(f"Article created: {article.title} (ID: {article.id})")
        return article
    
    @staticmethod
    def _generate_summary(content, max_length=200):
        """Generate a simple summary from content"""
        sentences = content.split('. ')
        summary = sentences[0]
        
        for sentence in sentences[1:]:
            if len(summary + '. ' + sentence) <= max_length:
                summary += '. ' + sentence
            else:
                break
        
        return summary + ('...' if len(content) > len(summary) else '')
    
    @staticmethod
    def track_article_view(article, user=None, ip_address=None, user_agent='', referrer=''):
        """
        Track article view with business logic
        """
        try:
            # Business logic: Don't track duplicate views from same IP within 1 hour
            if ip_address:
                recent_view = ArticleView.objects.filter(
                    article=article,
                    ip_address=ip_address,
                    timestamp__gte=timezone.now() - timezone.timedelta(hours=1)
                ).exists()
                
                if recent_view:
                    logger.debug(f"Duplicate view ignored for article {article.id} from IP {ip_address}")
                    return None
            
            # Create view record
            view = ArticleView.objects.create(
                article=article,
                user=user,
                ip_address=ip_address,
                user_agent=user_agent,
                referrer=referrer
            )
            
            # Increment view counter atomically
            Article.objects.filter(pk=article.pk).update(views=F('views') + 1)
            
            logger.info(f"Article view tracked: {article.title} (ID: {article.id})")
            return view
            
        except Exception as e:
            logger.error(f"Error tracking article view: {e}")
            return None
    
    @staticmethod
    def increment_shares(article_id):
        """
        Increment share counter with business logic
        """
        try:
            # Atomic increment
            updated = Article.objects.filter(pk=article_id).update(
                shares=F('shares') + 1
            )
            
            if updated:
                article = Article.objects.get(pk=article_id)
                logger.info(f"Share tracked for article: {article.title} (Total: {article.shares})")
                return article.shares
            
        except Exception as e:
            logger.error(f"Error incrementing shares for article {article_id}: {e}")
        
        return 0
    
    @staticmethod
    def get_similar_articles(article, limit=10, threshold=0.5):
        """
        Get articles similar to the given article using embeddings
        """
        if not article.embedding:
            return Article.objects.none()
        
        # Get articles with embeddings (excluding the current article)
        candidates = Article.objects.exclude(
            pk=article.pk
        ).exclude(
            embedding__isnull=True
        )
        
        # Calculate similarities
        similar_articles = []
        for candidate in candidates[:500]:  # Limit for performance
            if candidate.embedding:
                similarity = ArticleService._cosine_similarity(
                    article.embedding, 
                    candidate.embedding
                )
                
                if similarity > threshold:
                    candidate.similarity_score = similarity
                    similar_articles.append(candidate)
        
        # Sort by similarity and return top results
        similar_articles.sort(key=lambda x: x.similarity_score, reverse=True)
        return similar_articles[:limit]
    
    @staticmethod
    def _cosine_similarity(a, b):
        """Calculate cosine similarity between two vectors"""
        try:
            import numpy as np
            a = np.array(a)
            b = np.array(b)
            return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))
        except:
            return 0.0
    
    @staticmethod
    def search_articles(query, search_type='hybrid', category=None, language=None, limit=20):
        """
        Search articles using different search strategies
        """
        from apps.articles.views import ArticleViewSet
        
        # Create a temporary view instance to use search methods
        view = ArticleViewSet()
        
        if search_type == 'text':
            return view._full_text_search(query, category, language, limit)
        elif search_type == 'semantic':
            return view._semantic_search(query, category, language, limit)
        else:  # hybrid
            return view._hybrid_search(query, category, language, limit)
    
    @staticmethod
    def get_trending_articles(hours=24, limit=20):
        """
        Get trending articles based on recent activity
        """
        from django.db.models import Count
        from datetime import timedelta
        
        cutoff_time = timezone.now() - timedelta(hours=hours)
        
        # Get articles with recent views
        trending = Article.objects.filter(
            view_records__timestamp__gte=cutoff_time
        ).annotate(
            recent_views=Count('view_records')
        ).filter(
            recent_views__gt=0
        ).order_by('-recent_views', '-published_at')[:limit]
        
        return trending
    
    @staticmethod
    def bulk_update_embeddings(article_ids, batch_size=100):
        """
        Update embeddings for multiple articles
        """
        from apps.articles.tasks import generate_embeddings_batch
        
        # Split into batches
        batches = [
            article_ids[i:i + batch_size] 
            for i in range(0, len(article_ids), batch_size)
        ]
        
        # Queue Celery tasks
        task_ids = []
        for batch in batches:
            task = generate_embeddings_batch.delay(batch)
            task_ids.append(task.id)
        
        logger.info(f"Queued {len(task_ids)} embedding update tasks")
        return task_ids