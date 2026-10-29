from django.db import migrations, models
import django.db.models.deletion


TRAVEL_MODES = (
    'motorVehicleOccupants',
    'motorcyclists',
    'bicyclists',
    'pedestrians',
    'otherRoadUsers',
)
SEVERITIES = ('K', 'A', 'B', 'C', 'O')


def backfill_structured_cmf_data(apps, schema_editor):
    cmf_model = apps.get_model('cmfs', 'CMF')
    coefficient_model = apps.get_model('cmfs', 'CMFCoefficient')

    filter_fields = (
        'roadway_feature',
        'vehicle',
        'manner_of_collision',
        'contributing_circumstance',
        'intoxication_status',
    )
    age_fields = {
        '0-4': 'age_0004',
        '5-9': 'age_0509',
        '10-14': 'age_1014',
        '15-19': 'age_1519',
        '20-64': 'age_2064',
        '65+': 'age_65up',
    }

    for cmf in cmf_model.objects.all().iterator():
        updates = []
        if not cmf.cmf_group1:
            cmf.cmf_group1 = cmf.title
            updates.append('cmf_group1')
        if not cmf.descr_en_us:
            cmf.descr_en_us = cmf.description
            updates.append('descr_en_us')
        for index, field in enumerate(filter_fields, start=1):
            structured_field = f'mod_code{index}'
            if not getattr(cmf, structured_field):
                setattr(cmf, structured_field, getattr(cmf, field))
                updates.append(structured_field)
        selected_age_groups = set(cmf.age_groups or [])
        for age_key, field in age_fields.items():
            if getattr(cmf, field) is None and age_key in selected_age_groups:
                setattr(cmf, field, 1.0)
                updates.append(field)
        if updates:
            cmf.save(update_fields=updates)

        values = cmf.crash_modification_factors or {}
        cells = []
        for travel_mode, road_user_type in enumerate(TRAVEL_MODES, start=1):
            row = values.get(road_user_type, {})
            for severity_index, injury_type in enumerate(SEVERITIES):
                raw_value = row.get((
                    'fatalities',
                    'seriousInjuries',
                    'minorInjuries',
                    'possibleInjuries',
                    'propertyDamage',
                )[severity_index], 1)
                try:
                    value = float(raw_value)
                except (TypeError, ValueError):
                    value = 0.0
                cells.append(coefficient_model(
                    cmf_id=cmf.pk,
                    travel_mode=travel_mode,
                    severity=injury_type,
                    coefficient_a=0.0,
                    coefficient_b=0.0,
                    coefficient_c=value,
                ))
        coefficient_model.objects.bulk_create(cells, ignore_conflicts=True)


class Migration(migrations.Migration):
    dependencies = [
        ('cmfs', '0005_cmf_permission_scope'),
    ]

    operations = [
        migrations.AddField(
            model_name='cmf',
            name='age_0004',
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='cmf',
            name='age_0509',
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='cmf',
            name='age_1014',
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='cmf',
            name='age_1519',
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='cmf',
            name='age_2064',
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='cmf',
            name='age_65up',
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='cmf',
            name='cmf_group1',
            field=models.CharField(blank=True, default='', max_length=255),
        ),
        migrations.AddField(
            model_name='cmf',
            name='cmf_group2',
            field=models.CharField(blank=True, default='', max_length=255),
        ),
        migrations.AddField(
            model_name='cmf',
            name='cmf_group3',
            field=models.CharField(blank=True, default='', max_length=255),
        ),
        migrations.AddField(
            model_name='cmf',
            name='descr_en_us',
            field=models.TextField(blank=True, default=''),
        ),
        migrations.AddField(
            model_name='cmf',
            name='cmf_math',
            field=models.CharField(choices=[('E', 'Exponential'), ('Q', 'Quadratic')], default='E', max_length=1),
        ),
        migrations.AddField(
            model_name='cmf',
            name='mod_code1',
            field=models.CharField(blank=True, default='', max_length=20),
        ),
        migrations.AddField(
            model_name='cmf',
            name='mod_code2',
            field=models.CharField(blank=True, default='', max_length=20),
        ),
        migrations.AddField(
            model_name='cmf',
            name='mod_code3',
            field=models.CharField(blank=True, default='', max_length=20),
        ),
        migrations.AddField(
            model_name='cmf',
            name='mod_code4',
            field=models.CharField(blank=True, default='', max_length=20),
        ),
        migrations.AddField(
            model_name='cmf',
            name='mod_code5',
            field=models.CharField(blank=True, default='', max_length=20),
        ),
        migrations.CreateModel(
            name='CMFCoefficient',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('travel_mode', models.PositiveSmallIntegerField(choices=[(1, 'Motor vehicle occupant'), (2, 'Motorcycle'), (3, 'Bicycle'), (4, 'Pedestrian'), (5, 'Other')])),
                ('severity', models.CharField(choices=[('K', 'Fatal'), ('A', 'Serious'), ('B', 'Minor'), ('C', 'Possible'), ('O', 'Property damage only')], max_length=1)),
                ('coefficient_a', models.FloatField(default=0.0)),
                ('coefficient_b', models.FloatField(default=0.0)),
                ('coefficient_c', models.FloatField(default=0.0)),
                ('cmf', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='coefficients', to='cmfs.cmf')),
            ],
            options={'ordering': ['travel_mode', 'severity']},
        ),
        migrations.CreateModel(
            name='CMFUserPermission',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('crossroads', models.BooleanField(default=False)),
                ('borough', models.BooleanField(default=False)),
                ('ville', models.BooleanField(default=False)),
                ('shire', models.BooleanField(default=False)),
                ('provincia', models.BooleanField(default=False)),
                ('comarca', models.BooleanField(default=False)),
                ('metro', models.BooleanField(default=False)),
                ('commonwealth', models.BooleanField(default=False)),
                ('republic', models.BooleanField(default=False)),
                ('cmf', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='user_permissions', to='cmfs.cmf')),
            ],
        ),
        migrations.RunPython(backfill_structured_cmf_data, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name='cmfcoefficient',
            constraint=models.UniqueConstraint(fields=('cmf', 'travel_mode', 'severity'), name='unique_cmf_coefficient_cell'),
        ),
    ]
