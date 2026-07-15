from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User

from .models import Jcode


class JcodeApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='alice', email='a@example.com', password='pw')
        self.client.force_authenticate(user=self.user)
        Jcode.objects.create(
            id='0400100',
            state='Arizona',
            county='Maricopa',
            place_name_short='Phoenix',
            place_name_long='Phoenix city',
        )
        Jcode.objects.create(
            id='0600100',
            state='California',
            county='Los Angeles',
            place_name_short='LA',
            place_name_long='Los Angeles city',
        )

    def test_list_jcodes(self):
        response = self.client.get('/api/jcodes/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_filter_by_state(self):
        response = self.client.get('/api/jcodes/?state=Arizona')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['id'], '0400100')

    def test_jcodes_are_read_only(self):
        response = self.client.post('/api/jcodes/', {'id': '9999999', 'state': 'Texas'})
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
