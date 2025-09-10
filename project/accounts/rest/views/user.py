""" User Management Endpoints """
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.http import urlsafe_base64_decode
from drf_spectacular.utils import extend_schema
from rest_framework import status, generics
from rest_framework.exceptions import NotFound
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.models import User
from accounts.rest.serializers.user import (
    UserRegistrationSerializer,
    UserLoginSerializer,
    UserSerializer,
    OTPVerificationSerializer,
    UserListSerializer,
    ChangePasswordSerializer,
    PasswordResetRequestSerializer,
    PasswordResetConfirmSerializer,
)
from accounts.utils import (
    # is_user_subscribed,
    generate_password_reset_token_url)
from common.permission import (
    IsAdmin,
    IsSuperAdmin,
    IsEndUser,
    CheckAnyPermission
)
from gallery.tasks import send_mail_task


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
                # "is_subscribed": is_user_subscribed(user),
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


@extend_schema(
    summary="End Point for user Password Change",
    request=ChangePasswordSerializer,
    description="End Point for user Password Change, Authentication Required",
)
class PasswordChangeView(generics.UpdateAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = ChangePasswordSerializer
    http_method_names = ['put']

    def update(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({
            "detail": "Password changed successfully."
             }, status=status.HTTP_200_OK)


@extend_schema(
    summary="End Point for user Password Reset Request",
    request=PasswordResetRequestSerializer,
    description="End Point for user Password Reset Request, No Authentication Required",
)
class PasswordResetRequestView(generics.GenericAPIView):
    serializer_class = PasswordResetRequestSerializer

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user: User = User.objects.get(email=serializer.validated_data['email'])
        reset_url = generate_password_reset_token_url(user)

        subject = "Password Reset Request"
        text_content = (
            f"Click the link below to reset your password:\n\n"
            f"{reset_url}\n\n"
            f"If you did not request this, please ignore this email.\n\n"
            f"Best regards,\n"
            f"The Alibi Team"
        )
        html_content = (
            f"<p>Click the link below to reset your password:</p>"
            f"<p><a href='{reset_url}'>{reset_url}</a></p>"
            f"<p>If you did not request this, please ignore this email.</p>"
            f"<p>Best regards,<br>The Alibi Team</p>"
        )

        send_mail_task.delay(subject, text_content, html_content, user.email)

        return Response(
            {"detail": "Password reset request sent successfully."},
        )

@extend_schema(
    summary="End Point for user Password Reset Confirm",
    request=PasswordResetConfirmSerializer,
    description="End Point for user Password Reset Confirm, No Authentication Required",
)
class PasswordResetConfirmView(generics.GenericAPIView):
    serializer_class = PasswordResetConfirmSerializer

    def post(self, request, uid, token):
        try:
            user_id = urlsafe_base64_decode(uid).decode()
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return Response({
                "detail": "User does not exist."
            }, status=status.HTTP_404_NOT_FOUND)

        if not PasswordResetTokenGenerator().check_token(user, token):
            return Response({
                "detail": "Invalid or expired token."
            }, status=status.HTTP_400_BAD_REQUEST)

        serializer = PasswordResetConfirmSerializer(
            data=request.data, context={'user': user}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()


        return Response({
            "detail": "Password reset successfully."
        }, status=status.HTTP_200_OK)