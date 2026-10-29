from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User

from .models import FocusArea, InterventionType


class FocusAreaSeedTests(APITestCase):
    """The seed data migration should have already populated the real tree."""

    def test_tree_shape_matches_source_document(self):
        # Road Users, Infrastructure & Speed Management, Vehicle Features &
        # Conditions, and Post-Crash Medical Care are each independent
        # top-level categories (not nested under Road Users) - 3 levels total.
        self.assertEqual(FocusArea.objects.filter(level=1).count(), 4)
        self.assertEqual(FocusArea.objects.filter(level=2).count(), 19)
        self.assertEqual(FocusArea.objects.filter(level=3).count(), 66)
        self.assertEqual(FocusArea.objects.filter(level=4).count(), 0)

    def test_duplicate_name_allowed_under_different_parents(self):
        nodes = FocusArea.objects.filter(name='Post-Crash Medical Care')
        self.assertEqual(nodes.count(), 2)
        self.assertNotEqual(nodes[0].parent_id, nodes[1].parent_id)


class FocusAreaApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='alice', email='a@example.com', password='pw')
        self.client.force_authenticate(user=self.user)

    def test_l1_l2_returns_all_nineteen_combined_options(self):
        response = self.client.get('/api/focus-areas/l1-l2/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 19)
        labels = [item['label'] for item in response.data]
        self.assertEqual(labels[0], 'Road Users - Vulnerable Road Users')
        # Siblings under the same L1 parent must stay in document order.
        self.assertLess(
            labels.index('Road Users - Vulnerable Road Users'),
            labels.index('Road Users - Powersport Vehicle Users'),
        )
        self.assertIn('Infrastructure & Speed Management - Speed Management', labels)
        self.assertIn('Post-Crash Medical Care - Post-Crash Medical Care', labels)

    def test_children_of_vulnerable_road_users(self):
        vru = FocusArea.objects.get(name='Vulnerable Road Users')
        response = self.client.get(f'/api/focus-areas/{vru.pk}/children/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 5)
        self.assertEqual(response.data[0]['name'], 'Pedestrians')


class InterventionTypeApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='alice', email='a@example.com', password='pw')
        self.client.force_authenticate(user=self.user)
        self.vru = FocusArea.objects.get(name='Vulnerable Road Users')
        self.speed = FocusArea.objects.get(name='Speed Management')
        self.crossing_type = InterventionType.objects.create(name='Crossing Improvement')
        self.crossing_type.focus_areas.add(self.vru)
        self.speed_type = InterventionType.objects.create(name='Speed Camera', is_active=False)
        self.speed_type.focus_areas.add(self.speed)

    def test_filter_by_focus_area(self):
        response = self.client.get(f'/api/intervention-types/?focus_area={self.vru.pk}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Not an exact-count check: seed-migration data (e.g. the placeholder
        # Intervention Types linked to every FocusArea) legitimately persists
        # across tests since migrations aren't rolled back like setUp() is.
        names = [item['name'] for item in response.data]
        self.assertIn('Crossing Improvement', names)
        self.assertNotIn('Speed Camera', names)

    def test_inactive_types_are_excluded(self):
        response = self.client.get('/api/intervention-types/')
        names = [item['name'] for item in response.data]
        self.assertNotIn('Speed Camera', names)

    def test_seeded_interventions_expose_their_associated_cmf(self):
        response = self.client.get('/api/intervention-types/')
        rrfb = next(item for item in response.data if item['name'] == 'Rectangular Rapid Flashing Beacons (RRFBs)')

        self.assertEqual(rrfb['cmf']['code'], 'cmf-rrfb')
        self.assertEqual(len(rrfb['cmf']['coefficient_array']), 5)
        self.assertEqual(len(rrfb['cmf']['coefficient_array'][0]), 5)
