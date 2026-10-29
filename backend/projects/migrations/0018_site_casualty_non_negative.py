from django.core.validators import MinValueValidator
from django.contrib.postgres.fields import ArrayField
from django.db import migrations, models

import projects.models


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0017_site_casualty_cmf_table'),
    ]

    operations = [
        migrations.AlterField(
            model_name='site',
            name='casualty_obs',
            field=ArrayField(
                base_field=models.IntegerField(validators=[MinValueValidator(0)]),
                blank=True,
                default=projects.models.default_casualty_array,
                size=25,
            ),
        ),
        migrations.AlterField(
            model_name='site',
            name='casualty_est',
            field=ArrayField(
                base_field=models.IntegerField(validators=[MinValueValidator(0)]),
                blank=True,
                default=projects.models.default_casualty_array,
                size=25,
            ),
        ),
    ]
