"""User Management URLs"""
from django.urls import path

from accounts.rest.views.user import (
    UserRegistrationView,
    UserLoginView,
    UserProfileView,
    UserListView,
    VerifyOTPView,
    UserRetrieveUpdateDestroyView,
    PasswordChangeView,
    PasswordResetRequestView,
    PasswordResetConfirmView
)

urlpatterns = [
    path("/register", UserRegistrationView.as_view(), name="user-register"),
    path('/verify-otp', VerifyOTPView.as_view(), name='verify-otp'),
    path("/login", UserLoginView.as_view(), name="user-login"),
    path("/profile", UserProfileView.as_view(), name="user-profile"),
    path("", UserListView.as_view(), name="user-list"),
    path("/change-password", PasswordChangeView.as_view(), name="change-password"),
    path("/password-reset-request", PasswordResetRequestView.as_view(), name="password-reset-request"),
    path("/password-reset-confirm/<str:uid>/<str:token>", PasswordResetConfirmView.as_view(), name="password-reset-confirm"),
    path("/<str:uid>", UserRetrieveUpdateDestroyView.as_view(), name="user-retrieve-update-destroy")
]
