from decimal import Decimal

import django.core.validators
import django.db.models.deletion
from django.db import migrations, models
from django.db.models import Q


CONVERSION_ROWS = [
    ('K', '1.094202899', '0.268452983', '0.253791709', '0.187226154', '1.610'),
    ('A', '0', '1.157019553', '0.267324291', '0.232799014', '1.697'),
    ('B', '0', '0', '1.211455038', '0.203660190', '1.760'),
    ('C', '0', '0', '0', '1.342681306', '1.940'),
    ('O', '0', '0', '0', '0', '1.788'),
]


def seed_national_conversion_table(apps, schema_editor):
    country_model = apps.get_model('geo', 'CountryCode')
    table_model = apps.get_model('crashdata', 'CrashCasualtyConversionTable')
    row_model = apps.get_model('crashdata', 'CrashCasualtyConversionRow')

    table, _ = table_model.objects.get_or_create(
        dataset_key='crash-to-casualty',
        version='fhwa-2025-10',
        country_code=country_model.objects.get(alpha_2='US'),
        geography_level='national',
        region_code='',
        defaults={
            'period_start_year': 2019,
            'period_end_year': 2023,
            'source_title': 'Federal Highway Administration, Crash Costs for Highway Safety Analysis Tool; NHTSA (Blincoe et al.), The Economic and Societal Impact of Motor Vehicle Crashes, 2019 (Revised)',
            'source_version': 'FHWA October 2025; NHTSA 2019 (Revised)',
            'source_locator': 'FHWA: Convert worksheet, cells E69:I73; NHTSA: Table 3-9',
            'notes': 'Default US national values. Replace with state/province-specific values where possible.',
            'is_default': True,
        },
    )

    for severity, deaths, serious, minor, possible, vehicles in CONVERSION_ROWS:
        row_model.objects.update_or_create(
            table=table,
            crash_severity=severity,
            defaults={
                'deaths_per_crash': Decimal(deaths),
                'serious_injuries_per_crash': Decimal(serious),
                'minor_injuries_per_crash': Decimal(minor),
                'possible_injuries_per_crash': Decimal(possible),
                'vehicles_involved_per_crash': Decimal(vehicles),
            },
        )


def remove_national_conversion_table(apps, schema_editor):
    table_model = apps.get_model('crashdata', 'CrashCasualtyConversionTable')
    table_model.objects.filter(
        dataset_key='crash-to-casualty',
        version='fhwa-2025-10',
        country_code_id='US',
        geography_level='national',
        region_code='',
    ).delete()


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ('geo', '0004_jcode_country_code'),
    ]

    operations = [
        migrations.CreateModel(
            name='CrashCasualtyConversionTable',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('dataset_key', models.SlugField(default='crash-to-casualty', max_length=100)),
                ('version', models.SlugField(max_length=100)),
                ('geography_level', models.CharField(choices=[('national', 'National'), ('region', 'State / Province')], max_length=10)),
                ('region_code', models.CharField(blank=True, max_length=10)),
                ('period_start_year', models.PositiveSmallIntegerField()),
                ('period_end_year', models.PositiveSmallIntegerField()),
                ('source_title', models.CharField(max_length=500)),
                ('source_version', models.CharField(blank=True, max_length=100)),
                ('source_locator', models.CharField(blank=True, max_length=500)),
                ('source_url', models.URLField(blank=True)),
                ('notes', models.TextField(blank=True)),
                ('is_default', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('modified_at', models.DateTimeField(auto_now=True)),
                ('country_code', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='crash_casualty_conversion_tables', to='geo.countrycode')),
            ],
            options={
                'ordering': ['-period_end_year', '-period_start_year', '-modified_at'],
            },
        ),
        migrations.CreateModel(
            name='CrashCasualtyConversionRow',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('crash_severity', models.CharField(choices=[('K', 'Fatal injury / death'), ('A', 'Serious injury'), ('B', 'Minor injury'), ('C', 'Possible injury'), ('O', 'Property damage only')], max_length=1)),
                ('deaths_per_crash', models.DecimalField(decimal_places=9, max_digits=12, validators=[django.core.validators.MinValueValidator(Decimal('0'))])),
                ('serious_injuries_per_crash', models.DecimalField(decimal_places=9, max_digits=12, validators=[django.core.validators.MinValueValidator(Decimal('0'))])),
                ('minor_injuries_per_crash', models.DecimalField(decimal_places=9, max_digits=12, validators=[django.core.validators.MinValueValidator(Decimal('0'))])),
                ('possible_injuries_per_crash', models.DecimalField(decimal_places=9, max_digits=12, validators=[django.core.validators.MinValueValidator(Decimal('0'))])),
                ('vehicles_involved_per_crash', models.DecimalField(decimal_places=9, max_digits=12, validators=[django.core.validators.MinValueValidator(Decimal('0'))])),
                ('table', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='rows', to='crashdata.crashcasualtyconversiontable')),
            ],
            options={
                'ordering': ['crash_severity'],
            },
        ),
        migrations.AddConstraint(
            model_name='crashcasualtyconversiontable',
            constraint=models.CheckConstraint(
                condition=Q(('period_start_year__lte', models.F('period_end_year'))),
                name='conversion_period_start_before_end',
            ),
        ),
        migrations.AddConstraint(
            model_name='crashcasualtyconversiontable',
            constraint=models.CheckConstraint(
                condition=Q(('geography_level', 'national'), ('region_code', '')) | Q(('geography_level', 'region')) & ~Q(('region_code', '')),
                name='conversion_region_matches_geography_level',
            ),
        ),
        migrations.AddConstraint(
            model_name='crashcasualtyconversiontable',
            constraint=models.UniqueConstraint(fields=('dataset_key', 'version', 'country_code', 'geography_level', 'region_code'), name='unique_conversion_table_version_scope'),
        ),
        migrations.AddConstraint(
            model_name='crashcasualtyconversiontable',
            constraint=models.UniqueConstraint(condition=Q(('is_default', True)), fields=('dataset_key', 'country_code', 'geography_level', 'region_code'), name='one_default_conversion_table_per_scope'),
        ),
        migrations.AddConstraint(
            model_name='crashcasualtyconversionrow',
            constraint=models.UniqueConstraint(fields=('table', 'crash_severity'), name='unique_conversion_row_per_severity'),
        ),
        migrations.RunPython(seed_national_conversion_table, remove_national_conversion_table),
    ]
