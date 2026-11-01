from django.db import models
from django.contrib.auth.models import User

class Document(models.Model):
    STATUS_NOT_INGESTED = 'not_ingested'
    STATUS_INGESTED = 'ingested'
    STATUS_FAILED = 'failed'
    INGESTION_STATUS_CHOICES = [
        (STATUS_NOT_INGESTED, 'Not ingested'),
        (STATUS_INGESTED, 'Ingested'),
        (STATUS_FAILED, 'Failed'),
    ]

    title = models.CharField(max_length=255)
    content = models.TextField()
    uploaded_at = models.DateTimeField(auto_now_add=True)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='documents')

    # Assignment 3A: ingestion bookkeeping
    ingestion_status = models.CharField(
        max_length=20, choices=INGESTION_STATUS_CHOICES, default=STATUS_NOT_INGESTED
    )
    chunk_count = models.PositiveIntegerField(default=0)
    ingested_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        return self.title
