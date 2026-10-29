from django.db import migrations


def update_source_metadata(apps, schema_editor):
    table_model = apps.get_model('crashdata', 'CrashCasualtyConversionTable')
    table_model.objects.filter(
        dataset_key='crash-to-casualty',
        version='fhwa-2025-10',
        country_code_id='US',
        geography_level='national',
        region_code='',
    ).update(
        source_title=(
            'Federal Highway Administration, Crash Costs for Highway Safety Analysis Tool; '
            'NHTSA (Blincoe et al.), The Economic and Societal Impact of Motor Vehicle Crashes, '
            '2019 (Revised)'
        ),
        source_version='FHWA October 2025; NHTSA 2019 (Revised)',
        source_locator='FHWA: Convert worksheet, cells E69:I73; NHTSA: Table 3-9',
    )


class Migration(migrations.Migration):
    dependencies = [
        ('crashdata', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(update_source_metadata, migrations.RunPython.noop),
    ]
