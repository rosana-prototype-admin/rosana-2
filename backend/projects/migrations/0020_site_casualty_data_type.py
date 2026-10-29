from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0019_alter_site_casualty_time_months_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='site',
            name='casualty_data_type',
            field=models.CharField(
                choices=[
                    ('casualty-damage', 'Casualty / damage counts'),
                    ('crash', 'Crash counts'),
                ],
                default='casualty-damage',
                max_length=16,
            ),
        ),
    ]
