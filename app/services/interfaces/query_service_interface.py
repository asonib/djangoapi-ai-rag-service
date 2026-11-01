from abc import ABC, abstractmethod

class IQueryService(ABC):
    @abstractmethod
    def execute_query(self, user, query_text):
        pass

    @abstractmethod
    def get_query_history(self, user):
        pass
