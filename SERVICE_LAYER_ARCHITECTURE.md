# 🏗️ Service Layer Architecture

## Overview

The service layer provides a clean separation between business logic and presentation logic, following Domain-Driven Design (DDD) principles. This architecture makes the codebase more maintainable, testable, and scalable.

## 📁 Directory Structure

```
apps/
├── services/                    # Service Layer (Business Logic)
│   ├── __init__.py
│   ├── embedding_service.py     # ML/AI embedding operations
│   ├── article_service.py       # Article business logic
│   └── search_service.py        # Search functionality
├── articles/                    # Articles App
│   ├── models.py               # Data models
│   ├── views.py                # API endpoints (thin controllers)
│   ├── serializers.py          # Data serialization
│   └── ...
└── analytics/                   # Analytics App
    └── ...
```

## 🎯 Service Layer Principles

### 1. **Single Responsibility**
Each service handles one domain area:
- `EmbeddingService` → ML/AI operations
- `ArticleService` → Article business logic
- `SearchService` → Search functionality

### 2. **Dependency Inversion**
Services depend on abstractions, not concrete implementations:
```python
# Good: Service uses abstract embedding manager
class ArticleService:
    @staticmethod
    def create_article(title, content, **kwargs):
        # Business logic here
        embedding_manager.encode([content])  # Abstract interface
```

### 3. **Stateless Operations**
Services are stateless and use static methods:
```python
class ArticleService:
    @staticmethod
    def track_article_view(article, user=None, **kwargs):
        # No instance state, pure business logic
```

## 🔧 Service Implementations

### EmbeddingService (`apps/services/embedding_service.py`)

**Purpose**: Manage ML model operations and embedding generation

**Key Features**:
- ✅ Configurable model selection (fast, balanced, accurate, etc.)
- ✅ Singleton pattern for model caching
- ✅ Environment-based configuration
- ✅ Easy model switching without code changes

**Usage**:
```python
from apps.services.embedding_service import embedding_manager

# Generate embeddings
embeddings = embedding_manager.encode(["text1", "text2"])

# Switch models via environment
os.environ['EMBEDDING_MODEL'] = 'accurate'
model = embedding_manager.get_model()
```

### ArticleService (`apps/services/article_service.py`)

**Purpose**: Handle article-related business logic

**Key Features**:
- ✅ Article creation with auto-summary generation
- ✅ Smart view tracking (prevents duplicate views)
- ✅ Atomic share counting
- ✅ Similarity-based recommendations
- ✅ Bulk operations

**Usage**:
```python
from apps.services.article_service import ArticleService

# Create article with business logic
article = ArticleService.create_article(
    title="AI in Healthcare",
    content="Long content...",
    category="technology"
)

# Track views with duplicate prevention
ArticleService.track_article_view(
    article=article,
    user=request.user,
    ip_address="192.168.1.1"
)

# Get similar articles
similar = ArticleService.get_similar_articles(article, limit=5)
```

### SearchService (`apps/services/search_service.py`)

**Purpose**: Provide advanced search capabilities

**Key Features**:
- ✅ Full-text search using PostgreSQL tsvector
- ✅ Semantic search using embeddings
- ✅ Hybrid search with weighted scoring
- ✅ Search suggestions and analytics
- ✅ Unified search interface

**Usage**:
```python
from apps.services.search_service import SearchService

# Unified search interface
results = SearchService.search(
    query="artificial intelligence",
    search_type="hybrid",
    category="technology",
    limit=20
)

# Specific search types
text_results = SearchService.full_text_search("AI healthcare")
semantic_results = SearchService.semantic_search("machine learning")
```

## 🔄 Integration with Views

Views become thin controllers that orchestrate service calls:

```python
# Before: Fat controller with business logic
class ArticleViewSet(viewsets.ModelViewSet):
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        
        # Business logic mixed with controller logic
        if request.META.get('HTTP_X_FORWARDED_FOR'):
            ip = request.META['HTTP_X_FORWARDED_FOR'].split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        
        ArticleView.objects.create(
            article=instance,
            user=request.user if request.user.is_authenticated else None,
            ip_address=ip,
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            referrer=request.META.get('HTTP_REFERER', '')
        )
        
        instance.views = F('views') + 1
        instance.save(update_fields=['views'])
        
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

# After: Thin controller using service layer
class ArticleViewSet(viewsets.ModelViewSet):
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        
        # Delegate business logic to service
        ArticleService.track_article_view(
            article=instance,
            user=request.user if request.user.is_authenticated else None,
            ip_address=self._get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            referrer=request.META.get('HTTP_REFERER', '')
        )
        
        serializer = self.get_serializer(instance)
        return Response(serializer.data)
```

## 🧪 Testing Benefits

Service layer makes testing much easier:

```python
# Test business logic in isolation
def test_article_creation():
    article = ArticleService.create_article(
        title="Test Article",
        content="Test content for article creation"
    )
    
    assert article.title == "Test Article"
    assert article.summary  # Auto-generated
    assert article.published_at  # Auto-set

def test_duplicate_view_prevention():
    article = Article.objects.create(title="Test", content="Test")
    
    # First view should be tracked
    view1 = ArticleService.track_article_view(
        article=article, 
        ip_address="192.168.1.1"
    )
    assert view1 is not None
    
    # Duplicate view within 1 hour should be ignored
    view2 = ArticleService.track_article_view(
        article=article, 
        ip_address="192.168.1.1"
    )
    assert view2 is None
```

## 🚀 Performance Benefits

### 1. **Caching at Service Level**
```python
class EmbeddingModelManager:
    _instance = None
    _model = None  # Cached model instance
    
    def get_model(self):
        if self._model is None:
            self._model = SentenceTransformer(model_name)
        return self._model
```

### 2. **Batch Operations**
```python
class ArticleService:
    @staticmethod
    def bulk_update_embeddings(article_ids, batch_size=100):
        # Process in batches for efficiency
        batches = [article_ids[i:i + batch_size] for i in range(0, len(article_ids), batch_size)]
        return [generate_embeddings_batch.delay(batch) for batch in batches]
```

### 3. **Atomic Operations**
```python
class ArticleService:
    @staticmethod
    def increment_shares(article_id):
        # Atomic database operation
        return Article.objects.filter(pk=article_id).update(shares=F('shares') + 1)
```

## 🔧 Configuration Management

Services use environment-based configuration:

```python
# .env
EMBEDDING_MODEL=fast          # Development
EMBEDDING_MODEL=balanced      # Staging  
EMBEDDING_MODEL=accurate      # Production

# Service automatically picks up configuration
embedding_manager.get_model()  # Uses EMBEDDING_MODEL from .env
```

## 📊 Monitoring and Logging

Services include comprehensive logging:

```python
class ArticleService:
    @staticmethod
    def create_article(title, content, **kwargs):
        article = Article.objects.create(...)
        logger.info(f"Article created: {article.title} (ID: {article.id})")
        return article
    
    @staticmethod
    def track_article_view(article, **kwargs):
        view = ArticleView.objects.create(...)
        logger.info(f"Article view tracked: {article.title} (ID: {article.id})")
        return view
```

## 🔮 Future Extensions

The service layer makes it easy to add new features:

### 1. **Caching Service**
```python
class CacheService:
    @staticmethod
    def get_cached_search_results(query, search_type):
        # Redis-based search result caching
        pass
```

### 2. **Notification Service**
```python
class NotificationService:
    @staticmethod
    def notify_new_article(article):
        # Send notifications to subscribers
        pass
```

### 3. **Analytics Service**
```python
class AnalyticsService:
    @staticmethod
    def track_user_behavior(user, action, metadata):
        # Advanced user behavior tracking
        pass
```

## 🎯 Best Practices

### 1. **Keep Services Stateless**
```python
# Good: Stateless service
class ArticleService:
    @staticmethod
    def create_article(title, content):
        return Article.objects.create(title=title, content=content)

# Bad: Stateful service
class ArticleService:
    def __init__(self):
        self.current_user = None  # State!
```

### 2. **Use Dependency Injection**
```python
# Good: Inject dependencies
class ArticleService:
    @staticmethod
    def create_article(title, content, embedding_service=None):
        embedding_service = embedding_service or embedding_manager
        # Use injected service
```

### 3. **Handle Errors Gracefully**
```python
class ArticleService:
    @staticmethod
    def track_article_view(article, **kwargs):
        try:
            return ArticleView.objects.create(...)
        except Exception as e:
            logger.error(f"Error tracking view: {e}")
            return None  # Graceful degradation
```

### 4. **Document Business Rules**
```python
class ArticleService:
    @staticmethod
    def track_article_view(article, ip_address=None, **kwargs):
        """
        Track article view with business logic:
        - Prevents duplicate views from same IP within 1 hour
        - Increments view counter atomically
        - Logs all view attempts for analytics
        """
```

This service layer architecture provides a solid foundation for scaling the Smart News Analytics Platform while maintaining clean, testable, and maintainable code.