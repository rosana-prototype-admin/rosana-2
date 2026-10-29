from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cmfs', '0004_cmf_permitted_groups'),
    ]

    operations = [
        migrations.AddField(
            model_name='cmf',
            name='permission_scope',
            field=models.CharField(
                choices=[
                    ('agency', 'Agency'),
                    ('state', 'State'),
                    ('global', 'Global'),
                ],
                default='agency',
                max_length=6,
            ),
        ),
    ]
