from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('groups', '0007_entitlement_roles'),
    ]

    operations = [
        migrations.RenameField(
            model_name='membership',
            old_name='organization_role',
            new_name='rosana_role',
        ),
    ]
