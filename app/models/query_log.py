from django.db import models
from django.contrib.auth.models import User

class QueryLog(models.Model):
    query_text = models.TextField()
    result_summary = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='query_logs')

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Query by {self.user.username} at {self.created_at}"
