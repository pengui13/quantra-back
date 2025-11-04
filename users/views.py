from rest_framework import generics
from .serializers import RegisterSerializer, EmailTokenObtainPairSerializer
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer

    @extend_schema(
        request=RegisterSerializer,
        responses={201: RegisterSerializer},
        description="Register a new user"
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)

class EmailTokenObtainPairView(TokenObtainPairView):
    serializer_class = EmailTokenObtainPairSerializer

class Ping(APIView):
    permission_classes = (IsAuthenticated,)
    allowed_methods = ("GET", "OPTIONS", "HEAD")
    def get(self, request):
        return Response({"message": "pong"}, status=200)