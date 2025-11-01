from rest_framework import serializers
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

User = get_user_model()


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ["email", "password"]

    def create(self, validated_data):
        return User.objects.create_user(
            email=validated_data["email"],
            password=validated_data["password"]
        )


class EmailTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Override JWT login to use email instead of username."""

    def validate(self, attrs):
        # Replace "username" with "email"
        credentials = {
            "email": attrs.get("email"),
            "password": attrs.get("password")
        }

        # Call default validation
        return super().validate(credentials)

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["email"] = user.email
        return token
