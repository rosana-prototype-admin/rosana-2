"""Centralized subscription and organization entitlement decisions."""

from dataclasses import dataclass
from django.utils import timezone

from groups.models import Group, Membership, OrganizationRole

from .models import PlanFeature, SubscriptionSeatType, UserSubscription


class AccessState:
    ACTIVE = 'active'
    EXPIRED_GRACE = 'expired_grace'
    EXPIRED_RESTRICTED = 'expired_restricted'
    EXPIRED_LOCKED = 'expired_locked'
    ARCHIVE_DUE = 'archive_due'
    UNLICENSED = 'unlicensed'


@dataclass(frozen=True)
class EntitlementContext:
    user: object
    group: Group | None
    subscription: UserSubscription | None
    organization_role: str | None
    has_technical_seat: bool
    access_state: str


def top_level_group(group):
    """Return the billing organization at the top of a group tree."""
    while group is not None and group.parent_id is not None:
        group = group.parent
    return group


def subscription_for_group(group):
    organization = top_level_group(group)
    if organization is None:
        return None
    return organization.subscriptions.select_related('plan').order_by('-starts_at', '-created_at').first()


def _full_months_since(start, now):
    start_date = start.date() if hasattr(start, 'date') else start
    current_date = now.date() if hasattr(now, 'date') else now
    months = (current_date.year - start_date.year) * 12 + current_date.month - start_date.month
    if current_date.day < start_date.day:
        months -= 1
    return max(months, 0)


def subscription_access_state(subscription, now=None):
    if subscription is None:
        return AccessState.UNLICENSED
    now = now or timezone.now()
    if subscription.ends_at is None or subscription.ends_at > now:
        return AccessState.ACTIVE

    months = _full_months_since(subscription.ends_at, now)
    if months < 3:
        return AccessState.EXPIRED_GRACE
    if months < 6:
        return AccessState.EXPIRED_RESTRICTED
    if months < 12:
        return AccessState.EXPIRED_LOCKED
    return AccessState.ARCHIVE_DUE


def _organization_membership(user, group):
    if group.admin_id == user.pk:
        return None, OrganizationRole.TECHNICAL_ADMIN
    membership = Membership.objects.filter(group=group, user=user).first()
    return membership, membership.organization_role if membership else None


def entitlement_context(user, group=None):
    if user is None or not user.is_authenticated or not user.is_active:
        return EntitlementContext(user, group, None, None, False, AccessState.UNLICENSED)

    if group is not None:
        organization = top_level_group(group)
        subscription = subscription_for_group(group)
        membership, role = _organization_membership(user, group)
        if role is None and organization != group:
            membership, role = _organization_membership(user, organization)
        if role is None:
            return EntitlementContext(user, group, subscription, None, False, AccessState.UNLICENSED)
        seat = subscription and subscription.seats.filter(
            user=user, released_at__isnull=True,
            seat_type__in=[SubscriptionSeatType.TECHNICAL_USER, SubscriptionSeatType.TECHNICAL_ADMIN],
        ).exists()
        return EntitlementContext(user, organization, subscription, role, seat, subscription_access_state(subscription))

    memberships = Membership.objects.filter(user=user).select_related('group')
    for membership in memberships:
        context = entitlement_context(user, membership.group)
        if context.subscription is not None:
            return context
    for administered_group in Group.objects.filter(admin=user).select_related('parent'):
        context = entitlement_context(user, administered_group)
        if context.subscription is not None:
            return context
    return EntitlementContext(user, None, None, None, False, AccessState.UNLICENSED)


def plan_feature_enabled(subscription, feature_code):
    if subscription is None or subscription.plan_id is None:
        return False
    feature = PlanFeature.objects.filter(plan_id=subscription.plan_id, feature_code=feature_code).first()
    return bool(feature and feature.enabled)


def can_use_feature(user, feature_code, group=None):
    context = entitlement_context(user, group)
    if context.access_state != AccessState.ACTIVE:
        return False
    if user.is_staff:
        return True

    role = context.organization_role
    role_features = {
        'view_existing': {OrganizationRole.FINANCIAL_ADMIN, OrganizationRole.TECHNICAL_ADMIN, OrganizationRole.TECHNICAL_USER, OrganizationRole.COMMENTER},
        'comment': {OrganizationRole.FINANCIAL_ADMIN, OrganizationRole.TECHNICAL_ADMIN, OrganizationRole.COMMENTER},
        'analyze': {OrganizationRole.TECHNICAL_ADMIN, OrganizationRole.TECHNICAL_USER},
        'manage_billing': {OrganizationRole.FINANCIAL_ADMIN, OrganizationRole.TECHNICAL_ADMIN},
        'manage_users': {OrganizationRole.TECHNICAL_ADMIN},
        'manage_groups': {OrganizationRole.TECHNICAL_ADMIN},
        'delete_resources': {OrganizationRole.TECHNICAL_ADMIN},
    }
    if role not in role_features.get(feature_code, set()):
        return False
    if feature_code == 'analyze' and role == OrganizationRole.TECHNICAL_USER and not context.has_technical_seat:
        return False
    return plan_feature_enabled(context.subscription, feature_code)
