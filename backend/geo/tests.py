from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User

from .models import CountryCode, Jcode


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

    def test_filter_by_state_and_county(self):
        response = self.client.get('/api/jcodes/?state=Arizona&county=Maricopa')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([jcode['id'] for jcode in response.data], ['0400100'])

    def test_search_jcodes(self):
        response = self.client.get('/api/jcodes/?q=Phoenix')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([jcode['id'] for jcode in response.data], ['0400100'])

    def test_jcodes_are_read_only(self):
        response = self.client.post('/api/jcodes/', {'id': '9999999', 'state': 'Texas'})
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_jcode_defaults_to_us_country_code(self):
        # Every Jcode currently comes from US Census place-code imports, so
        # the FK defaults to 'US' rather than requiring every creation site
        # to set it explicitly.
        jcode = Jcode.objects.get(id='0400100')
        self.assertEqual(jcode.country_code_id, 'US')

        response = self.client.get('/api/jcodes/0400100/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['country_code']['alpha_2'], 'US')
        self.assertEqual(response.data['country_code']['name_short'], 'USA')


class CountryCodeApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='bob', email='b@example.com', password='pw')
        self.client.force_authenticate(user=self.user)

    def test_list_country_codes_seeded_from_migration(self):
        response = self.client.get('/api/country-codes/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), CountryCode.objects.count())
        self.assertGreater(len(response.data), 200)

    def test_retrieve_country_code(self):
        response = self.client.get('/api/country-codes/US/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['alpha_3'], 'USA')
        self.assertEqual(response.data['name_long'], 'United States of America')

    def test_country_codes_are_read_only(self):
        response = self.client.post('/api/country-codes/', {'alpha_2': 'ZZ', 'alpha_3': 'ZZZ'})
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_deleting_a_referenced_country_code_is_protected(self):
        from django.db.models import ProtectedError

        Jcode.objects.create(
            id='0400100',
            state='Arizona',
            place_name_short='Phoenix',
            place_name_long='Phoenix city',
        )
        us = CountryCode.objects.get(alpha_2='US')
        with self.assertRaises(ProtectedError):
            us.delete()
