"""Write custom permission classes here"""
from rest_framework.permissions import BasePermission
from common.choices import UserKind

class IsAdmin(BasePermission):
    """
    Custom permission to only allow access to admin users.
    """
    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.kind == UserKind.ADMIN
        )


class IsSuperAdmin(BasePermission):
    """
    Custom permission to only allow access to super admin users.
    """
    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.kind == UserKind.SUPER_ADMIN
        )


class IsEndUser(BasePermission):
    """
    Custom permission to only allow access to end users.
    """
    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.kind == UserKind.END_USER
        )


class CheckAnyPermission(BasePermission):
    """
    Custom permission to check if any of the permissions in `available_permission_classes` are met.
    """

    def has_permission(self, request, view):

        for permission_class in getattr(view, "available_permission_classes", []):
            if permission_class().has_permission(request, view):
                return True

        return False