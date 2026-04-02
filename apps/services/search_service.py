"""
Search service layer for advanced search functionality
"""
from django.contrib.postgres.search import SearchQuery, SearchRank
from django.db.models import F, Q
from apps.articles.models import Article
from apps.services.embedding_service import embedding_manager
import logging

logger = logging.getLogger('articles')


class SearchService:
    """Service class for search-related business logic"""
    
    @staticmethod
    def full_text_search(query, category=None, language=None, limit=20):
        """
        Full-text search using PostgreSQL tsvector
        """
        search_query = SearchQuery(query)
        
        queryset = Article.objects.filter(
            search_vector=search_query
        ).annotate(
            rank=SearchRank(F('search_vector'), search_query)
        ).order_by('-rank')
        
        # Apply filters
        if category:
            queryset = queryset.filter(category__iexact=category)
        if language:
            queryset = queryset.filter(language=language)
        
        results = list(queryset[:limit])
        
        # Add search metadata
        for article in results:
            article.search_type = 'text'
            article.similarity_score = getattr(article, 'rank', 0)
        
        logger.info(f"Full-text search for '{query}' returned {len(results)} results")
        return results
    
    @staticmethod
    def semantic_search(query, category=None, language=None, limit=20, threshold=0.3):
        """
        Semantic search using embeddings
        """
        # Generate query embedding
        query_embedding = embedding_manager.encode([query])[0].tolist()
        
        # Get articles with embeddings
        queryset = Article.objects.exclude(embedding__isnull=True)
        
        # Apply filters
        if category:
            queryset = queryset.filter(category__iexact=category)
        if language:
            queryset = queryset.filter(language=language)
        
        # Calculate similarity scores
        articles_with_scores = []
        for article in queryset[:1000]:  # Limit for performance
            if article.embedding:
                similarity = SearchService._cosine_similarity(
                    query_embedding, 
                    article.embedding
                )
                
                if similarity > threshold:
                    article.similarity_score = similarity
                    article.search_type = 'semantic'
                    articles_with_scores.append(article)
        
        # Sort by similarity
        results = sorted(
            articles_with_scores, 
            key=lambda x: x.similarity_score, 
            reverse=True
        )[:limit]
        
        logger.info(f"Semantic search for '{query}' returned {len(results)} results")
        return results
    
    @staticmethod
    def hybrid_search(query, category=None, language=None, limit=20):
        """
        Combine full-text and semantic search with weighted scoring
        """
        # Get results from both methods
        text_results = SearchService.full_text_search(
            query, category, language, limit * 2
        )
        semantic_results = SearchService.semantic_search(
            query, category, language, limit * 2
        )
        
        # Combine and deduplicate
        combined_results = {}
        
        # Add text search results with weighted score
        for i, article in enumerate(text_results):
            score = (len(text_results) - i) / len(text_results) if text_results else 0
            article.similarity_score = score * 0.6  # Weight text search 60%
            article.search_type = 'hybrid'
            combined_results[article.id] = article
        
        # Add semantic search results with weighted score
        for article in semantic_results:
            if article.id in combined_results:
                # Combine scores
                combined_results[article.id].similarity_score += article.similarity_score * 0.4
            else:
                article.similarity_score *= 0.4  # Weight semantic search 40%
                article.search_type = 'hybrid'
                combined_results[article.id] = article
        
        # Sort by combined score
        results = sorted(
            combined_results.values(),
            key=lambda x: x.similarity_score,
            reverse=True
        )[:limit]
        
        logger.info(f"Hybrid search for '{query}' returned {len(results)} results")
        return results
    
    @staticmethod
    def search(query, search_type='hybrid', **kwargs):
        """
        Unified search interface
        """
        search_methods = {
            'text': SearchService.full_text_search,
            'semantic': SearchService.semantic_search,
            'hybrid': SearchService.hybrid_search,
        }
        
        search_method = search_methods.get(search_type, SearchService.hybrid_search)
        return search_method(query, **kwargs)
    
    @staticmethod
    def get_search_suggestions(query, limit=5):
        """
        Get search suggestions based on existing article titles
        """
        suggestions = Article.objects.filter(
            Q(title__icontains=query) | Q(tags__contains=[query])
        ).values_list('title', flat=True).distinct()[:limit]
        
        return list(suggestions)
    
    @staticmethod
    def get_popular_searches(days=7, limit=10):
        """
        Get popular search terms (would need search logging to implement)
        For now, return popular article categories
        """
        from django.db.models import Count
        from datetime import timedelta
        from django.utils import timezone
        
        cutoff_date = timezone.now() - timedelta(days=days)
        
        popular_categories = Article.objects.filter(
            published_at__gte=cutoff_date
        ).values('category').annotate(
            count=Count('id')
        ).order_by('-count')[:limit]
        
        return [item['category'] for item in popular_categories if item['category']]
    
    @staticmethod
    def _cosine_similarity(a, b):
        """Calculate cosine similarity between two vectors"""
        try:
            import numpy as np
            a = np.array(a)
            b = np.array(b)
            return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))
        except:
            return 0.0
    
    @staticmethod
    def get_search_analytics(query):
        """
        Get analytics for a search query
        """
        # This would typically log search queries and return analytics
        # For now, return basic info
        return {
            'query': query,
            'timestamp': timezone.now(),
            'total_articles': Article.objects.count(),
            'articles_with_embeddings': Article.objects.exclude(embedding__isnull=True).count(),
        }