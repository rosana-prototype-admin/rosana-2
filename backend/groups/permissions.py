from rest_framework.permissions import SAFE_METHODS, BasePermission


def is_admin(user, group):
    return group.admin_id == user.pk


class GroupAccessPermission(BasePermission):
    """
    Any authenticated user may read a group; only its admin may write to it.
    Object-level only -- `create` has no object yet, so GroupViewSet checks
    the parent's admin explicitly in perform_create instead.
    """

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        return is_admin(request.user, obj)
