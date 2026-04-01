import os
from celery import Celery
from django.conf import settings

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'SmartNewsAnalyticsPlatform.settings')

app = Celery('SmartNewsAnalyticsPlatform')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps.
app.autodiscover_tasks()

# Celery Beat Schedule for periodic tasks
app.conf.beat_schedule = {
    'update-article-metrics': {
        'task': 'apps.articles.tasks.update_article_metrics',
        'schedule': 3600.0,  # Run every hour
    },
    'generate-daily-stats': {
        'task': 'apps.analytics.tasks.generate_daily_stats',
        'schedule': 86400.0,  # Run daily at midnight
    },
    'detect-trending-topics': {
        'task': 'apps.analytics.tasks.detect_trending_topics_task',
        'schedule': 1800.0,  # Run every 30 minutes
    },
}

app.conf.timezone = 'UTC'

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')