import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('groups', '0003_wipe_groups'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='group',
            name='admin',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name='administered_groups',
                to=settings.AUTH_USER_MODEL,
            ),
            preserve_default=False,
        ),
    ]
