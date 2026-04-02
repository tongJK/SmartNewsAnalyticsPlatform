from django.db import models
from django.contrib.postgres.fields import ArrayField
from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.search import SearchVectorField
from django.utils import timezone
from django.conf import settings
import logging

logger = logging.getLogger('articles')


class Article(models.Model):
    """
    Article model with PostgreSQL advanced features:
    - Vector embeddings for semantic search
    - Full-text search with tsvector
    - Proper indexing for performance
    """
    
    title = models.CharField(max_length=500, db_index=True)
    content = models.TextField()
    summary = models.TextField(blank=True, help_text="Auto-generated summary")
    
    # Metadata
    author = models.CharField(max_length=200, blank=True)
    source_url = models.URLField(blank=True)
    published_at = models.DateTimeField(db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # PostgreSQL advanced features
    embedding = ArrayField(
        models.FloatField(),
        size=768,
        null=True,
        blank=True,
        help_text="768-dimensional embedding vector for semantic search"
    )
    
    # Multimodal embeddings
    image_embedding = ArrayField(
        models.FloatField(),
        size=512,
        null=True,
        blank=True,
        help_text="CLIP image embedding for visual search"
    )
    
    video_embedding = ArrayField(
        models.FloatField(),
        size=512,
        null=True,
        blank=True,
        help_text="Video frame embedding for video search"
    )
    
    # Media URLs
    image_url = models.URLField(blank=True, help_text="Featured image URL")
    video_url = models.URLField(blank=True, help_text="Video content URL")
    media_type = models.CharField(
        max_length=20,
        choices=[
            ('text', 'Text Only'),
            ('image', 'With Image'),
            ('video', 'With Video'),
            ('mixed', 'Mixed Media')
        ],
        default='text',
        db_index=True
    )
    
    search_vector = SearchVectorField(
        null=True,
        blank=True,
        help_text="Full-text search vector"
    )
    
    # Analytics fields
    views = models.PositiveIntegerField(default=0)
    shares = models.PositiveIntegerField(default=0)
    
    # Categories and tags
    category = models.CharField(max_length=100, blank=True, db_index=True)
    tags = ArrayField(
        models.CharField(max_length=50),
        blank=True,
        default=list,
        help_text="Article tags for categorization"
    )
    
    # Language support
    language = models.CharField(max_length=10, default='en', db_index=True)
    
    class Meta:
        db_table = 'articles'
        indexes = [
            # Full-text search index
            GinIndex(fields=['search_vector']),
            # Tag search index
            GinIndex(fields=['tags']),
            # Time-based queries
            models.Index(fields=['published_at', 'category']),
            models.Index(fields=['created_at']),
            # Analytics queries
            models.Index(fields=['views', 'published_at']),
            # Media type queries
            models.Index(fields=['media_type']),
        ]
        ordering = ['-published_at']
    
    def __str__(self):
        return self.title
    
    def increment_views(self):
        """Thread-safe view counter increment"""
        self.__class__.objects.filter(pk=self.pk).update(views=models.F('views') + 1)
        self.refresh_from_db(fields=['views'])
    
    def increment_shares(self):
        """Thread-safe share counter increment"""
        self.__class__.objects.filter(pk=self.pk).update(shares=models.F('shares') + 1)
        self.refresh_from_db(fields=['shares'])
    
    @property
    def engagement_score(self):
        """Simple engagement score calculation"""
        return (self.views * 1) + (self.shares * 5)
    
    def save(self, *args, **kwargs):
        if not self.published_at:
            self.published_at = timezone.now()
        super().save(*args, **kwargs)
        logger.info(f"Article saved: {self.title} (ID: {self.pk})")


class ArticleView(models.Model):
    """
    Track individual article views for detailed analytics
    This will be used with TimescaleDB for time-series analysis
    """
    
    article = models.ForeignKey(Article, on_delete=models.CASCADE, related_name='view_records')
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    
    # Optional user tracking (if authenticated)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    
    # Request metadata
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    referrer = models.URLField(blank=True)
    
    class Meta:
        db_table = 'article_views'
        indexes = [
            # Time-series optimization
            models.Index(fields=['timestamp', 'article']),
            models.Index(fields=['article', 'timestamp']),
        ]
    
    def __str__(self):
        return f"View of '{self.article.title}' at {self.timestamp}"