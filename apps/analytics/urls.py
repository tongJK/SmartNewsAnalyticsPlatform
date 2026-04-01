from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AnalyticsViewSet, article_timeseries, predict_engagement, health_check

router = DefaultRouter()
router.register(r'analytics', AnalyticsViewSet, basename='analytics')

app_name = 'analytics'

urlpatterns = [
    path('api/', include(router.urls)),
    path('api/articles/<int:article_id>/timeseries/', article_timeseries, name='article_timeseries'),
    path('api/articles/<int:article_id>/predict/', predict_engagement, name='predict_engagement'),
    path('api/health/', health_check, name='health_check'),
]