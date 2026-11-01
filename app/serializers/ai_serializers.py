from rest_framework import serializers

from app.config.app_config import AIConfigConstants
from app.models.ai_query_log import AIQueryLog


# ---------------------------------------------------------------- requests

class AskAIRequestSerializer(serializers.Serializer):
    prompt = serializers.CharField(max_length=AIConfigConstants.MAX_PROMPT_CHARS, trim_whitespace=True)


class RagQueryRequestSerializer(serializers.Serializer):
    query = serializers.CharField(max_length=AIConfigConstants.MAX_QUERY_CHARS, trim_whitespace=True)


class IngestDocRequestSerializer(serializers.Serializer):
    document_id = serializers.IntegerField(min_value=1)


# --------------------------------------------------------------- responses

def _usage(obj):
    return {"input_tokens": obj.input_tokens, "output_tokens": obj.output_tokens}


class AskAIResponseSerializer(serializers.ModelSerializer):
    prompt = serializers.CharField(source='input_text')
    response = serializers.CharField(source='response_text')
    model = serializers.CharField(source='model_name')
    usage = serializers.SerializerMethodField()

    class Meta:
        model = AIQueryLog
        fields = ['id', 'prompt', 'response', 'prompt_template', 'model', 'usage', 'latency_ms', 'created_at']

    def get_usage(self, obj) -> dict:
        return _usage(obj)


class SourceChunkSerializer(serializers.Serializer):
    document_id = serializers.IntegerField()
    chunk_text = serializers.CharField()
    document_title = serializers.CharField(required=False)
    chunk_id = serializers.IntegerField(required=False)
    chunk_index = serializers.IntegerField(required=False)
    score = serializers.FloatField(required=False)


class RagQueryResponseSerializer(serializers.ModelSerializer):
    query = serializers.CharField(source='input_text')
    answer = serializers.CharField(source='response_text')
    sources = SourceChunkSerializer(many=True)
    model = serializers.CharField(source='model_name')
    usage = serializers.SerializerMethodField()

    class Meta:
        model = AIQueryLog
        fields = ['id', 'query', 'answer', 'sources', 'prompt_template', 'model', 'usage', 'latency_ms', 'created_at']

    def get_usage(self, obj) -> dict:
        return _usage(obj)


class IngestDocResponseSerializer(serializers.Serializer):
    document_id = serializers.IntegerField()
    title = serializers.CharField()
    status = serializers.CharField()
    chunk_count = serializers.IntegerField()
    chunk_size = serializers.IntegerField()
    chunk_overlap = serializers.IntegerField()
    embedding_model = serializers.CharField()
    vector_store = serializers.CharField()
    replaced_chunks = serializers.IntegerField()
    ingested_at = serializers.DateTimeField()


class AIQueryHistorySerializer(serializers.ModelSerializer):
    sources = SourceChunkSerializer(many=True)

    class Meta:
        model = AIQueryLog
        fields = ['id', 'query_type', 'input_text', 'response_text', 'sources', 'prompt_template',
                  'model_name', 'input_tokens', 'output_tokens', 'latency_ms', 'created_at']
        read_only_fields = fields
