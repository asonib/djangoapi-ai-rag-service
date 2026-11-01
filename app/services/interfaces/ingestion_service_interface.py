from abc import ABC, abstractmethod


class IDocumentIngestionService(ABC):
    @abstractmethod
    def ingest_document(self, user, document_id):
        """
        Chunk the user's document, embed every chunk and upsert the vectors in
        the vector store. Re-ingesting replaces the previous chunks.
        Returns a dict describing the ingestion result.
        """
        pass

    @abstractmethod
    def remove_document_vectors(self, user, document_id):
        """Drop every vector belonging to the document from the vector store."""
        pass
