import decimal

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cmfs', '0009_enforce_custom_quadratic'),
    ]

    operations = [
        migrations.AlterField(
            model_name='cmfcoefficient',
            name='coefficient_a',
            field=models.FloatField(
                default=0.0,
                validators=[
                    MinValueValidator(0),
                    MaxValueValidator(decimal.Decimal('2.5')),
                ],
            ),
        ),
        migrations.AlterField(
            model_name='cmfcoefficient',
            name='coefficient_b',
            field=models.FloatField(
                default=0.0,
                validators=[
                    MinValueValidator(0),
                    MaxValueValidator(decimal.Decimal('2.5')),
                ],
            ),
        ),
        migrations.AlterField(
            model_name='cmfcoefficient',
            name='coefficient_c',
            field=models.FloatField(
                default=0.0,
                validators=[
                    MinValueValidator(0),
                    MaxValueValidator(decimal.Decimal('2.5')),
                ],
            ),
        ),
    ]
