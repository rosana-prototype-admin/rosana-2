from rest_framework.permissions import SAFE_METHODS, BasePermission

from groups.permissions import has_any_group_permission, user_has_any_group_membership


class CMFAccessPermission(BasePermission):
    """Built-in CMFs are public/read-only; custom CMFs are shared/read-only."""

    def has_object_permission(self, request, view, obj):
        if obj.is_builtin:
            return request.method in SAFE_METHODS
        if obj.author_id == request.user.pk:
            if request.method in SAFE_METHODS:
                return True
            code = 'delete_cmf' if view.action == 'destroy' else 'create_modify_cmf'
            return (
                has_any_group_permission(request.user, code)
                or not user_has_any_group_membership(request.user)
            )
        return request.method in SAFE_METHODS and obj.can_be_used_by(request.user)
