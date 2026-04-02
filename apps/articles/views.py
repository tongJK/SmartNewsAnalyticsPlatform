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
from apps.services.article_service import ArticleService
from apps.services.search_service import SearchService
from apps.services.multimodal_service import multimodal_service
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
import tempfile
import os

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
        
        # Track the view using service layer
        ArticleService.track_article_view(
            article=instance,
            user=request.user if request.user.is_authenticated else None,
            ip_address=self._get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            referrer=request.META.get('HTTP_REFERER', '')
        )
        
        serializer = self.get_serializer(instance)
        return Response(serializer.data)
    

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
            # Use SearchService for unified search
            results = SearchService.search(
                query=query,
                search_type=search_type,
                category=category,
                language=language,
                limit=limit
            )
            
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
        
        # Use ArticleService for recommendations
        similar_articles = ArticleService.get_similar_articles(article, limit=10)
        
        serializer = ArticleSearchSerializer(similar_articles, many=True)
        return Response({
            'article_id': article.id,
            'article_title': article.title,
            'recommendations': serializer.data
        })
    
    @action(detail=True, methods=['post'])
    def share(self, request, pk=None):
        """Track article share"""
        article = self.get_object()
        total_shares = ArticleService.increment_shares(article.id)
        
        return Response({
            'message': 'Share tracked successfully',
            'total_shares': total_shares
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
    
    @action(detail=False, methods=['post'])
    def search_by_image(self, request):
        """
        Search articles by uploaded image using CLIP embeddings
        """
        if 'image' not in request.FILES:
            return Response({'error': 'No image provided'}, status=400)
        
        try:
            image_file = request.FILES['image']
            
            # Generate embedding for uploaded image
            with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as tmp_file:
                for chunk in image_file.chunks():
                    tmp_file.write(chunk)
                tmp_file.flush()
                
                query_embedding = multimodal_service.generate_image_embedding(tmp_file.name)
                os.unlink(tmp_file.name)
            
            if not query_embedding:
                return Response({'error': 'Failed to process image'}, status=400)
            
            # Find similar articles with image embeddings
            articles = Article.objects.exclude(image_embedding__isnull=True)
            
            results = []
            for article in articles:
                similarity = multimodal_service.cosine_similarity(
                    query_embedding, article.image_embedding
                )
                if similarity > 0.7:  # Similarity threshold
                    results.append({
                        'article': article,
                        'similarity': similarity
                    })
            
            # Sort by similarity
            results.sort(key=lambda x: x['similarity'], reverse=True)
            
            # Serialize results
            serialized_results = []
            for result in results[:10]:  # Top 10
                article_data = self.get_serializer(result['article']).data
                article_data['similarity'] = result['similarity']
                serialized_results.append(article_data)
            
            return Response({
                'results': serialized_results,
                'count': len(serialized_results)
            })
            
        except Exception as e:
            return Response({'error': str(e)}, status=500)
    
    @action(detail=False, methods=['post'])
    def search_by_text_to_image(self, request):
        """
        Search images by text description using CLIP
        """
        query = request.data.get('query', '').strip()
        if not query:
            return Response({'error': 'Query is required'}, status=400)
        
        try:
            # Generate CLIP text embedding
            query_embedding = multimodal_service.generate_text_embedding(query)
            
            if not query_embedding:
                return Response({'error': 'Failed to process query'}, status=400)
            
            # Find articles with similar image embeddings
            articles = Article.objects.exclude(image_embedding__isnull=True)
            
            results = []
            for article in articles:
                similarity = multimodal_service.cosine_similarity(
                    query_embedding, article.image_embedding
                )
                if similarity > 0.6:  # Lower threshold for text-to-image
                    results.append({
                        'article': article,
                        'similarity': similarity
                    })
            
            # Sort by similarity
            results.sort(key=lambda x: x['similarity'], reverse=True)
            
            # Serialize results
            serialized_results = []
            for result in results[:10]:
                article_data = self.get_serializer(result['article']).data
                article_data['similarity'] = result['similarity']
                serialized_results.append(article_data)
            
            return Response({
                'query': query,
                'results': serialized_results,
                'count': len(serialized_results)
            })
            
        except Exception as e:
            return Response({'error': str(e)}, status=500)