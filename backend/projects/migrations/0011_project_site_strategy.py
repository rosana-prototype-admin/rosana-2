import django.contrib.postgres.fields
import django.db.models.deletion
from django.db import migrations, models

import projects.models


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0010_revise_opportunity'),
        ('focusareas', '0005_seed_real_intervention_types'),
    ]

    operations = [
        migrations.CreateModel(
            name='Project',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=100)),
                ('comment', models.CharField(blank=True, max_length=1000)),
                ('status', models.IntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('modified_at', models.DateTimeField(auto_now=True)),
                ('opportunity', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE, related_name='projects', to='projects.opportunity'
                )),
            ],
            options={
                'ordering': ['-modified_at'],
            },
        ),
        migrations.CreateModel(
            name='Site',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=100)),
                ('comment', models.CharField(blank=True, max_length=1000)),
                ('site_type', models.IntegerField(default=0)),
                ('road_class', models.CharField(blank=True, max_length=255)),
                ('gps_x', models.FloatField(blank=True, null=True)),
                ('gps_y', models.FloatField(blank=True, null=True)),
                ('gps_z', models.FloatField(default=0)),
                ('aadt', models.FloatField(blank=True, null=True)),
                ('tev', models.IntegerField(blank=True, null=True)),
                ('casualty_obs', django.contrib.postgres.fields.ArrayField(
                    models.IntegerField(), blank=True, default=projects.models.default_casualty_array, size=4
                )),
                ('casualty_est', django.contrib.postgres.fields.ArrayField(
                    models.IntegerField(), blank=True, default=projects.models.default_casualty_array, size=4
                )),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('modified_at', models.DateTimeField(auto_now=True)),
                ('project', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE, related_name='sites', to='projects.project'
                )),
            ],
            options={
                'ordering': ['-modified_at'],
            },
        ),
        migrations.CreateModel(
            name='Strategy',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('modified_at', models.DateTimeField(auto_now=True)),
                ('intervention_type', models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='strategies',
                    to='focusareas.interventiontype',
                )),
                ('site', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE, related_name='strategies', to='projects.site'
                )),
            ],
            options={
                'ordering': ['-modified_at'],
            },
        ),
    ]
