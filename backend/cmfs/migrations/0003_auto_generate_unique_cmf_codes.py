import uuid

from django.db import migrations, models


def make_codes_unique(apps, schema_editor):
    cmf_model = apps.get_model('cmfs', 'CMF')
    seen_codes = set()
    for cmf in cmf_model.objects.order_by('pk'):
        if not cmf.code or cmf.code in seen_codes:
            cmf.code = f'cmf-{uuid.uuid4().hex}'
            while cmf.code in seen_codes:
                cmf.code = f'cmf-{uuid.uuid4().hex}'
            cmf.save(update_fields=['code'])
        seen_codes.add(cmf.code)


class Migration(migrations.Migration):

    dependencies = [
        ('cmfs', '0002_cmf_catalog_and_overrides'),
    ]

    operations = [
        migrations.RunPython(make_codes_unique, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='cmf',
            name='code',
            field=models.SlugField(blank=True, editable=False, max_length=100, unique=True),
        ),
        migrations.RemoveConstraint(
            model_name='cmf',
            name='unique_builtin_cmf_code',
        ),
    ]
