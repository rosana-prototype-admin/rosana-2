from django.db import migrations


def create_subscription_seat_if_missing(apps, schema_editor):
    """Repair databases where 0006 was recorded but its seat table is absent."""
    SubscriptionSeat = apps.get_model('accounts', 'SubscriptionSeat')
    table_name = SubscriptionSeat._meta.db_table
    existing_tables = schema_editor.connection.introspection.table_names()
    if table_name not in existing_tables:
        schema_editor.create_model(SubscriptionSeat)


class Migration(migrations.Migration):
    dependencies = [
        ('accounts', '0007_audit_events'),
    ]

    operations = [
        migrations.RunPython(create_subscription_seat_if_missing, migrations.RunPython.noop),
    ]
