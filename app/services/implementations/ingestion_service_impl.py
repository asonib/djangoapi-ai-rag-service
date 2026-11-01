import logging

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from app.config.app_config import AIConfigConstants
from app.exceptions.custom_exceptions import (
    EmbeddingServiceException,
    EmptyDocumentException,
    ResourceNotFoundException,
    VectorStoreException,
)
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.services.interfaces.embedding_service_interface import IEmbeddingService
from app.services.interfaces.ingestion_service_interface import IDocumentIngestionService
from app.services.interfaces.text_chunker_interface import ITextChunker
from app.services.interfaces.vector_store_interface import IVectorStore

logger = logging.getLogger(__name__)


def user_namespace(user) -> str:
    """Vector-store namespace for a user: guarantees per-tenant isolation of embeddings."""
    return f"user_{user.pk}"


class DocumentIngestionServiceImpl(IDocumentIngestionService):
    def __init__(self, chunker: ITextChunker, embedding_service: IEmbeddingService, vector_store: IVectorStore):
        self.chunker = chunker
        self.embedding_service = embedding_service
        self.vector_store = vector_store

    def _get_owned_document(self, user, document_id) -> Document:
        try:
            # 404 (not 403) for other users' documents so ids cannot be probed.
            return Document.objects.get(id=document_id, owner=user)
        except Document.DoesNotExist:
            raise ResourceNotFoundException("Document not found.")

    @staticmethod
    def _mark_failed(document: Document) -> None:
        Document.objects.filter(pk=document.pk).update(ingestion_status=Document.STATUS_FAILED)

    def ingest_document(self, user, document_id):
        document = self._get_owned_document(user, document_id)

        chunks = self.chunker.split(document.content)
        if not chunks:
            self._mark_failed(document)
            raise EmptyDocumentException()
        if len(chunks) > AIConfigConstants.MAX_CHUNKS_PER_DOCUMENT:
            self._mark_failed(document)
            raise ValidationError({
                "document_id": f"Document produces {len(chunks)} chunks; the limit is "
                               f"{AIConfigConstants.MAX_CHUNKS_PER_DOCUMENT}."
            })

        # Embed first (slowest + most failure-prone step) before touching any state.
        try:
            vectors = self.embedding_service.embed_documents([c.text for c in chunks])
        except EmbeddingServiceException:
            self._mark_failed(document)
            raise

        namespace = user_namespace(user)
        try:
            with transaction.atomic():
                old_ids = list(document.chunks.values_list("id", flat=True))
                document.chunks.all().delete()
                DocumentChunk.objects.bulk_create([
                    DocumentChunk(
                        document=document,
                        chunk_index=c.index,
                        chunk_text=c.text,
                        start_char=c.start_char,
                        end_char=c.end_char,
                    )
                    for c in chunks
                ])
                # Re-read ids in chunk order (portable across DB backends).
                new_ids = list(document.chunks.order_by("chunk_index").values_list("id", flat=True))

                # Vector writes happen inside the DB transaction: if FAISS fails,
                # the chunk rows are rolled back as well.
                self.vector_store.remove(namespace, old_ids)
                self.vector_store.add(namespace, new_ids, vectors)

                document.ingestion_status = Document.STATUS_INGESTED
                document.chunk_count = len(new_ids)
                document.ingested_at = timezone.now()
                document.save(update_fields=["ingestion_status", "chunk_count", "ingested_at"])
        except VectorStoreException:
            self._mark_failed(document)
            raise

        logger.info("Ingested document %s for user %s into %d chunks", document.pk, user.pk, len(new_ids))
        return {
            "document_id": document.pk,
            "title": document.title,
            "status": document.ingestion_status,
            "chunk_count": document.chunk_count,
            "chunk_size": self.chunker.chunk_size,
            "chunk_overlap": self.chunker.chunk_overlap,
            "embedding_model": self.embedding_service.model_name,
            "vector_store": self.vector_store.backend_name,
            "replaced_chunks": len(old_ids),
            "ingested_at": document.ingested_at,
        }

    def remove_document_vectors(self, user, document_id):
        ids = list(DocumentChunk.objects.filter(document_id=document_id, document__owner=user)
                   .values_list("id", flat=True))
        return self.vector_store.remove(user_namespace(user), ids)
