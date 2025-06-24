from django.urls import path
from .views import (
    SubscriptionPlanListView,
    CreateCheckoutSessionView,
    ConfirmSubscriptionView,
    CancelSubscriptionView,
    SubscriptionStatusView,
)



from .views import CreateStripeCheckoutSessionAPIView, PaymentHistoryListAPIView, VerifyStripeSessionAPIView


urlpatterns = [
    path("subscription/plans/", SubscriptionPlanListView.as_view(), name="list-subscription-plans"),
    path("subscription/subscribe/", CreateCheckoutSessionView.as_view(), name="create-checkout-session"),
    path("subscription/confirm/", ConfirmSubscriptionView.as_view(), name="confirm-subscription"),
    path("subscription/cancel/", CancelSubscriptionView.as_view(), name="cancel-subscription"),
    path("subscription/status/", SubscriptionStatusView.as_view(), name="subscription-status"),


    # Product Payment URLs
    path("product/create/", CreateStripeCheckoutSessionAPIView.as_view(), name="create-stripe-payment"),
    path("product/history/", PaymentHistoryListAPIView.as_view(), name="payment-history"),
    path("product/verify/", VerifyStripeSessionAPIView.as_view(), name="verify-stripe-session"),
]