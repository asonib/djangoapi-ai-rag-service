from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from rest_framework.exceptions import AuthenticationFailed, ValidationError
from app.services.interfaces.auth_service_interface import IAuthService
from app.models.user_session import UserSession

class AuthServiceImpl(IAuthService):
    def register_user(self, username, password, email=None):
        if User.objects.filter(username=username).exists():
            raise ValidationError({'username': 'Username already taken.'})
        user = User.objects.create_user(username=username, password=password, email=email)
        session = UserSession.create_session(user=user)
        return user, session.token

    def login_user(self, username, password):
        user = authenticate(username=username, password=password)
        if not user:
            raise AuthenticationFailed('Invalid username or password.')
        session = UserSession.create_session(user=user)
        return user, session.token
