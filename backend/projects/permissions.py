from django.shortcuts import get_object_or_404
from django.db.models import Q
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import SAFE_METHODS, BasePermission

from groups.permissions import has_group_permission, has_opportunity_permission, user_has_group_membership


def can_read(user, opportunity):
    return (
        opportunity.manager_id == user.pk
        or opportunity.delegates.filter(pk=user.pk).exists()
        or opportunity.stakeholders.filter(pk=user.pk).exists()
        or opportunity.assoc_agencies.filter(Q(admin_id=user.pk) | Q(memberships__user_id=user.pk)).exists()
    )


def can_write(user, opportunity):
    return opportunity.manager_id == user.pk or opportunity.delegates.filter(pk=user.pk).exists()


def can_write_with_permission(user, opportunity, permission_code):
    if not can_write(user, opportunity):
        return False
    return has_opportunity_permission(user, opportunity, permission_code)


def permission_for_view(view):
    action = getattr(view, 'action', None)
    view_name = view.__class__.__name__
    resource = {
        'OpportunityViewSet': 'opportunity',
        'ProjectViewSet': 'project',
        'SiteViewSet': 'site',
        'StrategyViewSet': 'strategy',
    }.get(view_name)
    if resource is None or action not in {'create', 'update', 'partial_update', 'destroy'}:
        return None
    return f'{"delete" if action == "destroy" else "create_modify"}_{resource}'


def can_invite(user, opportunity):
    """Whether `user` may add a new member (as delegate or stakeholder) to `opportunity`."""
    return opportunity.manager_id == user.pk


def can_manage_roles(user, opportunity):
    """Whether `user` may change or revoke an existing member's role on `opportunity`."""
    return opportunity.manager_id == user.pk


class OpportunityAccessPermission(BasePermission):
    """
    Object-level permission shared by every viewset in the Opportunity ->
    Project -> Site -> Strategy hierarchy. Each of those models implements
    get_opportunity() (Opportunity returns itself; the others walk up their
    FK chain), so this single class works unchanged at every nesting level,
    and is also what discussions.permissions builds on top of.
    """

    def has_object_permission(self, request, view, obj):
        opportunity = obj.get_opportunity()
        if request.method in SAFE_METHODS:
            return can_read(request.user, opportunity)
        permission_code = permission_for_view(view)
        if permission_code and not has_opportunity_permission(request.user, opportunity, permission_code):
            return False
        return can_write(request.user, opportunity)


class ProjectAncestorScopedMixin:
    """Resolve + authorize the ancestor Opportunity from the URL, never from the client body."""

    def get_ancestor(self):
        from .models import Opportunity

        return get_object_or_404(
            Opportunity.objects.visible_to(self.request.user),
            pk=self.kwargs['opportunity_pk'],
        )

    def perform_create(self, serializer):
        opportunity = self.get_ancestor()
        if not can_write_with_permission(self.request.user, opportunity, 'create_modify_project'):
            raise PermissionDenied('You do not have write access to this opportunity.')
        serializer.save(opportunity=opportunity)


class SiteAncestorScopedMixin:
    """Resolve + authorize the ancestor Project from the URL, never from the client body."""

    def get_ancestor(self):
        from .models import Opportunity, Project

        return get_object_or_404(
            Project.objects.filter(opportunity__in=Opportunity.objects.visible_to(self.request.user)),
            pk=self.kwargs['project_pk'],
        )

    def perform_create(self, serializer):
        project = self.get_ancestor()
        if not can_write_with_permission(self.request.user, project.opportunity, 'create_modify_site'):
            raise PermissionDenied('You do not have write access to this opportunity.')
        serializer.save(project=project)


class StrategyAncestorScopedMixin:
    """
    Resolve the ancestor Site from the URL. Unlike Project/Site, Strategy rows
    are never user-created (see Site.sync_strategies), so there's no
    perform_create here -- just the ancestor lookup, used both for the
    list-triggered sync and for get_serializer_context's 404 mechanism.
    """

    def get_ancestor(self):
        from .models import Opportunity, Site

        return get_object_or_404(
            Site.objects.filter(project__opportunity__in=Opportunity.objects.visible_to(self.request.user)),
            pk=self.kwargs['site_pk'],
        )
