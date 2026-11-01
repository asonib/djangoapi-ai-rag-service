import logging
import time
from typing import List

from rest_framework.exceptions import ValidationError

from app.config.app_config import AIConfigConstants
from app.models.ai_query_log import AIQueryLog
from app.models.document_chunk import DocumentChunk
from app.prompts.templates import (
    ASK_AI_TEMPLATE,
    RAG_CONTEXT_CHUNK_FORMAT,
    RAG_NO_CONTEXT_ANSWER,
    RAG_QUERY_TEMPLATE,
)
from app.services.implementations.ingestion_service_impl import user_namespace
from app.services.interfaces.ai_query_service_interface import IAIQueryService
from app.services.interfaces.embedding_service_interface import IEmbeddingService
from app.services.interfaces.llm_service_interface import ILLMService
from app.services.interfaces.vector_store_interface import IVectorStore

logger = logging.getLogger(__name__)


def _elapsed_ms(started: float) -> int:
    return int((time.perf_counter() - started) * 1000)


class AIQueryServiceImpl(IAIQueryService):
    def __init__(self, llm_service: ILLMService, embedding_service: IEmbeddingService, vector_store: IVectorStore,
                 top_k: int = AIConfigConstants.RAG_TOP_K,
                 min_similarity: float = AIConfigConstants.RAG_MIN_SIMILARITY):
        self.llm_service = llm_service
        self.embedding_service = embedding_service
        self.vector_store = vector_store
        self.top_k = top_k
        self.min_similarity = min_similarity

    # ------------------------------------------------------------------ ask-ai
    def ask_ai(self, user, prompt):
        prompt = (prompt or "").strip()
        if not prompt:
            raise ValidationError({"prompt": "This field may not be blank."})

        started = time.perf_counter()
        rendered = ASK_AI_TEMPLATE.to_messages(prompt=prompt)
        result = self.llm_service.generate(system=rendered["system"], messages=rendered["messages"])

        return AIQueryLog.objects.create(
            user=user,
            query_type=AIConfigConstants.QUERY_TYPE_ASK_AI,
            input_text=prompt,
            response_text=result.text,
            sources=[],
            prompt_template=ASK_AI_TEMPLATE.name,
            model_name=result.model,
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
            latency_ms=_elapsed_ms(started),
        )

    # --------------------------------------------------------------- rag-query
    def _retrieve(self, user, query) -> List[dict]:
        query_vector = self.embedding_service.embed_query(query)
        # Over-fetch so that stale vectors (e.g. of a deleted document) or
        # low-similarity hits can be dropped while still returning top_k.
        hits = self.vector_store.search(user_namespace(user), query_vector, self.top_k * 3)
        hits = [(cid, score) for cid, score in hits if score >= self.min_similarity]
        if not hits:
            return []

        chunk_map = {
            c.id: c
            for c in DocumentChunk.objects.select_related("document")
            .filter(id__in=[cid for cid, _ in hits], document__owner=user)
        }
        sources = []
        for cid, score in hits:
            chunk = chunk_map.get(cid)
            if chunk is None:
                continue
            sources.append({
                "document_id": chunk.document_id,
                "document_title": chunk.document.title,
                "chunk_id": chunk.id,
                "chunk_index": chunk.chunk_index,
                "chunk_text": chunk.chunk_text,
                "score": round(score, 4),
            })
            if len(sources) >= self.top_k:
                break
        return sources

    @staticmethod
    def _build_context(sources: List[dict]) -> str:
        return "\n\n".join(
            RAG_CONTEXT_CHUNK_FORMAT.format(
                document_id=s["document_id"],
                chunk_index=s["chunk_index"],
                title=s["document_title"].replace('"', "'"),
                chunk_text=s["chunk_text"],
            )
            for s in sources
        )

    def rag_query(self, user, query):
        query = (query or "").strip()
        if not query:
            raise ValidationError({"query": "This field may not be blank."})

        started = time.perf_counter()
        sources = self._retrieve(user, query)

        if sources:
            rendered = RAG_QUERY_TEMPLATE.to_messages(context=self._build_context(sources), query=query)
            result = self.llm_service.generate(system=rendered["system"], messages=rendered["messages"])
            answer, model_name = result.text, result.model
            input_tokens, output_tokens = result.input_tokens, result.output_tokens
        else:
            # Nothing relevant was retrieved: don't spend an LLM call or let the
            # model answer from parametric memory.
            answer, model_name = RAG_NO_CONTEXT_ANSWER, self.llm_service.model_name
            input_tokens = output_tokens = None

        return AIQueryLog.objects.create(
            user=user,
            query_type=AIConfigConstants.QUERY_TYPE_RAG,
            input_text=query,
            response_text=answer,
            sources=sources,
            prompt_template=RAG_QUERY_TEMPLATE.name,
            model_name=model_name,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=_elapsed_ms(started),
        )

    # ----------------------------------------------------------- query-history
    def get_query_history(self, user):
        return AIQueryLog.objects.filter(user=user)
