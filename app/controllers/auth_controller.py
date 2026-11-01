from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from app.services.implementations.auth_service_impl import AuthServiceImpl
from app.serializers.auth_serializers import RegisterSerializer, LoginSerializer

class RegisterController(APIView):
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        auth_service = AuthServiceImpl()
        user, token = auth_service.register_user(
            username=serializer.validated_data['username'],
            password=serializer.validated_data['password'],
            email=serializer.validated_data.get('email')
        )
        return Response({'token': token, 'username': user.username}, status=status.HTTP_201_CREATED)

class LoginController(APIView):
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        auth_service = AuthServiceImpl()
        user, token = auth_service.login_user(
            username=serializer.validated_data['username'],
            password=serializer.validated_data['password']
        )
        return Response({'token': token, 'username': user.username}, status=status.HTTP_200_OK)
