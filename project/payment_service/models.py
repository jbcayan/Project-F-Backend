import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from .stripe_client import init_stripe


class BillingInterval(models.TextChoices):
    MONTH = "month", _("Monthly")
    SIX_MONTH = "six_months", _("Every 6 Months")


INTERVAL_MAPPING = {
    BillingInterval.MONTH: {"interval": "month", "interval_count": 1},
    BillingInterval.SIX_MONTH: {"interval": "month", "interval_count": 6},
}


class SubscriptionPlan(models.Model):
    uid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, db_index=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    amount_jpy = models.PositiveIntegerField(help_text="Amount in JPY (e.g. 18000)")
    billing_interval = models.CharField(max_length=20, choices=BillingInterval.choices)
    stripe_product_id = models.CharField(max_length=100, blank=True, null=True)
    stripe_price_id = models.CharField(max_length=100, blank=True, null=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} - ¥{self.amount_jpy} ({self.get_billing_interval_display()})"

    def create_in_stripe(self):
        print(f"[DEBUG] Called create_in_stripe for: {self.name}")

        if self.stripe_product_id or self.stripe_price_id:
            raise Exception("Stripe product/price already exists for this plan.")

        stripe = init_stripe()
        print("[DEBUG] Stripe initialized")

        product = stripe.Product.create(
            name=self.name,
            description=self.description or ""
        )
        print(f"[DEBUG] Stripe Product created: {product.id}")
        self.stripe_product_id = product.id

        interval_data = INTERVAL_MAPPING[self.billing_interval]

        price = stripe.Price.create(
            unit_amount=self.amount_jpy,
            currency="jpy",
            recurring={
                "interval": interval_data["interval"],
                "interval_count": interval_data["interval_count"],
            },
            product=product.id,
        )
        print(f"[DEBUG] Stripe Price created: {price.id}")
        self.stripe_price_id = price.id
        self.save()
        print("[DEBUG] SubscriptionPlan saved with Stripe IDs")


class SubscriptionStatus(models.TextChoices):
    ACTIVE = "active", "Active"
    CANCELED = "canceled", "Canceled"
    INCOMPLETE = "incomplete", "Incomplete"
    PAST_DUE = "past_due", "Past Due"
    UNPAID = "unpaid", "Unpaid"
    TRIALING = "trialing", "Trialing"


class UserSubscription(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="subscription"
    )
    subscription_plan = models.ForeignKey(
        SubscriptionPlan,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    stripe_checkout_session_id = models.CharField(max_length=255, blank=True, null=True)
    stripe_subscription_id = models.CharField(max_length=100, blank=True, null=True)
    stripe_customer_id = models.CharField(max_length=100, blank=True, null=True)
    checkout_session_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Last known Stripe Checkout Session ID"
    )
    status = models.CharField(
        max_length=20,
        choices=SubscriptionStatus.choices,
        default=SubscriptionStatus.INCOMPLETE
    )
    start_date = models.DateTimeField(blank=True, null=True)
    current_period_end = models.DateTimeField(blank=True, null=True)
    cancel_at_period_end = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.email} - {self.subscription_plan.name if self.subscription_plan else 'N/A'} ({self.status})"

    @property
    def is_premium(self):
        return self.status == SubscriptionStatus.ACTIVE and not self.cancel_at_period_end



###### Product Payment Models ##########

from django.db import models
from accounts.models import User
from common.models import BaseModelWithUID
from common.choices import Status


class PaymentHistory(BaseModelWithUID):
    """Stores payment transactions made by users."""
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="payments")
    product_id = models.CharField(max_length=100)
    # order_id = models.CharField(
    #     max_length=100,
    #     help_text="order code from Edit Request"
    # )
    quantity = models.PositiveIntegerField(default=1)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    paid_at = models.DateTimeField(blank=True, null=True)  # Set when payment is confirmed

    # Stripe-related fields
    stripe_session_id = models.CharField(max_length=255, unique=True)
    stripe_order_id = models.CharField(max_length=255, blank=True, null=True)
    stripe_payment_status = models.CharField(max_length=50, blank=True, null=True)
    stripe_response_data = models.JSONField(blank=True, null=True)

    class Meta:
        ordering = ("-paid_at",)

    def __str__(self):
        return f"{self.user.email} - {self.product_id} - ${self.amount}"
