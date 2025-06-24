from django.contrib import admin, messages
from .models import SubscriptionPlan, UserSubscription


@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "amount_jpy",
        "billing_interval",
        "is_active",
        "stripe_product_id",
        "stripe_price_id",
    )
    search_fields = ("name",)
    list_filter = ("billing_interval", "is_active")
    readonly_fields = ("stripe_product_id", "stripe_price_id")
    actions = ["create_on_stripe"]

    def create_on_stripe(self, request, queryset):
        for plan in queryset:
            try:
                plan.create_in_stripe()
                self.message_user(
                    request,
                    f"✅ Stripe product and price created for: {plan.name}",
                    messages.SUCCESS,
                )
            except Exception as e:
                self.message_user(
                    request,
                    f"❌ Failed to create Stripe product/price for {plan.name}: {str(e)}",
                    messages.ERROR,
                )

    create_on_stripe.short_description = "Create selected plans in Stripe"


@admin.register(UserSubscription)
class UserSubscriptionAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "subscription_plan",
        "status",
        "current_period_end",
        "cancel_at_period_end",
        "checkout_session_id",
    )
    search_fields = ("user__email",)
    list_filter = ("status", "cancel_at_period_end")
    readonly_fields = (
        "stripe_customer_id",
        "stripe_subscription_id",
        "checkout_session_id",
    )
