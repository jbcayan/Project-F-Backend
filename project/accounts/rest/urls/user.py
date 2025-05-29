"""User Management URLs"""
from django.urls import path

from accounts.rest.views.user import (
    UserRegistrationView,
    UserLoginView,
    UserProfileView,
    UserListView
)

urlpatterns = [
    path("/register", UserRegistrationView.as_view(), name="user-register"),
    path("/login", UserLoginView.as_view(), name="user-login"),
    path("/profile", UserProfileView.as_view(), name="user-profile"),
    path("", UserListView.as_view(), name="user-list"),
]