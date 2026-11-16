from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('notifications', '0002_notification_permissions'),
    ]

    operations = [
        migrations.AlterField(
            model_name='notification',
            name='status',
            field=models.CharField(
                choices=[
                    ('pending', 'Pending'),
                    ('accepted', 'Accepted'),
                    ('declined', 'Declined'),
                    ('canceled', 'Canceled'),
                ],
                default='pending',
                max_length=16,
            ),
        ),
    ]
