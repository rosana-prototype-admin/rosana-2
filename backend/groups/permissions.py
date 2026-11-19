from rest_framework.permissions import SAFE_METHODS, BasePermission

GROUP_PERMISSION_DEFINITIONS = [
    {
        'code': 'add_new_user',
        'label': 'Add new user',
        'category': 'User Rights Management',
    },
    {
        'code': 'approve_new_user',
        'label': 'Approve new user',
        'category': 'User Rights Management',
    },
    {
        'code': 'delete_user',
        'label': 'Delete user',
        'category': 'User Rights Management',
    },
    {
        'code': 'change_user_permissions',
        'label': 'Change user permissions',
        'category': 'User Rights Management',
    },
    {
        'code': 'comment_existing_resources',
        'label': 'Comment on existing Opportunity/Project/Site/Strategy',
        'category': 'Collaboration',
    },
    {
        'code': 'summarize_other_comments',
        'label': "Summarize other users' comments",
        'category': 'Collaboration',
    },
    {
        'code': 'delete_other_comments',
        'label': "Delete other users' comments",
        'category': 'Collaboration',
    },
    {
        'code': 'create_modify_opportunity',
        'label': 'Create/Modify Opportunity',
        'category': 'Safety Analysis',
    },
    {
        'code': 'create_modify_project',
        'label': 'Create/Modify Project',
        'category': 'Safety Analysis',
    },
    {
        'code': 'create_modify_site',
        'label': 'Create/Modify Site',
        'category': 'Safety Analysis',
    },
    {
        'code': 'create_modify_strategy',
        'label': 'Create/Modify Strategy',
        'category': 'Safety Analysis',
    },
    {
        'code': 'create_modify_cmf',
        'label': 'Create/modify custom Casualty Modification Factor (CMF)',
        'category': 'Safety Analysis',
    },
    {
        'code': 'delete_opportunity',
        'label': 'Delete Opportunity',
        'category': 'Safety Analysis',
    },
    {
        'code': 'delete_project',
        'label': 'Delete Project',
        'category': 'Safety Analysis',
    },
    {
        'code': 'delete_site',
        'label': 'Delete Site',
        'category': 'Safety Analysis',
    },
    {
        'code': 'delete_strategy',
        'label': 'Delete Strategy',
        'category': 'Safety Analysis',
    },
    {
        'code': 'delete_cmf',
        'label': 'Delete custom Casualty Modification Factor (CMF)',
        'category': 'Safety Analysis',
    },
    {
        'code': 'change_organization_name',
        'label': 'Change organization name',
        'category': 'Subscriptions/Billing/Payment',
    },
    {
        'code': 'change_billing_address',
        'label': 'Change billing address',
        'category': 'Subscriptions/Billing/Payment',
    },
    {
        'code': 'change_subscription_plan',
        'label': 'Change subscription plan',
        'category': 'Subscriptions/Billing/Payment',
    },
    {
        'code': 'change_payment_details',
        'label': 'Change payment details (e.g., credit card number)',
        'category': 'Subscriptions/Billing/Payment',
    },
]
GROUP_PERMISSION_CODES = tuple(item['code'] for item in GROUP_PERMISSION_DEFINITIONS)

GROUP_PERMISSION_FEATURES = {
    'add_new_user': 'manage_users',
    'approve_new_user': 'manage_users',
    'delete_user': 'manage_users',
    'change_user_permissions': 'manage_users',
    'comment_existing_resources': 'comment',
    'summarize_other_comments': 'comment',
    'delete_other_comments': 'comment',
    'create_modify_opportunity': 'analyze',
    'create_modify_project': 'analyze',
    'create_modify_site': 'analyze',
    'create_modify_strategy': 'analyze',
    'create_modify_cmf': 'analyze',
    'delete_opportunity': 'delete_resources',
    'delete_project': 'delete_resources',
    'delete_site': 'delete_resources',
    'delete_strategy': 'delete_resources',
    'delete_cmf': 'delete_resources',
    'change_organization_name': 'manage_groups',
    'change_billing_address': 'manage_billing',
    'change_subscription_plan': 'manage_billing',
    'change_payment_details': 'manage_billing',
}


def default_group_permissions():
    return {code: False for code in GROUP_PERMISSION_CODES}


def all_group_permissions():
    return {code: True for code in GROUP_PERMISSION_CODES}


def normalize_group_permissions(value):
    if value is None:
        return default_group_permissions()
    if not isinstance(value, dict):
        raise ValueError('permissions must be an object of boolean values.')
    unknown = set(value) - set(GROUP_PERMISSION_CODES)
    if unknown:
        raise ValueError(f'Unknown group permission(s): {", ".join(sorted(unknown))}.')
    if any(not isinstance(item, bool) for item in value.values()):
        raise ValueError('permissions must contain only boolean values.')
    normalized = default_group_permissions()
    normalized.update(value)
    return normalized


def is_admin(user, group):
    return group.admin_id == user.pk


def has_group_feature(user, group, feature_code):
    """Apply subscription entitlement to a group-management capability.

    Groups without a subscription remain in compatibility mode and continue
    using the existing group-permission behavior.
    """
    # Imported lazily because groups.models imports default_group_permissions
    # from this module during Django app initialization.
    from accounts.entitlements import can_use_feature, subscription_for_group

    if subscription_for_group(group) is None:
        return True
    return can_use_feature(user, feature_code, group)


def has_group_permission(user, group, permission_code):
    if user is None or not user.is_authenticated or not user.is_active:
        return False
    if user.is_staff and user.is_active:
        return True
    feature_code = GROUP_PERMISSION_FEATURES.get(permission_code)
    if feature_code and not has_group_feature(user, group, feature_code):
        return False
    if is_admin(user, group):
        return True
    membership = group.memberships.filter(user_id=user.pk).only('permissions').first()
    return bool(membership and membership.permissions.get(permission_code, False))


def user_has_group_membership(user, group):
    return bool(
        user
        and user.is_authenticated
        and (
            group.admin_id == user.pk
            or group.memberships.filter(user_id=user.pk).exists()
        )
    )


def user_has_any_group_membership(user):
    from django.db.models import Q
    from .models import Group

    return Group.objects.filter(Q(admin_id=user.pk) | Q(memberships__user_id=user.pk)).exists()


def has_any_group_permission(user, permission_code):
    from django.db.models import Q
    from .models import Group

    if user is None or not user.is_authenticated or not user.is_active:
        return False
    if user.is_staff:
        return True
    groups = Group.objects.filter(Q(admin_id=user.pk) | Q(memberships__user_id=user.pk)).distinct()
    return any(has_group_permission(user, group, permission_code) for group in groups)


def has_opportunity_permission(user, opportunity, permission_code):
    """Check a permission on groups attached to an Opportunity.

    Opportunities may contain older direct user roles. Those users remain
    governed by the legacy role rules until they are also managed through a
    Group membership. Group-based access is governed by the new permission
    map, with any relevant group granting access being sufficient.
    """
    groups = [opportunity.lead_agency, *opportunity.assoc_agencies.all()]
    relevant_groups = [group for group in groups if user_has_group_membership(user, group)]
    if not relevant_groups:
        return True
    return any(has_group_permission(user, group, permission_code) for group in relevant_groups)


class GroupAccessPermission(BasePermission):
    """
    Any authenticated user may read a group; only its admin may write to it.
    Object-level only -- `create` has no object yet, so GroupViewSet checks
    the parent's admin explicitly in perform_create instead.
    """

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        if request.user.is_staff and request.user.is_active:
            return True
        if view.action == 'invite':
            return has_group_permission(request.user, obj, 'add_new_user')
        if view.action == 'member_detail':
            return has_group_permission(request.user, obj, 'delete_user') or has_group_permission(
                request.user, obj, 'change_user_permissions'
            )
        if view.action in {'update', 'partial_update'}:
            return has_group_permission(request.user, obj, 'change_organization_name')
        if view.action in {'destroy', 'set_admin'}:
            return is_admin(request.user, obj) and has_group_feature(
                request.user, obj, 'manage_users' if view.action == 'set_admin' else 'manage_groups'
            )
        if view.action == 'update_jcodes':
            return is_admin(request.user, obj) and has_group_feature(
                request.user, obj, 'manage_groups'
            )
        return False
