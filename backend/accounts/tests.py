from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

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
