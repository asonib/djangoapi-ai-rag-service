from django.http import JsonResponse
from app.models.user_session import UserSession
from app.config.app_config import AppConfigConstants

class TokenAuthFilterMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path_info
        if any(path.startswith(prefix) for prefix in AppConfigConstants.PUBLIC_URL_PREFIXES):
            return self.get_response(request)

        auth_header = request.headers.get('Authorization', '')
        if not auth_header:
            return JsonResponse({'detail': 'Authentication credentials were not provided.'}, status=401)

        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() not in ['bearer', 'token']:
            return JsonResponse({'detail': 'Invalid token header format. Use: Token <token> or Bearer <token>.'}, status=401)

        token_value = parts[1]
        try:
            session = UserSession.objects.select_related('user').get(token=token_value)
            if session.is_expired():
                return JsonResponse({'detail': 'Token has expired.'}, status=401)
            request.user = session.user
            request.user_session = session
        except UserSession.DoesNotExist:
            return JsonResponse({'detail': 'Invalid authentication token.'}, status=401)

        return self.get_response(request)
