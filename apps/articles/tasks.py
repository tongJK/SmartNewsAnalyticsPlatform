from celery import shared_task
from django.db import transaction
import numpy as np
import logging
from apps.services.embedding_service import embedding_manager
from apps.services.multimodal_service import multimodal_service

logger = logging.getLogger('articles')


@shared_task(bind=True, max_retries=3)
def generate_embedding_task(self, article_id):
    """
    Generate embedding vector for a single article
    """
    try:
        from .models import Article
        
        article = Article.objects.get(pk=article_id)
        
        # Combine title and content for embedding
        text = f"{article.title} {article.content}"
        
        # Generate embedding using the embedding service
        embedding = embedding_manager.encode([text])[0]
        
        # Update article with embedding
        article.embedding = embedding.tolist()
        article.save(update_fields=['embedding'])
        
        logger.info(f"Generated embedding for article: {article.title} (ID: {article_id})")
        return f"Embedding generated for article {article_id}"
        
    except Exception as exc:
        logger.error(f"Error generating embedding for article {article_id}: {exc}")
        raise self.retry(exc=exc, countdown=60)


@shared_task
def generate_embeddings_batch(article_ids):
    """
    Generate embeddings for multiple articles in batch
    More efficient for bulk processing
    """
    try:
        from .models import Article
        
        articles = Article.objects.filter(id__in=article_ids, embedding__isnull=True)
        
        if not articles.exists():
            return "No articles to process"
        
        # Prepare texts for batch encoding
        texts = []
        article_list = list(articles)
        
        for article in article_list:
            text = f"{article.title} {article.content}"
            texts.append(text)
        
        # Batch encode for efficiency using embedding service
        embeddings = embedding_manager.encode(texts)
        
        # Bulk update with transaction
        with transaction.atomic():
            updates = []
            for article, embedding in zip(article_list, embeddings):
                article.embedding = embedding.tolist()
                updates.append(article)
            
            Article.objects.bulk_update(updates, ['embedding'], batch_size=100)
        
        logger.info(f"Generated embeddings for {len(article_list)} articles")
        return f"Generated embeddings for {len(article_list)} articles"
        
    except Exception as exc:
        logger.error(f"Error in batch embedding generation: {exc}")
        raise


@shared_task
def update_article_metrics():
    """
    Periodic task to update article metrics from view records
    Runs every hour to sync view counts
    """
    try:
        from .models import Article, ArticleView
        from django.db.models import Count
        
        # Get view counts from ArticleView records
        view_counts = ArticleView.objects.values('article').annotate(
            total_views=Count('id')
        )
        
        # Update articles with correct view counts
        updated_count = 0
        for item in view_counts:
            Article.objects.filter(pk=item['article']).update(
                views=item['total_views']
            )
            updated_count += 1
        
        logger.info(f"Updated metrics for {updated_count} articles")
        return f"Updated metrics for {updated_count} articles"
        
    except Exception as exc:
        logger.error(f"Error updating article metrics: {exc}")
        raise


@shared_task(bind=True, max_retries=3)
def generate_image_embedding_task(self, article_id):
    """
    Generate image embedding for an article with image_url
    """
    try:
        from .models import Article
        
        article = Article.objects.get(pk=article_id)
        
        if not article.image_url:
            return f"No image URL for article {article_id}"
        
        # Generate image embedding
        embedding = multimodal_service.generate_image_embedding(article.image_url)
        
        if embedding:
            article.image_embedding = embedding
            article.media_type = 'image' if article.media_type == 'text' else 'mixed'
            article.save(update_fields=['image_embedding', 'media_type'])
            
            logger.info(f"Generated image embedding for article: {article.title} (ID: {article_id})")
            return f"Image embedding generated for article {article_id}"
        else:
            logger.warning(f"Failed to generate image embedding for article {article_id}")
            return f"Failed to generate image embedding for article {article_id}"
        
    except Exception as exc:
        logger.error(f"Error generating image embedding for article {article_id}: {exc}")
        raise self.retry(exc=exc, countdown=60)


@shared_task(bind=True, max_retries=3)
def generate_video_embedding_task(self, article_id):
    """
    Generate video embedding for an article with video_url
    """
    try:
        from .models import Article
        
        article = Article.objects.get(pk=article_id)
        
        if not article.video_url:
            return f"No video URL for article {article_id}"
        
        # Generate video embedding
        embedding = multimodal_service.generate_video_embedding(article.video_url)
        
        if embedding:
            article.video_embedding = embedding
            article.media_type = 'video' if article.media_type == 'text' else 'mixed'
            article.save(update_fields=['video_embedding', 'media_type'])
            
            logger.info(f"Generated video embedding for article: {article.title} (ID: {article_id})")
            return f"Video embedding generated for article {article_id}"
        else:
            logger.warning(f"Failed to generate video embedding for article {article_id}")
            return f"Failed to generate video embedding for article {article_id}"
        
    except Exception as exc:
        logger.error(f"Error generating video embedding for article {article_id}: {exc}")
        raise self.retry(exc=exc, countdown=60)