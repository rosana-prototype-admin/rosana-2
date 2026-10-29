from decimal import Decimal

from django.db import IntegrityError
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User
from geo.models import CountryCode

from .models import CrashCasualtyConversionRow, CrashCasualtyConversionTable


class CrashCasualtyConversionModelTests(TestCase):
    def test_fhwa_national_default_is_seeded_with_all_severities(self):
        table = CrashCasualtyConversionTable.objects.get(
            dataset_key='crash-to-casualty',
            version='fhwa-2025-10',
            geography_level='national',
            country_code_id='US',
        )

        self.assertTrue(table.is_default)
        self.assertEqual((table.period_start_year, table.period_end_year), (2019, 2023))
        self.assertIn('NHTSA', table.source_title)
        self.assertEqual(table.source_locator, 'FHWA: Convert worksheet, cells E69:I73; NHTSA: Table 3-9')
        self.assertEqual(table.rows.count(), 5)
        fatal = table.rows.get(crash_severity='K')
        self.assertEqual(fatal.deaths_per_crash, Decimal('1.094202899'))
        self.assertEqual(fatal.vehicles_involved_per_crash, Decimal('1.610000000'))

    def test_resolution_prefers_region_and_falls_back_to_national(self):
        regional = CrashCasualtyConversionTable.objects.create(
            dataset_key='crash-to-casualty',
            version='state-example',
            country_code=CountryCode.objects.get(alpha_2='US'),
            geography_level=CrashCasualtyConversionTable.GeographyLevel.REGION,
            region_code='NY',
            period_start_year=2019,
            period_end_year=2023,
            source_title='State source',
        )
        CrashCasualtyConversionRow.objects.create(
            table=regional,
            crash_severity='K',
            deaths_per_crash='2.0',
            serious_injuries_per_crash='0',
            minor_injuries_per_crash='0',
            possible_injuries_per_crash='0',
            vehicles_involved_per_crash='1.0',
        )

        resolved_region = CrashCasualtyConversionTable.objects.resolve_for_analysis(
            2021, region_code='ny', version='state-example'
        )
        self.assertEqual(resolved_region.pk, regional.pk)

        resolved_national = CrashCasualtyConversionTable.objects.resolve_for_analysis(2021)
        self.assertEqual(resolved_national.geography_level, 'national')
        self.assertEqual(resolved_national.country_code_id, 'US')

    def test_only_one_row_per_severity_is_allowed(self):
        table = CrashCasualtyConversionTable.objects.get(version='fhwa-2025-10')
        with self.assertRaises(IntegrityError):
            CrashCasualtyConversionRow.objects.create(
                table=table,
                crash_severity='K',
                deaths_per_crash='0',
                serious_injuries_per_crash='0',
                minor_injuries_per_crash='0',
                possible_injuries_per_crash='0',
                vehicles_involved_per_crash='0',
            )


class CrashCasualtyConversionApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='analyst', email='analyst@example.com', password='pw'
        )
        self.client.force_authenticate(user=self.user)

    def test_resolve_endpoint_returns_national_default(self):
        response = self.client.get('/api/crash-conversion-tables/resolve/?year=2023')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['country_code'], 'US')
        self.assertEqual(response.data['geography_level'], 'national')
        self.assertEqual(len(response.data['rows']), 5)

    def test_resolve_endpoint_requires_year(self):
        response = self.client.get('/api/crash-conversion-tables/resolve/')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('year', response.data)

    def test_resolve_endpoint_returns_not_found_outside_period(self):
        response = self.client.get('/api/crash-conversion-tables/resolve/?year=2024')

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_reference_tables_are_read_only(self):
        response = self.client.post('/api/crash-conversion-tables/', {})

        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
