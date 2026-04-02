# Generated migration for multimodal search fields

from django.db import migrations
from django.contrib.postgres.fields import ArrayField
import django.db.models as models


class Migration(migrations.Migration):

    dependencies = [
        ('articles', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='article',
            name='image_embedding',
            field=ArrayField(
                models.FloatField(),
                blank=True,
                help_text='CLIP image embedding for visual search',
                null=True,
                size=512
            ),
        ),
        migrations.AddField(
            model_name='article',
            name='video_embedding',
            field=ArrayField(
                models.FloatField(),
                blank=True,
                help_text='Video frame embedding for video search',
                null=True,
                size=512
            ),
        ),
        migrations.AddField(
            model_name='article',
            name='image_url',
            field=models.URLField(blank=True, help_text='Featured image URL'),
        ),
        migrations.AddField(
            model_name='article',
            name='video_url',
            field=models.URLField(blank=True, help_text='Video content URL'),
        ),
        migrations.AddField(
            model_name='article',
            name='media_type',
            field=models.CharField(
                choices=[
                    ('text', 'Text Only'),
                    ('image', 'With Image'),
                    ('video', 'With Video'),
                    ('mixed', 'Mixed Media')
                ],
                db_index=True,
                default='text',
                max_length=20
            ),
        ),
        migrations.AddIndex(
            model_name='article',
            index=models.Index(fields=['media_type'], name='articles_article_media_type_idx'),
        ),
    ]