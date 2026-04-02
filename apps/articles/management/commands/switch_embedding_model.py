"""
Management command to switch embedding models and reindex articles
"""
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from apps.articles.models import Article
from apps.services.embedding_service import EmbeddingModelConfig, embedding_manager
from apps.articles.tasks import generate_embeddings_batch
import os


class Command(BaseCommand):
    help = 'Switch embedding model and optionally reindex all articles'
    
    def add_arguments(self, parser):
        parser.add_argument(
            'model_key',
            nargs='?',
            default='list',
            help='Model key to switch to (fast, balanced, accurate, qa, search, multilingual) or "list" to show available models'
        )
        parser.add_argument(
            '--reindex',
            action='store_true',
            help='Reindex all articles with the new model'
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=100,
            help='Batch size for reindexing (default: 100)'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force reindexing even if articles already have embeddings'
        )
    
    def handle(self, *args, **options):
        model_key = options['model_key']
        
        if model_key == 'list':
            self.list_models()
            return
        
        if model_key not in EmbeddingModelConfig.MODELS:
            raise CommandError(f'Invalid model key: {model_key}. Use "list" to see available models.')
        
        # Show current model info
        current_info = embedding_manager.get_model_info()
        self.stdout.write(f"Current model: {current_info['name']} ({current_info['description']})")
        
        # Switch to new model
        new_info = embedding_manager.get_model_info(model_key)
        self.stdout.write(f"Switching to: {new_info['name']} ({new_info['description']})")
        
        # Update environment variable (for this session)
        os.environ['EMBEDDING_MODEL'] = model_key
        
        # Test the new model
        try:
            test_embedding = embedding_manager.encode(["test text"], model_key=model_key)
            self.stdout.write(
                self.style.SUCCESS(
                    f"✅ Model loaded successfully. Embedding dimensions: {len(test_embedding[0])}"
                )
            )
        except Exception as e:
            raise CommandError(f"Failed to load model: {e}")
        
        if options['reindex']:
            self.reindex_articles(model_key, options['batch_size'], options['force'])
        else:
            self.stdout.write(
                self.style.WARNING(
                    "⚠️  Model switched but articles not reindexed. Use --reindex to update embeddings."
                )
            )
            self.stdout.write("To reindex later, run:")
            self.stdout.write(f"  python manage.py switch_embedding_model {model_key} --reindex")
    
    def list_models(self):
        """List all available embedding models"""
        self.stdout.write("\n📋 Available Embedding Models:\n")
        
        current_info = embedding_manager.get_model_info()
        current_key = next(
            (key for key, config in EmbeddingModelConfig.MODELS.items() 
             if config['name'] == current_info['name']), 
            'custom'
        )
        
        for key, config in EmbeddingModelConfig.MODELS.items():
            status = " (CURRENT)" if key == current_key else ""
            self.stdout.write(
                f"  {key:12} | {config['name']:30} | {config['size_mb']:3}MB | {config['dimensions']} dims{status}"
            )
            self.stdout.write(f"             | {config['description']}")
            self.stdout.write("")
        
        self.stdout.write("Usage:")
        self.stdout.write("  python manage.py switch_embedding_model <model_key> [--reindex]")
        self.stdout.write("  python manage.py switch_embedding_model fast --reindex")
    
    def reindex_articles(self, model_key, batch_size, force):
        """Reindex all articles with the new model"""
        self.stdout.write("\n🔄 Starting article reindexing...")
        
        # Get articles to reindex
        if force:
            articles = Article.objects.all()
            self.stdout.write("Reindexing ALL articles (--force flag used)")
        else:
            articles = Article.objects.filter(embedding__isnull=True)
            self.stdout.write("Reindexing articles without embeddings")
        
        total_count = articles.count()
        if total_count == 0:
            self.stdout.write(self.style.SUCCESS("✅ No articles to reindex."))
            return
        
        self.stdout.write(f"Found {total_count} articles to reindex")
        
        # Process in batches
        article_ids = list(articles.values_list('id', flat=True))
        batches = [article_ids[i:i + batch_size] for i in range(0, len(article_ids), batch_size)]
        
        self.stdout.write(f"Processing {len(batches)} batches of {batch_size} articles each...")
        
        # Clear existing embeddings if force reindex
        if force:
            with transaction.atomic():
                Article.objects.filter(id__in=article_ids).update(embedding=None)
            self.stdout.write("Cleared existing embeddings")
        
        # Queue Celery tasks for each batch
        task_ids = []
        for i, batch in enumerate(batches, 1):
            try:
                task = generate_embeddings_batch.delay(batch)
                task_ids.append(task.id)
                self.stdout.write(f"Queued batch {i}/{len(batches)} (Task ID: {task.id})")
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"Failed to queue batch {i}: {e}")
                )
        
        self.stdout.write(
            self.style.SUCCESS(
                f"\n✅ Queued {len(task_ids)} reindexing tasks. "
                f"Monitor progress in Celery logs."
            )
        )
        
        # Show monitoring commands
        self.stdout.write("\n📊 Monitor progress:")
        self.stdout.write("  # Check task status")
        for task_id in task_ids[:3]:  # Show first 3 task IDs
            self.stdout.write(f"  celery -A SmartNewsAnalyticsPlatform inspect active | grep {task_id}")
        if len(task_ids) > 3:
            self.stdout.write(f"  ... and {len(task_ids) - 3} more tasks")
        
        self.stdout.write("\n  # Check embedding progress")
        self.stdout.write("  python manage.py shell -c \"from apps.articles.models import Article; print(f'Embedded: {Article.objects.exclude(embedding__isnull=True).count()}/{Article.objects.count()}')\"")
        
        # Update environment permanently (reminder)
        self.stdout.write(
            self.style.WARNING(
                f"\n⚠️  Remember to update your .env file:\n"
                f"  EMBEDDING_MODEL={model_key}"
            )
        )