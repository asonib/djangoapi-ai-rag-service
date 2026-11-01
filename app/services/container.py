"""
Composition root for the service layer.

Controllers ask this module for fully-wired services instead of instantiating
infrastructure (LLM client, embedding model, FAISS store) themselves. Heavy
singletons are created once per process. Tests replace providers with
`container.override(...)` / `container.reset()`.
"""
import threading

from django.conf import settings

from app.config.app_config import AIConfigConstants

_lock = threading.Lock()
_singletons = {}
_overrides = {}


def _singleton(name, factory):
    if name in _overrides:
        return _overrides[name]
    instance = _singletons.get(name)
    if instance is None:
        with _lock:
            instance = _singletons.get(name)
            if instance is None:
                instance = factory()
                _singletons[name] = instance
    return instance


def override(**providers):
    """Replace infrastructure providers, e.g. override(llm_service=FakeLLM())."""
    _overrides.update(providers)


def reset():
    _overrides.clear()
    _singletons.clear()


# ---- infrastructure ---------------------------------------------------------

def get_text_chunker():
    from app.services.implementations.text_chunker_impl import RecursiveCharacterTextChunker
    return _singleton("text_chunker", lambda: RecursiveCharacterTextChunker(
        chunk_size=AIConfigConstants.CHUNK_SIZE,
        chunk_overlap=AIConfigConstants.CHUNK_OVERLAP,
    ))


def get_embedding_service():
    from app.services.implementations.sentence_transformer_embedding_service_impl import (
        SentenceTransformerEmbeddingService,
    )
    return _singleton("embedding_service", lambda: SentenceTransformerEmbeddingService(
        model_name=AIConfigConstants.EMBEDDING_MODEL_NAME,
        dimension=AIConfigConstants.EMBEDDING_DIMENSION,
        cache_folder=getattr(settings, "EMBEDDING_CACHE_DIR", None),
    ))


def get_vector_store():
    from app.services.implementations.faiss_vector_store_impl import FaissVectorStore
    return _singleton("vector_store", lambda: FaissVectorStore(
        base_dir=settings.VECTOR_STORE_DIR,
        dimension=AIConfigConstants.EMBEDDING_DIMENSION,
    ))


def get_llm_service():
    from app.services.implementations.anthropic_llm_service_impl import AnthropicLLMService
    return _singleton("llm_service", lambda: AnthropicLLMService(
        api_key=settings.ANTHROPIC_API_KEY,
        model=settings.ANTHROPIC_MODEL,
    ))


# ---- business services --------------------------------------------------------

def build_ingestion_service():
    from app.services.implementations.ingestion_service_impl import DocumentIngestionServiceImpl
    return DocumentIngestionServiceImpl(
        chunker=get_text_chunker(),
        embedding_service=get_embedding_service(),
        vector_store=get_vector_store(),
    )


def build_ai_query_service():
    from app.services.implementations.ai_query_service_impl import AIQueryServiceImpl
    return AIQueryServiceImpl(
        llm_service=get_llm_service(),
        embedding_service=get_embedding_service(),
        vector_store=get_vector_store(),
    )


def build_document_service():
    from app.services.implementations.document_service_impl import DocumentServiceImpl
    return DocumentServiceImpl(ingestion_service=build_ingestion_service())
