# 🎨 Multimodal Search Guide

## Overview

The Smart News Analytics Platform now supports **multimodal search** across text, images, and videos using CLIP (Contrastive Language-Image Pre-training) embeddings.

## Features

- **Image-to-Image Search**: Upload an image to find visually similar articles
- **Text-to-Image Search**: Search for images using text descriptions
- **Video Search**: Find articles with similar video content
- **Cross-Modal Search**: Search across different media types

## Architecture

```
Text Query → CLIP Text Encoder → 512D Vector → Similarity Search
Image Upload → CLIP Image Encoder → 512D Vector → Similarity Search
Video File → Frame Sampling → CLIP Image Encoder → 512D Vector → Similarity Search
```

## Database Schema

```sql
-- Extended Article model with multimodal fields
ALTER TABLE articles ADD COLUMN image_embedding FLOAT[512];
ALTER TABLE articles ADD COLUMN video_embedding FLOAT[512];
ALTER TABLE articles ADD COLUMN image_url VARCHAR(200);
ALTER TABLE articles ADD COLUMN video_url VARCHAR(200);
ALTER TABLE articles ADD COLUMN media_type VARCHAR(20) DEFAULT 'text';

-- Index for media type filtering
CREATE INDEX idx_articles_media_type ON articles(media_type);
```

## API Endpoints

### 1. Image-to-Image Search

**POST** `/api/articles/search_by_image/`

Upload an image to find visually similar articles.

```bash
curl -X POST http://localhost:8000/api/articles/search_by_image/ \
  -F "image=@/path/to/image.jpg"
```

**Response:**
```json
{
  "results": [
    {
      "id": 1,
      "title": "Article Title",
      "image_url": "https://example.com/image.jpg",
      "similarity": 0.85,
      "media_type": "image"
    }
  ],
  "count": 1
}
```

### 2. Text-to-Image Search

**POST** `/api/articles/search_by_text_to_image/`

Search for images using text descriptions.

```bash
curl -X POST http://localhost:8000/api/articles/search_by_text_to_image/ \
  -H "Content-Type: application/json" \
  -d '{
    "query": "sunset over mountains"
  }'
```

**Response:**
```json
{
  "query": "sunset over mountains",
  "results": [
    {
      "id": 2,
      "title": "Beautiful Mountain Sunset",
      "image_url": "https://example.com/sunset.jpg",
      "similarity": 0.78,
      "media_type": "image"
    }
  ],
  "count": 1
}
```

## Management Commands

### Generate Multimodal Embeddings

```bash
# Generate all embeddings
python manage.py generate_multimodal_embeddings

# Generate only image embeddings
python manage.py generate_multimodal_embeddings --media-type image

# Generate only video embeddings
python manage.py generate_multimodal_embeddings --media-type video

# Force regenerate existing embeddings
python manage.py generate_multimodal_embeddings --force

# Custom batch size
python manage.py generate_multimodal_embeddings --batch-size 5
```

## Adding Media to Articles

### Via Django Admin

1. Open article in admin
2. Add `image_url` or `video_url`
3. Save article
4. Run embedding generation command

### Via API

```python
# Create article with image
article_data = {
    "title": "Article with Image",
    "content": "Article content...",
    "image_url": "https://example.com/image.jpg",
    "media_type": "image"
}

response = requests.post(
    "http://localhost:8000/api/articles/",
    json=article_data
)
```

### Programmatically

```python
from apps.articles.models import Article
from apps.articles.tasks import generate_image_embedding_task

# Create article
article = Article.objects.create(
    title="Test Article",
    content="Content...",
    image_url="https://example.com/test.jpg"
)

# Generate embedding asynchronously
generate_image_embedding_task.delay(article.id)
```

## Similarity Thresholds

| Search Type | Threshold | Reasoning |
|-------------|-----------|-----------|
| Image-to-Image | 0.7 | High precision for visual similarity |
| Text-to-Image | 0.6 | Lower threshold for cross-modal search |
| Video-to-Video | 0.65 | Balanced for frame-based comparison |

## Performance Considerations

### Vector Search Optimization

```sql
-- For large datasets, consider using specialized vector indexes
-- PostgreSQL with pgvector extension (future enhancement)
CREATE INDEX ON articles USING ivfflat (image_embedding vector_cosine_ops);
```

### Batch Processing

```python
# Process embeddings in batches to avoid memory issues
python manage.py generate_multimodal_embeddings --batch-size 10
```

### Caching

```python
# Cache frequently searched embeddings
from django.core.cache import cache

def cached_similarity_search(query_embedding, cache_key):
    results = cache.get(cache_key)
    if not results:
        results = perform_similarity_search(query_embedding)
        cache.set(cache_key, results, timeout=3600)
    return results
```

## Model Configuration

### CLIP Model Selection

The platform uses `openai/clip-vit-base-patch32` by default:

- **Size**: ~150MB
- **Dimensions**: 512
- **Speed**: Fast inference
- **Quality**: Good for general use

### Alternative Models

```python
# In multimodal_service.py, change model_name:
model_name = "openai/clip-vit-large-patch14"  # Higher quality, slower
model_name = "openai/clip-vit-base-patch16"   # Balanced option
```

## Use Cases

### 1. Content Discovery
- Find articles with similar visual themes
- Discover related visual content

### 2. Content Verification
- Check if an image has been used before
- Find duplicate or similar visual content

### 3. Visual Analytics
- Analyze trending visual patterns
- Group articles by visual similarity

### 4. Cross-Modal Search
- Search images using text descriptions
- Find articles that match visual concepts

## Error Handling

### Common Issues

**CLIP Model Not Available**
```bash
pip install torch transformers
```

**Image Processing Errors**
```bash
pip install Pillow opencv-python
```

**Memory Issues**
```python
# Reduce batch size
python manage.py generate_multimodal_embeddings --batch-size 5
```

### Graceful Degradation

```python
# Service handles missing dependencies gracefully
if not CLIP_AVAILABLE:
    logger.warning("CLIP not available. Install: pip install torch transformers")
    return None
```

## Future Enhancements

1. **pgvector Integration**: Use PostgreSQL pgvector for optimized vector search
2. **Audio Search**: Add audio embedding support
3. **Multi-Language CLIP**: Support for multilingual image-text matching
4. **Real-time Processing**: WebSocket-based real-time similarity updates
5. **Advanced Filtering**: Combine multimodal search with traditional filters

## Technical Details

### Embedding Generation Process

1. **Image Processing**: Load image → Resize → Normalize → CLIP encode
2. **Text Processing**: Tokenize → CLIP text encode → Normalize
3. **Video Processing**: Sample frames → Process each frame → Average embeddings
4. **Storage**: Store as PostgreSQL FLOAT array

### Similarity Calculation

```python
def cosine_similarity(vec1, vec2):
    dot_product = np.dot(vec1, vec2)
    norm1 = np.linalg.norm(vec1)
    norm2 = np.linalg.norm(vec2)
    return dot_product / (norm1 * norm2)
```

### Performance Metrics

- **Embedding Generation**: ~100ms per image
- **Similarity Search**: ~50ms for 1000 articles
- **Memory Usage**: ~2MB per 1000 embeddings
- **Storage**: ~2KB per embedding (512 floats)

---

**Ready to search across all media types! 🎨📹🔍**