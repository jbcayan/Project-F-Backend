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


from stripe.error import InvalidRequestError

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
        customer = None
        if not subscription.stripe_customer_id:
            customer = stripe_api.Customer.create(email=user.email)
            subscription.stripe_customer_id = customer.id
            subscription.save()
        else:
            try:
                customer = stripe_api.Customer.retrieve(subscription.stripe_customer_id)
            except InvalidRequestError as e:
                logger.warning(f"Invalid Stripe customer ID found: {subscription.stripe_customer_id}. Creating new one.")
                customer = stripe_api.Customer.create(email=user.email)
                subscription.stripe_customer_id = customer.id
                subscription.save()

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
  





###### Product Payment Views ##########

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status, generics, permissions, filters
from django_filters.rest_framework import DjangoFilterBackend

from payment_service.models import PaymentHistory
from payment_service.serializers import PaymentHistorySerializer
from payment_service.stripe_client import init_stripe

from drf_spectacular.utils import (
    extend_schema,
    OpenApiParameter,
    OpenApiExample,
    inline_serializer,
)
from rest_framework import serializers

import uuid
from datetime import datetime
from django.utils.timezone import make_aware

stripe = init_stripe()


# --------- Serializer for POST input ---------
class CreateStripeCheckoutInputSerializer(serializers.Serializer):
    product_id = serializers.CharField()
    amount = serializers.DecimalField(max_digits=10, decimal_places=0)  # JPY = no decimal
    quantity = serializers.IntegerField(required=False, default=1)
    success_url = serializers.URLField()
    cancel_url = serializers.URLField()


# --------- Create Stripe Checkout Session (JPY safe) ---------
@extend_schema(
    request=CreateStripeCheckoutInputSerializer,
    responses={
        200: inline_serializer(
            name="StripeCheckoutResponse",
            fields={"checkout_url": serializers.URLField()}
        ),
        400: OpenApiExample("Bad Request", value={"detail": "Missing required fields."}),
        500: OpenApiExample("Stripe Error", value={"detail": "Stripe error: <error message>"}),
    },
    summary="Create Stripe Checkout Session (JPY)",
    description="Creates a Stripe Checkout Session with amount in JPY and stores the initial PaymentHistory entry.",
)
class CreateStripeCheckoutSessionAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        product_id = request.data.get("product_id")
        amount = request.data.get("amount")
        quantity = request.data.get("quantity", 1)
        success_url = request.data.get("success_url")
        cancel_url = request.data.get("cancel_url")

        if not all([product_id, amount, success_url, cancel_url]):
            return Response(
                {"detail": "Product ID, amount, success_url, and cancel_url are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            amount_jpy = int(float(amount))  # JPY does not support decimals
            internal_uid = str(uuid.uuid4())

            session = stripe.checkout.Session.create(
                payment_method_types=["card"],
                line_items=[
                    {
                        "price_data": {
                            "currency": "jpy",
                            "product_data": {"name": f"Product {product_id}"},
                            "unit_amount": amount_jpy,
                        },
                        "quantity": quantity,
                    }
                ],
                mode="payment",
                success_url=f"{success_url}?session_id={{CHECKOUT_SESSION_ID}}",
                cancel_url=cancel_url,
                metadata={
                    "user_id": str(user.uid),
                    "product_id": product_id,
                    "quantity": quantity,
                    "internal_id": internal_uid,
                },
                customer_email=user.email,
            )

            # Save initial payment record
            PaymentHistory.objects.create(
                user=user,
                product_id=product_id,
                quantity=quantity,
                amount=amount,
                stripe_session_id=session.id,
                stripe_payment_status="created",
            )

            return Response({"checkout_url": session.url}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {"detail": f"Stripe error: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


# --------- Verify Checkout Session & Confirm Payment ---------
@extend_schema(
    summary="Confirm Stripe Checkout Payment",
    description="Verifies if a Stripe Checkout Session was successful and updates the corresponding PaymentHistory record.",
    parameters=[
        OpenApiParameter(name="session_id", required=True, type=str, description="Stripe session ID from success URL"),
    ],
    responses={
        200: inline_serializer(
            name="PaymentConfirmationResponse",
            fields={
                "status": serializers.CharField(),
                "stripe_order_id": serializers.CharField(),
                "amount": serializers.DecimalField(max_digits=10, decimal_places=0),
            }
        ),
        202: OpenApiExample("Pending", value={"status": "open", "detail": "Payment not completed yet."}),
        400: OpenApiExample("Missing session_id", value={"detail": "session_id is required."}),
    }
)
class VerifyStripeSessionAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        session_id = request.query_params.get("session_id")
        if not session_id:
            return Response({"detail": "session_id is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            session = stripe.checkout.Session.retrieve(session_id)

            if session.payment_status != "paid":
                return Response(
                    {"status": session.payment_status, "detail": "Payment not completed yet."},
                    status=status.HTTP_202_ACCEPTED,
                )

            try:
                payment = PaymentHistory.objects.get(stripe_session_id=session.id)
            except PaymentHistory.DoesNotExist:
                return Response(
                    {"detail": "Payment record not found. Cannot confirm."},
                    status=status.HTTP_404_NOT_FOUND,
                )

            # Update record
            payment.paid_at = make_aware(datetime.utcfromtimestamp(session.created))
            payment.stripe_order_id = session.payment_intent
            payment.stripe_payment_status = session.payment_status
            payment.stripe_response_data = session
            payment.save()

            return Response({
                "status": "paid",
                "stripe_order_id": session.payment_intent,
                "amount": float(session.amount_total),  # JPY: no division
            })

        except Exception as e:
            return Response({"detail": f"Stripe error: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# --------- View for listing payment histories ---------
@extend_schema(
    summary="List Payment History",
    description="Returns payment history for the authenticated user. Admins see all. Supports filters and sorting.",
    parameters=[
        OpenApiParameter(name="product_id", required=False, type=str),
        OpenApiParameter(name="stripe_payment_status", required=False, type=str),
        OpenApiParameter(name="status", required=False, type=str),
        OpenApiParameter(name="ordering", required=False, type=str),
    ],
    responses=PaymentHistorySerializer(many=True),
)
class PaymentHistoryListAPIView(generics.ListAPIView):
    serializer_class = PaymentHistorySerializer
    queryset = PaymentHistory.objects.all()
    permission_classes = [permissions.IsAuthenticated]

    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['product_id', 'stripe_payment_status', 'status']
    ordering_fields = ['paid_at', 'amount']
    ordering = ['-paid_at']

    def get_queryset(self):
        user = self.request.user
        if user.kind == "SUPER_ADMIN" or user.is_staff:
            return PaymentHistory.objects.all()
        return PaymentHistory.objects.filter(user=user)
