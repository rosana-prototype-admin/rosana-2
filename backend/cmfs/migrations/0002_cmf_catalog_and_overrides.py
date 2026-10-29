import django.db.models.deletion
from django.db import migrations, models
from django.db.models import Q


def backfill_cmf_codes(apps, schema_editor):
    cmf_model = apps.get_model('cmfs', 'CMF')
    for cmf in cmf_model.objects.filter(code__isnull=True).only('pk'):
        cmf.code = f'custom-cmf-{cmf.pk}'
        cmf.save(update_fields=['code'])


class Migration(migrations.Migration):

    dependencies = [
        ('cmfs', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='cmf',
            name='code',
            field=models.SlugField(max_length=100, null=True),
        ),
        migrations.AddField(
            model_name='cmf',
            name='is_builtin',
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name='cmf',
            name='author',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='custom_cmfs',
                to='accounts.user',
            ),
        ),
        migrations.AddField(
            model_name='cmf',
            name='base_cmf',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='overrides',
                to='cmfs.cmf',
            ),
        ),
        migrations.RunPython(backfill_cmf_codes, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='cmf',
            name='code',
            field=models.SlugField(max_length=100),
        ),
        migrations.AddConstraint(
            model_name='cmf',
            constraint=models.UniqueConstraint(
                condition=Q(is_builtin=True),
                fields=('code',),
                name='unique_builtin_cmf_code',
            ),
        ),
        migrations.AddConstraint(
            model_name='cmf',
            constraint=models.UniqueConstraint(
                condition=Q(author__isnull=False, base_cmf__isnull=False),
                fields=('author', 'base_cmf'),
                name='unique_cmf_override_per_author',
            ),
        ),
    ]
