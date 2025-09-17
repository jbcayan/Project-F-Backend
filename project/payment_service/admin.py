from django.contrib import admin
from .models import SubscriptionPlan, PaymentHistory, TransactionToken


@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ('name', 'amount', 'currency', 'period', 'is_active', 'created_at')
    list_filter = ('is_active', 'period', 'currency', 'created_at')
    search_fields = ('name',)
    ordering = ('-created_at',)
    list_per_page = 20
    
    fieldsets = (
        ('Plan Information', {
            'fields': ('name', 'is_active')
        }),
        ('Pricing', {
            'fields': ('amount', 'currency', 'period')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    readonly_fields = ('created_at', 'updated_at')


@admin.register(TransactionToken)
class TransactionTokenAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'token_type', 'payment_type', 'card_brand', 
                    'card_last_four', 'is_active', 'mode', 'created_at')
    list_filter = ('token_type', 'payment_type', 'is_active', 'mode', 'card_brand', 
                   'cvv_authorize_enabled', 'three_ds_enabled')
    search_fields = ('user__email', 'univapay_token_id', 'email', 'card_last_four')
    readonly_fields = ('created_at', 'updated_at', 'last_used_at', 'raw_token_data')
    list_per_page = 25
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('user', 'univapay_token_id', 'token_type', 'payment_type', 'email')
        }),
        ('Card Details', {
            'fields': ('card_brand', 'card_last_four', 'card_exp_month', 'card_exp_year',
                      'card_bin', 'card_type', 'card_category', 'card_issuer')
        }),
        ('Security Features', {
            'fields': ('cvv_authorize_enabled', 'cvv_authorize_status', 
                      'three_ds_enabled', 'three_ds_status')
        }),
        ('Token Settings', {
            'fields': ('is_active', 'usage_limit', 'mode')
        }),
        ('Additional Data', {
            'fields': ('billing_data', 'raw_token_data'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'last_used_at')
        })
    )
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('user')


@admin.register(PaymentHistory)
class PaymentHistoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'payment_type', 'amount', 'currency', 
                    'status', 'mode', 'is_successful', 'created_at')
    list_filter = ('payment_type', 'status', 'mode', 'currency', 
                   'period', 'three_ds_mode', 'termination_mode')
    search_fields = ('user__email', 'univapay_id', 'transaction_token__univapay_token_id',
                    'error_code', 'error_message')
    readonly_fields = ('created_at', 'updated_at', 'raw_json', 'is_successful')
    date_hierarchy = 'created_at'
    list_per_page = 25
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('user', 'payment_type', 'status', 'mode', 'transaction_token', 'is_successful')
        }),
        ('Payment Details', {
            'fields': ('univapay_id', 'store_id', 'univapay_transaction_token_id',
                      'amount', 'currency', 'amount_formatted')
        }),
        ('Charged Amounts (One-time Payments)', {
            'fields': ('charged_amount', 'charged_currency', 'charged_amount_formatted',
                      'fee_amount', 'fee_currency', 'fee_amount_formatted'),
            'classes': ('collapse',)
        }),
        ('Subscription Information', {
            'fields': ('subscription_plan', 'period', 'cyclical_period', 
                      'initial_amount', 'initial_amount_formatted',
                      'subsequent_cycles_start', 'schedule_settings',
                      'first_charge_capture_after', 'first_charge_authorization_only'),
            'classes': ('collapse',)
        }),
        ('Next Payment Details (Subscriptions)', {
            'fields': ('next_payment_id', 'next_payment_due_date', 'next_payment_zone_id',
                      'next_payment_amount', 'next_payment_currency', 'next_payment_amount_formatted',
                      'next_payment_is_paid', 'next_payment_is_last_payment',
                      'next_payment_created_on', 'next_payment_updated_on', 'next_payment_retry_date'),
            'classes': ('collapse',)
        }),
        ('Subscription Management', {
            'fields': ('cancelled_on', 'termination_mode', 'retry_interval'),
            'classes': ('collapse',)
        }),
        ('Payment Flow & Security', {
            'fields': ('redirect_endpoint', 'redirect_id', 'three_ds_redirect_endpoint', 
                      'three_ds_redirect_id', 'three_ds_mode', 'capture_at',
                      'descriptor', 'descriptor_phone_number'),
            'classes': ('collapse',)
        }),
        ('Bank Transfer Fields', {
            'fields': ('bank_ledger_type', 'balance', 'virtual_bank_account_holder_name',
                      'virtual_bank_account_number', 'virtual_account_id',
                      'transaction_date', 'transaction_timestamp', 'transaction_id'),
            'classes': ('collapse',)
        }),
        ('Error Information', {
            'fields': ('error_code', 'error_message', 'error_detail'),
            'classes': ('collapse',)
        }),
        ('Additional Data', {
            'fields': ('metadata', 'raw_json'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_on', 'created_at', 'updated_at')
        })
    )
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('user', 'transaction_token', 'subscription_plan')
    
    def is_successful(self, obj):
        """Display success status with color coding"""
        if obj.is_successful():
            return "✅ Success"
        else:
            return "❌ Failed"
    is_successful.short_description = "Success"
    is_successful.admin_order_field = 'status'