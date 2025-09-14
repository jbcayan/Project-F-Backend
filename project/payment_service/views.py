import os
import json
import threading
import time
import hmac
import hashlib
from datetime import datetime
from django.utils.timezone import now, make_aware
from django.utils import timezone

from rest_framework import status, viewsets, mixins
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.views import APIView
from rest_framework.authentication import SessionAuthentication, TokenAuthentication

from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter, OpenApiExample
from drf_spectacular.types import OpenApiTypes

from django.conf import settings
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from .models import SubscriptionPlan, PaymentHistory, TransactionToken
from .serializers import (
    SubscriptionPlanSerializer,
    PurchaseSerializer, 
    SubscribeSerializer, 
    UnivapayChargeSerializer,
    UnivapaySubscriptionSerializer, 
    PaymentHistorySerializer,
    PaymentHistoryListSerializer,
    WebhookEventSerializer,
    WebhookChargeSerializer,
    WebhookSubscriptionSerializer,
    CancelSubscriptionSerializer,
    RefundChargeSerializer,
    PaymentStatusSerializer,
    CreateTransactionTokenSerializer,
    TransactionTokenSerializer
)
from .univapay_client import UnivapayClient, UnivapayError, UNIVAPAY_WEBHOOK_AUTH

# Constants
POLL_AFTER_SECONDS = 30
POLL_RETRY_AFTER_SECONDS = 60
ENABLE_POLL_FALLBACK = True


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


def verify_webhook_signature(request):
    """Verify Univapay webhook signature using HMAC-SHA256."""
    if not UNIVAPAY_WEBHOOK_AUTH:
        return True  # Skip verification if not configured (dev only)
    
    signature = request.headers.get('X-Signature', '')
    if not signature:
        return False
    
    # Get raw body
    body = request.body
    
    # Calculate expected signature
    expected_signature = hmac.new(
        UNIVAPAY_WEBHOOK_AUTH.encode(),
        body,
        hashlib.sha256
    ).hexdigest()
    
    # Secure comparison
    return hmac.compare_digest(signature, expected_signature)


def parse_datetime(dt_string):
    """Parse datetime string from Univapay API responses."""
    if not dt_string:
        return None
    try:
        # Handle ISO format with Z timezone
        if dt_string.endswith('Z'):
            dt_string = dt_string.replace('Z', '+00:00')
        # Parse and make timezone aware
        dt = datetime.fromisoformat(dt_string)
        if timezone.is_naive(dt):
            dt = make_aware(dt)
        return dt
    except Exception as e:
        print(f"Error parsing datetime '{dt_string}': {e}")
        return None


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
                old_status = payment.status
                payment.status = status_val
                
                # Update other fields that might have changed
                update_fields = ['status', 'updated_at']
                
                if kind == "charge":
                    # Update charge-specific fields
                    if data.get('charged_amount') is not None:
                        payment.charged_amount = data.get('charged_amount')
                        update_fields.append('charged_amount')
                    if data.get('charged_currency'):
                        payment.charged_currency = data.get('charged_currency')
                        update_fields.append('charged_currency')
                    if data.get('charged_amount_formatted') is not None:
                        payment.charged_amount_formatted = data.get('charged_amount_formatted')
                        update_fields.append('charged_amount_formatted')
                    if data.get('fee_amount') is not None:
                        payment.fee_amount = data.get('fee_amount')
                        update_fields.append('fee_amount')
                    if data.get('fee_currency'):
                        payment.fee_currency = data.get('fee_currency')
                        update_fields.append('fee_currency')
                    if data.get('fee_amount_formatted') is not None:
                        payment.fee_amount_formatted = data.get('fee_amount_formatted')
                        update_fields.append('fee_amount_formatted')
                    
                    # Update the main amount field if charged_amount is available
                    if data.get('charged_amount') is not None:
                        payment.amount = data.get('charged_amount')
                        update_fields.append('amount')
                    if data.get('charged_currency'):
                        payment.currency = data.get('charged_currency')
                        update_fields.append('currency')
                        
                elif kind == "subscription":
                    # Update subscription-specific fields
                    if data.get('amount') is not None:
                        payment.amount = data.get('amount')
                        update_fields.append('amount')
                    if data.get('currency'):
                        payment.currency = data.get('currency')
                        update_fields.append('currency')
                    if data.get('amount_formatted') is not None:
                        payment.amount_formatted = data.get('amount_formatted')
                        update_fields.append('amount_formatted')
                    if data.get('period'):
                        payment.period = data.get('period')
                        update_fields.append('period')
                    if data.get('cyclical_period'):
                        payment.cyclical_period = data.get('cyclical_period')
                        update_fields.append('cyclical_period')
                    
                    # Update next payment details
                    next_payment = data.get('next_payment', {})
                    if next_payment:
                        if next_payment.get('id'):
                            payment.next_payment_id = next_payment.get('id')
                            update_fields.append('next_payment_id')
                        if next_payment.get('due_date'):
                            payment.next_payment_due_date = next_payment.get('due_date')
                            update_fields.append('next_payment_due_date')
                        if next_payment.get('zone_id'):
                            payment.next_payment_zone_id = next_payment.get('zone_id')
                            update_fields.append('next_payment_zone_id')
                        if next_payment.get('amount') is not None:
                            payment.next_payment_amount = next_payment.get('amount')
                            update_fields.append('next_payment_amount')
                        if next_payment.get('currency'):
                            payment.next_payment_currency = next_payment.get('currency')
                            update_fields.append('next_payment_currency')
                        if next_payment.get('amount_formatted') is not None:
                            payment.next_payment_amount_formatted = next_payment.get('amount_formatted')
                            update_fields.append('next_payment_amount_formatted')
                        if next_payment.get('is_paid') is not None:
                            payment.next_payment_is_paid = next_payment.get('is_paid')
                            update_fields.append('next_payment_is_paid')
                        if next_payment.get('is_last_payment') is not None:
                            payment.next_payment_is_last_payment = next_payment.get('is_last_payment')
                            update_fields.append('next_payment_is_last_payment')
                        if next_payment.get('created_on'):
                            payment.next_payment_created_on = parse_datetime(next_payment.get('created_on'))
                            update_fields.append('next_payment_created_on')
                        if next_payment.get('updated_on'):
                            payment.next_payment_updated_on = parse_datetime(next_payment.get('updated_on'))
                            update_fields.append('next_payment_updated_on')
                        if next_payment.get('retry_date'):
                            payment.next_payment_retry_date = next_payment.get('retry_date')
                            update_fields.append('next_payment_retry_date')
                
                payment.save(update_fields=update_fields)

                # Optional: second attempt if still "pending/awaiting" for charges
                if not retry and kind == "charge" and status_val in ("pending", "awaiting"):
                    _poll_provider_status_later(kind, provider_id, POLL_RETRY_AFTER_SECONDS, retry=True)

        except Exception as e:
            # Log error for monitoring purposes
            pass

    thread = threading.Thread(target=_task)
    thread.daemon = True
    thread.start()


# Widget Configuration Endpoint
@extend_schema(
    tags=['Payment Widget'],
    summary='Get Univapay Widget Configuration',
    description='Retrieves the configuration needed to initialize the Univapay payment widget on the frontend.',
    responses={
        200: {
            'description': 'Widget configuration retrieved successfully',
            'examples': {
                'application/json': {
                    'app_token': 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...',
                    'mode': 'test',
                    'store_id': '11f06e27-a6a8-5c72-836c-17d938e5f8be',
                    'widget_url': 'https://widget.univapay.com/client/checkout.js',
                    'api_endpoint': 'https://api.univapay.com'
                }
            }
        },
        401: {'description': 'Authentication required'}
    }
)
class WidgetConfigView(APIView):
    """
    API endpoint to get widget configuration for frontend.
    
    This endpoint provides the necessary configuration data to initialize
    the Univapay payment widget on the frontend, including the app token,
    store ID, and API endpoints.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Return widget configuration for frontend initialization."""
        
        config = {
            'app_token': os.getenv('UNIVAPAY_APP_TOKEN', ''),
            'mode': 'test' if settings.DEBUG else 'live',
            'store_id': os.getenv('UNIVAPAY_STORE_ID', ''),
            'widget_url': 'https://widget.univapay.com/client/checkout.js',
            'api_endpoint': os.getenv('UNIVAPAY_BASE_URL', 'https://api.univapay.com')
        }
        
        return Response(config)


# Subscription Plan Views
@extend_schema_view(
    list=extend_schema(
        tags=['Subscription Plans'],
        summary='List Available Subscription Plans',
        description='Retrieve all active subscription plans available for purchase.',
        responses={
            200: SubscriptionPlanSerializer(many=True)
        }
    ),
    retrieve=extend_schema(
        tags=['Subscription Plans'],
        summary='Get Subscription Plan Details',
        description='Retrieve detailed information about a specific subscription plan.',
        responses={
            200: SubscriptionPlanSerializer,
            404: {'description': 'Subscription plan not found'}
        }
    )
)
class SubscriptionPlanViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for viewing subscription plans.
    
    This endpoint provides access to all active subscription plans
    available for purchase. No authentication is required to view plans.
    """
    queryset = SubscriptionPlan.objects.filter(is_active=True)
    serializer_class = SubscriptionPlanSerializer
    permission_classes = [AllowAny]


# Payment History Views
@extend_schema_view(
    list=extend_schema(
        tags=['Payment History'],
        summary='List User Payment History',
        description='Retrieve all payment history for the authenticated user, including both one-time payments and subscriptions with comprehensive details.',
        responses={
            200: {
                'description': 'Payment history retrieved successfully',
                'examples': {
                    'application/json': [
                        {
                            'id': 5,
                            'user_email': 'user@example.com',
                            'payment_type': 'one_time',
                            'amount': '9800.00',
                            'currency': 'JPY',
                            'amount_formatted': '¥9,800',
                            'charged_amount': '9800.00',
                            'charged_currency': 'JPY',
                            'charged_amount_formatted': '¥9,800',
                            'fee_amount': '294.00',
                            'fee_currency': 'JPY',
                            'fee_amount_formatted': '¥294',
                            'status': 'completed',
                            'status_display': 'Completed',
                            'is_successful': True,
                            'transaction_token_last_four': '0000',
                            'transaction_token_brand': 'visa',
                            'univapay_id': '11f0915e-46b1-bb10-a5fb-9b084b293c0f',
                            'created_at': '2025-01-17T10:30:00Z'
                        },
                        {
                            'id': 9,
                            'user_email': 'user@example.com',
                            'payment_type': 'recurring',
                            'amount': '18000.00',
                            'currency': 'JPY',
                            'amount_formatted': '¥18,000',
                            'status': 'current',
                            'status_display': 'Current',
                            'is_successful': True,
                            'period': 'monthly',
                            'next_payment_due_date': '2025-09-14',
                            'next_payment_amount': '18000.00',
                            'next_payment_currency': 'JPY',
                            'subscription_plan_name': 'Premium Plan',
                            'subscription_plan_description': 'Monthly premium subscription',
                            'transaction_token_last_four': '0000',
                            'transaction_token_brand': 'visa',
                            'univapay_id': '11f09161-6936-f7ec-bbb6-a323a8a85f3c',
                            'created_at': '2025-01-17T10:30:00Z'
                        }
                    ]
                }
            },
            401: {'description': 'Authentication required'}
        }
    ),
    retrieve=extend_schema(
        tags=['Payment History'],
        summary='Get Payment Details',
        description='Retrieve detailed information about a specific payment record.',
        responses={
            200: PaymentHistorySerializer,
            401: {'description': 'Authentication required'},
            404: {'description': 'Payment not found'}
        }
    )
)
class PaymentHistoryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for viewing payment history.
    
    This endpoint provides access to the user's payment history, including
    both one-time payments and recurring subscriptions. Users can only
    view their own payment records.
    """
    serializer_class = PaymentHistoryListSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return PaymentHistory.objects.filter(
            user=self.request.user
        ).select_related(
            'transaction_token',
            'subscription_plan'
        ).order_by('-created_at')

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return PaymentHistorySerializer
        return PaymentHistoryListSerializer

    @extend_schema(
        tags=['Payment History'],
        summary='List User Subscriptions',
        description='Retrieve all subscription records for the authenticated user. Useful for finding subscription IDs for cancellation.',
        responses={
            200: {
                'description': 'Subscription records retrieved successfully',
                'examples': {
                    'application/json': {
                        'subscriptions': [
                            {
                                'id': 9,
                                'user_email': 'user@example.com',
                                'payment_type': 'recurring',
                                'amount': '18000.00',
                                'currency': 'JPY',
                                'amount_formatted': '¥18,000',
                                'status': 'current',
                                'status_display': 'Current',
                                'is_successful': True,
                                'period': 'monthly',
                                'next_payment_due_date': '2025-09-14',
                                'next_payment_amount': '18000.00',
                                'next_payment_currency': 'JPY',
                                'univapay_id': '11f09161-6936-f7ec-bbb6-a323a8a85f3c',
                                'created_at': '2025-01-17T10:30:00Z'
                            }
                        ],
                        'count': 1
                    }
                }
            },
            401: {'description': 'Authentication required'}
        }
    )
    @action(detail=False, methods=['get'])
    def subscriptions(self, request):
        """Get all subscription records for the user."""
        
        subscriptions = PaymentHistory.objects.filter(
            user=request.user,
            payment_type='recurring'
        ).select_related(
            'transaction_token',
            'subscription_plan'
        ).order_by('-created_at')
        
        
        serializer = PaymentHistoryListSerializer(subscriptions, many=True)
        return Response({
            'subscriptions': serializer.data,
            'count': subscriptions.count()
        })


# Transaction Token Views
@extend_schema_view(
    list=extend_schema(
        tags=['Transaction Tokens'],
        summary='List User Transaction Tokens',
        description='Retrieve all transaction tokens for the authenticated user.',
        responses={
            200: TransactionTokenSerializer(many=True),
            401: {'description': 'Authentication required'}
        }
    ),
    retrieve=extend_schema(
        tags=['Transaction Tokens'],
        summary='Get Transaction Token Details',
        description='Retrieve details of a specific transaction token.',
        responses={
            200: TransactionTokenSerializer,
            401: {'description': 'Authentication required'},
            404: {'description': 'Transaction token not found'}
        }
    ),
    create=extend_schema(
        tags=['Transaction Tokens'],
        summary='Create Transaction Token',
        description='Create a new transaction token.',
        responses={
            201: TransactionTokenSerializer,
            400: {'description': 'Invalid data provided'},
            401: {'description': 'Authentication required'}
        }
    ),
    update=extend_schema(
        tags=['Transaction Tokens'],
        summary='Update Transaction Token',
        description='Update an existing transaction token.',
        responses={
            200: TransactionTokenSerializer,
            400: {'description': 'Invalid data provided'},
            401: {'description': 'Authentication required'},
            404: {'description': 'Transaction token not found'}
        }
    ),
    partial_update=extend_schema(
        tags=['Transaction Tokens'],
        summary='Partially Update Transaction Token',
        description='Partially update an existing transaction token.',
        responses={
            200: TransactionTokenSerializer,
            400: {'description': 'Invalid data provided'},
            401: {'description': 'Authentication required'},
            404: {'description': 'Transaction token not found'}
        }
    ),
    destroy=extend_schema(
        tags=['Transaction Tokens'],
        summary='Delete Transaction Token',
        description='Delete a transaction token.',
        responses={
            204: {'description': 'Transaction token deleted successfully'},
            401: {'description': 'Authentication required'},
            404: {'description': 'Transaction token not found'}
        }
    )
)
class TransactionTokenViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing transaction tokens.
    
    Transaction tokens represent saved payment methods (cards, bank accounts, etc.)
    that can be reused for future payments without requiring the user to re-enter
    their payment details.
    """
    serializer_class = TransactionTokenSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return TransactionToken.objects.filter(
            user=self.request.user
        ).order_by('-created_at')

    @extend_schema(
        tags=['Transaction Tokens'],
        summary='Store Transaction Token from Widget',
        description='Store a transaction token received from the Univapay widget response. This endpoint processes the token data returned by the payment widget and saves it for future use.',
        request={
            'application/json': {
                'type': 'object',
                'properties': {
                    'id': {
                        'type': 'string',
                        'format': 'uuid',
                        'description': 'Unique identifier for the transaction token from Univapay'
                    },
                    'type': {
                        'type': 'string',
                        'enum': ['one_time', 'subscription', 'recurring'],
                        'description': 'Type of transaction token'
                    },
                    'email': {
                        'type': 'string',
                        'format': 'email',
                        'description': 'Email address associated with the token'
                    },
                    'data': {
                        'type': 'object',
                        'description': 'Token data containing card/billing information',
                        'properties': {
                            'card': {
                                'type': 'object',
                                'description': 'Card information'
                            },
                            'billing': {
                                'type': 'object',
                                'description': 'Billing address information'
                            }
                        }
                    },
                    'mode': {
                        'type': 'string',
                        'enum': ['test', 'live'],
                        'description': 'Environment mode'
                    }
                },
                'required': ['id', 'type', 'email', 'data', 'mode']
            }
        },
        responses={
            200: {
                'description': 'Token already exists and was updated',
                'examples': {
                    'application/json': {
                        'id': 7,
                        'user': {'id': 1, 'email': 'user@example.com'},
                        'univapay_token_id': '11f0915e-4510-7904-b51c-abed498a7343',
                        'token_type': 'recurring',
                        'card_last_four': '0000',
                        'card_brand': 'visa'
                    }
                }
            },
            201: {
                'description': 'New token created successfully',
                'examples': {
                    'application/json': {
                        'id': 8,
                        'user': {'id': 1, 'email': 'user@example.com'},
                        'univapay_token_id': '11f0915f-0093-0fe8-b51c-67fa2fce35a9',
                        'token_type': 'recurring',
                        'card_last_four': '0000',
                        'card_brand': 'visa'
                    }
                }
            },
            400: {'description': 'Invalid token data provided'},
            401: {'description': 'Authentication required'}
        }
    )
    @action(detail=False, methods=['post'])
    def store_token(self, request):
        """
        Store a transaction token from Univapay widget response.
        Expected format from widget:
        {
            "id": "uuid",
            "type": "one_time|subscription|recurring",
            "email": "user@example.com",
            "data": {
                "card": {...},
                "billing": {...}
            },
            "mode": "test|live"
        }
        """
        
        try:
            # Extract data from widget response
            token_id = request.data.get('id')
            token_type = request.data.get('type', 'one_time')
            email = request.data.get('email', request.user.email)
            data = request.data.get('data', {})
            mode = request.data.get('mode', 'test')
            
            
            if not token_id:
                return Response(
                    {'error': 'Token ID is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Extract card details if present
            card_data = data.get('card', {})
            billing_data = data.get('billing', {})
            
            with transaction.atomic():
                # Check if token already exists
                existing_token = TransactionToken.objects.filter(
                    univapay_token_id=token_id
                ).first()
                
                if existing_token:
                    # Update last_used_at
                    existing_token.last_used_at = now()
                    existing_token.save(update_fields=['last_used_at', 'updated_at'])
                    response_data = TransactionTokenSerializer(existing_token).data
                    return Response(
                        response_data,
                        status=status.HTTP_200_OK
                    )
                
                # Create new token
                
                # Extract CVV and 3DS data from the correct location
                cvv_data = data.get('cvvAuthorize', {})
                three_ds_data = data.get('threeDs', {})
                
                token = TransactionToken.objects.create(
                    user=request.user,
                    univapay_token_id=token_id,
                    token_type=token_type,
                    payment_type=request.data.get('paymentType', 'card'),
                    email=email,
                    card_last_four=card_data.get('lastFour'),
                    card_brand=card_data.get('brand'),
                    card_exp_month=card_data.get('expMonth'),
                    card_exp_year=card_data.get('expYear'),
                    card_bin=card_data.get('cardBin'),
                    card_type=card_data.get('cardType'),
                    card_category=card_data.get('category'),
                    card_issuer=card_data.get('issuer'),
                    billing_data=billing_data,
                    cvv_authorize_enabled=cvv_data.get('enabled', False),
                    cvv_authorize_status=cvv_data.get('status'),
                    three_ds_enabled=three_ds_data.get('enabled', False),
                    three_ds_status=three_ds_data.get('status'),
                    usage_limit=request.data.get('usageLimit'),
                    mode=mode,
                    raw_token_data=request.data,
                    last_used_at=now()
                )
                
                response_data = TransactionTokenSerializer(token).data
                return Response(
                    response_data,
                    status=status.HTTP_201_CREATED
                )
                
        except Exception as e:
            return Response(
                {'error': f'Failed to store token: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        """Deactivate a transaction token."""
        token = self.get_object()
        token.is_active = False
        token.save(update_fields=['is_active', 'updated_at'])
        return Response({'status': 'Token deactivated'})


# Simple Payment Views (without Univapay integration)
@extend_schema(
    tags=['Simple Payments'],
    summary='Create Simple Purchase Record',
    description='Create a simple purchase record for testing/demo purposes. This endpoint does not integrate with Univapay and creates local payment records only.',
    request=PurchaseSerializer,
    responses={
        201: {
            'description': 'Purchase record created successfully',
            'examples': {
                'application/json': {
                    'ok': True,
                    'payment': {
                        'id': 1,
                        'user': {'id': 1, 'email': 'user@example.com'},
                        'amount': '1000.00',
                        'currency': 'JPY',
                        'status': 'completed',
                        'payment_type': 'one_time'
                    }
                }
            }
        },
        400: {'description': 'Invalid request data'},
        401: {'description': 'Authentication required'}
    }
)
class PurchaseView(APIView):
    """
    API endpoint for creating a simple purchase record (testing/demo).
    
    This endpoint creates local payment records without integrating with
    external payment providers. Useful for testing and demonstration purposes.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        
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

            response_data = {
                'ok': True,
                'payment': PaymentHistorySerializer(payment).data
            }
            return Response(response_data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    tags=['Simple Payments'],
    summary='Create Simple Subscription Record',
    description='Create a simple subscription record for testing/demo purposes. This endpoint does not integrate with Univapay and creates local subscription records only.',
    request=SubscribeSerializer,
    responses={
        201: {
            'description': 'Subscription record created successfully',
            'examples': {
                'application/json': {
                    'ok': True,
                    'payment': {
                        'id': 2,
                        'user': {'id': 1, 'email': 'user@example.com'},
                        'amount': '5000.00',
                        'currency': 'JPY',
                        'status': 'current',
                        'payment_type': 'recurring',
                        'period': 'monthly'
                    }
                }
            }
        },
        400: {'description': 'Invalid request data'},
        401: {'description': 'Authentication required'}
    }
)
class SubscribeView(APIView):
    """
    API endpoint for creating a simple subscription record (testing/demo).
    
    This endpoint creates local subscription records without integrating with
    external payment providers. Useful for testing and demonstration purposes.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        
        serializer = SubscribeSerializer(data=request.data)
        if serializer.is_valid():
            plan_id = serializer.validated_data['plan'].id

            # Get the subscription plan
            subscription_plan = get_object_or_404(SubscriptionPlan, id=plan_id, is_active=True)

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
                metadata={'plan': subscription_plan.name}
            )

            response_data = {
                'ok': True,
                'payment': PaymentHistorySerializer(payment).data
            }
            return Response(response_data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# Univapay Payment Views
@extend_schema(
    tags=['Univapay Payments'],
    summary='Create One-Time Payment Charge',
    description='Create a one-time payment charge using Univapay. This endpoint processes payments using saved transaction tokens.',
    request=UnivapayChargeSerializer,
    responses={
        201: {
            'description': 'Charge created successfully',
            'examples': {
                'application/json': {
                    'ok': True,
                    'payment': {
                        'id': 5,
                        'user': {'id': 1, 'email': 'user@example.com'},
                        'amount': '9800.00',
                        'currency': 'JPY',
                        'status': 'pending',
                        'payment_type': 'one_time',
                        'univapay_id': '11f0915e-46b1-bb10-a5fb-9b084b293c0f'
                    },
                    'univapay': {
                        'charge_id': '11f0915e-46b1-bb10-a5fb-9b084b293c0f',
                        'status': 'pending',
                        'mode': 'test'
                    }
                }
            }
        },
        400: {
            'description': 'Invalid request data or payment failed',
            'examples': {
                'application/json': {
                    'error': 'UnivaPay charge failed',
                    'detail': 'Insufficient funds',
                    'status': 402
                }
            }
        },
        401: {'description': 'Authentication required'},
        500: {'description': 'Internal server error'}
    }
)
class UnivapayChargeView(APIView):
    """
    API endpoint for creating a charge with Univapay.
    
    This endpoint processes one-time payments using saved transaction tokens.
    It creates a charge with Univapay and stores the payment record locally.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        
        serializer = UnivapayChargeSerializer(data=request.data)
        if serializer.is_valid():
            try:
                token_id = _coerce_token_id(serializer.validated_data['transaction_token_id'])
                amount = serializer.validated_data['amount']
                currency = serializer.validated_data.get('currency', 'JPY')
                metadata = serializer.validated_data.get('metadata', {})
                
                
                # Get or create TransactionToken record
                token_record = None
                try:
                    token_record = TransactionToken.objects.get(
                        univapay_token_id=token_id,
                        user=request.user
                    )
                    token_record.last_used_at = now()
                    token_record.save(update_fields=['last_used_at', 'updated_at'])
                except TransactionToken.DoesNotExist:
                    # Token doesn't exist in our DB, but we can still proceed with the charge
                    pass
                
                univapay = UnivapayClient()
                idem_key = univapay.new_idempotency_key()

                # Create charge with Univapay
                resp = univapay.create_charge(
                    transaction_token_id=token_id,
                    amount=amount,
                    currency=currency,
                    metadata=metadata,
                    only_direct_currency=serializer.validated_data.get('only_direct_currency', False),
                    capture_at=serializer.validated_data.get('capture_at'),
                    descriptor=serializer.validated_data.get('descriptor'),
                    descriptor_phone_number=serializer.validated_data.get('descriptor_phone_number'),
                    redirect_endpoint=serializer.validated_data.get('redirect', {}).get('endpoint') if serializer.validated_data.get('redirect') else None,
                    three_ds_mode=serializer.validated_data.get('three_ds', {}).get('mode', 'normal') if serializer.validated_data.get('three_ds') else 'normal',
                    idempotency_key=idem_key,
                )

                error_data = resp.get('error') or {}

                # Create local payment record with TransactionToken link
                
                # Prepare payment data with proper field mapping
                payment_data = {
                    'user': request.user,
                    'payment_type': 'one_time',
                    'transaction_token': token_record,  # Link the token if it exists
                    'univapay_id': resp.get('id'),
                    'store_id': resp.get('store_id'),
                    'univapay_transaction_token_id': resp.get('transaction_token_id'),
                    'transaction_token_type': resp.get('transaction_token_type'),
                    'subscription_id': resp.get('subscription_id'),
                    'merchant_transaction_id': resp.get('merchant_transaction_id'),
                    'requested_amount': resp.get('requested_amount'),
                    'requested_currency': resp.get('requested_currency'),
                    'requested_amount_formatted': resp.get('requested_amount_formatted'),
                    'charged_amount': resp.get('charged_amount'),
                    'charged_currency': resp.get('charged_currency'),
                    'charged_amount_formatted': resp.get('charged_amount_formatted'),
                    'fee_amount': resp.get('fee_amount'),
                    'fee_currency': resp.get('fee_currency'),
                    'fee_amount_formatted': resp.get('fee_amount_formatted'),
                    'amount': resp.get('charged_amount') or resp.get('requested_amount') or amount,
                    'currency': resp.get('charged_currency') or resp.get('requested_currency') or currency,
                    'amount_formatted': resp.get('charged_amount_formatted') or resp.get('requested_amount_formatted'),
                    'only_direct_currency': resp.get('only_direct_currency'),
                    'capture_at': parse_datetime(resp.get('capture_at')),
                    'descriptor': resp.get('descriptor'),
                    'descriptor_phone_number': resp.get('descriptor_phone_number'),
                    'status': resp.get('status', 'pending'),
                    'error_code': error_data.get('code'),
                    'error_message': error_data.get('message'),
                    'error_detail': error_data.get('detail'),
                    'metadata': resp.get('metadata', {}),
                    'mode': resp.get('mode', 'test'),
                    'created_on': parse_datetime(resp.get('created_on')) or now(),
                    'redirect_endpoint': resp.get('redirect', {}).get('endpoint') if resp.get('redirect') else None,
                    'redirect_id': resp.get('redirect', {}).get('redirect_id') if resp.get('redirect') else None,
                    'three_ds_redirect_endpoint': resp.get('three_ds', {}).get('redirect_endpoint') if resp.get('three_ds') else None,
                    'three_ds_redirect_id': resp.get('three_ds', {}).get('redirect_id') if resp.get('three_ds') else None,
                    'three_ds_mode': resp.get('three_ds', {}).get('mode') if resp.get('three_ds') else None,
                    'raw_json': resp
                }
                
                payment = PaymentHistory.objects.create(**payment_data)

                # Schedule a one-off poll as fallback to webhook
                if ENABLE_POLL_FALLBACK and payment.univapay_id:
                    try:
                        _poll_provider_status_later("charge", payment.id, POLL_AFTER_SECONDS)
                    except Exception as e:
                        pass

                try:
                    response_data = {
                    'ok': True,
                    'payment': PaymentHistorySerializer(payment).data,
                    'univapay': {
                        'charge_id': resp.get('id'),
                        'status': resp.get('status'),
                        'mode': resp.get('mode'),
                        'redirect': resp.get('redirect') or resp.get('three_ds'),
                    }
                    }
                    return Response(response_data, status=status.HTTP_201_CREATED)
                except Exception as e:
                    # Return a simple success response if serialization fails
                    return Response({
                        'ok': True,
                        'payment_id': payment.id,
                        'univapay_id': resp.get('id'),
                        'status': resp.get('status')
                }, status=status.HTTP_201_CREATED)

            except UnivapayError as e:
                return Response({
                    'error': 'UnivaPay charge failed',
                    'detail': e.body,
                    'status': e.status
                }, status=status.HTTP_400_BAD_REQUEST)
            except Exception as e:
                return Response({
                    'error': 'Unexpected error creating charge',
                    'detail': str(e)
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    tags=['Univapay Payments'],
    summary='Create Recurring Subscription',
    description='Create a recurring subscription using Univapay. This endpoint sets up automatic recurring payments using saved transaction tokens.',
    request=UnivapaySubscriptionSerializer,
    responses={
        201: {
            'description': 'Subscription created successfully',
            'examples': {
                'application/json': {
                    'ok': True,
                    'payment': {
                        'id': 9,
                        'user': {'id': 1, 'email': 'user@example.com'},
                        'amount': '18000.00',
                        'currency': 'JPY',
                        'status': 'unverified',
                        'payment_type': 'recurring',
                        'period': 'monthly',
                        'univapay_id': '11f09161-6936-f7ec-bbb6-a323a8a85f3c'
                    },
                    'univapay': {
                        'subscription_id': '11f09161-6936-f7ec-bbb6-a323a8a85f3c',
                        'status': 'unverified',
                        'mode': 'test',
                        'period': 'monthly',
                        'next_payment': {
                            'due_date': '2025-09-14',
                            'amount': 18000,
                            'currency': 'JPY'
                        }
                    }
                }
            }
        },
        400: {
            'description': 'Invalid request data or subscription failed',
            'examples': {
                'application/json': {
                    'error': 'UnivaPay subscription failed',
                    'detail': 'Invalid period specified',
                    'status': 400
                }
            }
        },
        401: {'description': 'Authentication required'},
        500: {'description': 'Internal server error'}
    }
)
class UnivapaySubscriptionView(APIView):
    """
    API endpoint for creating a subscription with Univapay.
    
    This endpoint sets up recurring subscriptions using saved transaction tokens.
    It creates a subscription with Univapay and stores the payment record locally.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        
        serializer = UnivapaySubscriptionSerializer(data=request.data)
        if serializer.is_valid():
            
            # Check if user already has an active subscription
            existing_subscription = PaymentHistory.objects.filter(
                user=request.user,
                payment_type='recurring',
                status__in=['current', 'active', 'unverified']
            ).first()
            
            if existing_subscription:
                return Response({
                    'error': 'User already has an active subscription',
                    'detail': f'You already have an active subscription (ID: {existing_subscription.id}). Please cancel your current subscription before creating a new one.',
                    'existing_subscription': {
                        'id': existing_subscription.id,
                        'univapay_id': existing_subscription.univapay_id,
                        'status': existing_subscription.status,
                        'amount': str(existing_subscription.amount),
                        'currency': existing_subscription.currency,
                        'period': existing_subscription.period,
                        'created_at': existing_subscription.created_at.isoformat()
                    }
                }, status=status.HTTP_409_CONFLICT)
            
            try:
                token_id = _coerce_token_id(serializer.validated_data['transaction_token_id'])
                amount = serializer.validated_data['amount']
                currency = serializer.validated_data.get('currency', 'JPY')
                period = serializer.validated_data['period']
                metadata = serializer.validated_data.get('metadata', {})
                
                
                # Get or create TransactionToken record
                token_record = None
                try:
                    token_record = TransactionToken.objects.get(
                        univapay_token_id=token_id,
                        user=request.user
                    )
                    token_record.last_used_at = now()
                    token_record.save(update_fields=['last_used_at', 'updated_at'])
                except TransactionToken.DoesNotExist:
                    # Token doesn't exist in our DB, but we can still proceed
                    pass
                
                univapay = UnivapayClient()
                idem_key = univapay.new_idempotency_key()

                # Create subscription with Univapay
                resp = univapay.create_subscription(
                    transaction_token_id=token_id,
                    amount=amount,
                    currency=currency,
                    period=period,
                    metadata=metadata,
                    only_direct_currency=serializer.validated_data.get('only_direct_currency', False),
                    initial_amount=serializer.validated_data.get('initial_amount'),
                    schedule_settings=serializer.validated_data.get('schedule_settings', {}),
                    first_charge_capture_after=serializer.validated_data.get('first_charge_capture_after'),
                    first_charge_authorization_only=serializer.validated_data.get('first_charge_authorization_only', False),
                    redirect_endpoint=serializer.validated_data.get('redirect', {}).get('endpoint') if serializer.validated_data.get('redirect') else None,
                    three_ds_mode=serializer.validated_data.get('three_ds', {}).get('mode', 'normal') if serializer.validated_data.get('three_ds') else 'normal',
                    idempotency_key=idem_key,
                )


                next_payment_data = resp.get('next_payment', {})

                # Prepare subscription data with proper field mapping
                subscription_data = {
                    'user': request.user,
                    'payment_type': 'recurring',
                    'transaction_token': token_record,  # Link the token if it exists
                    'univapay_id': resp.get('id'),
                    'store_id': resp.get('store_id'),
                    'univapay_transaction_token_id': resp.get('transaction_token_id'),
                    'amount': resp.get('amount'),
                    'currency': resp.get('currency'),
                    'amount_formatted': resp.get('amount_formatted'),
                    'initial_amount': resp.get('initial_amount'),
                    'initial_amount_formatted': resp.get('initial_amount_formatted'),
                    'subsequent_cycles_start': resp.get('subsequent_cycles_start'),
                    'schedule_settings': resp.get('schedule_settings', {}),
                    'only_direct_currency': resp.get('only_direct_currency'),
                    'first_charge_capture_after': resp.get('first_charge_capture_after'),
                    'first_charge_authorization_only': resp.get('first_charge_authorization_only'),
                    'status': resp.get('status', 'unverified'),
                    'metadata': resp.get('metadata', {}),
                    'mode': resp.get('mode', 'test'),
                    'created_on': parse_datetime(resp.get('created_on')) or now(),
                    'period': resp.get('period'),
                    'cyclical_period': resp.get('cyclical_period'),
                    'next_payment_id': next_payment_data.get('id'),
                    'next_payment_due_date': next_payment_data.get('due_date'),
                    'next_payment_zone_id': next_payment_data.get('zone_id'),
                    'next_payment_amount': next_payment_data.get('amount'),
                    'next_payment_currency': next_payment_data.get('currency'),
                    'next_payment_amount_formatted': next_payment_data.get('amount_formatted'),
                    'next_payment_is_paid': next_payment_data.get('is_paid', False),
                    'next_payment_is_last_payment': next_payment_data.get('is_last_payment', False),
                    'next_payment_created_on': parse_datetime(next_payment_data.get('created_on')),
                    'next_payment_updated_on': parse_datetime(next_payment_data.get('updated_on')),
                    'next_payment_retry_date': next_payment_data.get('retry_date'),
                    'redirect_endpoint': resp.get('redirect', {}).get('endpoint') if resp.get('redirect') else None,
                    'redirect_id': resp.get('redirect', {}).get('redirect_id') if resp.get('redirect') else None,
                    'three_ds_redirect_endpoint': resp.get('three_ds', {}).get('redirect_endpoint') if resp.get('three_ds') else None,
                    'three_ds_redirect_id': resp.get('three_ds', {}).get('redirect_id') if resp.get('three_ds') else None,
                    'three_ds_mode': resp.get('three_ds', {}).get('mode') if resp.get('three_ds') else None,
                    'raw_json': resp
                }
                
                payment = PaymentHistory.objects.create(**subscription_data)

                # Schedule a one-off poll as fallback to webhook
                if ENABLE_POLL_FALLBACK and payment.univapay_id:
                    try:
                        _poll_provider_status_later("subscription", payment.id, POLL_AFTER_SECONDS)
                    except Exception as e:
                        pass

                try:
                    response_data = {
                    'ok': True,
                    'payment': PaymentHistorySerializer(payment).data,
                    'univapay': {
                        'subscription_id': resp.get('id'),
                        'status': resp.get('status'),
                        'mode': resp.get('mode'),
                            'period': resp.get('period'),
                        'next_payment': resp.get('next_payment', {}),
                    }
                    }
                    return Response(response_data, status=status.HTTP_201_CREATED)
                except Exception as e:
                    # Return a simple success response if serialization fails
                    return Response({
                        'ok': True,
                        'payment_id': payment.id,
                        'univapay_id': resp.get('id'),
                        'status': resp.get('status')
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


@extend_schema(
    tags=['Univapay Payments'],
    summary='Cancel Current Subscription',
    description='Cancel the current active subscription for the authenticated user. If no subscription_id is provided, it will automatically detect and cancel the current subscription.',
    request={
        'application/json': {
            'type': 'object',
            'properties': {
                'subscription_id': {
                    'type': 'string',
                    'format': 'uuid',
                    'description': 'Optional: Specific subscription ID to cancel. If not provided, will cancel the current active subscription.',
                    'nullable': True
                },
                'termination_mode': {
                    'type': 'string',
                    'enum': ['immediate', 'on_next_payment'],
                    'description': 'When to cancel the subscription',
                    'default': 'immediate'
                },
                'reason': {
                    'type': 'string',
                    'description': 'Reason for cancellation (optional)',
                    'maxLength': 500
                }
            }
        }
    },
    responses={
        200: {
            'description': 'Subscription cancelled successfully',
            'examples': {
                'application/json': {
                    'ok': True,
                    'payment': {
                        'id': 9,
                        'univapay_id': '11f09161-6936-f7ec-bbb6-a323a8a85f3c',
                        'status': 'canceled',
                        'amount': '18000.00',
                        'currency': 'JPY',
                        'period': 'monthly'
                    },
                    'univapay': {
                        'status': 'canceled'
                    }
                }
            }
        },
        404: {
            'description': 'No active subscription found',
            'examples': {
                'application/json': {
                    'error': 'No active subscription found',
                    'detail': 'You do not have any active subscription to cancel.',
                    'user_id': 1
                }
            }
        },
        200: {
            'description': 'Subscription cancelled successfully (even if Univapay returned 404)',
            'examples': {
                'application/json': {
                    'ok': True,
                    'payment': {
                        'id': 9,
                        'univapay_id': '11f09161-6936-f7ec-bbb6-a323a8a85f3c',
                        'status': 'canceled',
                        'amount': '18000.00',
                        'currency': 'JPY',
                        'period': 'monthly',
                        'cancelled_on': '2025-01-17T10:30:00Z'
                    },
                    'univapay': None,
                    'message': 'Subscription marked as cancelled locally. Univapay returned 404 (subscription not found in their system).'
                }
            }
        },
        400: {
            'description': 'Invalid request or subscription not found',
            'examples': {
                'application/json': {
                    'error': 'Invalid cancellation request',
                    'detail': 'Invalid termination mode specified',
                    'status': 400
                }
            }
        },
        401: {'description': 'Authentication required'}
    }
)
class CancelSubscriptionView(APIView):
    """
    API endpoint for canceling a subscription.
    
    This endpoint cancels the current active subscription for the authenticated user.
    If no subscription_id is provided, it automatically detects and cancels the current subscription.
    Users can only have one active subscription at a time.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        
        serializer = CancelSubscriptionSerializer(data=request.data)
        if serializer.is_valid():
            try:
                subscription_id = serializer.validated_data.get('subscription_id')
                termination_mode = serializer.validated_data.get('termination_mode', 'immediate')
                reason = serializer.validated_data.get('reason', '')

                # If no subscription_id provided, find the current active subscription
                if not subscription_id:
                    current_subscription = PaymentHistory.objects.filter(
                        user=request.user,
                        payment_type='recurring',
                        status__in=['current', 'active', 'unverified']
                    ).order_by('-created_at').first()
                    
                    if not current_subscription:
                        return Response({
                            'error': 'No active subscription found',
                            'detail': 'You do not have any active subscription to cancel.',
                            'user_id': request.user.id
                        }, status=status.HTTP_404_NOT_FOUND)
                    
                    subscription_id = current_subscription.univapay_id
                else:
                    pass
                
                # Verify the subscription belongs to the user
                payment = PaymentHistory.objects.filter(
                    univapay_id=subscription_id,
                    user=request.user,
                    payment_type='recurring'
                ).first()
                
                if not payment:
                    return Response({
                        'error': 'Subscription not found',
                        'detail': f'Subscription with ID {subscription_id} was not found or does not belong to you.',
                        'subscription_id': str(subscription_id)
                    }, status=status.HTTP_404_NOT_FOUND)
                
                univapay = UnivapayClient()

                # Cancel subscription with Univapay
                resp = univapay.cancel_subscription(
                    subscription_id=subscription_id,
                    termination_mode=termination_mode,
                    reason=reason
                )

                # Update local payment record
                payment.status = 'canceled'
                payment.cancelled_on = now()
                payment.termination_mode = termination_mode
                payment.save(update_fields=['status', 'cancelled_on', 'termination_mode', 'updated_at'])

                return Response({
                    'ok': True,
                    'payment': PaymentHistorySerializer(payment).data,
                    'univapay': resp
                }, status=status.HTTP_200_OK)

            except UnivapayError as e:
                
                # Handle specific error cases
                if e.status == 404:
                    # If subscription not found in Univapay, check if it's already cancelled locally
                    if payment.status == 'canceled':
                        return Response({
                            'ok': True,
                            'payment': PaymentHistorySerializer(payment).data,
                            'univapay': None,
                            'message': 'Subscription was already cancelled locally. Univapay returned 404 (not found).'
                        }, status=status.HTTP_200_OK)
                    else:
                        # Mark as cancelled locally even if Univapay doesn't have it
                        payment.status = 'canceled'
                        payment.cancelled_on = now()
                        payment.termination_mode = termination_mode
                        payment.save(update_fields=['status', 'cancelled_on', 'termination_mode', 'updated_at'])
                        
                        return Response({
                            'ok': True,
                            'payment': PaymentHistorySerializer(payment).data,
                            'univapay': None,
                            'message': 'Subscription marked as cancelled locally. Univapay returned 404 (subscription not found in their system).'
                        }, status=status.HTTP_200_OK)
                elif e.status == 400:
                    return Response({
                        'error': 'Invalid cancellation request',
                        'detail': e.body,
                        'status': e.status
                    }, status=status.HTTP_400_BAD_REQUEST)
                else:
                    return Response({
                        'error': 'UnivaPay subscription cancellation failed',
                        'detail': e.body,
                        'status': e.status
                    }, status=status.HTTP_400_BAD_REQUEST)
            except Exception as e:
                return Response({
                    'error': 'Unexpected error canceling subscription',
                    'detail': str(e)
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class RefundChargeView(APIView):
    """
    API endpoint for refunding a charge.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = RefundChargeSerializer(data=request.data)
        if serializer.is_valid():
            try:
                charge_id = serializer.validated_data['charge_id']
                amount = serializer.validated_data.get('amount')
                reason = serializer.validated_data.get('reason', '')
                metadata = serializer.validated_data.get('metadata', {})

                univapay = UnivapayClient()
                idem_key = univapay.new_idempotency_key()

                # Refund charge with Univapay
                resp = univapay.refund_charge(
                    charge_id=charge_id,
                    amount=amount,
                    reason=reason,
                    metadata=metadata,
                    idempotency_key=idem_key,
                )

                # Update local payment record
                payment = get_object_or_404(
                    PaymentHistory, 
                    univapay_id=charge_id, 
                    user=request.user,
                    payment_type='one_time'
                )
                
                # Set status based on refund amount
                if amount and amount < payment.amount:
                    payment.status = 'partially_refunded'
                else:
                    payment.status = 'refunded'
                
                payment.save(update_fields=['status', 'updated_at'])

                return Response({
                    'ok': True,
                    'payment': PaymentHistorySerializer(payment).data,
                    'univapay': resp
                }, status=status.HTTP_200_OK)

            except UnivapayError as e:
                return Response({
                    'error': 'UnivaPay refund failed',
                    'detail': e.body,
                    'status': e.status
                }, status=status.HTTP_400_BAD_REQUEST)
            except Exception as e:
                return Response({
                    'error': 'Unexpected error processing refund',
                    'detail': str(e)
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PaymentStatusView(APIView):
    """
    API endpoint for checking payment status.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = PaymentStatusSerializer(data=request.data)
        if serializer.is_valid():
            try:
                payment_id = serializer.validated_data['payment_id']
                payment_type = serializer.validated_data['payment_type']

                univapay = UnivapayClient()

                if payment_type == 'charge':
                    resp = univapay.get_charge(payment_id)
                elif payment_type == 'subscription':
                    resp = univapay.get_subscription(payment_id)
                else:
                    return Response({
                        'error': 'Invalid payment type. Must be "charge" or "subscription"'
                    }, status=status.HTTP_400_BAD_REQUEST)

                # Update local payment record if it exists
                payment = PaymentHistory.objects.filter(
                    univapay_id=payment_id, 
                    user=request.user
                ).first()
                
                if payment:
                    payment.status = resp.get('status', payment.status)
                    payment.save(update_fields=['status', 'updated_at'])
                    
                    return Response({
                        'ok': True,
                        'payment': PaymentHistorySerializer(payment).data,
                        'univapay': resp
                    }, status=status.HTTP_200_OK)
                else:
                    # Payment not found in local DB, return Univapay data only
                    return Response({
                        'ok': True,
                        'payment': None,
                        'univapay': resp
                    }, status=status.HTTP_200_OK)

            except UnivapayError as e:
                return Response({
                    'error': 'UnivaPay status check failed',
                    'detail': e.body,
                    'status': e.status
                }, status=status.HTTP_400_BAD_REQUEST)
            except Exception as e:
                return Response({
                    'error': 'Unexpected error checking status',
                    'detail': str(e)
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    tags=['Subscription Status'],
    summary='Check User Subscription Status and Premium Access',
    description='Check the subscription status and premium access for the authenticated user. Distinguishes between subscription status and premium access - users maintain premium access until their paid period expires, even if subscription is cancelled. Status "current" means active subscription with premium access.',
    responses={
        200: {
            'description': 'Active subscription with premium access',
            'examples': {
                'application/json': {
                    'has_active_subscription': True,
                    'has_premium_access': True,
                    'subscription_status': 'current',
                    'access_level': 'premium',
                    'subscription': {
                        'id': 9,
                        'amount': '18000.00',
                        'currency': 'JPY',
                        'period': 'monthly',
                        'status': 'current',
                        'next_payment_due_date': '2025-09-14',
                        'created_at': '2025-01-17T10:30:00Z',
                        'has_premium_access': True,
                        'access_expires_at': '2025-09-14T00:00:00Z'
                    },
                    'premium_features': {
                        'can_access_premium_content': True,
                        'can_download_files': True,
                        'can_use_advanced_features': True,
                        'can_create_unlimited_projects': True,
                        'can_export_data': True,
                        'can_access_priority_support': True
                    },
                    'user_id': 1,
                    'checked_at': '2025-01-17T10:30:00Z'
                }
            }
        },
        200: {
            'description': 'Cancelled subscription but still has premium access',
            'examples': {
                'application/json': {
                    'has_active_subscription': False,
                    'has_premium_access': True,
                    'subscription_status': 'canceled',
                    'access_level': 'premium',
                    'subscription': {
                        'id': 9,
                        'amount': '18000.00',
                        'currency': 'JPY',
                        'period': 'monthly',
                        'status': 'canceled',
                        'cancelled_on': '2025-01-15T10:30:00Z',
                        'next_payment_due_date': '2025-09-14',
                        'created_at': '2025-01-17T10:30:00Z',
                        'has_premium_access': True,
                        'access_expires_at': '2025-09-14T00:00:00Z'
                    },
                    'premium_features': {
                        'can_access_premium_content': True,
                        'can_download_files': True,
                        'can_use_advanced_features': True,
                        'can_create_unlimited_projects': True,
                        'can_export_data': True,
                        'can_access_priority_support': True
                    },
                    'user_id': 1,
                    'checked_at': '2025-01-17T10:30:00Z'
                }
            }
        },
        200: {
            'description': 'No subscription or expired access',
            'examples': {
                'application/json': {
                    'has_active_subscription': False,
                    'has_premium_access': False,
                    'subscription_status': None,
                    'access_level': 'free',
                    'subscription': None,
                    'premium_features': {
                        'can_access_premium_content': False,
                        'can_download_files': False,
                        'can_use_advanced_features': False,
                        'can_create_unlimited_projects': False,
                        'can_export_data': False,
                        'can_access_priority_support': False
                    },
                    'user_id': 1,
                    'checked_at': '2025-01-17T10:30:00Z'
                }
            }
        },
        401: {'description': 'Authentication required'}
    }
)
class SubscriptionStatusView(APIView):
    """
    API endpoint for checking user subscription status.
    
    This endpoint provides the current subscription status for the authenticated user,
    helping the frontend determine what features and content the user can access.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        
        try:
            # Get the most recent subscription for the user (regardless of status)
            latest_subscription = PaymentHistory.objects.filter(
                user=request.user,
                payment_type='recurring'
            ).order_by('-created_at').first()
            
            
            if latest_subscription:
                # Determine subscription status and premium access separately
                subscription_status = latest_subscription.status
                has_premium_access = self._has_premium_access(latest_subscription)
                
                subscription_data = PaymentHistorySerializer(latest_subscription).data
                
                # Add access information to subscription data
                subscription_data['has_premium_access'] = has_premium_access
                subscription_data['access_expires_at'] = self._get_access_expiry_date(latest_subscription)
                
                access_level = 'premium' if has_premium_access else 'free'
            else:
                subscription_data = None
                subscription_status = None
                has_premium_access = False
                access_level = 'free'
            
            # Define premium features based on access level
            premium_features = {
                'can_access_premium_content': has_premium_access,
                'can_download_files': has_premium_access,
                'can_use_advanced_features': has_premium_access,
                'can_create_unlimited_projects': has_premium_access,
                'can_export_data': has_premium_access,
                'can_access_priority_support': has_premium_access
            }
            
            response_data = {
                'has_active_subscription': subscription_status in ['current', 'active', 'unverified'],
                'has_premium_access': has_premium_access,
                'subscription_status': subscription_status,
                'access_level': access_level,
                'subscription': subscription_data,
                'premium_features': premium_features,
                'user_id': request.user.id,
                'checked_at': now().isoformat()
            }
            
            return Response(response_data, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'error': 'Error checking subscription status',
                'detail': str(e),
                'has_active_subscription': False,
                'has_premium_access': False,
                'access_level': 'free'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _has_premium_access(self, subscription):
        """
        Check if user has premium access based on subscription status and expiry dates.
        Users should have premium access until their paid period expires.
        """
        from datetime import timedelta, date
        
        current_time = now()
        
        # If subscription is cancelled, check if we're still within the paid period
        if subscription.status == 'canceled':
            # For cancelled subscriptions, check if we're still within the current billing period
            if subscription.cancelled_on:
                # Calculate the end of the current billing period
                period_end = self._get_access_expiry_date(subscription)
                if period_end:
                    # Ensure both are datetime objects for comparison
                    if isinstance(period_end, date) and not isinstance(period_end, datetime):
                        period_end = make_aware(datetime.combine(period_end, datetime.min.time()))
                    
                    if current_time < period_end:
                        return True
            return False
        
        # If subscription failed or expired, no access
        if subscription.status in ['failed', 'expired']:
            return False
        
        # For active subscriptions, check if we're within the current period
        if subscription.status in ['current', 'active', 'unverified']:
            # For 'current' status, user should have premium access
            if subscription.status == 'current':
                return True
            
            # For 'active' status, check if we're within the current billing period
            if subscription.status == 'active':
                period_end = self._get_access_expiry_date(subscription)
                if period_end:
                    # Ensure both are datetime objects for comparison
                    if isinstance(period_end, date) and not isinstance(period_end, datetime):
                        period_end = make_aware(datetime.combine(period_end, datetime.min.time()))
                    
                    if current_time < period_end:
                        print(f"[DEBUG] SubscriptionStatusView._has_premium_access - Active subscription within period until {period_end}")
                        return True
            
            # For unverified subscriptions, give 24 hours grace period
            if subscription.status == 'unverified':
                if subscription.created_at and (current_time - subscription.created_at) < timedelta(hours=24):
                    print(f"[DEBUG] SubscriptionStatusView._has_premium_access - Unverified but within 24h grace period")
                    return True
        
        return False
    
    def _get_access_expiry_date(self, subscription):
        """
        Calculate when the user's premium access expires based on subscription details.
        """
        from datetime import timedelta, date
        
        # If subscription is cancelled, access expires at the end of current billing period
        if subscription.status == 'canceled' and subscription.cancelled_on:
            # For cancelled subscriptions, access continues until the end of the current period
            # We need to calculate when the current period would have ended
            if subscription.next_payment_due_date:
                expiry_date = subscription.next_payment_due_date
                # Ensure it's a datetime object
                if isinstance(expiry_date, date) and not isinstance(expiry_date, datetime):
                    expiry_date = make_aware(datetime.combine(expiry_date, datetime.min.time()))
                return expiry_date
            else:
                # Fallback: add one billing period from creation date
                return self._calculate_next_billing_date(subscription.created_at, subscription.period)
        
        # For active subscriptions, access expires at next payment due date
        if subscription.next_payment_due_date:
            expiry_date = subscription.next_payment_due_date
            # Ensure it's a datetime object
            if isinstance(expiry_date, date) and not isinstance(expiry_date, datetime):
                expiry_date = make_aware(datetime.combine(expiry_date, datetime.min.time()))
            return expiry_date
        
        # Fallback: calculate based on creation date and period
        if subscription.created_at and subscription.period:
            return self._calculate_next_billing_date(subscription.created_at, subscription.period)
        
        return None
    
    def _calculate_next_billing_date(self, start_date, period):
        """
        Calculate the next billing date based on start date and period.
        """
        from datetime import timedelta, date
        
        if not start_date:
            return None
            
        # Ensure start_date is a datetime object
        if isinstance(start_date, date) and not isinstance(start_date, datetime):
            start_date = make_aware(datetime.combine(start_date, datetime.min.time()))
        
        if period == 'daily':
            return start_date + timedelta(days=1)
        elif period == 'weekly':
            return start_date + timedelta(weeks=1)
        elif period == 'monthly':
            # Add approximately one month (30 days)
            return start_date + timedelta(days=30)
        elif period == 'yearly':
            return start_date + timedelta(days=365)
        else:
            # Default to monthly
            return start_date + timedelta(days=30)


# Webhook Handler
@method_decorator(csrf_exempt, name='dispatch')
@extend_schema(
    tags=['Webhooks'],
    summary='Univapay Webhook Endpoint',
    description='Webhook endpoint for receiving payment events from Univapay. This endpoint processes charge updates, subscription changes, and refund notifications.',
    request={
        'application/json': {
            'type': 'object',
            'description': 'Webhook payload from Univapay',
            'properties': {
                'event': {
                    'type': 'string',
                    'description': 'Event type (charge.updated, subscription.updated, etc.)'
                },
                'data': {
                    'type': 'object',
                    'description': 'Event data containing payment/subscription information'
                }
            }
        }
    },
    responses={
        200: {
            'description': 'Webhook processed successfully',
            'examples': {
                'application/json': {
                    'status': 'success',
                    'message': 'Webhook processed'
                }
            }
        },
        401: {
            'description': 'Invalid webhook signature',
            'examples': {
                'application/json': {
                    'error': 'Invalid signature'
                }
            }
        },
        400: {
            'description': 'Invalid webhook data',
            'examples': {
                'application/json': {
                    'error': 'Invalid webhook data'
                }
            }
        }
    }
)
class WebhookView(APIView):
    """
    Webhook endpoint for Univapay events with signature verification.
    
    This endpoint receives and processes webhook notifications from Univapay
    for payment status updates, subscription changes, and other events.
    """
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        print(f"[DEBUG] WebhookView.post - Request headers: {dict(request.headers)}")
        print(f"[DEBUG] WebhookView.post - Request body: {request.body}")
        
        # Verify webhook signature
        if not verify_webhook_signature(request):
            print(f"[DEBUG] WebhookView.post - Invalid webhook signature")
            return Response({'error': 'Invalid signature'}, status=status.HTTP_401_UNAUTHORIZED)
        
        try:
            data = request.data
            event_type = data.get('event') or data.get('type') or data.get('object')
            
            # Log webhook for debugging
            print(f"[DEBUG] WebhookView.post - Received webhook event: {event_type}")
            print(f"[DEBUG] WebhookView.post - Webhook data: {json.dumps(data, indent=2)}")
            
            # Handle different event types
            if event_type in ['charge.finished', 'charge.updated', 'charge']:
                self._handle_charge_event(data)
            elif event_type in ['subscription.updated', 'subscription.payment', 'subscription.canceled', 'subscription']:
                self._handle_subscription_event(data)
            elif event_type in ['refund.finished', 'refund']:
                self._handle_refund_event(data)
            
            print(f"[DEBUG] WebhookView.post - Webhook processed successfully")
            return Response({'ok': True}, status=status.HTTP_200_OK)
            
        except Exception as e:
            print(f"[DEBUG] WebhookView.post - Webhook error: {e}")
            # Always return OK to prevent retries
            return Response({'ok': True}, status=status.HTTP_200_OK)
    
    def _handle_charge_event(self, data):
        """Handle charge-related webhook events."""
        print(f"[DEBUG] WebhookView._handle_charge_event - Processing charge event")
        charge_data = data.get('data') or data
        charge_id = charge_data.get('id')
        
        if not charge_id:
            print(f"[DEBUG] WebhookView._handle_charge_event - No charge ID found")
            return
        
        payment = PaymentHistory.objects.filter(
            univapay_id=charge_id,
            payment_type='one_time'
        ).first()
        
        if payment:
            # Update payment status
            payment.status = charge_data.get('status', payment.status)
            
            # Update amounts if provided
            if charge_data.get('charged_amount'):
                payment.charged_amount = charge_data['charged_amount']
            if charge_data.get('charged_currency'):
                payment.charged_currency = charge_data['charged_currency']
            
            # Update error information
            error_info = charge_data.get('error', {})
            if error_info:
                payment.error_code = error_info.get('code')
                payment.error_message = error_info.get('message')
                payment.error_detail = error_info.get('detail')
            
            payment.save()
            print(f"[DEBUG] WebhookView._handle_charge_event - Updated charge {charge_id} status to {payment.status}")
    
    def _handle_subscription_event(self, data):
        """Handle subscription-related webhook events."""
        sub_data = data.get('data') or data
        sub_id = sub_data.get('id')
        
        if not sub_id:
            return
        
        payment = PaymentHistory.objects.filter(
            univapay_id=sub_id,
            payment_type='recurring'
        ).first()
        
        if payment:
            # Update subscription status
            payment.status = sub_data.get('status', payment.status)
            
            # Update cancellation info
            if sub_data.get('cancelled_on'):
                payment.cancelled_on = parse_datetime(sub_data['cancelled_on'])
            
            # Update next payment information
            next_payment = sub_data.get('next_payment', {})
            if next_payment:
                payment.next_payment_id = next_payment.get('id')
                payment.next_payment_due_date = next_payment.get('due_date')
                payment.next_payment_amount = next_payment.get('amount')
                payment.next_payment_currency = next_payment.get('currency')
                payment.next_payment_is_paid = next_payment.get('is_paid', False)
                payment.next_payment_is_last_payment = next_payment.get('is_last_payment', False)
                payment.next_payment_retry_date = next_payment.get('retry_date')
            
            payment.save()
            print(f"[DEBUG] WebhookView._handle_subscription_event - Updated subscription {sub_id} status to {payment.status}")
    
    def _handle_refund_event(self, data):
        """Handle refund-related webhook events."""
        refund_data = data.get('data') or data
        charge_id = refund_data.get('charge_id')
        
        if not charge_id:
            return
        
        payment = PaymentHistory.objects.filter(
            univapay_id=charge_id,
            payment_type='one_time'
        ).first()
        
        if payment:
            # Update payment status based on refund
            refund_amount = refund_data.get('amount')
            if refund_amount and refund_amount < payment.amount:
                payment.status = 'partially_refunded'
            else:
                payment.status = 'refunded'
            
            payment.save()
            print(f"[DEBUG] WebhookView._handle_refund_event - Updated charge {charge_id} to refunded status")


# Alternative function-based webhook handler (if you prefer this style)
@api_view(['POST'])
@permission_classes([AllowAny])
def webhook_handler(request):
    """
    Alternative function-based webhook endpoint for Univapay events.
    """
    # Verify webhook signature
    if not verify_webhook_signature(request):
        return Response({'error': 'Invalid signature'}, status=status.HTTP_401_UNAUTHORIZED)
    
    # Process webhook using the same logic as WebhookView
    view = WebhookView()
    return view.post(request)