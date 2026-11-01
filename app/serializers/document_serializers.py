from rest_framework import serializers
from app.models.document import Document

class DocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Document
        fields = ['id', 'title', 'content', 'uploaded_at', 'owner',
                  'ingestion_status', 'chunk_count', 'ingested_at']
        read_only_fields = ['id', 'uploaded_at', 'owner',
                            'ingestion_status', 'chunk_count', 'ingested_at']
