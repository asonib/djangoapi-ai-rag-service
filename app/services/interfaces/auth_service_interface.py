from abc import ABC, abstractmethod

class IAuthService(ABC):
    @abstractmethod
    def register_user(self, username, password, email=None):
        pass

    @abstractmethod
    def login_user(self, username, password):
        pass
