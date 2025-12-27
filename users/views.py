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
    
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from drf_spectacular.utils import extend_schema

from assets.models import Asset


class SetFiat(APIView):
    permission_classes = (IsAuthenticated,)
    allowed_methods = ("POST", "OPTIONS", "HEAD")

    @extend_schema(
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "asset_id": {"type": "integer"}
                },
                "required": ["asset_id"]
            }
        },
        responses={200: None},
        description="Set user's preferred fiat currency by asset id"
    )
    def post(self, request, *args, **kwargs):
        user = request.user
        asset_id = request.data.get("asset_id")

        if not asset_id:
            return Response(
                {"error": "asset_id is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            asset = Asset.objects.get(id=asset_id, fiat=True)
        except Asset.DoesNotExist:
            return Response(
                {"error": "Invalid fiat asset"},
                status=status.HTTP_404_NOT_FOUND,
            )

        user.preferred_currency = asset
        user.save(update_fields=["preferred_currency"])

        return Response(
            {
                "message": "Preferred fiat currency updated",
                "currency": asset.symbol,
            },
            status=status.HTTP_200_OK,
        )
