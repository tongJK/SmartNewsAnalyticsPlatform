import json
import asyncio
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone
import logging

logger = logging.getLogger('analytics')


class DashboardConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for real-time dashboard updates
    """
    
    async def connect(self):
        self.room_group_name = 'dashboard'
        
        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Start sending periodic updates
        self.update_task = asyncio.create_task(self.send_periodic_updates())
    
    async def disconnect(self, close_code):
        # Cancel the update task
        if hasattr(self, 'update_task'):
            self.update_task.cancel()
        
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
    
    async def receive(self, text_data):
        """Handle incoming WebSocket messages"""
        try:
            text_data_json = json.loads(text_data)
            message_type = text_data_json.get('type')
            
            if message_type == 'get_dashboard_data':
                await self.send_dashboard_data()
            elif message_type == 'get_real_time_metrics':
                await self.send_real_time_metrics()
                
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'error': 'Invalid JSON format'
            }))
    
    async def send_periodic_updates(self):
        """Send periodic dashboard updates"""
        try:
            while True:
                await self.send_real_time_metrics()
                await asyncio.sleep(30)  # Update every 30 seconds
        except asyncio.CancelledError:
            pass
    
    async def send_dashboard_data(self):
        """Send complete dashboard data"""
        try:
            dashboard_data = await self.get_dashboard_data()
            await self.send(text_data=json.dumps({
                'type': 'dashboard_data',
                'data': dashboard_data,
                'timestamp': timezone.now().isoformat()
            }))
        except Exception as e:
            logger.error(f"Error sending dashboard data: {e}")
            await self.send(text_data=json.dumps({
                'error': 'Failed to load dashboard data'
            }))
    
    async def send_real_time_metrics(self):
        """Send real-time metrics"""
        try:
            metrics = await self.get_real_time_metrics()
            await self.send(text_data=json.dumps({
                'type': 'real_time_metrics',
                'data': metrics,
                'timestamp': timezone.now().isoformat()
            }))
        except Exception as e:
            logger.error(f"Error sending real-time metrics: {e}")
    
    @database_sync_to_async
    def get_dashboard_data(self):
        """Get dashboard data from database"""
        from .services import DashboardService
        return DashboardService.get_overview_stats(days=7)
    
    @database_sync_to_async
    def get_real_time_metrics(self):
        """Get real-time metrics from database"""
        from .services import DashboardService
        return DashboardService.get_real_time_metrics()
    
    # Receive message from room group
    async def dashboard_message(self, event):
        message = event['message']
        
        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'type': 'dashboard_update',
            'message': message
        }))


class ArticleMetricsConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for real-time article metrics
    """
    
    async def connect(self):
        self.article_id = self.scope['url_route']['kwargs']['article_id']
        self.room_group_name = f'article_{self.article_id}'
        
        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Send initial article data
        await self.send_article_metrics()
        
        # Start sending periodic updates
        self.update_task = asyncio.create_task(self.send_periodic_updates())
    
    async def disconnect(self, close_code):
        # Cancel the update task
        if hasattr(self, 'update_task'):
            self.update_task.cancel()
        
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
    
    async def receive(self, text_data):
        """Handle incoming WebSocket messages"""
        try:
            text_data_json = json.loads(text_data)
            message_type = text_data_json.get('type')
            
            if message_type == 'get_metrics':
                await self.send_article_metrics()
            elif message_type == 'get_timeseries':
                days = text_data_json.get('days', 30)
                await self.send_timeseries_data(days)
                
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'error': 'Invalid JSON format'
            }))
    
    async def send_periodic_updates(self):
        """Send periodic article metrics updates"""
        try:
            while True:
                await self.send_article_metrics()
                await asyncio.sleep(60)  # Update every minute
        except asyncio.CancelledError:
            pass
    
    async def send_article_metrics(self):
        """Send current article metrics"""
        try:
            metrics = await self.get_article_metrics()
            if metrics:
                await self.send(text_data=json.dumps({
                    'type': 'article_metrics',
                    'article_id': self.article_id,
                    'data': metrics,
                    'timestamp': timezone.now().isoformat()
                }))
            else:
                await self.send(text_data=json.dumps({
                    'error': 'Article not found'
                }))
        except Exception as e:
            logger.error(f"Error sending article metrics: {e}")
    
    async def send_timeseries_data(self, days=30):
        """Send article timeseries data"""
        try:
            timeseries = await self.get_timeseries_data(days)
            await self.send(text_data=json.dumps({
                'type': 'timeseries_data',
                'article_id': self.article_id,
                'data': timeseries,
                'period_days': days,
                'timestamp': timezone.now().isoformat()
            }))
        except Exception as e:
            logger.error(f"Error sending timeseries data: {e}")
    
    @database_sync_to_async
    def get_article_metrics(self):
        """Get article metrics from database"""
        try:
            from apps.articles.models import Article
            article = Article.objects.get(pk=self.article_id)
            return {
                'id': article.id,
                'title': article.title,
                'views': article.views,
                'shares': article.shares,
                'engagement_score': article.engagement_score,
                'published_at': article.published_at.isoformat(),
            }
        except Article.DoesNotExist:
            return None
    
    @database_sync_to_async
    def get_timeseries_data(self, days):
        """Get timeseries data from database"""
        from .services import TimeSeriesAnalytics
        df = TimeSeriesAnalytics.get_article_views_timeseries(
            article_id=int(self.article_id),
            days=days
        )
        return df.to_dict('records')
    
    # Receive message from room group
    async def article_update(self, event):
        message = event['message']
        
        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'type': 'article_update',
            'message': message
        }))