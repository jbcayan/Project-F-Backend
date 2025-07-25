""" User Management Endpoints """
from django.contrib.auth import get_user_model
from drf_spectacular.utils import extend_schema
from rest_framework import status, generics
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.rest.serializers.user import (
    UserRegistrationSerializer,
    UserLoginSerializer,
    UserSerializer,
    OTPVerificationSerializer,
    UserListSerializer
)
from accounts.utils import is_user_subscribed
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
    request=OTPVerificationSerializer,
    description="End Point for user Login, No Authentication Required",
)
class VerifyOTPView(generics.CreateAPIView):
    def post(self, request, *args, **kwargs):
        serializer = OTPVerificationSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            return Response(
                {"detail": f"OTP verified successfully."},
                status=status.HTTP_200_OK
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


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
        if not user.is_active:
            return Response(
                {"detail": "User is not active"},
                status=status.HTTP_403_FORBIDDEN,
            )
        if not user.is_verified:
            return Response(
                {"detail": "User is not verified"},
                status=status.HTTP_403_FORBIDDEN,
            )

        refresh = RefreshToken.for_user(user)

        response_data = {
            "user": {
                "email": user.email,
                "kind": user.kind,
                "is_subscribed": is_user_subscribed(user),
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
    tags=["Admin"],
)
class UserListView(generics.ListAPIView):
    available_permission_classes = (
        IsSuperAdmin,
        IsAdmin,
    )
    permission_classes = (CheckAnyPermission,)

    serializer_class = UserListSerializer
    queryset = User.objects.all()


@extend_schema(
    summary="End Point for user Detail, Update and Delete for Admin User",
    tags=["Admin"],
)
class UserRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    available_permission_classes = (
        IsSuperAdmin,
        IsAdmin,
        IsEndUser,
    )
    permission_classes = (CheckAnyPermission,)
    serializer_class = UserListSerializer

    def get_object(self):
        user_uid = self.kwargs['uid']
        try:
            return User.objects.get(uid=user_uid)
        except User.DoesNotExist:
            raise NotFound

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

    def perform_destroy(self, instance):
        instance.delete()

