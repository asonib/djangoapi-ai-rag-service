from rest_framework.authentication import BaseAuthentication

class FilterPassthroughAuthentication(BaseAuthentication):
    """
    Bridges the user attached to request by TokenAuthFilterMiddleware
    into DRF's request.user.
    """
    def authenticate(self, request):
        django_user = getattr(request._request, 'user', None)
        if django_user and django_user.is_authenticated:
            return (django_user, getattr(request._request, 'user_session', None))
        return None