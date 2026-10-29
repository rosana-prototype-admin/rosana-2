from rest_framework.permissions import SAFE_METHODS, BasePermission


class CMFAccessPermission(BasePermission):
    """Built-in CMFs are public/read-only; custom CMFs are shared/read-only."""

    def has_object_permission(self, request, view, obj):
        if obj.is_builtin:
            return request.method in SAFE_METHODS
        if obj.author_id == request.user.pk:
            return True
        return request.method in SAFE_METHODS and obj.can_be_used_by(request.user)
