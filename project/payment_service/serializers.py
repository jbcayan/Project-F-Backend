# serializers.py
from rest_framework import serializers
from django.contrib.auth import authenticate
from .models import SubscriptionPlan, PaymentHistory
from django.contrib.auth import get_user_model

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source='profile.full_name', read_only=True)

    class Meta:
        model = User
        fields = ('uid', 'email', 'full_name')


class SubscriptionPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubscriptionPlan
        fields = '__all__'


class PurchaseSerializer(serializers.Serializer):
    item_name = serializers.CharField(max_length=255)
    amount = serializers.IntegerField(min_value=1)


class SubscribeSerializer(serializers.Serializer):
    plan = serializers.ChoiceField(choices=['monthly', 'semiannually'])


class UnivapayChargeSerializer(serializers.Serializer):
    transaction_token_id = serializers.CharField(max_length=36)
    item_name = serializers.CharField(max_length=255)
    amount = serializers.IntegerField(min_value=1)
    redirect_endpoint = serializers.URLField(required=False, allow_null=True)
    three_ds_mode = serializers.ChoiceField(
        choices=['normal', 'require', 'force', 'skip'],
        required=False,
        allow_null=True
    )


class UnivapaySubscriptionSerializer(serializers.Serializer):
    transaction_token_id = serializers.CharField(max_length=36)
    plan = serializers.ChoiceField(choices=['monthly', 'semiannually'])
    redirect_endpoint = serializers.URLField(required=False, allow_null=True)
    three_ds_mode = serializers.ChoiceField(
        choices=['normal', 'require', 'force', 'skip'],
        required=False,
        allow_null=True
    )


class PaymentHistorySerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    subscription_plan = SubscriptionPlanSerializer(read_only=True)

    class Meta:
        model = PaymentHistory
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')


class WebhookEventSerializer(serializers.Serializer):
    event = serializers.CharField(required=False)
    type = serializers.CharField(required=False)
    status = serializers.CharField(required=False)
    object = serializers.CharField(required=False)
    data = serializers.DictField(required=False)

    def validate(self, data):
        # At least one of these should be present
        if not any(key in data for key in ['event', 'type', 'status']):
            raise serializers.ValidationError("At least one of 'event', 'type', or 'status' is required.")
        return data