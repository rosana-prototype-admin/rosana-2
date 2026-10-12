from django.shortcuts import get_object_or_404
from rest_framework.permissions import BasePermission

from projects.models import Opportunity
from projects.permissions import can_read


class CommentAccessPermission(BasePermission):
    """
    Deliberately NOT a reuse of projects.permissions.OpportunityAccessPermission:
    that class requires can_write() for every non-safe method, which would
    incorrectly block guests from posting/replying/voting. Full read access to
    the Opportunity (owner, editor, or guest) is also sufficient to comment and
    vote here -- can_read is the semantic bar for "can participate". The one
    exception is editing/deleting a specific comment, which is author-only
    regardless of Opportunity role.
    """

    AUTHOR_ONLY_ACTIONS = {'update', 'partial_update', 'destroy'}

    def has_object_permission(self, request, view, obj):
        if not can_read(request.user, obj.get_opportunity()):
            return False
        if view.action in self.AUTHOR_ONLY_ACTIONS:
            return obj.author_id == request.user.pk
        return True


class CommentAncestorScopedMixin:
    """
    Mirrors projects.permissions.AncestorScopedMixin's shape (resolve +
    authorize the ancestor Opportunity from the URL, never from client body),
    but the authorization bar is can_read, not can_write: guests may post
    comments. Opportunity.objects.visible_to() already scopes to exactly
    can_read, so get_object_or_404 failing IS the authorization check.
    """

    def get_ancestor(self):
        return get_object_or_404(
            Opportunity.objects.visible_to(self.request.user),
            pk=self.kwargs['opportunity_pk'],
        )

    def perform_create(self, serializer):
        serializer.save(opportunity=self.get_ancestor(), author=self.request.user)
