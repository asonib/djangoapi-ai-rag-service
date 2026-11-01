from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

from app.services import container
from app.serializers.document_serializers import DocumentSerializer
from app.controllers.pagination import StandardResultsPagination

class DocumentListCreateController(APIView):
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.document_service = container.build_document_service()

    def post(self, request):
        uploaded_file = request.FILES.get('file')
        document = self.document_service.create_document(
            user=request.user,
            data=request.data,
            file_obj=uploaded_file
        )
        serializer = DocumentSerializer(document)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def get(self, request):
        documents = self.document_service.get_user_documents(request.user)
        paginator = StandardResultsPagination()
        paginated_docs = paginator.paginate_queryset(documents, request)
        serializer = DocumentSerializer(paginated_docs, many=True)
        return paginator.get_paginated_response(serializer.data)

class DocumentDetailController(APIView):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.document_service = container.build_document_service()

    def get(self, request, pk):
        document = self.document_service.get_document_by_id(document_id=pk, user=request.user)
        serializer = DocumentSerializer(document)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def delete(self, request, pk):
        self.document_service.delete_document(document_id=pk, user=request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)
