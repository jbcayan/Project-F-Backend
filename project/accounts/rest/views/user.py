""" User Management Endpoints """
from django.contrib.auth import get_user_model
from drf_spectacular.utils import extend_schema
from rest_framework import status, generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.rest.serializers.user import (
    UserRegistrationSerializer,
    UserLoginSerializer,
    UserSerializer
)

from common.permission import (
    IsAdmin,
    IsSuperAdmin,
    IsEndUser,
    CheckAnyPermission
)

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
            "user": {
                "email": user.email,
                "kind": user.kind
            },
            "refresh": str(refresh),
            "access": str(refresh.access_token),
        }

        return Response(response_data, status=status.HTTP_200_OK)


@extend_schema(
    summary="End Point for user Profile",
    request=UserSerializer,
    description="End Point for user Profile, Authentication Required",
)
class UserProfileView(generics.RetrieveUpdateAPIView):
    available_permission_classes = (
        IsSuperAdmin,
        IsAdmin,
        IsEndUser,
    )
    permission_classes = (CheckAnyPermission,)
    serializer_class = UserSerializer


    def get_object(self):
        return self.request.user


@extend_schema(
    summary="End Point for user List",
    request=UserSerializer,
    description="End Point for user List, Authentication Required",
)
class UserListView(generics.ListAPIView):
    available_permission_classes = (
        IsSuperAdmin,
        IsAdmin,
    )
    permission_classes = (CheckAnyPermission,)

    serializer_class = UserSerializer
    queryset = User.objects.all()



