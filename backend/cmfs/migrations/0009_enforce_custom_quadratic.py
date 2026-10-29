from django.db import migrations


def enforce_custom_quadratic(apps, schema_editor):
    cmf_model = apps.get_model('cmfs', 'CMF')
    metadata_model = apps.get_model('cmfs', 'CMFMetadata')
    custom_cmf_ids = cmf_model.objects.filter(is_builtin=False).values_list('pk', flat=True)
    metadata_model.objects.filter(cmf_id__in=custom_cmf_ids).update(cmf_math='Q')


class Migration(migrations.Migration):
    dependencies = [
        ('cmfs', '0008_normalize_cmf_structure'),
    ]

    operations = [
        migrations.RunPython(enforce_custom_quadratic, migrations.RunPython.noop),
    ]
