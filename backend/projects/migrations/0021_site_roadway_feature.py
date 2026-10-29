from django.db import migrations, models


ROADWAY_FEATURE_CODES = {
    'RFALL',
    'RFSEG',
    'RFRMP',
    'RFISN',
    'RF2WS',
    'RFAWS',
    'RFSIG',
    'RFRAB',
    'RFRRX',
    'RFPDX',
    'RFSCH',
    'RFWZN',
}


def normalize_legacy_site_types(apps, schema_editor):
    Site = apps.get_model('projects', 'Site')
    Site.objects.exclude(site_type__in=ROADWAY_FEATURE_CODES).update(site_type='RFALL')


def restore_legacy_site_types(apps, schema_editor):
    Site = apps.get_model('projects', 'Site')
    Site.objects.all().update(site_type='0')


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0020_site_casualty_data_type'),
    ]

    operations = [
        migrations.AlterField(
            model_name='site',
            name='site_type',
            field=models.CharField(default='RFALL', max_length=5),
        ),
        migrations.RunPython(normalize_legacy_site_types, restore_legacy_site_types),
    ]
