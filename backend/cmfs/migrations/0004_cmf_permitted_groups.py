from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cmfs', '0003_auto_generate_unique_cmf_codes'),
        ('groups', '0004_group_admin'),
    ]

    operations = [
        migrations.AddField(
            model_name='cmf',
            name='permitted_groups',
            field=models.ManyToManyField(
                blank=True,
                related_name='permitted_cmfs',
                to='groups.group',
            ),
        ),
    ]
