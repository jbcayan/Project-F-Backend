from django.urls import path
from .views import (
    SubscriptionPlanListView,
    CreateCheckoutSessionView,
    ConfirmSubscriptionView,
    CancelSubscriptionView,
    SubscriptionStatusView,
)

urlpatterns = [
    path("plans/", SubscriptionPlanListView.as_view(), name="list-subscription-plans"),
    path("subscribe/", CreateCheckoutSessionView.as_view(), name="create-checkout-session"),
    path("confirm/", ConfirmSubscriptionView.as_view(), name="confirm-subscription"),
    path("cancel/", CancelSubscriptionView.as_view(), name="cancel-subscription"),
    path("status/", SubscriptionStatusView.as_view(), name="subscription-status"),
]
