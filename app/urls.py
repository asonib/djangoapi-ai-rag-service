from django.urls import path, re_path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)
from app.controllers.auth_controller import RegisterController, LoginController
from app.controllers.document_controller import DocumentListCreateController, DocumentDetailController
from app.controllers.query_controller import QueryController, QueryHistoryController
from app.controllers.ai_controller import (
    AskAIController,
    RagQueryController,
    IngestDocController,
    AIQueryHistoryController,
)

urlpatterns = [
    # OpenAPI Schema, Swagger & ReDoc Documentation
    path('schema/', SpectacularAPIView.as_view(), name='schema'),
    path('docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),

    # Auth endpoints
    path('auth/register/', RegisterController.as_view(), name='auth-register'),
    path('auth/login/', LoginController.as_view(), name='auth-login'),

    # Document endpoints
    path('documents/', DocumentListCreateController.as_view(), name='document-list-create'),
    path('documents/<int:pk>/', DocumentDetailController.as_view(), name='document-detail'),

    # Query endpoints
    path('query/', QueryController.as_view(), name='query-create'),
    path('queries/', QueryHistoryController.as_view(), name='query-history'),

    # AI / RAG endpoints (Assignment 3A). Trailing slash is optional so both
    # /api/ask-ai and /api/ask-ai/ work for POST requests.
    re_path(r'^ask-ai/?$', AskAIController.as_view(), name='ai-ask'),
    re_path(r'^rag-query/?$', RagQueryController.as_view(), name='ai-rag-query'),
    re_path(r'^ingest-doc/?$', IngestDocController.as_view(), name='ai-ingest-doc'),
    re_path(r'^query-history/?$', AIQueryHistoryController.as_view(), name='ai-query-history'),
]
