from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('notifications', '0003_notification_canceled_status'),
    ]

    operations = [
        migrations.AddField(
            model_name='notification',
            name='rosana_role',
            field=models.CharField(
                choices=[
                    ('financial_admin', 'Financial Admin'),
                    ('technical_admin', 'Technical Admin'),
                    ('technical_user', 'Technical User'),
                    ('commenter', 'Commenter'),
                ],
                default='commenter',
                max_length=20,
            ),
        ),
    ]
