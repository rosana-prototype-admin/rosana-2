from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import migrations, models
import django.db.models.deletion


def clamp(value):
    try:
        value = float(value)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(1.0, value))


def migrate_cmf_data(apps, schema_editor):
    cmf_model = apps.get_model('cmfs', 'CMF')
    metadata_model = apps.get_model('cmfs', 'CMFMetadata')
    coefficient_model = apps.get_model('cmfs', 'CMFCoefficient')

    age_fields = ('age_0004', 'age_0509', 'age_1014', 'age_1519', 'age_2064', 'age_65up')
    for cmf in cmf_model.objects.all().iterator():
        custom = not cmf.is_builtin or cmf.author_id is not None
        if len(cmf.title or '') > 64:
            cmf.title = cmf.title[:64]
            cmf.save(update_fields=['title'])
        metadata_model.objects.update_or_create(
            cmf_id=cmf.pk,
            defaults={
                'cmf_group1': cmf.cmf_group1 or cmf.title or 'Untitled CMF',
                'cmf_group2': cmf.cmf_group2 or None,
                'cmf_group3': (cmf.cmf_group3 or None) if cmf.cmf_group2 else None,
                'descr_en_us': cmf.descr_en_us or cmf.description or '',
                'descr_en_au': '',
                'descr_en_ca': '',
                'descr_fr_ca': '',
                'descr_es': '',
                'cmf_math': 'Q' if custom else (cmf.cmf_math if cmf.cmf_math in ('E', 'L', 'P', 'Q') else 'Q'),
                'mod_code1': cmf.mod_code1 or cmf.roadway_feature or 'RFALL',
                'mod_code2': cmf.mod_code2 or cmf.vehicle or 'VTALL',
                'mod_code3': cmf.mod_code3 or cmf.manner_of_collision or 'MCALL',
                'mod_code4': cmf.mod_code4 or cmf.contributing_circumstance or 'CCNON',
                'mod_code5': cmf.mod_code5 or cmf.intoxication_status or 'IXALL',
                **{field: bool(getattr(cmf, field)) for field in age_fields},
            },
        )

        selected_age_groups = set(cmf.age_groups or [])
        if selected_age_groups:
            metadata_model.objects.filter(cmf_id=cmf.pk).update(**{
                field: True for age_group, field in zip(
                    ('0-4', '5-9', '10-14', '15-19', '20-64', '65+'), age_fields
                ) if age_group in selected_age_groups
            })

        for cell in coefficient_model.objects.filter(cmf_id=cmf.pk).iterator():
            if custom:
                # Previous CMFs stored the table value in coefficient_c. The
                # new custom-CMF contract stores it in coefficient_b only.
                cell.coefficient_a = 0.0
                cell.coefficient_b = clamp(cell.coefficient_b or cell.coefficient_c)
                cell.coefficient_c = 0.0
            else:
                cell.coefficient_a = clamp(cell.coefficient_a)
                cell.coefficient_b = clamp(cell.coefficient_b)
                cell.coefficient_c = clamp(cell.coefficient_c)
            cell.save(update_fields=['coefficient_a', 'coefficient_b', 'coefficient_c'])


class Migration(migrations.Migration):
    dependencies = [
        ('cmfs', '0007_alter_cmf_title'),
    ]

    operations = [
        migrations.CreateModel(
            name='CMFMetadata',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('cmf_group1', models.CharField(max_length=255)),
                ('cmf_group2', models.CharField(blank=True, max_length=255, null=True)),
                ('cmf_group3', models.CharField(blank=True, max_length=255, null=True)),
                ('descr_en_us', models.TextField(blank=True, default='')),
                ('descr_en_au', models.TextField(blank=True, default='')),
                ('descr_en_ca', models.TextField(blank=True, default='')),
                ('descr_fr_ca', models.TextField(blank=True, default='')),
                ('descr_es', models.TextField(blank=True, default='')),
                ('cmf_math', models.CharField(choices=[('E', 'Exponential'), ('L', 'Logarithmic'), ('P', 'Power'), ('Q', 'Quadratic')], default='Q', max_length=1)),
                ('mod_code1', models.CharField(default='RFALL', max_length=5)),
                ('mod_code2', models.CharField(default='VTALL', max_length=5)),
                ('mod_code3', models.CharField(default='MCALL', max_length=5)),
                ('mod_code4', models.CharField(default='CCNON', max_length=5)),
                ('mod_code5', models.CharField(default='IXALL', max_length=5)),
                ('age_0004', models.BooleanField(default=False)),
                ('age_0509', models.BooleanField(default=False)),
                ('age_1014', models.BooleanField(default=False)),
                ('age_1519', models.BooleanField(default=False)),
                ('age_2064', models.BooleanField(default=False)),
                ('age_65up', models.BooleanField(default=False)),
                ('cmf', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='metadata', to='cmfs.cmf')),
            ],
        ),
        migrations.RunPython(migrate_cmf_data, migrations.RunPython.noop),
        migrations.RemoveField(model_name='cmf', name='cmf_group1'),
        migrations.RemoveField(model_name='cmf', name='cmf_group2'),
        migrations.RemoveField(model_name='cmf', name='cmf_group3'),
        migrations.RemoveField(model_name='cmf', name='descr_en_us'),
        migrations.RemoveField(model_name='cmf', name='cmf_math'),
        migrations.RemoveField(model_name='cmf', name='mod_code1'),
        migrations.RemoveField(model_name='cmf', name='mod_code2'),
        migrations.RemoveField(model_name='cmf', name='mod_code3'),
        migrations.RemoveField(model_name='cmf', name='mod_code4'),
        migrations.RemoveField(model_name='cmf', name='mod_code5'),
        migrations.RemoveField(model_name='cmf', name='age_0004'),
        migrations.RemoveField(model_name='cmf', name='age_0509'),
        migrations.RemoveField(model_name='cmf', name='age_1014'),
        migrations.RemoveField(model_name='cmf', name='age_1519'),
        migrations.RemoveField(model_name='cmf', name='age_2064'),
        migrations.RemoveField(model_name='cmf', name='age_65up'),
        migrations.RemoveField(model_name='cmf', name='roadway_feature'),
        migrations.RemoveField(model_name='cmf', name='vehicle'),
        migrations.RemoveField(model_name='cmf', name='manner_of_collision'),
        migrations.RemoveField(model_name='cmf', name='contributing_circumstance'),
        migrations.RemoveField(model_name='cmf', name='intoxication_status'),
        migrations.RemoveField(model_name='cmf', name='age_groups'),
        migrations.RemoveField(model_name='cmf', name='crash_modification_factors'),
        migrations.RemoveField(model_name='cmf', name='description'),
        migrations.AlterField(
            model_name='cmf',
            name='title',
            field=models.CharField(max_length=64),
        ),
        migrations.AlterField(
            model_name='cmf',
            name='cmf_source',
            field=models.CharField(blank=True, default='', max_length=1000),
        ),
        migrations.AlterField(
            model_name='cmfcoefficient',
            name='coefficient_a',
            field=models.FloatField(default=0.0, validators=[MinValueValidator(0), MaxValueValidator(1)]),
        ),
        migrations.AlterField(
            model_name='cmfcoefficient',
            name='coefficient_b',
            field=models.FloatField(default=0.0, validators=[MinValueValidator(0), MaxValueValidator(1)]),
        ),
        migrations.AlterField(
            model_name='cmfcoefficient',
            name='coefficient_c',
            field=models.FloatField(default=0.0, validators=[MinValueValidator(0), MaxValueValidator(1)]),
        ),
    ]
