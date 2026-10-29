from django.db import migrations, models


STATUS_VALUES = {
    0: 'drafting',
    1: 'review',
    2: 'implementation',
    3: 'completed',
    4: 'cancelled',
}


def migrate_opportunity_statuses(apps, schema_editor):
    Opportunity = apps.get_model('projects', 'Opportunity')
    for opportunity in Opportunity.objects.all().iterator():
        opportunity.status_text = STATUS_VALUES.get(opportunity.status, 'drafting')
        opportunity.save(update_fields=['status_text'])


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0013_remove_opportunity_comments_enabled_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='opportunity',
            name='status_text',
            field=models.CharField(
                choices=[
                    ('drafting', 'Drafting'),
                    ('review', 'Review'),
                    ('implementation', 'Implementation'),
                    ('completed', 'Completed'),
                    ('cancelled', 'Cancelled'),
                ],
                default='drafting',
                max_length=16,
            ),
        ),
        migrations.RunPython(migrate_opportunity_statuses, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name='opportunity',
            name='status',
        ),
        migrations.RenameField(
            model_name='opportunity',
            old_name='status_text',
            new_name='status',
        ),
    ]
