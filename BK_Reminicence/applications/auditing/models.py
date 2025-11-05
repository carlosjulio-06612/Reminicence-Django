from django.db import models
from django.conf import settings

class AuditLog(models.Model):
    audit_id = models.AutoField(primary_key=True)
    db_user_name = models.CharField(max_length=100)
    app_user_id = models.IntegerField(blank=True, null=True)
    app_user_email = models.CharField(max_length=255, blank=True, null=True)
    app_user_role = models.CharField(max_length=50, blank=True, null=True) 
    action_type = models.CharField(max_length=10)
    timestamp = models.DateTimeField()
    table_name = models.CharField(max_length=50)
    record_id = models.IntegerField(blank=True, null=True)
    old_values = models.JSONField(blank=True, null=True)
    new_values = models.JSONField(blank=True, null=True)
    connection_ip = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.TextField(blank=True, null=True)
    api_endpoint = models.CharField(max_length=255, blank=True, null=True)
    request_id = models.CharField(max_length=100, blank=True, null=True)
    application_name = models.CharField(max_length=50, blank=True, null=True)
    environment = models.CharField(max_length=20, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'audit_log'
        verbose_name = 'Audit Log Entry'
        verbose_name_plural = 'Audit Log Entries'
        ordering = ['-timestamp']

    def __str__(self):
        """
        Representación en texto del objeto, útil para el admin de Django.
        """
        user_info = self.app_user_email or f"User ID {self.app_user_id}"
        return f"{self.action_type} on {self.table_name} (ID: {self.record_id}) by {user_info} at {self.timestamp}"