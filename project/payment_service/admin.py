# admin.py
from django.contrib import admin
from .models import SubscriptionPlan, PaymentHistory


@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ('name', 'amount', 'currency', 'period', 'is_active')
    list_filter = ('is_active', 'period', 'currency')
    search_fields = ('name',)


@admin.register(PaymentHistory)
class PaymentHistoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'amount', 'currency', 'status', 'created_at')
    list_filter = ('status', 'mode', 'currency')
    search_fields = ('user__email', 'univapay_id', 'transaction_token_id')
    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        ('Basic Information', {
            'fields': ('user', 'status', 'mode')
        }),
        ('Payment Details', {
            'fields': (
                'univapay_id', 'store_id', 'transaction_token_id',
                'amount', 'currency', 'subscription_plan', 'period'
            )
        }),
        ('Additional Information', {
            'fields': (
                'metadata', 'redirect_endpoint', 'redirect_id',
                'next_payment_due_date', 'next_payment_id'
            )
        }),
        ('Timestamps', {
            'fields': ('created_on', 'created_at', 'updated_at')
        }),
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.defer('payment_type')
