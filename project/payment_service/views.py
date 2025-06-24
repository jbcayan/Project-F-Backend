from rest_framework.generics import ListAPIView
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from django.utils import timezone
from django.utils.timezone import is_naive
from django.utils.timezone import make_aware
from datetime import datetime
from .models import SubscriptionPlan, UserSubscription, SubscriptionStatus
from .serializers import (
    SubscriptionPlanSerializer,
    CreateCheckoutSessionSerializer,
    ConfirmSubscriptionSerializer,
)
from .stripe_client import init_stripe
import stripe
import logging

logger = logging.getLogger(__name__)


def make_aware_safe(dt):
    return timezone.make_aware(dt) if is_naive(dt) else dt


class SubscriptionPlanListView(ListAPIView):
    queryset = SubscriptionPlan.objects.filter(is_active=True).order_by("amount_jpy")
    serializer_class = SubscriptionPlanSerializer
    permission_classes = []


class CreateCheckoutSessionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = CreateCheckoutSessionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user
        plan = serializer.validated_data["plan"]
        success_url = serializer.validated_data["success_url"]
        cancel_url = serializer.validated_data["cancel_url"]

        stripe_api = init_stripe()
        subscription, _ = UserSubscription.objects.get_or_create(user=user)

        # Create or retrieve Stripe customer
        if not subscription.stripe_customer_id:
            customer = stripe_api.Customer.create(email=user.email)
            subscription.stripe_customer_id = customer.id
            subscription.save()
        else:
            customer = stripe_api.Customer.retrieve(subscription.stripe_customer_id)

        try:
            session = stripe_api.checkout.Session.create(
                customer=customer.id,
                payment_method_types=["card"],
                line_items=[{"price": plan.stripe_price_id, "quantity": 1}],
                mode="subscription",
                success_url=success_url,
                cancel_url=cancel_url,
                metadata={
                    "user_id": str(user.id),
                    "plan_id": str(plan.uid),
                },
            )

            # Store session ID for retry/reference
            subscription.stripe_checkout_session_id = session.id
            subscription.save()

            return Response({
                "checkout_url": session.url,
                "session_id": session.id
            }, status=status.HTTP_200_OK)

        except stripe.error.StripeError as e:
            logger.exception("Stripe error during checkout session creation")
            return Response(
                {"detail": f"Stripe error: {str(e)}"},
                status=status.HTTP_502_BAD_GATEWAY
            )


class CancelSubscriptionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        try:
            subscription = user.subscription
        except UserSubscription.DoesNotExist:
            return Response({"detail": "You do not have a subscription."}, status=404)

        if not subscription.stripe_subscription_id:
            return Response({"detail": "No active Stripe subscription found."}, status=400)

        if subscription.cancel_at_period_end:
            return Response({"detail": "Your subscription is already scheduled to cancel."}, status=400)

        stripe_api = init_stripe()

        try:
            updated = stripe_api.Subscription.modify(
                subscription.stripe_subscription_id,
                cancel_at_period_end=True,
            )

            subscription.cancel_at_period_end = True
            end_timestamp = updated.get("current_period_end")
            if end_timestamp:
                subscription.current_period_end = make_aware_safe(datetime.fromtimestamp(end_timestamp))

            subscription.save()

            return Response({
                "detail": "Subscription will be canceled at the end of the billing period.",
                "ends_on": subscription.current_period_end,
            }, status=200)

        except stripe.error.StripeError as e:
            logger.exception("Stripe error during cancel subscription")
            return Response(
                {"detail": f"Stripe error: {str(e)}"},
                status=status.HTTP_502_BAD_GATEWAY
            )


class SubscriptionStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        try:
            subscription = user.subscription
        except UserSubscription.DoesNotExist:
            return Response({
                "has_subscription": False,
                "is_premium": False
            }, status=200)

        return Response({
            "has_subscription": True,
            "is_premium": subscription.is_premium,
            "plan_name": subscription.subscription_plan.name if subscription.subscription_plan else None,
            "status": subscription.status,
            "current_period_end": subscription.current_period_end,
            "cancel_at_period_end": subscription.cancel_at_period_end,
        }, status=200)


class ConfirmSubscriptionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ConfirmSubscriptionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        session_id = serializer.validated_data["session_id"]

        stripe_api = init_stripe()

        try:
            # Step 1: Retrieve checkout session
            session = stripe_api.checkout.Session.retrieve(session_id)

            # Step 2: Get subscription ID from session
            stripe_subscription_id = session.get("subscription")
            if not stripe_subscription_id:
                return Response({"detail": "Subscription not found in session."}, status=400)

            # Step 3: Retrieve full subscription (including items)
            stripe_subscription = stripe_api.Subscription.retrieve(
                stripe_subscription_id,
                expand=["items"]
            )

            # Step 4: Get plan from session metadata
            plan_id = session.metadata.get("plan_id")
            try:
                plan = SubscriptionPlan.objects.get(uid=plan_id)
            except SubscriptionPlan.DoesNotExist:
                return Response({"detail": "Subscription plan not found."}, status=400)

            # Step 5: Safely extract timestamps
            start_timestamp = stripe_subscription.get("start_date")

            # Stripe v2024+ stores current_period_end per item
            items = stripe_subscription.get("items", {}).get("data", [])
            first_item = items[0] if items else {}
            end_timestamp = first_item.get("current_period_end")

            # Step 6: Save to UserSubscription
            subscription, _ = UserSubscription.objects.get_or_create(user=request.user)
            subscription.subscription_plan = plan
            subscription.stripe_subscription_id = stripe_subscription.id
            subscription.stripe_checkout_session_id = session.id
            subscription.status = stripe_subscription.get("status")
            subscription.start_date = make_aware(datetime.fromtimestamp(start_timestamp)) if start_timestamp else None
            subscription.current_period_end = make_aware(datetime.fromtimestamp(end_timestamp)) if end_timestamp else None
            subscription.cancel_at_period_end = stripe_subscription.get("cancel_at_period_end", False)
            subscription.save()

            return Response({
                "detail": "Subscription confirmed successfully.",
                "is_premium": subscription.is_premium,
                "status": subscription.status,
                "current_period_end": subscription.current_period_end,
            }, status=200)

        except stripe.error.StripeError as e:
            logger.exception("Stripe error in confirmation")
            return Response({"detail": f"Stripe error: {str(e)}"}, status=502)