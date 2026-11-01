from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from app.services.implementations.query_service_impl import QueryServiceImpl
from app.serializers.query_serializers import QueryLogSerializer
from app.controllers.pagination import StandardResultsPagination

class QueryController(APIView):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.query_service = QueryServiceImpl()

    def post(self, request):
        query_text = request.data.get('query_text')
        if not query_text:
            return Response({'query_text': 'This field is required.'}, status=status.HTTP_400_BAD_REQUEST)

        query_log = self.query_service.execute_query(user=request.user, query_text=query_text)
        serializer = QueryLogSerializer(query_log)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

class QueryHistoryController(APIView):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.query_service = QueryServiceImpl()

    def get(self, request):
        queries = self.query_service.get_query_history(user=request.user)
        paginator = StandardResultsPagination()
        paginated_queries = paginator.paginate_queryset(queries, request)
        serializer = QueryLogSerializer(paginated_queries, many=True)
        return paginator.get_paginated_response(serializer.data)
