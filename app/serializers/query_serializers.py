from rest_framework import serializers
from app.models.query_log import QueryLog

class QueryLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = QueryLog
        fields = ['id', 'query_text', 'result_summary', 'created_at', 'user']
        read_only_fields = ['id', 'result_summary', 'created_at', 'user']
