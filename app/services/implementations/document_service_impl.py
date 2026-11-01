import logging
import os
from rest_framework.exceptions import APIException, ValidationError
from app.services.interfaces.document_service_interface import IDocumentService
from app.models.document import Document
from app.config.app_config import AppConfigConstants
from app.exceptions.custom_exceptions import (
    PayloadTooLargeException,
    UnsupportedFileTypeException,
    ResourceNotFoundException,
    ForbiddenOperationException
)

logger = logging.getLogger(__name__)


class DocumentServiceImpl(IDocumentService):
    def __init__(self, ingestion_service=None):
        # Optional IDocumentIngestionService used to purge vectors on delete.
        self.ingestion_service = ingestion_service

    def create_document(self, user, data, file_obj=None):
        if file_obj:
            if file_obj.size > AppConfigConstants.MAX_FILE_SIZE_BYTES:
                raise PayloadTooLargeException()

            _, ext = os.path.splitext(file_obj.name)
            if ext.lower() not in AppConfigConstants.ALLOWED_EXTENSIONS:
                raise UnsupportedFileTypeException(f"Unsupported file format. Allowed: {AppConfigConstants.ALLOWED_EXTENSIONS}")

            title = data.get('title') or file_obj.name
            try:
                content = file_obj.read().decode('utf-8', errors='ignore')
            except Exception:
                content = "[Binary or unreadable file content]"
        else:
            title = data.get('title')
            content = data.get('content')
            if not title or not content:
                raise ValidationError({"detail": "Title and content are required when not uploading a file."})

        return Document.objects.create(title=title, content=content, owner=user)

    def get_user_documents(self, user):
        return Document.objects.filter(owner=user)

    def get_document_by_id(self, document_id, user):
        try:
            document = Document.objects.get(id=document_id)
        except Document.DoesNotExist:
            raise ResourceNotFoundException("Document not found.")

        if document.owner != user:
            raise ResourceNotFoundException("Document not found.")

        return document

    def delete_document(self, document_id, user):
        try:
            document = Document.objects.get(id=document_id)
        except Document.DoesNotExist:
            raise ResourceNotFoundException("Document not found.")

        if document.owner != user:
            raise ForbiddenOperationException("You do not own this document.")

        if self.ingestion_service is not None:
            try:
                self.ingestion_service.remove_document_vectors(user, document.id)
            except APIException:
                # Deletion must not be blocked by the vector index; any stale
                # vectors are ignored at query time because their chunk rows
                # no longer exist.
                logger.warning("Could not remove vectors for document %s", document.id, exc_info=True)

        document.delete()
