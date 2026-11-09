from django.urls import reverse
from django.core import mail
from django.core.exceptions import ValidationError
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase

from geo.models import Jcode
from groups.models import Group, Membership

from .models import AuditEvent, Contract, User, UserSubscription
from .staff import validate_staff_account_change


class RegistrationAndAuthTests(APITestCase):
    @override_settings(
        EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
        FRONTEND_BASE_URL='https://app.example.com',
    )
    def test_register_creates_inactive_user_and_sends_verification_email(self):
        response = self.client.post(
            reverse('register'),
            {
                'username': 'alice',
                'email': 'alice@example.com',
                'password': 'StrongPass123!',
            },
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user = User.objects.get(username='alice')
        self.assertTrue(user.check_password('StrongPass123!'))
        self.assertFalse(user.is_active)
        self.assertFalse(user.email_verified)
        self.assertNotIn('password', response.data)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['alice@example.com'])
        self.assertIn('https://app.example.com/verify-email?', mail.outbox[0].body)

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_unverified_user_cannot_sign_in_until_email_is_verified(self):
        response = self.client.post(
            reverse('register'),
            {
                'username': 'alice',
                'email': 'alice@example.com',
                'password': 'StrongPass123!',
            },
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        token_response = self.client.post(
            reverse('token_obtain_pair'),
            {'username': 'alice', 'password': 'StrongPass123!'},
        )
        self.assertEqual(token_response.status_code, status.HTTP_401_UNAUTHORIZED)

        user = User.objects.get(username='alice')
        uid = mail.outbox[0].body.split('uid=')[1].split('&', 1)[0]
        verification_token = mail.outbox[0].body.split('token=', 1)[1].split('&', 1)[0].split()[0]
        verify_response = self.client.post(
            reverse('verify-email'),
            {'uid': uid, 'token': verification_token},
        )
        self.assertEqual(verify_response.status_code, status.HTTP_200_OK)
        user.refresh_from_db()
        self.assertTrue(user.is_active)
        self.assertTrue(user.email_verified)

        token_response = self.client.post(
            reverse('token_obtain_pair'),
            {'username': 'alice', 'password': 'StrongPass123!'},
        )
        self.assertEqual(token_response.status_code, status.HTTP_200_OK)

        replay_response = self.client.post(
            reverse('verify-email'),
            {'uid': uid, 'token': verification_token},
        )
        self.assertEqual(replay_response.status_code, status.HTTP_400_BAD_REQUEST)

    @override_settings(
        EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
        FRONTEND_BASE_URL='https://app.example.com',
    )
    def test_password_reset_sends_email_without_revealing_unknown_accounts(self):
        user = User.objects.create_user(
            username='reset-user',
            email='reset@example.com',
            password='OldStrongPass123!',
        )
        response = self.client.post(
            reverse('password-reset'),
            {'email': user.email},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('https://app.example.com/reset-password?', mail.outbox[0].body)

        mail.outbox = []
        response = self.client.post(
            reverse('password-reset'),
            {'email': 'nobody@example.com'},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(mail.outbox), 0)

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_password_reset_changes_password_and_invalidates_token(self):
        user = User.objects.create_user(
            username='reset-user',
            email='reset@example.com',
            password='OldStrongPass123!',
        )
        self.client.post(reverse('password-reset'), {'email': user.email})
        body = mail.outbox[0].body
        uid = body.split('uid=')[1].split('&', 1)[0]
        token = body.split('token=', 1)[1].split()[0]

        response = self.client.post(
            reverse('password-reset-confirm'),
            {'uid': uid, 'token': token, 'new_password': 'NewStrongPass123!'},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        old_login = self.client.post(
            reverse('token_obtain_pair'),
            {'username': user.username, 'password': 'OldStrongPass123!'},
        )
        self.assertEqual(old_login.status_code, status.HTTP_401_UNAUTHORIZED)
        new_login = self.client.post(
            reverse('token_obtain_pair'),
            {'username': user.username, 'password': 'NewStrongPass123!'},
        )
        self.assertEqual(new_login.status_code, status.HTTP_200_OK)

        replay = self.client.post(
            reverse('password-reset-confirm'),
            {'uid': uid, 'token': token, 'new_password': 'AnotherStrongPass123!'},
        )
        self.assertEqual(replay.status_code, status.HTTP_400_BAD_REQUEST)

    def test_obtain_token_and_fetch_me(self):
        User.objects.create_user(username='bob', email='bob@example.com', password='StrongPass123!')

        token_response = self.client.post(
            reverse('token_obtain_pair'),
            {'username': 'bob', 'password': 'StrongPass123!'},
        )
        self.assertEqual(token_response.status_code, status.HTTP_200_OK)
        access = token_response.data['access']

        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access}')
        me_response = self.client.get(reverse('me'))
        self.assertEqual(me_response.status_code, status.HTTP_200_OK)
        self.assertEqual(me_response.data['username'], 'bob')
        self.assertEqual(me_response.data['subscription_type'], 'none')

    def test_me_requires_authentication(self):
        response = self.client.get(reverse('me'))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_subscription_type_is_not_self_editable(self):
        user = User.objects.create_user(username='carol', email='carol@example.com', password='StrongPass123!')
        self.client.force_authenticate(user=user)
        response = self.client.patch(reverse('me'), {'subscription_type': 'admin'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        user.refresh_from_db()
        self.assertEqual(user.subscription_type, 'none')

    def test_user_preferences_have_defaults_and_can_be_updated(self):
        user = User.objects.create_user(username='dana', email='dana@example.com', password='StrongPass123!')
        self.client.force_authenticate(user=user)

        response = self.client.get(reverse('me'))
        self.assertEqual(response.data['language'], 'en-US')
        self.assertEqual(response.data['currency'], 'USD')
        self.assertEqual(response.data['length_unit'], 'm')
        self.assertEqual(response.data['distance_unit'], 'km')
        self.assertEqual(response.data['speed_unit'], 'km/h')
        self.assertEqual(response.data['area_small_unit'], 'm2')
        self.assertEqual(response.data['area_large_unit'], 'ha')
        self.assertEqual(response.data['volume_unit'], 'L')

        response = self.client.patch(
            reverse('me'),
            {
                'language': 'fr-CA',
                'currency': 'CAD',
                'length_unit': 'ft',
                'distance_unit': 'mi',
                'speed_unit': 'mph',
                'area_small_unit': 'sq ft',
                'area_large_unit': 'ac',
                'volume_unit': 'gal (Imp)',
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        user.refresh_from_db()
        self.assertEqual(user.language, 'fr-CA')
        self.assertEqual(user.currency, 'CAD')
        self.assertEqual(user.length_unit, 'ft')
        self.assertEqual(user.distance_unit, 'mi')
        self.assertEqual(user.speed_unit, 'mph')
        self.assertEqual(user.area_small_unit, 'sq ft')
        self.assertEqual(user.area_large_unit, 'ac')
        self.assertEqual(user.volume_unit, 'gal (Imp)')


class UserSearchTests(APITestCase):
    def setUp(self):
        self.searcher = User.objects.create_user(username='searcher', email='searcher@example.com', password='pw')
        self.alice = User.objects.create_user(
            username='alice', email='alice@example.com', password='pw',
            first_name='Alice', last_name='Anderson',
        )
        self.bob = User.objects.create_user(
            username='bob', email='bob@example.com', password='pw',
            first_name='Bob', last_name='Baker',
        )
        self.jcode = Jcode.objects.create(
            id='US1900000000', state='Iowa', place_name_short='Iowa', place_name_long='State of Iowa',
        )
        self.other_jcode = Jcode.objects.create(
            id='US1900100000', state='Iowa', county='Adair', place_name_short='Adair County',
            place_name_long='Adair County',
        )
        alice_group = Group.objects.create(name='Alice Group', admin=self.alice)
        alice_group.jcodes.add(self.jcode)
        bob_group = Group.objects.create(name='Bob Group', admin=self.bob)
        bob_group.jcodes.add(self.other_jcode)

        self.client.force_authenticate(user=self.searcher)

    def test_requires_authentication(self):
        self.client.force_authenticate(user=None)
        response = self.client.get(reverse('user-search'), {'q': 'alice'})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_no_params_returns_empty(self):
        response = self.client.get(reverse('user-search'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])

    def test_query_below_minimum_length_returns_empty(self):
        response = self.client.get(reverse('user-search'), {'q': 'a'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])

    def test_query_matches_username(self):
        response = self.client.get(reverse('user-search'), {'q': 'alic'})
        usernames = [row['username'] for row in response.data]
        self.assertEqual(usernames, ['alice'])

    def test_query_matches_email_case_insensitively(self):
        response = self.client.get(reverse('user-search'), {'q': 'ALICE@EXAMPLE'})
        usernames = [row['username'] for row in response.data]
        self.assertEqual(usernames, ['alice'])

    def test_query_matches_last_name(self):
        response = self.client.get(reverse('user-search'), {'q': 'Baker'})
        usernames = [row['username'] for row in response.data]
        self.assertEqual(usernames, ['bob'])

    def test_sensitive_fields_are_not_exposed(self):
        response = self.client.get(reverse('user-search'), {'q': 'alice'})
        self.assertNotIn('subscription_type', response.data[0])
        self.assertNotIn('jcodes', response.data[0])
        self.assertNotIn('company', response.data[0])

    def test_jcode_filter_alone(self):
        response = self.client.get(reverse('user-search'), {'jcode': self.jcode.id})
        usernames = [row['username'] for row in response.data]
        self.assertEqual(usernames, ['alice'])

    def test_jcode_and_query_combined_intersect(self):
        response = self.client.get(reverse('user-search'), {'jcode': self.jcode.id, 'q': 'bob'})
        self.assertEqual(response.data, [])

        response = self.client.get(reverse('user-search'), {'jcode': self.jcode.id, 'q': 'alice'})
        usernames = [row['username'] for row in response.data]
        self.assertEqual(usernames, ['alice'])

    def test_unknown_jcode_returns_empty(self):
        response = self.client.get(reverse('user-search'), {'jcode': 'US9999999999'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])


class AdminUserManagementTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username='platform-admin', email='admin@example.com', password='pw', is_staff=True,
        )
        self.user = User.objects.create_user(
            username='managed-user', email='user@example.com', password='pw',
        )
        self.company = Group.objects.create(name='Managed Company', admin=self.admin)
        Membership.objects.create(group=self.company, user=self.user)
    def test_admin_user_list_requires_staff(self):
        response = self.client.get(reverse('admin-user-list'))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        self.client.force_authenticate(user=self.user)
        response = self.client.get(reverse('admin-user-list'))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_staff_can_list_and_filter_users(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.get(reverse('admin-user-list'), {'q': 'managed'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['username'], 'managed-user')
        self.assertIn('is_staff', response.data[0])

    def test_staff_can_update_account_status_without_assigning_a_company_subscription(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.patch(
            reverse('admin-user-detail', args=[self.user.pk]),
            {'is_active': False, 'email_verified': False, 'subscription_type': 'basic'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_active)
        self.assertFalse(self.user.email_verified)
        self.assertEqual(self.user.subscription_type, 'none')
        self.assertTrue(AuditEvent.objects.filter(action='user.updated', entity_id=str(self.user.pk)).exists())

    def test_staff_cannot_deactivate_themselves(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.patch(
            reverse('admin-user-detail', args=[self.admin.pk]),
            {'is_active': False},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_last_active_staff_user_cannot_be_deactivated(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.patch(
            reverse('admin-user-detail', args=[self.user.pk]),
            {'is_active': False},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.admin.refresh_from_db()
        with self.assertRaises(ValidationError):
            validate_staff_account_change(self.admin, is_active=False)

    def test_another_active_staff_user_can_be_deactivated(self):
        second_admin = User.objects.create_user(
            username='second-admin', email='second-admin@example.com', password='pw', is_staff=True,
        )
        self.client.force_authenticate(user=self.admin)
        response = self.client.patch(
            reverse('admin-user-detail', args=[second_admin.pk]),
            {'is_active': False},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_admin_can_resend_verification_email(self):
        self.user.email_verified = False
        self.user.is_active = False
        self.user.save(update_fields=['email_verified', 'is_active'])
        self.client.force_authenticate(user=self.admin)

        response = self.client.post(
            reverse('admin-resend-verification', args=[self.user.pk]),
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('/verify-email?', mail.outbox[0].body)

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_admin_can_send_password_reset_email(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.post(
            reverse('admin-send-password-reset', args=[self.user.pk]),
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('/reset-password?', mail.outbox[0].body)

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_admin_lifecycle_actions_reject_ineligible_accounts(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.post(
            reverse('admin-resend-verification', args=[self.user.pk]),
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        self.user.email_verified = False
        self.user.save(update_fields=['email_verified'])
        response = self.client.post(
            reverse('admin-send-password-reset', args=[self.user.pk]),
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_admin_can_read_and_update_company_subscription_record(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.get(reverse('admin-group-subscription', args=[self.company.pk]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['plan_code'], 'none')

        response = self.client.patch(
            reverse('admin-group-subscription', args=[self.company.pk]),
            {'plan_code': 'premium', 'status': 'trialing', 'seat_limit': 5, 'notes': 'Pilot access'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'trialing')
        self.assertEqual(response.data['seat_limit'], 5)
        self.assertEqual(UserSubscription.objects.filter(group=self.company).count(), 1)
        event = AuditEvent.objects.get(action='subscription.updated')
        self.assertEqual(event.group_id, self.company.pk)
        self.assertEqual(event.after['seat_limit'], 5)

    def test_admin_can_create_and_update_company_contract(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.post(
            reverse('admin-group-contract-list', args=[self.company.pk]),
            {'title': 'Pilot agreement', 'status': 'pending', 'notes': 'Needs signature'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        contract_id = response.data['id']
        self.assertTrue(Contract.objects.filter(pk=contract_id, group=self.company).exists())

        response = self.client.patch(
            reverse('admin-group-contract-detail', args=[self.company.pk, contract_id]),
            {'status': 'active'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'active')
        self.assertTrue(AuditEvent.objects.filter(action='contract.created', entity_id=str(contract_id)).exists())

    def test_non_staff_cannot_manage_subscription_or_contracts(self):
        self.client.force_authenticate(user=self.user)
        self.assertEqual(
            self.client.get(reverse('admin-group-subscription', args=[self.company.pk])).status_code,
            status.HTTP_403_FORBIDDEN,
        )
        self.assertEqual(
            self.client.get(reverse('admin-group-contract-list', args=[self.company.pk])).status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_admin_can_assign_seats_only_to_group_members_within_limit(self):
        self.client.force_authenticate(user=self.admin)
        subscription_url = reverse('admin-group-subscription', args=[self.company.pk])
        self.client.patch(subscription_url, {'seat_limit': 1}, format='json')
        response = self.client.post(
            reverse('admin-group-seat-list', args=[self.company.pk]),
            {'user_id': self.user.pk}, format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        response = self.client.post(
            reverse('admin-group-seat-list', args=[self.company.pk]),
            {'user_id': self.admin.pk}, format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(AuditEvent.objects.filter(action='seat.assigned').exists())
