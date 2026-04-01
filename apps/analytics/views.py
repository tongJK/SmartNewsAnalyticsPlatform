from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from datetime import timedelta
import logging

from .models import ArticleMetrics, DailyArticleStats, TrendingTopic
from .services import TimeSeriesAnalytics, TrendAnalyzer, DashboardService

logger = logging.getLogger('analytics')


class AnalyticsViewSet(viewsets.ViewSet):
    """
    ViewSet for analytics and metrics endpoints
    """
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def dashboard(self, request):
        """
        Get dashboard overview statistics
        """
        days = int(request.query_params.get('days', 7))
        
        try:
            overview_stats = DashboardService.get_overview_stats(days=days)
            real_time_metrics = DashboardService.get_real_time_metrics()
            
            return Response({
                'overview': overview_stats,
                'real_time': real_time_metrics,
                'timestamp': timezone.now()
            })
            
        except Exception as e:
            logger.error(f"Dashboard error: {e}")
            return Response(
                {'error': 'Failed to load dashboard data'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def trending(self, request):
        """
        Get trending topics and articles
        """
        hours = int(request.query_params.get('hours', 24))
        
        try:
            trending_topics = TrendAnalyzer.detect_trending_topics(hours=hours)
            trending_articles = TimeSeriesAnalytics.get_trending_articles(hours=hours)
            
            return Response({
                'trending_topics': trending_topics,
                'trending_articles': trending_articles,
                'period_hours': hours
            })
            
        except Exception as e:
            logger.error(f"Trending analysis error: {e}")
            return Response(
                {'error': 'Failed to analyze trending data'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def category_performance(self, request):
        """
        Get performance metrics by category
        """
        days = int(request.query_params.get('days', 7))
        
        try:
            performance_data = TimeSeriesAnalytics.get_category_performance(days=days)
            
            return Response({
                'category_performance': performance_data,
                'period_days': days
            })
            
        except Exception as e:
            logger.error(f"Category performance error: {e}")
            return Response(
                {'error': 'Failed to analyze category performance'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def traffic_patterns(self, request):
        """
        Get traffic patterns by hour of day
        """
        days = int(request.query_params.get('days', 7))
        
        try:
            traffic_data = TimeSeriesAnalytics.get_hourly_traffic_pattern(days=days)
            
            return Response({
                'hourly_patterns': traffic_data.to_dict('records'),
                'period_days': days
            })
            
        except Exception as e:
            logger.error(f"Traffic pattern error: {e}")
            return Response(
                {'error': 'Failed to analyze traffic patterns'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


@api_view(['GET'])
def article_timeseries(request, article_id):
    """
    Get time-series data for a specific article
    """
    days = int(request.GET.get('days', 30))
    
    try:
        timeseries_data = TimeSeriesAnalytics.get_article_views_timeseries(
            article_id=article_id,
            days=days
        )
        
        return Response({
            'article_id': article_id,
            'timeseries': timeseries_data.to_dict('records'),
            'period_days': days
        })
        
    except Exception as e:
        logger.error(f"Article timeseries error: {e}")
        return Response(
            {'error': 'Failed to load article timeseries data'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
def predict_engagement(request, article_id):
    """
    Predict engagement for an article
    """
    try:
        prediction = TrendAnalyzer.predict_engagement(article_id)
        
        if 'error' in prediction:
            return Response(prediction, status=status.HTTP_404_NOT_FOUND)
        
        return Response({
            'article_id': article_id,
            'prediction': prediction,
            'timestamp': timezone.now()
        })
        
    except Exception as e:
        logger.error(f"Engagement prediction error: {e}")
        return Response(
            {'error': 'Failed to predict engagement'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
def health_check(request):
    """
    Health check endpoint for monitoring
    """
    try:
        # Check database connectivity
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        
        # Check Redis connectivity
        from django.core.cache import cache
        cache.set('health_check', 'ok', 10)
        cache_status = cache.get('health_check') == 'ok'
        
        return Response({
            'status': 'healthy',
            'timestamp': timezone.now(),
            'database': 'connected',
            'cache': 'connected' if cache_status else 'disconnected',
            'version': '1.0.0'
        })
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return Response(
            {
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': timezone.now()
            },
            status=status.HTTP_503_SERVICE_UNAVAILABLE
        )