from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User
from geo.models import CountryCode, Jcode
from groups.models import Group, Membership

from .config import CMF_FILTER_CONFIG, CMF_LOWER_LIMIT, CMF_MATH_CONFIG, CMF_MOD_CODE_OPTIONS, CMF_UPPER_LIMIT
from .models import CMF, CMFCoefficient, CMFUserPermission


class CMFApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='user', email='user@example.com', password='pw')
        self.other_user = User.objects.create_user(
            username='other', email='other@example.com', password='pw'
        )
        self.agency = Group.objects.create(name='Agency', admin=self.other_user)
        Membership.objects.create(user=self.user, group=self.agency)
        self.builtin = CMF.objects.create(
            code='all-road-users',
            title='All road users',
            is_builtin=True,
            author=None,
        )

    def test_authenticated_users_can_list_builtins_and_custom_cmfs(self):
        CMF.objects.create(code='other-custom', title='Other custom', author=self.other_user)
        self.client.force_authenticate(user=self.user)

        response = self.client.get('/api/cmfs/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([item['code'] for item in response.data], ['other-custom', 'all-road-users'])

    def test_seeded_intervention_cmfs_include_source_weights_and_cells(self):
        helmet = CMF.objects.get(code='cmf-motorcycle-helmets')
        metadata = helmet.metadata

        self.assertTrue(helmet.is_builtin)
        self.assertEqual(helmet.title, 'Mandatory Use of Motorcycle Helmets')
        self.assertEqual(
            [getattr(metadata, field) for field in (
                'age_0004', 'age_0509', 'age_1014', 'age_1519', 'age_2064', 'age_65up'
            )],
            [0.85] * 6,
        )
        self.assertEqual(helmet.coefficients.count(), 25)
        self.assertEqual(
            helmet.coefficients.get(travel_mode=2, severity='K').coefficient_b,
            0.85,
        )

        roundabout = CMF.objects.get(code='cmf-signalized-intersection-roundabout')
        self.assertEqual(
            roundabout.coefficients.get(travel_mode=1, severity='O').coefficient_b,
            1.25,
        )

    def test_builtin_cmfs_are_read_only(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.patch(
            f'/api/cmfs/{self.builtin.pk}/', {'title': 'Changed'}, format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_user_can_create_one_override_and_resolution_prefers_it(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.post(
            '/api/cmfs/',
            {
                'title': 'My all road users',
                'base_cmf': self.builtin.pk,
                'permitted_groups': [self.agency.pk],
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertFalse(response.data['is_builtin'])
        self.assertTrue(response.data['code'].startswith('cmf-'))
        self.assertEqual(response.data['base_cmf'], self.builtin.pk)

        resolved = self.client.get('/api/cmfs/resolve/?code=all-road-users')
        self.assertEqual(resolved.status_code, status.HTTP_200_OK)
        self.assertEqual(resolved.data['id'], response.data['id'])

    def test_resolution_falls_back_to_builtin_for_users_without_override(self):
        self.client.force_authenticate(user=self.other_user)

        response = self.client.get('/api/cmfs/resolve/?code=all-road-users')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], self.builtin.pk)

    def test_user_cannot_create_duplicate_override(self):
        CMF.objects.create(
            title='Existing override',
            author=self.user,
            base_cmf=self.builtin,
        )
        self.client.force_authenticate(user=self.user)

        response = self.client.post(
            '/api/cmfs/',
            {
                'title': 'Second override',
                'base_cmf': self.builtin.pk,
                'permitted_groups': [self.agency.pk],
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('base_cmf', response.data)

    def test_config_exposes_inclusive_cmf_bounds(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.get('/api/cmfs/config/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {
            'cmf_lower_limit': float(CMF_LOWER_LIMIT),
            'cmf_upper_limit': float(CMF_UPPER_LIMIT),
            'cmf_filters': CMF_FILTER_CONFIG,
            'cmf_math': CMF_MATH_CONFIG,
            'cmf_mod_codes': CMF_MOD_CODE_OPTIONS,
        })

    def test_structured_cmf_metadata_coefficients_and_permissions_round_trip(self):
        self.client.force_authenticate(user=self.user)
        coefficients = [
            {
                'travel_mode': travel_mode,
                'severity': severity,
                'coefficient_a': 0.1,
                'coefficient_b': 0.2,
                'coefficient_c': 0.3,
            }
            for travel_mode in range(1, 6)
            for severity in ('K', 'A', 'B', 'C', 'O')
        ]
        response = self.client.post(
            '/api/cmfs/',
            {
                'cmf_group1': 'Roadway group',
                'cmf_group2': 'Vehicle group',
                'descr_en_us': 'A structured CMF.',
                'cmf_math': 'E',
                'mod_code1': 'RFALL',
                'age_0004': True,
                'permitted_groups': [self.agency.pk],
                'coefficients': coefficients,
                'user_permissions': {'crossroads': True, 'metro': True},
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['cmf_group1'], 'Roadway group')
        self.assertEqual(response.data['cmf_math'], 'Q')
        self.assertIsNone(response.data['cmf_group3'])
        self.assertEqual(len(response.data['coefficients']), 25)
        self.assertEqual(response.data['coefficient_array'][0][0], [0.0, 0.2, 0.0])
        self.assertTrue(response.data['user_permissions']['crossroads'])

        cmf = CMF.objects.get(pk=response.data['id'])
        self.assertEqual(cmf.coefficients.count(), 25)
        self.assertEqual(cmf.user_permissions.metro, True)

    def test_user_cannot_create_cmf_with_value_above_upper_bound(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.post(
            '/api/cmfs/',
            {
                'title': 'Out of range',
                'permitted_groups': [self.agency.pk],
                'crash_modification_factors': {
                    'motorVehicleOccupants': {'fatalities': '2.5001'},
                },
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('crash_modification_factors', response.data)

    def test_group_three_is_cleared_when_group_two_is_null(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.post(
            '/api/cmfs/',
            {
                'cmf_group1': 'Roadway group',
                'cmf_group3': 'Should be cleared',
                'permitted_groups': [self.agency.pk],
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIsNone(response.data['cmf_group2'])
        self.assertIsNone(response.data['cmf_group3'])

    def test_user_can_create_a_cmf_without_assigning_an_agency(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.post('/api/cmfs/', {'title': 'Unshared CMF'}, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['permitted_groups'], [])

    def test_user_can_only_assign_agencies_they_belong_to(self):
        other_agency = Group.objects.create(name='Other Agency', admin=self.other_user)
        self.client.force_authenticate(user=self.user)

        response = self.client.post(
            '/api/cmfs/',
            {'title': 'Wrong agency', 'permitted_groups': [other_agency.pk]},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('permitted_groups', response.data)

    def test_permitted_agency_members_can_read_a_custom_cmf(self):
        cmf = CMF.objects.create(title='Shared CMF', author=self.other_user)
        cmf.permitted_groups.add(self.agency)
        self.client.force_authenticate(user=self.user)

        response = self.client.get(f'/api/cmfs/{cmf.pk}/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['permitted_groups'], [self.agency.pk])

    def test_global_scope_allows_any_authenticated_user_to_read(self):
        stranger = User.objects.create_user(
            username='stranger', email='stranger@example.com', password='pw'
        )
        cmf = CMF.objects.create(
            title='Global CMF',
            author=self.other_user,
            permission_scope=CMF.PermissionScope.GLOBAL,
        )
        cmf.permitted_groups.add(self.agency)
        self.client.force_authenticate(user=stranger)

        response = self.client.get(f'/api/cmfs/{cmf.pk}/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_state_scope_allows_members_of_agencies_in_the_same_state(self):
        country, _ = CountryCode.objects.get_or_create(
            alpha_2='US',
            defaults={
                'alpha_3': 'USA', 'name_short': 'United States', 'name_long': 'United States',
            },
        )
        jcode = Jcode.objects.create(
            id='state-test', country_code=country, state='Test State',
            place_name_short='Test Place', place_name_long='Test Place',
        )
        self.agency.jcodes.add(jcode)
        self.agency.memberships.filter(user=self.user).delete()
        requester_agency = Group.objects.create(name='Requester Agency', admin=self.other_user)
        Membership.objects.create(user=self.user, group=requester_agency)
        requester_agency.jcodes.add(jcode)
        cmf = CMF.objects.create(
            title='State CMF',
            author=self.other_user,
            permission_scope=CMF.PermissionScope.STATE,
        )
        cmf.permitted_groups.add(self.agency)
        self.client.force_authenticate(user=self.user)

        response = self.client.get(f'/api/cmfs/{cmf.pk}/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
