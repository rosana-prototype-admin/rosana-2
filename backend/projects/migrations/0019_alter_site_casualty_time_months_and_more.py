from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0018_site_casualty_non_negative'),
    ]

    operations = [
        migrations.AlterField(
            model_name='site',
            name='casualty_time_months',
            field=models.IntegerField(
                default=1,
                validators=[MinValueValidator(0), MaxValueValidator(11)],
            ),
        ),
        migrations.AlterField(
            model_name='site',
            name='casualty_time_years',
            field=models.IntegerField(
                default=1,
                validators=[MinValueValidator(0), MaxValueValidator(25)],
            ),
        ),
    ]
