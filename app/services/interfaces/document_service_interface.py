from abc import ABC, abstractmethod

class IDocumentService(ABC):
    @abstractmethod
    def create_document(self, user, data, file_obj=None):
        pass

    @abstractmethod
    def get_user_documents(self, user):
        pass

    @abstractmethod
    def get_document_by_id(self, document_id, user):
        pass

    @abstractmethod
    def delete_document(self, document_id, user):
        pass
