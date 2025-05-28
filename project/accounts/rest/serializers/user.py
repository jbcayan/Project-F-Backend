from django.contrib.auth import get_user_model, authenticate
from rest_framework import serializers

from common.helpers import validate_password_complexity

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
        fields = ['email', 'password']
        extra_kwargs = {'password': {'write_only': True}}

    def validate(self, attrs):
        """Ensure password and confirm_password match."""
        if attrs["password"] != attrs["confirm_password"]:
            raise serializers.ValidationError({"confirm_password": "Passwords didn't match."})
        return attrs

    def create(self, validated_data):
        password = validated_data.pop('password', None)
        user = User.objects.create(
            email=validated_data["email"],
        )

        user.set_password(password)
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