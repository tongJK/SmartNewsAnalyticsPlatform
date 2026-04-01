# 📊 Smart News Analytics Platform - Data Pipeline Flow

## Complete Data Flow: From HTTP Request to Database Storage

```mermaid
graph TD
    A[HTTP POST Request] --> B[Django URL Router]
    B --> C[ArticleViewSet.create()]
    C --> D[ArticleCreateSerializer]
    D --> E{Validation}
    E -->|Valid| F[Article.save()]
    E -->|Invalid| G[Return 400 Error]
    F --> H[Database INSERT]
    H --> I[Django Signals Triggered]
    I --> J[update_search_vector_post_save]
    I --> K[generate_embedding]
    J --> L[Update PostgreSQL tsvector]
    K --> M[Queue Celery Task]
    M --> N[generate_embedding_task]
    N --> O[SentenceTransformer Processing]
    O --> P[Update Article.embedding]
    P --> Q[Analytics Pipeline]
    Q --> R[TimescaleDB Metrics]
```

## 🔄 Step-by-Step Breakdown

### 1. **HTTP Request Reception**
```bash
POST /api/articles/
Content-Type: application/json
{
  "title": "AI Revolution in Healthcare",
  "content": "Artificial intelligence is transforming medical diagnosis...",
  "author": "Dr. Smith",
  "category": "technology",
  "tags": ["AI", "healthcare", "technology"]
}
```

### 2. **Django View Processing**
**File**: `apps/articles/views.py`
```python
class ArticleViewSet(viewsets.ModelViewSet):
    def create(self, request, *args, **kwargs):
        # 1. Get appropriate serializer (ArticleCreateSerializer)
        serializer = self.get_serializer(data=request.data)
        
        # 2. Validate incoming data
        serializer.is_valid(raise_exception=True)
        
        # 3. Save to database
        self.perform_create(serializer)
        
        # 4. Return response
        return Response(serializer.data, status=201)
```

### 3. **Serializer Validation**
**File**: `apps/articles/serializers.py`
```python
class ArticleCreateSerializer(serializers.ModelSerializer):
    def validate_title(self, value):
        if len(value.strip()) < 10:
            raise ValidationError("Title must be at least 10 characters")
        return value.strip()
    
    def validate_content(self, value):
        if len(value.strip()) < 100:
            raise ValidationError("Content must be at least 100 characters")
        return value.strip()
```

**Validation Steps**:
- ✅ Title length >= 10 characters
- ✅ Content length >= 100 characters  
- ✅ Field type validation (CharField, TextField, etc.)
- ✅ Required fields present

### 4. **Model Save Operation**
**File**: `apps/articles/models.py`
```python
class Article(models.Model):
    def save(self, *args, **kwargs):
        # Set published_at if not provided
        if not self.published_at:
            self.published_at = timezone.now()
        
        # Call parent save method
        super().save(*args, **kwargs)
        
        # Log the operation
        logger.info(f"Article saved: {self.title} (ID: {self.pk})")
```

**Database Operations**:
1. **INSERT** into `articles` table
2. **Auto-generate** ID (primary key)
3. **Set timestamps** (created_at, updated_at)
4. **Apply indexes** (title, published_at, category, etc.)

### 5. **Django Signals (Post-Save Processing)**
**File**: `apps/articles/signals.py`

#### Signal 1: Update Search Vector
```python
@receiver(post_save, sender=Article)
def update_search_vector_post_save(sender, instance, created, **kwargs):
    # Update PostgreSQL tsvector for full-text search
    with connection.cursor() as cursor:
        cursor.execute(
            "UPDATE articles SET search_vector = to_tsvector('english', %s || ' ' || %s) WHERE id = %s",
            [instance.title, instance.content, instance.id]
        )
```

**What happens**:
- Combines `title + content` into searchable text
- Creates PostgreSQL `tsvector` for full-text search
- Updates `search_vector` field with GIN index

#### Signal 2: Generate Embedding
```python
@receiver(post_save, sender=Article)
def generate_embedding(sender, instance, created, **kwargs):
    if created or not instance.embedding:
        # Queue async task for embedding generation
        generate_embedding_task.delay(instance.pk)
```

**What happens**:
- Queues Celery task for ML processing
- Avoids blocking the HTTP response
- Handles Redis/Celery unavailability gracefully

### 6. **Background Processing (Celery Tasks)**
**File**: `apps/articles/tasks.py`

```python
@shared_task(bind=True, max_retries=3)
def generate_embedding_task(self, article_id):
    # 1. Load the article
    article = Article.objects.get(pk=article_id)
    
    # 2. Combine title + content
    text = f"{article.title} {article.content}"
    
    # 3. Generate 768-dimensional vector using SentenceTransformer
    embedding = model.encode(text, normalize_embeddings=True)
    
    # 4. Save embedding to database
    article.embedding = embedding.tolist()
    article.save(update_fields=['embedding'])
```

**ML Processing**:
- Uses `sentence-transformers/all-MiniLM-L6-v2` model
- Generates 768-dimensional vector
- Normalizes embeddings for cosine similarity
- Stores as PostgreSQL ArrayField

### 7. **Database Storage Architecture**

#### Articles Table Structure
```sql
CREATE TABLE articles (
    id SERIAL PRIMARY KEY,
    title VARCHAR(500) NOT NULL,
    content TEXT NOT NULL,
    summary TEXT,
    author VARCHAR(200),
    source_url TEXT,
    published_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE,
    embedding FLOAT[768],  -- Vector embeddings
    search_vector TSVECTOR, -- Full-text search
    views INTEGER DEFAULT 0,
    shares INTEGER DEFAULT 0,
    category VARCHAR(100),
    tags TEXT[],           -- Array field
    language VARCHAR(10) DEFAULT 'en'
);
```

#### Indexes for Performance
```sql
-- Full-text search (GIN index)
CREATE INDEX idx_articles_search_vector ON articles USING GIN(search_vector);

-- Tag search (GIN index)  
CREATE INDEX idx_articles_tags ON articles USING GIN(tags);

-- Time-based queries
CREATE INDEX idx_articles_published_category ON articles(published_at, category);

-- Analytics queries
CREATE INDEX idx_articles_views_published ON articles(views, published_at);
```

### 8. **Analytics Pipeline Integration**

#### View Tracking
```python
def retrieve(self, request, *args, **kwargs):
    instance = self.get_object()
    
    # Track individual view
    ArticleView.objects.create(
        article=instance,
        user=request.user if request.user.is_authenticated else None,
        ip_address=self._get_client_ip(request),
        user_agent=request.META.get('HTTP_USER_AGENT', ''),
        referrer=request.META.get('HTTP_REFERER', '')
    )
    
    # Increment counter
    instance.increment_views()
```

#### TimescaleDB Integration
- `ArticleView` records → TimescaleDB hypertable
- Time-series analytics on view patterns
- Real-time dashboard updates via WebSockets

## 🚀 Performance Optimizations

### 1. **Database Level**
- **GIN indexes** for array fields and full-text search
- **Composite indexes** for common query patterns
- **Partial indexes** for filtered queries
- **Connection pooling** via pgbouncer

### 2. **Application Level**
- **Async task processing** (Celery) for ML operations
- **Batch embedding generation** for bulk imports
- **Query optimization** with select_related/prefetch_related
- **Caching** with Redis for frequent queries

### 3. **Search Performance**
- **Full-text search**: O(log n) with GIN indexes
- **Vector search**: O(n) but limited to 1000 articles
- **Hybrid search**: Combines both with weighted scoring

## 🔍 Search Pipeline Deep Dive

### Full-Text Search Flow
```python
def _full_text_search(self, query, category=None, language=None, limit=20):
    search_query = SearchQuery(query)  # Parse query
    
    queryset = Article.objects.filter(
        search_vector=search_query      # Use GIN index
    ).annotate(
        rank=SearchRank(F('search_vector'), search_query)  # Relevance scoring
    ).order_by('-rank')
    
    return queryset[:limit]
```

### Semantic Search Flow
```python
def _semantic_search(self, query, category=None, language=None, limit=20):
    # 1. Generate query embedding
    model = SentenceTransformer('all-MiniLM-L6-v2')
    query_embedding = model.encode(query, normalize_embeddings=True)
    
    # 2. Get articles with embeddings
    queryset = Article.objects.exclude(embedding__isnull=True)
    
    # 3. Calculate cosine similarity
    articles_with_scores = []
    for article in queryset[:1000]:  # Performance limit
        similarity = cosine_similarity(query_embedding, article.embedding)
        if similarity > 0.3:  # Relevance threshold
            article.similarity_score = similarity
            articles_with_scores.append(article)
    
    # 4. Sort by similarity
    return sorted(articles_with_scores, key=lambda x: x.similarity_score, reverse=True)[:limit]
```

## 📊 Monitoring & Observability

### Logging Points
1. **Article creation**: Title, ID, timestamp
2. **Search vector updates**: Success/failure
3. **Embedding generation**: Queue status, processing time
4. **Search operations**: Query, type, result count, performance
5. **View tracking**: IP, user agent, referrer

### Metrics Tracked
- **Article creation rate**: Articles/hour
- **Search performance**: Query time, result relevance
- **Embedding generation**: Success rate, processing time
- **View patterns**: Popular articles, traffic sources
- **Database performance**: Query execution time, index usage

## 🛠️ Error Handling & Resilience

### Graceful Degradation
- **Redis unavailable**: Skip Celery tasks, log warning
- **ML model loading fails**: Return text search only
- **Database timeout**: Return cached results
- **Embedding generation fails**: Retry with exponential backoff

### Data Consistency
- **Atomic transactions** for related operations
- **Signal handling** with try/catch blocks
- **Task retries** with max attempts
- **Database constraints** to prevent invalid data

This pipeline ensures **high performance**, **scalability**, and **reliability** while providing advanced search capabilities through PostgreSQL's full-text search and ML-powered semantic search.