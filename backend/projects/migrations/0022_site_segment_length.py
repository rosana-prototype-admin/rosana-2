from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0021_site_roadway_feature'),
    ]

    operations = [
        migrations.AddField(
            model_name='site',
            name='segment_length',
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='site',
            name='segment_length_unit',
            field=models.CharField(
                choices=[
                    ('meters', 'Meters'),
                    ('feet', 'Feet'),
                    ('kilometers', 'Kilometers'),
                    ('miles', 'Miles'),
                ],
                default='meters',
                max_length=11,
            ),
        ),
    ]
