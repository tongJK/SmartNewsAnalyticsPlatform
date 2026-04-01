from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.contrib.postgres.search import SearchVector
from .models import Article
from .tasks import generate_embedding_task
import logging

logger = logging.getLogger('articles')


@receiver(post_save, sender=Article)
def update_search_vector_post_save(sender, instance, created, **kwargs):
    """
    Update search vector after saving article
    Combines title and content for full-text search
    """
    if instance.title and instance.content:
        # Update search vector using raw SQL to avoid F() expression issues
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute(
                "UPDATE articles SET search_vector = to_tsvector('english', %s || ' ' || %s) WHERE id = %s",
                [instance.title, instance.content, instance.id]
            )
        logger.info(f"Updated search vector for article: {instance.title}")


@receiver(post_save, sender=Article)
def generate_embedding(sender, instance, created, **kwargs):
    """
    Generate embedding vector after article is saved
    Uses Celery task for async processing
    """
    if created or not instance.embedding:
        # For now, skip Celery task if Redis is not available
        try:
            generate_embedding_task.delay(instance.pk)
            logger.info(f"Queued embedding generation for article: {instance.title} (ID: {instance.pk})")
        except Exception as e:
            logger.warning(f"Could not queue embedding task for article {instance.pk}: {e}")
            logger.info(f"Skipping embedding generation for article: {instance.title} (ID: {instance.pk})")