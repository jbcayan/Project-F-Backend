from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _
from .models import User, UserProfile, OTP


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Profile'
    fk_name = 'user'

class CustomUserAdmin(BaseUserAdmin):
    model = User
    inlines = [UserProfileInline]
    list_display = ('email', 'is_staff', 'is_superuser', 'is_verified', 'kind', 'is_active')
    list_filter = ('is_staff', 'is_superuser', 'is_verified', 'kind', 'is_active')
    search_fields = ('email', 'phone_number')
    ordering = ('-created_at',)
    readonly_fields = ('last_login',)

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        (_('Personal info'), {'fields': ('phone_number',)}),
        (_('Permissions'), {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'is_verified', 'kind', 'groups', 'user_permissions'),
        }),
        (_('Important dates'), {'fields': ('last_login',)}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2', 'is_active', 'is_staff', 'is_superuser', 'kind'),
        }),
    )

    def get_inline_instances(self, request, obj=None):
        if obj is None:
            return []
        return super().get_inline_instances(request, obj)


class OTPAdmin(admin.ModelAdmin):
    list_display = ('otp', 'user_email', 'is_used', 'created_at')
    list_filter = ('is_used', 'created_at')
    search_fields = ('otp', 'user__email')
    ordering = ('-created_at',)
    readonly_fields = ('uid', 'created_at', 'updated_at')

    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'User Email'



# ✅ Register the user model with the custom admin class
admin.site.register(User, CustomUserAdmin)
admin.site.register(OTP, OTPAdmin)
