from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0002_subscription_plan_choices'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='language',
            field=models.CharField(
                choices=[
                    ('en-AU', 'English (Australia)'),
                    ('en-CA', 'English (Canada)'),
                    ('en-GB', 'English (UK)'),
                    ('en-US', 'English (US)'),
                    ('fr-CA', 'Français (Canada)'),
                    ('es-419', 'Español (Latinoamericano)'),
                ],
                default='en-US',
                max_length=6,
            ),
        ),
        migrations.AddField(
            model_name='user',
            name='currency',
            field=models.CharField(
                choices=[
                    ('AUD', 'Australian Dollar'),
                    ('GBP', 'British Pound'),
                    ('CAD', 'Canadian Dollar'),
                    ('EUR', 'Euro'),
                    ('MXN', 'México Peso'),
                    ('USD', 'US Dollar'),
                ],
                default='USD',
                max_length=3,
            ),
        ),
        migrations.AddField(
            model_name='user',
            name='length_unit',
            field=models.CharField(
                choices=[('m', 'metres'), ('ft', 'feet')],
                default='m',
                max_length=2,
            ),
        ),
        migrations.AddField(
            model_name='user',
            name='distance_unit',
            field=models.CharField(
                choices=[('km', 'kilometres'), ('mi', 'miles')],
                default='km',
                max_length=2,
            ),
        ),
        migrations.AddField(
            model_name='user',
            name='speed_unit',
            field=models.CharField(
                choices=[('km/h', 'kilometres per hour'), ('mph', 'miles per hour')],
                default='km/h',
                max_length=5,
            ),
        ),
        migrations.AddField(
            model_name='user',
            name='area_small_unit',
            field=models.CharField(
                choices=[('m2', 'square metres'), ('sq ft', 'square feet')],
                default='m2',
                max_length=6,
            ),
        ),
        migrations.AddField(
            model_name='user',
            name='area_large_unit',
            field=models.CharField(
                choices=[('ha', 'hectares'), ('ac', 'acres')],
                default='ha',
                max_length=2,
            ),
        ),
        migrations.AddField(
            model_name='user',
            name='volume_unit',
            field=models.CharField(
                choices=[('L', 'litres'), ('gal (US)', 'gallons (US)'), ('gal (Imp)', 'gallons (Imperial)')],
                default='L',
                max_length=9,
            ),
        ),
    ]
