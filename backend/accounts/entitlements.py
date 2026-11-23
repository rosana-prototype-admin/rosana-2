"""Centralized subscription and organization entitlement decisions."""

from dataclasses import dataclass
from django.utils import timezone

from groups.models import Group, Membership, OrganizationRole

from .models import PlanFeature, SubscriptionSeatType, SubscriptionStatus, UserSubscription


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

    # These statuses represent an interruption before the contractual end
    # date. They are intentionally testable without a payment provider.
    if subscription.status == SubscriptionStatus.PAST_DUE:
        return AccessState.EXPIRED_GRACE
    if subscription.status == SubscriptionStatus.PAUSED:
        return AccessState.EXPIRED_RESTRICTED

    # A canceled or explicitly expired record enters the same dated lifecycle
    # as an ended subscription. If no end date exists, treat the status change
    # as occurring now, which starts the grace period.
    if subscription.status in {SubscriptionStatus.CANCELED, SubscriptionStatus.EXPIRED}:
        end = subscription.ends_at or now
        months = _full_months_since(end, now)
        if months < 3:
            return AccessState.EXPIRED_GRACE
        if months < 6:
            return AccessState.EXPIRED_RESTRICTED
        if months < 12:
            return AccessState.EXPIRED_LOCKED
        return AccessState.ARCHIVE_DUE

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


def user_entitlement_contexts(user):
    """Return the user's distinct organization contexts with subscriptions."""
    if user is None or not user.is_authenticated or not user.is_active:
        return []
    groups = list(Membership.objects.filter(user=user).values_list('group_id', flat=True))
    groups += list(Group.objects.filter(admin=user).values_list('id', flat=True))
    contexts = []
    seen_organizations = set()
    for group_id in groups:
        group = Group.objects.select_related('parent').get(pk=group_id)
        context = entitlement_context(user, group)
        organization_id = context.group.id if context.group else None
        if context.subscription is not None and organization_id not in seen_organizations:
            contexts.append(context)
            seen_organizations.add(organization_id)
    return contexts


def user_entitlement_plan_codes(user):
    return {
        context.subscription.plan_code
        for context in user_entitlement_contexts(user)
        if (
            context.access_state == AccessState.ACTIVE
            and context.subscription.plan_code
            and context.organization_role in {OrganizationRole.TECHNICAL_ADMIN, OrganizationRole.TECHNICAL_USER}
            and (
                context.organization_role == OrganizationRole.TECHNICAL_ADMIN
                or context.has_technical_seat
            )
        )
    }


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


def can_view_existing(user, group=None):
    """Whether a user may view resources belonging to an organization.

    The first three months after expiry are deliberately read-only. A user
    with no subscription context is left to the legacy resource-permission
    checks so existing, not-yet-migrated organizations continue to work.
    """
    context = entitlement_context(user, group)
    if context.subscription is None:
        return True
    if user.is_staff:
        return True
    if context.organization_role not in {
        OrganizationRole.FINANCIAL_ADMIN,
        OrganizationRole.TECHNICAL_ADMIN,
        OrganizationRole.TECHNICAL_USER,
        OrganizationRole.COMMENTER,
    }:
        return False
    if context.access_state == AccessState.EXPIRED_GRACE:
        return True
    if context.access_state != AccessState.ACTIVE:
        return False
    return plan_feature_enabled(context.subscription, 'view_existing')


def can_view_billing(user, group=None):
    """Whether the user may view organization subscription information."""
    context = entitlement_context(user, group)
    if user is not None and user.is_staff and user.is_active:
        return True
    return context.organization_role in {
        OrganizationRole.FINANCIAL_ADMIN,
        OrganizationRole.TECHNICAL_ADMIN,
    }


def can_change_billing(user, group=None):
    """Whether the user may change subscription records without payment access."""
    context = entitlement_context(user, group)
    if user is not None and user.is_staff and user.is_active:
        return True
    if context.organization_role != OrganizationRole.FINANCIAL_ADMIN:
        return False
    return context.access_state != AccessState.ARCHIVE_DUE


def can_manage_seats(user, group=None):
    """Whether the user may assign or release technical seats."""
    context = entitlement_context(user, group)
    if user is not None and user.is_staff and user.is_active:
        return True
    return (
        context.organization_role == OrganizationRole.TECHNICAL_ADMIN
        and context.access_state == AccessState.ACTIVE
    )
