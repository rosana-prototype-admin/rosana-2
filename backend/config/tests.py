from django.test import TestCase, override_settings
from django.urls import reverse


class HealthEndpointTests(TestCase):
    def test_liveness_does_not_require_authentication(self):
        response = self.client.get(reverse('health'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'ok')

    def test_readiness_reports_database_health(self):
        response = self.client.get(reverse('health-readiness'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['database'], 'ok')

    @override_settings(SECURE_SSL_REDIRECT=True)
    def test_health_endpoints_remain_probeable_when_https_redirects_are_enabled(self):
        liveness = self.client.get(reverse('health'))
        readiness = self.client.get(reverse('health-readiness'))

        self.assertEqual(liveness.status_code, 200)
        self.assertEqual(readiness.status_code, 200)
