"""
URL configuration for SmartNewsAnalyticsPlatform project.
"""
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('apps.articles.urls')),
    path('', include('apps.analytics.urls')),
    path('', include('apps.users.urls')),
]