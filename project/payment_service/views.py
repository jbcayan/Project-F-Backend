# views.py
import os
import json
import threading
import time
from datetime import datetime, timedelta
from django.utils.timezone import now, make_aware

from rest_framework import status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.authtoken.models import Token
from rest_framework.authentication import TokenAuthentication

from django.conf import settings
from django.db import transaction
from django.shortcuts import get_object_or_404

from .models import SubscriptionPlan, PaymentHistory
from .serializers import (
    UserSerializer, SubscriptionPlanSerializer,
    PurchaseSerializer, SubscribeSerializer, UnivapayChargeSerializer,
    UnivapaySubscriptionSerializer, PaymentHistorySerializer,
    WebhookEventSerializer
)
from .univapay_client import UnivapayClient, UnivapayError

# Constants
POLL_AFTER_SECONDS = os.environ.get("POLL_AFTER_SECONDS" or 30)
POLL_RETRY_AFTER_SECONDS = os.environ.get("POLL_RETRY_AFTER_SECONDS" or 60)
ENABLE_POLL_FALLBACK = os.environ.get("ENABLE_POLL_FALLBACK" or True)


# Helper functions
def _coerce_token_id(val):
    """Accept a string or a dict and return a trimmed string id."""
    if val is None:
        return ""
    if isinstance(val, str):
        return val.strip()
    if isinstance(val, dict):
        cand = val.get("id") or val.get("token_id") or val.get("univapayTokenId")
        if isinstance(cand, str):
            return cand.strip()
        return (str(cand) if cand is not None else "").strip()
    return str(val).strip()


def _poll_provider_status_later(kind, provider_id, delay_s, retry=False):
    """
    Schedule a one-off background poll to refresh provider status.
    kind: 'charge' | 'subscription'
    provider_id: PaymentHistory.id
    delay_s: seconds to wait
    retry: whether this is the second attempt
    """
    if not ENABLE_POLL_FALLBACK:
        return

    def _task():
        time.sleep(delay_s)
        try:
            payment = PaymentHistory.objects.get(id=provider_id)
            univapay = UnivapayClient()

            if kind == "charge" and payment.univapay_id:
                data = univapay.get_charge(payment.univapay_id)
            elif kind == "subscription" and payment.univapay_id:
                data = univapay.get_subscription(payment.univapay_id)
            else:
                return

            status_val = (data or {}).get("status")
            if status_val:
                payment.status = status_val
                payment.save(update_fields=['status'])

                # Optional: second attempt if still "pending/awaiting" for charges
                if not retry and kind == "charge" and (status_val in ("pending", "awaiting") or not status_val):
                    _poll_provider_status_later(kind, provider_id, POLL_RETRY_AFTER_SECONDS, retry=True)

        except Exception as e:
            print(f"[Poller] Error polling {kind} provider_id={provider_id}: {e}")

    thread = threading.Thread(target=_task)
    thread.daemon = True
    thread.start()


# Subscription Plan Views
class SubscriptionPlanViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = SubscriptionPlan.objects.filter(is_active=True)
    serializer_class = SubscriptionPlanSerializer
    permission_classes = [AllowAny]


# Payment Views
class PaymentHistoryViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = PaymentHistorySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return PaymentHistory.objects.filter(user=self.request.user).order_by('-created_at')


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def purchase(request):
    serializer = PurchaseSerializer(data=request.data)
    if serializer.is_valid():
        item_name = serializer.validated_data['item_name']
        amount = serializer.validated_data['amount']

        # Create a local payment record
        payment = PaymentHistory.objects.create(
            user=request.user,
            payment_type='one_time',
            amount=amount,
            currency='JPY',
            status='pending',
            mode='test' if settings.DEBUG else 'live',
            created_on=now(),
            metadata={'item_name': item_name}
        )

        return Response({
            'ok': True,
            'payment': PaymentHistorySerializer(payment).data
        }, status=status.HTTP_201_CREATED)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def subscribe(request):
    serializer = SubscribeSerializer(data=request.data)
    if serializer.is_valid():
        plan = serializer.validated_data['plan']

        # Get the subscription plan
        subscription_plan = get_object_or_404(SubscriptionPlan, period=plan, is_active=True)

        # Create a local subscription record
        payment = PaymentHistory.objects.create(
            user=request.user,
            payment_type='recurring',
            subscription_plan=subscription_plan,
            amount=subscription_plan.amount,
            currency=subscription_plan.currency,
            period=subscription_plan.period,
            status='unverified',
            mode='test' if settings.DEBUG else 'live',
            created_on=now(),
            metadata={'plan': plan}
        )

        return Response({
            'ok': True,
            'payment': PaymentHistorySerializer(payment).data
        }, status=status.HTTP_201_CREATED)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def univapay_charge(request):
    serializer = UnivapayChargeSerializer(data=request.data)
    if serializer.is_valid():
        # try:
            token_id = _coerce_token_id(serializer.validated_data['transaction_token_id'])
            item_name = serializer.validated_data['item_name']
            amount = serializer.validated_data['amount']
            redirect_endpoint = serializer.validated_data.get('redirect_endpoint')
            three_ds_mode = serializer.validated_data.get('three_ds_mode')

            univapay = UnivapayClient()
            idem_key = univapay.new_idempotency_key()

            # Create charge with Univapay
            resp = univapay.create_charge(
                transaction_token_id=token_id,
                amount=amount,
                currency="JPY",
                capture=True,
                metadata={"user": request.user.id, "item_name": item_name},
                three_ds_mode=three_ds_mode,
                redirect_endpoint=redirect_endpoint,
                idempotency_key=idem_key,
            )

            # Create local payment record
            payment = PaymentHistory.objects.create(
                user=request.user,
                payment_type='one_time',
                univapay_id=resp.get('id'),
                store_id=resp.get('store_id'),
                transaction_token_id=resp.get('transaction_token_id'),
                amount=amount,
                currency="JPY",
                status=resp.get('status', 'pending'),
                metadata={
                    'user': request.user.id,
                    'item_name': item_name,
                    **resp.get('metadata', {})
                },
                mode=resp.get('mode', 'test'),
                created_on=make_aware(datetime.fromisoformat(resp['created_on'].replace('Z', '+00:00'))),
                redirect_endpoint=resp.get('redirect', {}).get('endpoint'),
                redirect_id=resp.get('redirect', {}).get('redirect_id'),
                raw_json=json.dumps(resp)
            )

            # Schedule a one-off poll as fallback to webhook
            if ENABLE_POLL_FALLBACK and payment.univapay_id:
                _poll_provider_status_later("charge", payment.id, POLL_AFTER_SECONDS)

            return Response({
                'ok': True,
                'payment': PaymentHistorySerializer(payment).data,
                'univapay': {
                    'charge_id': resp.get('id'),
                    'status': resp.get('status'),
                    'mode': resp.get('mode'),
                    'redirect': resp.get('redirect', {}) or resp.get('three_ds', {}),
                }
            }, status=status.HTTP_201_CREATED)

        # except UnivapayError as e:
        #     return Response({
        #         'error': 'UnivaPay charge failed',
        #         'detail': e.body,
        #         'status': e.status
        #     }, status=status.HTTP_400_BAD_REQUEST)
        # except Exception as e:
        #     return Response({
        #         'error': 'Unexpected error creating charge',
        #         'detail': str(e)
        #     }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def univapay_subscription(request):
    serializer = UnivapaySubscriptionSerializer(data=request.data)
    if serializer.is_valid():
        try:
            token_id = _coerce_token_id(serializer.validated_data['transaction_token_id'])
            plan = serializer.validated_data['plan']
            redirect_endpoint = serializer.validated_data.get('redirect_endpoint')
            three_ds_mode = serializer.validated_data.get('three_ds_mode')

            # Get subscription plan details
            subscription_plan = get_object_or_404(SubscriptionPlan, period=plan, is_active=True)

            # Map our plan periods to Univapay periods
            period_map = {
                'monthly': 'monthly',
                '6-month': 'semiannually'
            }
            univapay_period = period_map.get(plan, 'monthly')

            univapay = UnivapayClient()
            idem_key = univapay.new_idempotency_key()

            # Create subscription with Univapay
            resp = univapay.create_subscription(
                transaction_token_id=token_id,
                amount=subscription_plan.amount,
                currency=subscription_plan.currency,
                period=univapay_period,
                metadata={"user": request.user.id, "plan": plan},
                three_ds_mode=three_ds_mode,
                redirect_endpoint=redirect_endpoint,
                idempotency_key=idem_key,
            )

            # Create local subscription record
            payment = PaymentHistory.objects.create(
                user=request.user,
                payment_type='recurring',
                subscription_plan=subscription_plan,
                univapay_id=resp.get('id'),
                store_id=resp.get('store_id'),
                transaction_token_id=resp.get('transaction_token_id'),
                amount=subscription_plan.amount,
                currency=subscription_plan.currency,
                period=univapay_period,
                status=resp.get('status', 'unverified'),
                metadata={
                    'user': request.user.username,
                    'plan': plan,
                    **resp.get('metadata', {})
                },
                mode=resp.get('mode', 'test'),
                created_on=make_aware(datetime.fromisoformat(resp['created_on'].replace('Z', '+00:00'))),
                next_payment_due_date=resp.get('next_payment', {}).get('due_date'),
                next_payment_id=resp.get('next_payment', {}).get('id'),
                raw_json=json.dumps(resp)
            )

            # Schedule a one-off poll as fallback to webhook
            if ENABLE_POLL_FALLBACK and payment.univapay_id:
                _poll_provider_status_later("subscription", payment.id, POLL_AFTER_SECONDS)

            return Response({
                'ok': True,
                'payment': PaymentHistorySerializer(payment).data,
                'univapay': {
                    'subscription_id': resp.get('id'),
                    'status': resp.get('status'),
                    'mode': resp.get('mode'),
                    'next_payment': resp.get('next_payment', {}),
                }
            }, status=status.HTTP_201_CREATED)

        except UnivapayError as e:
            return Response({
                'error': 'UnivaPay subscription failed',
                'detail': e.body,
                'status': e.status
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({
                'error': 'Unexpected error creating subscription',
                'detail': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def univapay_webhook(request):
    # Verify webhook authentication if configured
    webhook_auth = getattr(settings, 'UNIVAPAY_WEBHOOK_AUTH', None)
    if webhook_auth:
        auth_header = request.headers.get('Authorization', '')
        expected = f'Bearer {webhook_auth}'
        if auth_header != expected:
            return Response({'error': 'Unauthorized webhook'}, status=status.HTTP_401_UNAUTHORIZED)

    # Parse and validate webhook data
    serializer = WebhookEventSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    data = serializer.validated_data
    event_type = data.get('event') or data.get('type') or data.get('status')
    obj = data.get('object')
    data_obj = data.get('data') or {}

    # Extract IDs from various possible shapes
    charge_id = None
    subscription_id = None

    if obj in ('charge', 'charges'):
        charge_id = data.get('id') or data_obj.get('id')
    elif obj in ('subscription', 'subscriptions'):
        subscription_id = data.get('id') or data_obj.get('id')
    else:
        # Try nested shapes
        charge_id = (data.get('charge', {}) or {}).get('id') or data_obj.get('charge_id')
        subscription_id = (data.get('subscription', {}) or {}).get('id') or data_obj.get('subscription_id')

    new_status = data.get('status') or data_obj.get('status')

    # Update payment status if we found an ID
    updated = False
    if charge_id:
        try:
            payment = PaymentHistory.objects.get(univapay_id=charge_id)
            if new_status:
                payment.status = new_status
                payment.save(update_fields=['status'])
                updated = True
        except PaymentHistory.DoesNotExist:
            pass

    if subscription_id and not updated:
        try:
            payment = PaymentHistory.objects.get(univapay_id=subscription_id)
            if new_status:
                payment.status = new_status
                payment.save(update_fields=['status'])
                updated = True
        except PaymentHistory.DoesNotExist:
            pass

    return Response({'ok': True, 'updated': updated})