from django.db import models
from django.contrib.auth.models import User


class AIQueryLog(models.Model):
    """Audit trail of every AI request (ask-ai and rag-query) made by a user."""
    QUERY_TYPE_CHOICES = [
        ('ask_ai', 'Ask AI'),
        ('rag_query', 'RAG Query'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ai_query_logs')
    query_type = models.CharField(max_length=20, choices=QUERY_TYPE_CHOICES)
    input_text = models.TextField()
    response_text = models.TextField()
    # For rag_query: [{"document_id", "chunk_id", "chunk_index", "chunk_text", "score"}, ...]
    sources = models.JSONField(default=list, blank=True)
    prompt_template = models.CharField(max_length=100)
    model_name = models.CharField(max_length=100)
    input_tokens = models.PositiveIntegerField(null=True, blank=True)
    output_tokens = models.PositiveIntegerField(null=True, blank=True)
    latency_ms = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at', '-id']
        indexes = [models.Index(fields=['user', '-created_at'], name='ai_query_user_created_idx')]

    def __str__(self):
        return f"AIQuery({self.query_type}) by {self.user.username} at {self.created_at}"
