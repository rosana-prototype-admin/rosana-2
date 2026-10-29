from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('accounts', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='subscription_type',
            field=models.CharField(
                choices=[
                    ('none', 'None'),
                    ('basic', 'Basic'),
                    ('premium', 'Premium'),
                    ('admin', 'Admin'),
                    ('crossroads', 'Crossroads'),
                    ('borough', 'Borough'),
                    ('ville', 'Ville'),
                    ('shire', 'Shire'),
                    ('provincia', 'Provincia'),
                    ('comarca', 'Comarca'),
                    ('metro', 'Metro'),
                    ('commonwealth', 'Commonwealth'),
                    ('republic', 'Republic'),
                ],
                default='none',
                max_length=20,
            ),
        ),
    ]
