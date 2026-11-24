from django.shortcuts import get_object_or_404
from django.db.models import Q
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import SAFE_METHODS, BasePermission

from accounts.entitlements import (
    can_use_feature,
    can_view_existing,
    entitlement_context,
    feature_denial_message,
    is_platform_admin,
    subscription_for_group,
)
from groups.permissions import has_group_permission, has_opportunity_permission, user_has_group_membership


def can_read(user, opportunity):
    if is_platform_admin(user):
        return True
    legacy_access = (
        opportunity.manager_id == user.pk
        or opportunity.delegates.filter(pk=user.pk).exists()
        or opportunity.stakeholders.filter(pk=user.pk).exists()
        or opportunity.assoc_agencies.filter(Q(admin_id=user.pk) | Q(memberships__user_id=user.pk)).exists()
    )
    if not legacy_access:
        return False
    subscription = subscription_for_group(opportunity.lead_agency)
    if subscription is None:
        return True
    # Users outside the owning organization may still be invited external
    # reviewers, including during the post-expiry period.
    context = entitlement_context(user, opportunity.lead_agency)
    if context.rosana_role is None:
        return True
    return can_view_existing(user, opportunity.lead_agency)


def can_write(user, opportunity):
    legacy_write = opportunity.manager_id == user.pk or opportunity.delegates.filter(pk=user.pk).exists()
    if not legacy_write:
        return False
    subscription = subscription_for_group(opportunity.lead_agency)
    return subscription is None or can_use_feature(user, 'analyze', opportunity.lead_agency)


def can_comment(user, opportunity):
    """Whether the user may comment under the current subscription rules."""
    subscription = subscription_for_group(opportunity.lead_agency)
    if subscription is None:
        return True
    context = entitlement_context(user, opportunity.lead_agency)
    # An invited user from another organization retains review commenting
    # access throughout the expiration lifecycle.
    if context.rosana_role is None:
        return True
    return can_use_feature(user, 'comment', opportunity.lead_agency)


def enforce_resource_write_access(user, opportunity, permission_code, resource_label):
    """Raise a transparent error when a technical resource cannot be changed."""
    lead_agency = opportunity.lead_agency
    if not can_use_feature(user, 'analyze', lead_agency):
        raise PermissionDenied(feature_denial_message(user, 'analyze', lead_agency))
    if not can_write(user, opportunity):
        raise PermissionDenied('You do not have write access to this opportunity.')
    if not has_opportunity_permission(user, opportunity, permission_code):
        raise PermissionDenied(f'You do not have permission to create or modify {resource_label} for this Group.')


def enforce_project_write_access(user, opportunity):
    return enforce_resource_write_access(
        user, opportunity, 'create_modify_project', 'Projects'
    )


def enforce_site_write_access(user, opportunity):
    return enforce_resource_write_access(
        user, opportunity, 'create_modify_site', 'Sites'
    )


def entitled_opportunity_queryset(queryset, user):
    """Filter legacy visibility through organization entitlements."""
    allowed_ids = [opportunity.pk for opportunity in queryset if can_read(user, opportunity)]
    return queryset.filter(pk__in=allowed_ids)


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
        if (
            view.__class__.__name__ == 'ProjectViewSet'
            and request.method in {'PUT', 'PATCH'}
        ):
            enforce_project_write_access(request.user, opportunity)
        if view.__class__.__name__ == 'SiteViewSet' and request.method in {'PUT', 'PATCH'}:
            enforce_site_write_access(request.user, opportunity)
        if permission_code and not has_opportunity_permission(request.user, opportunity, permission_code):
            return False
        return can_write(request.user, opportunity)


class ProjectAncestorScopedMixin:
    """Resolve + authorize the ancestor Opportunity from the URL, never from the client body."""

    def get_ancestor(self):
        from .models import Opportunity

        return get_object_or_404(
            entitled_opportunity_queryset(
                Opportunity.objects.visible_to(self.request.user), self.request.user
            ),
            pk=self.kwargs['opportunity_pk'],
        )

    def perform_create(self, serializer):
        opportunity = self.get_ancestor()
        enforce_project_write_access(self.request.user, opportunity)
        serializer.save(opportunity=opportunity)


class SiteAncestorScopedMixin:
    """Resolve + authorize the ancestor Project from the URL, never from the client body."""

    def get_ancestor(self):
        from .models import Opportunity, Project

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
        enforce_site_write_access(self.request.user, project.opportunity)
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
            Site.objects.filter(
                project__opportunity__in=entitled_opportunity_queryset(
                    Opportunity.objects.visible_to(self.request.user), self.request.user
                )
            ),
            pk=self.kwargs['site_pk'],
        )
