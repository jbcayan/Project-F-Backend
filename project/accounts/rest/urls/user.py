"""User Management URLs"""
from django.urls import path

from accounts.rest.views.user import (
    UserRegistrationView,
    UserLoginView,
    UserProfileView,
    UserListView,
    VerifyOTPView
)

urlpatterns = [
    path("/register", UserRegistrationView.as_view(), name="user-register"),
    path('/verify-otp', VerifyOTPView.as_view(), name='verify-otp'),
    path("/login", UserLoginView.as_view(), name="user-login"),
    path("/profile", UserProfileView.as_view(), name="user-profile"),
    path("", UserListView.as_view(), name="user-list"),
]