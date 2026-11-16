from django.db import migrations, models

import groups.permissions


class Migration(migrations.Migration):
    dependencies = [
        ('groups', '0005_group_archive_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='membership',
            name='permissions',
            field=models.JSONField(blank=True, default=groups.permissions.default_group_permissions),
        ),
    ]
