from app.services.interfaces.query_service_interface import IQueryService
from app.models.query_log import QueryLog

class QueryServiceImpl(IQueryService):
    def execute_query(self, user, query_text):
        result_summary = f"Processed response for: {query_text[:60]}..."
        return QueryLog.objects.create(
            user=user,
            query_text=query_text,
            result_summary=result_summary
        )

    def get_query_history(self, user):
        return QueryLog.objects.filter(user=user)
