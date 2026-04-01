from django.db import models
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    """
    Extended user model for additional analytics tracking
    """
    
    # Additional fields for analytics
    preferred_categories = models.JSONField(default=list, blank=True)
    reading_time_avg = models.FloatField(null=True, help_text="Average reading time in seconds")
    last_active = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'auth_user_extended'
    
    def __str__(self):
        return self.username