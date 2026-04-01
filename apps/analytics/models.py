from django.db import models
from django.utils import timezone
from django.conf import settings


class ArticleMetrics(models.Model):
    """
    Time-series metrics for articles
    This table will be converted to TimescaleDB hypertable
    """
    
    article = models.ForeignKey('articles.Article', on_delete=models.CASCADE)
    timestamp = models.DateTimeField(default=timezone.now, db_index=True)
    
    # Engagement metrics
    views_count = models.PositiveIntegerField(default=0)
    shares_count = models.PositiveIntegerField(default=0)
    comments_count = models.PositiveIntegerField(default=0)
    
    # Time-based metrics
    read_time_avg = models.FloatField(null=True, help_text="Average read time in seconds")
    bounce_rate = models.FloatField(null=True, help_text="Bounce rate percentage")
    
    # Traffic source
    traffic_source = models.CharField(max_length=100, blank=True)
    referrer_domain = models.CharField(max_length=200, blank=True)
    
    class Meta:
        db_table = 'article_metrics'
        indexes = [
            # TimescaleDB optimization - time-based partitioning key first
            models.Index(fields=['timestamp', 'article']),
            models.Index(fields=['article', 'timestamp']),
            models.Index(fields=['timestamp', 'traffic_source']),
        ]
        # Unique constraint to prevent duplicate metrics for same article/timestamp
        constraints = [
            models.UniqueConstraint(
                fields=['article', 'timestamp'],
                name='unique_article_timestamp'
            )
        ]
    
    def __str__(self):
        return f"Metrics for {self.article.title} at {self.timestamp}"


class DailyArticleStats(models.Model):
    """
    Daily aggregated statistics for articles
    Pre-computed for faster dashboard queries
    """
    
    article = models.ForeignKey('articles.Article', on_delete=models.CASCADE)
    date = models.DateField(db_index=True)
    
    # Daily totals
    total_views = models.PositiveIntegerField(default=0)
    total_shares = models.PositiveIntegerField(default=0)
    total_comments = models.PositiveIntegerField(default=0)
    unique_visitors = models.PositiveIntegerField(default=0)
    
    # Daily averages
    avg_read_time = models.FloatField(null=True)
    avg_bounce_rate = models.FloatField(null=True)
    
    # Rankings
    views_rank = models.PositiveIntegerField(null=True, help_text="Daily ranking by views")
    engagement_rank = models.PositiveIntegerField(null=True, help_text="Daily ranking by engagement")
    
    class Meta:
        db_table = 'daily_article_stats'
        indexes = [
            models.Index(fields=['date', 'total_views']),
            models.Index(fields=['date', 'views_rank']),
            models.Index(fields=['article', 'date']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['article', 'date'],
                name='unique_article_date'
            )
        ]
    
    def __str__(self):
        return f"Daily stats for {self.article.title} on {self.date}"


class TrendingTopic(models.Model):
    """
    Track trending topics and keywords over time
    """
    
    topic = models.CharField(max_length=200, db_index=True)
    timestamp = models.DateTimeField(default=timezone.now, db_index=True)
    
    # Trend metrics
    mention_count = models.PositiveIntegerField(default=0)
    article_count = models.PositiveIntegerField(default=0)
    total_engagement = models.PositiveIntegerField(default=0)
    
    # Trend analysis
    trend_score = models.FloatField(help_text="Calculated trend score")
    velocity = models.FloatField(help_text="Rate of change in mentions")
    
    # Related articles
    related_articles = models.ManyToManyField(
        'articles.Article',
        blank=True,
        help_text="Articles related to this trending topic"
    )
    
    class Meta:
        db_table = 'trending_topics'
        indexes = [
            models.Index(fields=['timestamp', 'trend_score']),
            models.Index(fields=['topic', 'timestamp']),
        ]
    
    def __str__(self):
        return f"Trending: {self.topic} (Score: {self.trend_score})"


class UserEngagement(models.Model):
    """
    Track user engagement patterns
    """
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    session_id = models.CharField(max_length=100, db_index=True)
    timestamp = models.DateTimeField(default=timezone.now, db_index=True)
    
    # Engagement data
    article = models.ForeignKey('articles.Article', on_delete=models.CASCADE)
    time_spent = models.PositiveIntegerField(help_text="Time spent reading in seconds")
    scroll_depth = models.FloatField(help_text="Percentage of article scrolled")
    
    # User behavior
    came_from = models.URLField(blank=True)
    went_to = models.URLField(blank=True)
    device_type = models.CharField(max_length=50, blank=True)
    
    class Meta:
        db_table = 'user_engagement'
        indexes = [
            models.Index(fields=['timestamp', 'article']),
            models.Index(fields=['session_id', 'timestamp']),
            models.Index(fields=['user', 'timestamp']),
        ]
    
    def __str__(self):
        return f"Engagement: {self.article.title} ({self.time_spent}s)"