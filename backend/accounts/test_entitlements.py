from datetime import timedelta

from django.test import TestCase
from django.utils import timezone
from django.urls import reverse
from rest_framework.test import APITestCase

from groups.models import Group, Membership, RosanaRole

from .entitlements import (
    AccessState,
    can_use_feature,
    can_view_existing,
    entitlement_context,
    subscription_access_state,
)
from .models import Plan, PlanFeature, SubscriptionSeat, User, UserSubscription


class EntitlementEngineTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username='org-admin', email='admin@example.com', password='pw',
        )
        self.technical_user = User.objects.create_user(
            username='technical-user', email='technical@example.com', password='pw',
        )
        self.commenter = User.objects.create_user(
            username='commenter', email='commenter@example.com', password='pw',
        )
        self.organization = Group.objects.create(name='Organization', admin=self.admin)
        Membership.objects.create(
            group=self.organization,
            user=self.technical_user,
            rosana_role=RosanaRole.TECHNICAL_USER,
        )
        Membership.objects.create(
            group=self.organization,
            user=self.commenter,
            rosana_role=RosanaRole.COMMENTER,
        )
        self.plan = Plan.objects.create(code='test-plan', name='Test Plan')
        for feature in ('analyze', 'comment', 'view_existing'):
            PlanFeature.objects.create(plan=self.plan, feature_code=feature)
        self.subscription = UserSubscription.objects.create(
            group=self.organization,
            plan=self.plan,
            plan_code='none',
            starts_at=timezone.now() - timedelta(days=1),
        )
        SubscriptionSeat.objects.create(
            subscription=self.subscription,
            user=self.technical_user,
        )

    def test_context_resolves_subscription_and_role(self):
        context = entitlement_context(self.technical_user, self.organization)
        self.assertEqual(context.subscription, self.subscription)
        self.assertEqual(context.rosana_role, RosanaRole.TECHNICAL_USER)
        self.assertTrue(context.has_technical_seat)
        self.assertEqual(context.access_state, AccessState.ACTIVE)

    def test_technical_user_requires_technical_seat_to_analyze(self):
        self.assertTrue(can_use_feature(self.technical_user, 'analyze', self.organization))
        SubscriptionSeat.objects.filter(subscription=self.subscription, user=self.technical_user).update(
            released_at=timezone.now(),
        )
        self.assertFalse(can_use_feature(self.technical_user, 'analyze', self.organization))

    def test_commenter_can_comment_but_cannot_analyze(self):
        self.assertTrue(can_use_feature(self.commenter, 'comment', self.organization))
        self.assertFalse(can_use_feature(self.commenter, 'analyze', self.organization))

    def test_expired_subscription_enters_restricted_lifecycle(self):
        self.subscription.ends_at = timezone.now() - timedelta(days=100)
        self.subscription.save(update_fields=['ends_at'])
        self.assertEqual(subscription_access_state(self.subscription), AccessState.EXPIRED_RESTRICTED)
        self.assertFalse(can_use_feature(self.technical_user, 'analyze', self.organization))

    def test_past_due_subscription_is_read_only_during_grace_period(self):
        self.subscription.status = 'past_due'
        self.subscription.save(update_fields=['status'])
        self.assertEqual(subscription_access_state(self.subscription), AccessState.EXPIRED_GRACE)
        self.assertTrue(can_view_existing(self.technical_user, self.organization))
        self.assertFalse(can_use_feature(self.technical_user, 'analyze', self.organization))

    def test_paused_subscription_is_restricted(self):
        self.subscription.status = 'paused'
        self.subscription.save(update_fields=['status'])
        self.assertEqual(subscription_access_state(self.subscription), AccessState.EXPIRED_RESTRICTED)
        self.assertFalse(can_view_existing(self.technical_user, self.organization))

    def test_archived_organization_has_no_entitlement_context(self):
        self.organization.archived_at = timezone.now()
        self.organization.save(update_fields=['archived_at'])

        context = entitlement_context(self.technical_user, self.organization)

        self.assertIsNone(context.subscription)
        self.assertEqual(context.access_state, AccessState.UNLICENSED)
        self.assertFalse(can_use_feature(self.technical_user, 'analyze', self.organization))


class EntitlementEndpointTests(APITestCase):
    def test_entitlements_endpoint_requires_authentication(self):
        response = self.client.get(reverse('my-entitlements'))
        self.assertEqual(response.status_code, 401)
