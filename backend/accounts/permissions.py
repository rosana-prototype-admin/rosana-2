from rest_framework.permissions import BasePermission

from .entitlements import is_platform_admin


class IsPlatformAdmin(BasePermission):
    """Allow only active users who are explicitly marked as platform staff."""

    message = 'Platform administrator access is required.'

    def has_permission(self, request, view):
        return is_platform_admin(request.user)
