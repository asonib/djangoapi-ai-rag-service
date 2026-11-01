from rest_framework.exceptions import APIException
from rest_framework.views import exception_handler
from rest_framework import status

class PayloadTooLargeException(APIException):
    status_code = status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
    default_detail = 'File size exceeds maximum allowed limit.'
    default_code = 'file_too_large'

class UnsupportedFileTypeException(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = 'File type is not permitted.'
    default_code = 'invalid_file_type'

class ResourceNotFoundException(APIException):
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = 'Requested resource not found.'
    default_code = 'not_found'

class ForbiddenOperationException(APIException):
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = 'You do not have permission to perform this operation.'
    default_code = 'forbidden'


# ---------------------------------------------------------------------------
# AI / RAG layer exceptions (Assignment 3A)
# ---------------------------------------------------------------------------

class EmptyDocumentException(APIException):
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    default_detail = 'Document has no extractable text content to ingest.'
    default_code = 'empty_document'

class LLMNotConfiguredException(APIException):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_detail = 'LLM provider is not configured. Set ANTHROPIC_API_KEY in the environment.'
    default_code = 'llm_not_configured'

class LLMServiceException(APIException):
    status_code = status.HTTP_502_BAD_GATEWAY
    default_detail = 'The upstream LLM provider failed to produce a response.'
    default_code = 'llm_upstream_error'

class EmbeddingServiceException(APIException):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_detail = 'Embedding model is unavailable.'
    default_code = 'embedding_unavailable'

class VectorStoreException(APIException):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_detail = 'Vector store operation failed.'
    default_code = 'vector_store_error'


def custom_exception_handler(exc, context):
    return exception_handler(exc, context)
