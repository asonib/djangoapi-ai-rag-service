from abc import ABC, abstractmethod


class IAIQueryService(ABC):
    @abstractmethod
    def ask_ai(self, user, prompt):
        """Answer a free-form prompt through the ask-ai prompt template. Returns AIQueryLog."""
        pass

    @abstractmethod
    def rag_query(self, user, query):
        """Retrieve the most relevant chunks of the user's documents and answer from them. Returns AIQueryLog."""
        pass

    @abstractmethod
    def get_query_history(self, user):
        """Return the user's AI query history queryset, newest first."""
        pass
