from datetime import timedelta

from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from groups.models import Group, Membership, OrganizationRole

from .models import Plan, PlanFeature, SubscriptionSeat, User, UserSubscription


class OrganizationSubscriptionWorkflowTests(APITestCase):
    def setUp(self):
        self.technical_admin = User.objects.create_user(
            username='technical-admin', email='technical-admin@example.com', password='pw'
        )
        self.financial_admin = User.objects.create_user(
            username='financial-admin', email='financial-admin@example.com', password='pw'
        )
        self.commenter = User.objects.create_user(
            username='commenter', email='commenter@example.com', password='pw'
        )
        self.organization = Group.objects.create(name='Billing Organization', admin=self.technical_admin)
        Membership.objects.create(
            group=self.organization,
            user=self.financial_admin,
            organization_role=OrganizationRole.FINANCIAL_ADMIN,
        )
        Membership.objects.create(
            group=self.organization,
            user=self.commenter,
            organization_role=OrganizationRole.COMMENTER,
        )
        self.plan = Plan.objects.create(code='self-service-test', name='Self-Service Test')
        self.new_plan = Plan.objects.create(code='self-service-plus', name='Self-Service Plus')
        PlanFeature.objects.create(plan=self.plan, feature_code='manage_billing')
        self.subscription = UserSubscription.objects.create(
            group=self.organization,
            plan=self.plan,
            plan_code=self.plan.code,
            starts_at=timezone.now() - timedelta(days=1),
            seat_limit=3,
        )

    def url(self):
        return reverse('organization-subscription', args=[self.organization.pk])

    def users_url(self):
        return reverse('organization-subscription-users', args=[self.organization.pk])

    def test_financial_and_technical_admins_can_view_billing_summary(self):
        for user in (self.financial_admin, self.technical_admin):
            self.client.force_authenticate(user=user)
            response = self.client.get(self.url())
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.data['subscription']['plan_code'], self.plan.code)
            self.assertEqual(response.data['payment_processing'], 'not_configured')

    def test_commenter_cannot_view_billing_summary(self):
        self.client.force_authenticate(user=self.commenter)
        response = self.client.get(self.url())
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_financial_admin_can_simulate_plan_change(self):
        self.client.force_authenticate(user=self.financial_admin)
        response = self.client.patch(self.url(), {'plan_id': self.new_plan.pk}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.subscription.refresh_from_db()
        self.assertEqual(self.subscription.plan_id, self.new_plan.pk)
        self.assertEqual(self.subscription.plan_code, self.new_plan.code)

    def test_technical_admin_can_view_but_not_change_subscription(self):
        self.client.force_authenticate(user=self.technical_admin)
        response = self.client.patch(self.url(), {'seat_limit': 20}, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_billing_user_list_includes_active_seat_assignment(self):
        SubscriptionSeat.objects.create(
            subscription=self.subscription,
            user=self.technical_admin,
        )
        self.client.force_authenticate(user=self.financial_admin)
        response = self.client.get(self.users_url())
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        by_username = {entry['username']: entry for entry in response.data['users']}
        self.assertEqual(by_username['technical-admin']['seat_type'], 'technical_user')
