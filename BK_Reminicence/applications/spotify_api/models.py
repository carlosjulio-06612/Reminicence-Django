from django.db import models
from django.conf import settings

class SpotifyUserToken(models.Model):
    token_id = models.AutoField(primary_key=True)
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    access_token = models.TextField()
    refresh_token = models.TextField(blank=True, null=True)
    expires_at = models.DateTimeField()
    scope = models.TextField(blank=True, null=True)
    spotify_user_id = models.CharField(max_length=100, blank=True, null=True, unique=True)  # 👈 AGREGADO unique=True
    
    class Meta:
        managed = False
        db_table = 'spotify_user_tokens'

class SpotifyApiCache(models.Model):
    cache_id = models.AutoField(primary_key=True)
    cache_key = models.CharField(unique=True, max_length=500)
    response_data = models.JSONField()
    expires_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'spotify_api_cache'
        
class SpotifySyncLog(models.Model):
    sync_id = models.AutoField(primary_key=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    sync_type = models.CharField(max_length=50)
    status = models.CharField(max_length=20)
    items_processed = models.IntegerField(blank=True, null=True)
    items_total = models.IntegerField(blank=True, null=True)
    error_message = models.TextField(blank=True, null=True)
    started_at = models.DateTimeField(blank=True, null=True)
    completed_at = models.DateTimeField(blank=True, null=True)
    
    class Meta:
        managed = False
        db_table = 'spotify_sync_log'
        