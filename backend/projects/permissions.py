from rest_framework.permissions import SAFE_METHODS, BasePermission


def can_read(user, opportunity):
    return (
        opportunity.owner_id == user.pk
        or opportunity.editors.filter(pk=user.pk).exists()
        or opportunity.guests.filter(pk=user.pk).exists()
    )


def can_write(user, opportunity):
    return opportunity.owner_id == user.pk or opportunity.editors.filter(pk=user.pk).exists()


def can_invite(user, opportunity):
    """Whether `user` may add a new member (as guest or editor) to `opportunity`."""
    return opportunity.owner_id == user.pk


def can_manage_roles(user, opportunity):
    """Whether `user` may change or revoke an existing member's role on `opportunity`."""
    return opportunity.owner_id == user.pk


class OpportunityAccessPermission(BasePermission):
    """
    Object-level permission shared by Opportunity, Strategy, Intervention,
    and Project viewsets. Every model in the hierarchy implements
    get_opportunity() so this one class can enforce owner/editor (read+write)
    vs. guest (read-only) access without duplicating the check per model.
    """

    def has_object_permission(self, request, view, obj):
        opportunity = obj.get_opportunity()
        if request.method in SAFE_METHODS:
            return can_read(request.user, opportunity)
        return can_write(request.user, opportunity)


class AncestorScopedMixin:
    """
    Shared behavior for viewsets nested under an ancestor object (an
    Opportunity for Strategy, a Strategy for Intervention or Project):
    resolves + authorizes the ancestor from the URL, never from
    client-supplied body data, and uses it to scope create.
    """

    def get_ancestor(self):
        raise NotImplementedError

    def perform_create(self, serializer):
        ancestor = self.get_ancestor()
        if not can_write(self.request.user, ancestor.get_opportunity()):
            from rest_framework.exceptions import PermissionDenied

            raise PermissionDenied('You do not have write access to this opportunity.')
        serializer.save(**self.get_create_kwargs(ancestor))

    def get_create_kwargs(self, ancestor):
        raise NotImplementedError
