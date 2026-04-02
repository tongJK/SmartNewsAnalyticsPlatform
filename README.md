# 📊 Smart News Analytics Platform

A modern news analytics platform built with Django and PostgreSQL advanced features including TimescaleDB, vector search, and full-text search.

## 🚀 Features

### Core Functionality
- **Article Management**: CRUD operations with rich metadata
- **Advanced Search**: Full-text, semantic (vector), and hybrid search
- **Real-time Analytics**: Live dashboards with WebSocket updates
- **Time-series Analysis**: Historical trends and patterns
- **Recommendation Engine**: Semantic similarity-based recommendations

### PostgreSQL Advanced Features
- **TimescaleDB**: Time-series data for analytics
- **Vector Search**: Semantic search using embeddings
- **Full-text Search**: PostgreSQL tsvector with GIN indexes
- **Advanced Indexing**: Optimized for high-performance queries

### Architecture
- **Django + DRF**: REST API backend
- **Service Layer**: Clean business logic separation
- **Celery**: Async task processing
- **Redis**: Caching and message broker
- **WebSockets**: Real-time updates
- **Docker**: Containerized deployment
- **ML Models**: Configurable embedding models for semantic search

## 📋 Prerequisites

- Python 3.12+
- Docker & Docker Compose
- PostgreSQL 15+ (with TimescaleDB)
- Redis

## 🛠️ Quick Start

### 1. Clone and Setup

```bash
git clone <repository-url>
cd SmartNewsAnalyticsPlatform

# Copy environment variables
cp .env.example .env
# Edit .env with your settings
```

### 2. Start with Docker

```bash
# Start all services
docker-compose up -d

# Check services are running
docker-compose ps
```

### 3. Initialize Database

```bash
# Run migrations
docker-compose exec web python manage.py migrate

# Create superuser
docker-compose exec web python manage.py createsuperuser

# Load sample data (optional)
docker-compose exec web python manage.py load_sample_data

# Generate embeddings for semantic search
docker-compose exec web python manage.py switch_embedding_model fast --reindex
```

### 4. Access the Application

- **API**: http://localhost:8000/api/
- **Admin**: http://localhost:8000/admin/
- **Health Check**: http://localhost:8000/api/health/

## 📚 API Endpoints

### Articles
```
GET    /api/articles/                    # List articles
POST   /api/articles/                    # Create article
GET    /api/articles/{id}/               # Get article details
PUT    /api/articles/{id}/               # Update article
DELETE /api/articles/{id}/               # Delete article
POST   /api/articles/search/             # Search articles
GET    /api/articles/{id}/recommend/     # Get recommendations
POST   /api/articles/{id}/share/         # Track share
GET    /api/articles/trending/           # Get trending articles
```

### Analytics
```
GET    /api/analytics/dashboard/         # Dashboard overview
GET    /api/analytics/trending/          # Trending topics
GET    /api/analytics/category_performance/  # Category stats
GET    /api/analytics/traffic_patterns/  # Traffic patterns
GET    /api/articles/{id}/timeseries/    # Article time-series
POST   /api/articles/{id}/predict/       # Engagement prediction
```

### WebSocket Endpoints
```
ws://localhost:8000/ws/analytics/dashboard/        # Real-time dashboard
ws://localhost:8000/ws/analytics/article/{id}/     # Article metrics
```

## 🤖 Embedding Models & Configuration

### Available Models

The platform supports multiple embedding models optimized for different use cases:

| Model | Size | Dimensions | Speed | Quality | Best For |
|-------|------|------------|-------|---------|----------|
| `fast` | 23MB | 384 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | General purpose, development |
| `balanced` | 33MB | 384 | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | Production balance |
| `accurate` | 420MB | 768 | ⭐⭐ | ⭐⭐⭐⭐⭐ | High accuracy needs |
| `qa` | 23MB | 384 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | Q&A systems |
| `search` | 23MB | 384 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | Search/retrieval |
| `multilingual` | 470MB | 384 | ⭐⭐ | ⭐⭐⭐⭐ | Multi-language support |

### Model Management

```bash
# List available models
python manage.py switch_embedding_model list

# Switch to a different model
python manage.py switch_embedding_model balanced

# Switch and reindex all articles
python manage.py switch_embedding_model accurate --reindex

# Force reindex with custom batch size
python manage.py switch_embedding_model fast --reindex --force --batch-size 50
```

### Environment Configuration

```bash
# .env
EMBEDDING_MODEL=fast          # Development
EMBEDDING_MODEL=balanced      # Staging
EMBEDDING_MODEL=accurate      # Production
```

## 🏗️ Service Layer Architecture

The platform follows clean architecture principles with a dedicated service layer:

```
Views (Controllers) → Services (Business Logic) → Models (Data Layer)
```

### Service Classes

- **EmbeddingService** (`apps/services/embedding_service.py`): ML model management
- **ArticleService** (`apps/services/article_service.py`): Article business logic
- **SearchService** (`apps/services/search_service.py`): Advanced search functionality

### Benefits

- ✅ **Clean separation** of concerns
- ✅ **Testable** business logic
- ✅ **Reusable** across different interfaces
- ✅ **Maintainable** and scalable code

## 🔍 Search Examples

### Full-text Search
```bash
curl -X POST http://localhost:8000/api/articles/search/ \
  -H "Content-Type: application/json" \
  -d '{
    "query": "artificial intelligence",
    "search_type": "text",
    "limit": 10
  }'
```

### Semantic Search
```bash
curl -X POST http://localhost:8000/api/articles/search/ \
  -H "Content-Type: application/json" \
  -d '{
    "query": "machine learning algorithms",
    "search_type": "semantic",
    "category": "technology",
    "limit": 5
  }'
```

### Hybrid Search
```bash
curl -X POST http://localhost:8000/api/articles/search/ \
  -H "Content-Type: application/json" \
  -d '{
    "query": "climate change solutions",
    "search_type": "hybrid",
    "limit": 20
  }'
```

## 🏗️ Architecture Overview

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   Django API    │    │   PostgreSQL    │
│   (Optional)    │◄──►│   + DRF         │◄──►│   + TimescaleDB │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │
                              ▼
                       ┌─────────────────┐    ┌─────────────────┐
                       │     Celery      │◄──►│     Redis       │
                       │   (Workers)     │    │   (Broker)      │
                       └─────────────────┘    └─────────────────┘
```

### Key Components

1. **Articles App**: Core article management and search
2. **Analytics App**: Time-series analytics and dashboards
3. **Users App**: User management and preferences
4. **Service Layer**: Business logic (ArticleService, SearchService, EmbeddingService)
5. **Celery Tasks**: Background processing (embeddings, analytics)
6. **WebSocket Consumers**: Real-time updates

## 🔧 Development

### Local Development Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -e .

# Set up local PostgreSQL with TimescaleDB
# (See docker-compose.yml for reference)

# Run migrations
python manage.py migrate

# Start development server
python manage.py runserver

# In separate terminals:
celery -A SmartNewsAnalyticsPlatform worker --loglevel=info
celery -A SmartNewsAnalyticsPlatform beat --loglevel=info
```

### Database Migrations

```bash
# Create migrations
python manage.py makemigrations

# Apply migrations
python manage.py migrate

# Create TimescaleDB hypertables
python manage.py setup_timescaledb
```

### Running Tests

```bash
# Run all tests
python manage.py test

# Run specific app tests
python manage.py test apps.articles
python manage.py test apps.analytics

# Run with coverage
coverage run --source='.' manage.py test
coverage report
```

## 📊 Performance Optimization

### Database Indexes
- **Articles**: GIN indexes for full-text and array fields
- **Metrics**: Time-based partitioning with TimescaleDB
- **Embeddings**: Custom similarity functions

### Caching Strategy
- **Redis**: API response caching
- **Database**: Query optimization with select_related/prefetch_related
- **Embeddings**: Batch processing for efficiency

### Monitoring
- **Health Checks**: `/api/health/` endpoint
- **Logging**: Structured logging with rotation
- **Metrics**: Real-time dashboard monitoring

## 🚀 Production Deployment

### Environment Variables
```bash
# Database
DATABASE_URL=postgresql://user:pass@host:5432/dbname
POSTGRES_DB=smart_news_prod
POSTGRES_USER=smart_news_user
POSTGRES_PASSWORD=secure_password

# Redis
REDIS_URL=redis://redis-host:6379/0

# Django
SECRET_KEY=your-secret-key
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,api.yourdomain.com

# Celery
CELERY_BROKER_URL=redis://redis-host:6379/0
CELERY_RESULT_BACKEND=redis://redis-host:6379/0

# Embedding Model
EMBEDDING_MODEL=fast          # Options: fast, balanced, accurate, qa, search, multilingual
```

### Docker Production
```bash
# Build production image
docker build -t smart-news-analytics .

# Run with production settings
docker-compose -f docker-compose.prod.yml up -d
```

### Scaling Considerations
- **Database**: Read replicas for analytics queries
- **Celery**: Multiple worker instances
- **Redis**: Cluster setup for high availability
- **Load Balancer**: Nginx for static files and load balancing

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Troubleshooting

### Common Issues

**Database Connection Error**
```bash
# Check PostgreSQL is running
docker-compose ps db

# Check logs
docker-compose logs db
```

**Celery Tasks Not Running**
```bash
# Check Redis connection
docker-compose ps redis

# Check Celery worker logs
docker-compose logs celery
```

**Search Not Working**
```bash
# Switch embedding model and reindex
python manage.py switch_embedding_model fast --reindex

# Check search indexes
python manage.py shell -c "from apps.articles.models import Article; print(f'Articles with embeddings: {Article.objects.exclude(embedding__isnull=True).count()}/{Article.objects.count()}')"
```

### Performance Issues

**Slow Queries**
- Check database indexes with `EXPLAIN ANALYZE`
- Monitor query performance in logs
- Use `django-debug-toolbar` in development

**High Memory Usage**
- Monitor Celery worker memory
- Adjust batch sizes for embedding generation
- Use database connection pooling

## 📞 Support

For support and questions:
- Create an issue on GitHub
- Check the documentation:
  - [Data Pipeline Flow](DATA_PIPELINE_FLOW.md)
  - [Embedding Models Guide](EMBEDDING_MODELS_GUIDE.md)
  - [Service Layer Architecture](SERVICE_LAYER_ARCHITECTURE.md)
- Review the API examples above

---

**Built with ❤️ using Django, PostgreSQL, and modern Python practices**