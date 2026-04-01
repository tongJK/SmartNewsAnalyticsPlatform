from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/analytics/dashboard/$', consumers.DashboardConsumer.as_asgi()),
    re_path(r'ws/analytics/article/(?P<article_id>\d+)/$', consumers.ArticleMetricsConsumer.as_asgi()),
]