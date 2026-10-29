from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from geo.models import Jcode
from groups.models import Group

from .models import User


class RegistrationAndAuthTests(APITestCase):
    def test_register_creates_user_with_hashed_password(self):
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
        self.assertNotIn('password', response.data)

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
