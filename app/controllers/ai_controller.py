from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.parsers import JSONParser
from rest_framework.response import Response
from rest_framework.views import APIView

from app.controllers.pagination import StandardResultsPagination
from app.serializers.ai_serializers import (
    AIQueryHistorySerializer,
    AskAIRequestSerializer,
    AskAIResponseSerializer,
    IngestDocRequestSerializer,
    IngestDocResponseSerializer,
    RagQueryRequestSerializer,
    RagQueryResponseSerializer,
)
from app.services import container


class AskAIController(APIView):
    """POST /api/ask-ai — LLM Q&A through a defined prompt template."""
    parser_classes = [JSONParser]

    @extend_schema(tags=['AI'], request=AskAIRequestSerializer, responses={200: AskAIResponseSerializer})
    def post(self, request):
        serializer = AskAIRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        log = container.build_ai_query_service().ask_ai(
            user=request.user, prompt=serializer.validated_data['prompt']
        )
        return Response(AskAIResponseSerializer(log).data, status=status.HTTP_200_OK)


class RagQueryController(APIView):
    """POST /api/rag-query — retrieval-augmented answer + retrieved source chunks."""
    parser_classes = [JSONParser]

    @extend_schema(tags=['AI'], request=RagQueryRequestSerializer, responses={200: RagQueryResponseSerializer})
    def post(self, request):
        serializer = RagQueryRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        log = container.build_ai_query_service().rag_query(
            user=request.user, query=serializer.validated_data['query']
        )
        return Response(RagQueryResponseSerializer(log).data, status=status.HTTP_200_OK)


class IngestDocController(APIView):
    """POST /api/ingest-doc — chunk a document and store its embeddings in FAISS."""
    parser_classes = [JSONParser]

    @extend_schema(tags=['AI'], request=IngestDocRequestSerializer, responses={201: IngestDocResponseSerializer})
    def post(self, request):
        serializer = IngestDocRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = container.build_ingestion_service().ingest_document(
            user=request.user, document_id=serializer.validated_data['document_id']
        )
        return Response(IngestDocResponseSerializer(result).data, status=status.HTTP_201_CREATED)


class AIQueryHistoryController(APIView):
    """GET /api/query-history — the requester's AI query history, paginated."""

    @extend_schema(
        tags=['AI'],
        parameters=[
            OpenApiParameter('page', int, description='Page number (1-based).'),
            OpenApiParameter('page_size', int, description='Items per page (max 100).'),
        ],
        responses={200: AIQueryHistorySerializer(many=True)},
    )
    def get(self, request):
        queries = container.build_ai_query_service().get_query_history(user=request.user)
        paginator = StandardResultsPagination()
        page = paginator.paginate_queryset(queries, request, view=self)
        return paginator.get_paginated_response(AIQueryHistorySerializer(page, many=True).data)
