from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.contrib.postgres.search import SearchQuery, SearchRank
from django.db.models import Q, F
from django_ratelimit.decorators import ratelimit
from django.utils.decorators import method_decorator
import numpy as np
import logging

from .models import Article, ArticleView
from .serializers import (
    ArticleSerializer, ArticleListSerializer, ArticleSearchSerializer,
    ArticleCreateSerializer, SearchQuerySerializer, ArticleViewSerializer
)
from .tasks import generate_embedding_task

logger = logging.getLogger('articles')


class ArticleViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Article CRUD operations with advanced search
    """
    queryset = Article.objects.all()
    permission_classes = [AllowAny]
    
    def get_serializer_class(self):
        if self.action == 'list':
            return ArticleListSerializer
        elif self.action == 'create':
            return ArticleCreateSerializer
        elif self.action in ['search', 'recommend']:
            return ArticleSearchSerializer
        return ArticleSerializer
    
    def get_queryset(self):
        queryset = Article.objects.all()
        
        # Filter by category
        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(category__iexact=category)
        
        # Filter by language
        language = self.request.query_params.get('language')
        if language:
            queryset = queryset.filter(language=language)
        
        # Filter by date range
        date_from = self.request.query_params.get('date_from')
        date_to = self.request.query_params.get('date_to')
        if date_from:
            queryset = queryset.filter(published_at__gte=date_from)
        if date_to:
            queryset = queryset.filter(published_at__lte=date_to)
        
        return queryset.order_by('-published_at')
    
    def retrieve(self, request, *args, **kwargs):
        """Override retrieve to track article views"""
        instance = self.get_object()
        
        # Track the view
        self._track_article_view(request, instance)
        
        # Increment view counter
        instance.increment_views()
        
        serializer = self.get_serializer(instance)
        return Response(serializer.data)
    
    def _track_article_view(self, request, article):
        """Track article view for analytics"""
        try:
            ArticleView.objects.create(
                article=article,
                user=request.user if request.user.is_authenticated else None,
                ip_address=self._get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                referrer=request.META.get('HTTP_REFERER', '')
            )
        except Exception as e:
            logger.error(f"Error tracking article view: {e}")
    
    def _get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    @method_decorator(ratelimit(key='ip', rate='100/h', method='POST'))
    @action(detail=False, methods=['post'])
    def search(self, request):
        """
        Advanced search with full-text and semantic search
        """
        serializer = SearchQuerySerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        query = serializer.validated_data['query']
        search_type = serializer.validated_data['search_type']
        category = serializer.validated_data.get('category')
        language = serializer.validated_data.get('language')
        limit = serializer.validated_data['limit']
        
        try:
            if search_type == 'text':
                results = self._full_text_search(query, category, language, limit)
            elif search_type == 'semantic':
                results = self._semantic_search(query, category, language, limit)
            else:  # hybrid
                results = self._hybrid_search(query, category, language, limit)
            
            serializer = ArticleSearchSerializer(results, many=True)
            return Response({
                'query': query,
                'search_type': search_type,
                'count': len(results),
                'results': serializer.data
            })
            
        except Exception as e:
            logger.error(f"Search error: {e}")
            return Response(
                {'error': 'Search failed'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _full_text_search(self, query, category=None, language=None, limit=20):
        """Full-text search using PostgreSQL tsvector"""
        search_query = SearchQuery(query)
        
        queryset = Article.objects.filter(
            search_vector=search_query
        ).annotate(
            rank=SearchRank(F('search_vector'), search_query)
        ).order_by('-rank')
        
        if category:
            queryset = queryset.filter(category__iexact=category)
        if language:
            queryset = queryset.filter(language=language)
        
        return queryset[:limit]
    
    def _semantic_search(self, query, category=None, language=None, limit=20):
        """Semantic search using embeddings"""
        from sentence_transformers import SentenceTransformer
        
        # Generate query embedding
        model = SentenceTransformer('all-MiniLM-L6-v2')
        query_embedding = model.encode(query, normalize_embeddings=True).tolist()
        
        # Get articles with embeddings
        queryset = Article.objects.exclude(embedding__isnull=True)
        
        if category:
            queryset = queryset.filter(category__iexact=category)
        if language:
            queryset = queryset.filter(language=language)
        
        # Calculate similarity scores
        articles_with_scores = []
        for article in queryset[:1000]:  # Limit for performance
            if article.embedding:
                similarity = self._cosine_similarity(query_embedding, article.embedding)
                if similarity > 0.3:  # Threshold for relevance
                    article.similarity_score = similarity
                    articles_with_scores.append(article)
        
        # Sort by similarity and return top results
        articles_with_scores.sort(key=lambda x: x.similarity_score, reverse=True)
        return articles_with_scores[:limit]
    
    def _hybrid_search(self, query, category=None, language=None, limit=20):
        """Combine full-text and semantic search"""
        # Get results from both methods
        text_results = list(self._full_text_search(query, category, language, limit * 2))
        semantic_results = list(self._semantic_search(query, category, language, limit * 2))
        
        # Combine and deduplicate
        combined_results = {}
        
        # Add text search results with rank-based score
        for i, article in enumerate(text_results):
            score = (len(text_results) - i) / len(text_results)  # Normalize rank
            article.similarity_score = score * 0.6  # Weight text search 60%
            combined_results[article.id] = article
        
        # Add semantic search results
        for article in semantic_results:
            if article.id in combined_results:
                # Combine scores
                combined_results[article.id].similarity_score += article.similarity_score * 0.4
            else:
                article.similarity_score *= 0.4  # Weight semantic search 40%
                combined_results[article.id] = article
        
        # Sort by combined score
        final_results = list(combined_results.values())
        final_results.sort(key=lambda x: x.similarity_score, reverse=True)
        
        return final_results[:limit]
    
    def _cosine_similarity(self, a, b):
        """Calculate cosine similarity between two vectors"""
        try:
            a = np.array(a)
            b = np.array(b)
            return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))
        except:
            return 0.0
    
    @action(detail=True, methods=['get'])
    def recommend(self, request, pk=None):
        """
        Get recommended articles based on semantic similarity
        """
        article = self.get_object()
        
        if not article.embedding:
            return Response(
                {'message': 'No recommendations available - article embedding not generated yet'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Find similar articles
        similar_articles = []
        queryset = Article.objects.exclude(pk=article.pk).exclude(embedding__isnull=True)
        
        for other_article in queryset[:500]:  # Limit for performance
            if other_article.embedding:
                similarity = self._cosine_similarity(article.embedding, other_article.embedding)
                if similarity > 0.5:  # Higher threshold for recommendations
                    other_article.similarity_score = similarity
                    similar_articles.append(other_article)
        
        # Sort by similarity
        similar_articles.sort(key=lambda x: x.similarity_score, reverse=True)
        
        # Return top 10 recommendations
        serializer = ArticleSearchSerializer(similar_articles[:10], many=True)
        return Response({
            'article_id': article.id,
            'article_title': article.title,
            'recommendations': serializer.data
        })
    
    @action(detail=True, methods=['post'])
    def share(self, request, pk=None):
        """Track article share"""
        article = self.get_object()
        article.increment_shares()
        
        return Response({
            'message': 'Share tracked successfully',
            'total_shares': article.shares
        })
    
    @action(detail=False, methods=['get'])
    def trending(self, request):
        """Get trending articles"""
        from apps.analytics.services import TimeSeriesAnalytics
        
        trending_data = TimeSeriesAnalytics.get_trending_articles(hours=24, limit=20)
        return Response({
            'trending_articles': trending_data,
            'period': '24 hours'
        })