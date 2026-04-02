"""
Management command to generate image and video embeddings for articles
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from apps.articles.models import Article
from apps.services.multimodal_service import multimodal_service
import logging

logger = logging.getLogger('articles')


class Command(BaseCommand):
    help = 'Generate image and video embeddings for articles'

    def add_arguments(self, parser):
        parser.add_argument(
            '--batch-size',
            type=int,
            default=10,
            help='Number of articles to process in each batch'
        )
        parser.add_argument(
            '--media-type',
            choices=['image', 'video', 'all'],
            default='all',
            help='Type of media embeddings to generate'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Regenerate embeddings even if they already exist'
        )

    def handle(self, *args, **options):
        batch_size = options['batch_size']
        media_type = options['media_type']
        force = options['force']

        self.stdout.write(f"Generating {media_type} embeddings...")

        # Get articles that need embeddings
        if media_type == 'image' or media_type == 'all':
            self.process_image_embeddings(batch_size, force)
        
        if media_type == 'video' or media_type == 'all':
            self.process_video_embeddings(batch_size, force)

        self.stdout.write(
            self.style.SUCCESS('Successfully generated multimodal embeddings')
        )

    def process_image_embeddings(self, batch_size, force):
        """Process image embeddings"""
        if force:
            articles = Article.objects.exclude(image_url='')
        else:
            articles = Article.objects.exclude(image_url='').filter(
                image_embedding__isnull=True
            )

        total = articles.count()
        if total == 0:
            self.stdout.write("No articles need image embeddings")
            return

        self.stdout.write(f"Processing {total} articles for image embeddings...")

        processed = 0
        for i in range(0, total, batch_size):
            batch = articles[i:i + batch_size]
            
            with transaction.atomic():
                for article in batch:
                    try:
                        embedding = multimodal_service.generate_image_embedding(
                            article.image_url
                        )
                        
                        if embedding:
                            article.image_embedding = embedding
                            article.media_type = 'image' if article.media_type == 'text' else 'mixed'
                            article.save(update_fields=['image_embedding', 'media_type'])
                            processed += 1
                            
                            self.stdout.write(f"✓ Generated image embedding for: {article.title}")
                        else:
                            self.stdout.write(
                                self.style.WARNING(f"✗ Failed to generate image embedding for: {article.title}")
                            )
                    
                    except Exception as e:
                        self.stdout.write(
                            self.style.ERROR(f"✗ Error processing {article.title}: {e}")
                        )

        self.stdout.write(f"Processed {processed}/{total} image embeddings")

    def process_video_embeddings(self, batch_size, force):
        """Process video embeddings"""
        if force:
            articles = Article.objects.exclude(video_url='')
        else:
            articles = Article.objects.exclude(video_url='').filter(
                video_embedding__isnull=True
            )

        total = articles.count()
        if total == 0:
            self.stdout.write("No articles need video embeddings")
            return

        self.stdout.write(f"Processing {total} articles for video embeddings...")

        processed = 0
        for i in range(0, total, batch_size):
            batch = articles[i:i + batch_size]
            
            with transaction.atomic():
                for article in batch:
                    try:
                        embedding = multimodal_service.generate_video_embedding(
                            article.video_url
                        )
                        
                        if embedding:
                            article.video_embedding = embedding
                            article.media_type = 'video' if article.media_type == 'text' else 'mixed'
                            article.save(update_fields=['video_embedding', 'media_type'])
                            processed += 1
                            
                            self.stdout.write(f"✓ Generated video embedding for: {article.title}")
                        else:
                            self.stdout.write(
                                self.style.WARNING(f"✗ Failed to generate video embedding for: {article.title}")
                            )
                    
                    except Exception as e:
                        self.stdout.write(
                            self.style.ERROR(f"✗ Error processing {article.title}: {e}")
                        )

        self.stdout.write(f"Processed {processed}/{total} video embeddings")