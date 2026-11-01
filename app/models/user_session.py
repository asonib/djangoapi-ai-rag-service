import secrets
from datetime import timedelta
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from app.config.app_config import AppConfigConstants

class UserSession(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sessions')
    token = models.CharField(max_length=64, unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    @classmethod
    def create_session(cls, user):
        token = secrets.token_hex(32)
        expiry = timezone.now() + timedelta(days=AppConfigConstants.TOKEN_EXPIRY_DAYS)
        return cls.objects.create(user=user, token=token, expires_at=expiry)

    def is_expired(self):
        return timezone.now() > self.expires_at

    def __str__(self):
        return f"Session({self.user.username}, expires_at={self.expires_at})"
