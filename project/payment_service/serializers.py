from rest_framework import serializers
from .models import SubscriptionPlan


class SubscriptionPlanSerializer(serializers.ModelSerializer):
    billing_interval_label = serializers.CharField(source='get_billing_interval_display', read_only=True)

    class Meta:
        model = SubscriptionPlan
        fields = (
            "uid",
            "name",
            "description",
            "amount_jpy",
            "billing_interval",
            "billing_interval_label",
            "is_active",
        )


class CreateCheckoutSessionSerializer(serializers.Serializer):
    """
    Serializer to initiate a Stripe Checkout Session for a subscription.
    """
    plan_id = serializers.UUIDField()
    success_url = serializers.URLField()
    cancel_url = serializers.URLField()

    def validate(self, attrs):
        plan_id = attrs.get("plan_id")

        try:
            plan = SubscriptionPlan.objects.get(uid=plan_id, is_active=True)
        except SubscriptionPlan.DoesNotExist:
            raise serializers.ValidationError({
                "plan_id": "Subscription plan not found or inactive."
            })

        if not plan.stripe_price_id:
            raise serializers.ValidationError({
                "plan_id": "This plan is not linked to Stripe."
            })

        attrs["plan"] = plan
        return attrs


class ConfirmSubscriptionSerializer(serializers.Serializer):
    """
    Serializer to confirm Stripe subscription after payment.
    """
    session_id = serializers.CharField()









###### Product Payment Serializers ##########

from rest_framework import serializers
from payment_service.models import PaymentHistory


class PaymentHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentHistory
        fields = [
            "uid",
            "user",
            "order_id",
            "quantity",
            "amount",
            "paid_at",
            "stripe_session_id",
            "stripe_order_id",
            "stripe_payment_status",
            "stripe_response_data",
        ]
        read_only_fields = [
            "uid",
            "user",
            "paid_at",
            "stripe_session_id",
            "stripe_order_id",
            "stripe_payment_status",
            "stripe_response_data",
        ]
