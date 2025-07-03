from django.utils import timezone
from datetime import timedelta

from django.contrib.auth import get_user_model, authenticate
from django.db import transaction
from rest_framework import serializers

from accounts.utils import generate_unique_otp, is_user_subscribed
from common.choices import UserKind
from common.helpers import validate_password_complexity

from accounts.models import OTP
from gallery.tasks import send_mail_task

User = get_user_model()

class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password_complexity],
    )
    confirm_password = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = ['email', 'password', 'confirm_password']
        extra_kwargs = {'password': {'write_only': True}}

    def validate(self, attrs):
        """Ensure password and confirm_password match."""
        if attrs["password"] != attrs["confirm_password"]:
            raise serializers.ValidationError({"confirm_password": "Passwords didn't match."})
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        password = validated_data.pop('password', None)
        user = User.objects.create(
            email=validated_data["email"],
        )
        user.kind = UserKind.END_USER

        user.set_password(password)
        user.save()

        # Create OTP
        otp = generate_unique_otp()
        OTP.objects.create(
            user=user,
            otp=otp,
        )

        # Send OTP to user email
        subject = "OTP"
        text_content = (
            f"Hello {user.email},\n\n"
            f"Your One-Time Password (OTP) is: {otp}\n\n"
            f"Please use this OTP to verify your account. It is valid for the next 24 hours.\n\n"
            f"If you did not request this, please ignore this email.\n\n"
            f"Best regards,\n"
            f"The Alibi Team"
        )
        html_content = (
            f"<p>Hello {user.email},</p>"
            f"<p>Your <strong>One-Time Password (OTP)</strong> is: "
            f"<strong style='font-size: 18px; color: #2c3e50;'>{otp}</strong></p>"
            f"<p>Please use this OTP to verify your account. It is valid for the next 24 hours.</p>"
            f"<p>If you did not request this, please ignore this email.</p>"
            f"<p>Best regards,<br><strong>The Alibi Team</strong></p>"
        )
        send_mail_task.delay(subject, text_content, html_content, user.email)
        return user


class OTPVerificationSerializer(serializers.Serializer):
    otp = serializers.CharField(max_length=6)

    def validate_otp(self, value):
        try:
            otp_instance = OTP.objects.select_related('user').get(
                otp=value,
                is_used=False,
                created_at__gte=timezone.now() - timedelta(hours=24)
            )
        except OTP.DoesNotExist:
            raise serializers.ValidationError("Invalid or expired OTP.")
        self.otp_instance = otp_instance
        return value

    def save(self, **kwargs):
        otp_instance = self.otp_instance
        otp_instance.is_used = True
        otp_instance.save()

        user = otp_instance.user
        user.is_verified = True
        user.save()

        return user



class UserLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField()

    def validate(self, attrs):
        email = attrs.get("email")
        password = attrs.get("password")

        if email and password:
            user = authenticate(request=self.context.get("request"), email=email, password=password)

            if not user:
                raise serializers.ValidationError(
                    {"detail": "Unable to log in with provided credentials."
                     }, code="authorization"
                )
        else:
            raise serializers.ValidationError({
                "detail": "Must include email and password."
            }, code="authorization")

        attrs["user"] = user
        return attrs


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['email', 'kind']


class UserListSerializer(serializers.ModelSerializer):
    is_subscribed = serializers.SerializerMethodField(
        read_only=True,
    )
    class Meta:
        model = User
        fields = [
            "email",
            "is_active",
            "kind",
            "is_verified",
            "is_subscribed",
        ]
        read_only_fields = [
            "is_subscribed",
        ]

    def get_is_subscribed(self, obj):
        return is_user_subscribed(obj)