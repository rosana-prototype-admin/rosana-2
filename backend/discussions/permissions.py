from django.shortcuts import get_object_or_404
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import BasePermission

from projects.models import Opportunity, Project
from projects.permissions import can_read


class CommentAccessPermission(BasePermission):
    """
    Deliberately NOT a reuse of projects.permissions.OpportunityAccessPermission:
    that class requires can_write() for every non-safe method, which would
    incorrectly block guests from posting/replying/voting. Full read access to
    the Opportunity (owner, editor, or guest) is also sufficient to comment and
    vote here -- can_read is the semantic bar for "can participate".

    Editing a comment is always author-only. Deleting is author-only OR the
    Opportunity manager acting as forum moderator (see
    CommentViewSet.perform_destroy for how that distinction gets recorded).
    """

    EDIT_ONLY_ACTIONS = {'update', 'partial_update'}

    def has_object_permission(self, request, view, obj):
        opportunity = obj.get_opportunity()
        if not can_read(request.user, opportunity):
            return False
        if view.action in self.EDIT_ONLY_ACTIONS:
            return obj.author_id == request.user.pk
        if view.action == 'destroy':
            return obj.author_id == request.user.pk or opportunity.manager_id == request.user.pk
        return True


class CommentAncestorScopedMixin:
    """
    Mirrors projects.permissions.SiteAncestorScopedMixin's shape (resolve +
    authorize the ancestor Project from the URL, never from client body),
    but the authorization bar is can_read, not can_write: guests may post
    comments. Opportunity.objects.visible_to() already scopes to exactly
    can_read, so get_object_or_404 failing IS the authorization check.
    """

    def get_ancestor(self):
        return get_object_or_404(
            Project.objects.filter(opportunity__in=Opportunity.objects.visible_to(self.request.user)),
            pk=self.kwargs['project_pk'],
        )

    def perform_create(self, serializer):
        project = self.get_ancestor()
        if not project.comments_enabled:
            raise PermissionDenied('Comments are disabled for this project.')
        serializer.save(project=project, author=self.request.user)
