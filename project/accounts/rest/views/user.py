""" User Management Endpoints """
from django.contrib.auth import get_user_model
from drf_spectacular.utils import extend_schema
from rest_framework import status, generics
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.rest.serializers.user import UserRegistrationSerializer, UserLoginSerializer

User = get_user_model()


@extend_schema(
    summary="End Point for user Registration by Email and Password",
    request=UserRegistrationSerializer,
    description="End Point for user Registration, No Authentication Required",
)
class UserRegistrationView(generics.CreateAPIView):
    serializer_class = UserRegistrationSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        # Optionally, you can send a welcome email or perform other actions here


        return Response(
            {"detail": "User registered successfully"},
            status=status.HTTP_201_CREATED,
        )


@extend_schema(
    summary="End Point for user Login by Email and Password",
    request=UserLoginSerializer,
    description="End Point for user Login, No Authentication Required",
)
class UserLoginView(generics.CreateAPIView):
    serializer_class = UserLoginSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data.get("user")

        refresh = RefreshToken.for_user(user)

        response_data = {
            "refresh": str(refresh),
            "access": str(refresh.access_token),
            "user": {
                "email": user.email,
                "kind": user.kind
            }
        }

        return Response(response_data, status=status.HTTP_200_OK)



