from django.shortcuts import get_object_or_404
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import BasePermission

from projects.models import Opportunity, Project
from groups.permissions import has_opportunity_permission
from projects.permissions import can_comment, can_read, entitled_opportunity_queryset


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
        if not can_comment(request.user, opportunity):
            return False
        if view.action in self.EDIT_ONLY_ACTIONS:
            return obj.author_id == request.user.pk
        if view.action == 'destroy':
            return obj.author_id == request.user.pk or (
                opportunity.manager_id == request.user.pk
                and has_opportunity_permission(request.user, opportunity, 'delete_other_comments')
            )
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
            Project.objects.filter(
                opportunity__in=entitled_opportunity_queryset(
                    Opportunity.objects.visible_to(self.request.user), self.request.user
                )
            ),
            pk=self.kwargs['project_pk'],
        )

    def perform_create(self, serializer):
        project = self.get_ancestor()
        if not project.comments_enabled:
            raise PermissionDenied('Comments are disabled for this project.')
        if not can_comment(self.request.user, project.opportunity):
            raise PermissionDenied('Your subscription does not allow commenting on this Opportunity.')
        if not has_opportunity_permission(
            self.request.user, project.opportunity, 'comment_existing_resources'
        ):
            raise PermissionDenied('You do not have permission to comment on this Opportunity.')
        serializer.save(project=project, author=self.request.user)
