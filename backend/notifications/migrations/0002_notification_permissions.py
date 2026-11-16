from django.db import migrations, models

import groups.permissions


class Migration(migrations.Migration):
    dependencies = [
        ('notifications', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='notification',
            name='permissions',
            field=models.JSONField(blank=True, default=groups.permissions.default_group_permissions),
        ),
    ]
