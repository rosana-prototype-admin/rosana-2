from django.db import migrations


def wipe_opportunities(apps, schema_editor):
    Opportunity = apps.get_model('projects', 'Opportunity')
    Opportunity.objects.all().delete()


class Migration(migrations.Migration):
    """
    Deletes all existing Opportunity rows ahead of 0010, which adds required
    lead_agency/manager fields with no sensible default for pre-existing
    rows (per explicit approval -- only throwaway local dev data existed).
    Doing this as its own migration means 0010's ADD COLUMN ... NOT NULL
    hits an empty table, so no interactive default is ever needed.
    """

    dependencies = [
        ('projects', '0008_remove_project_organizations_remove_project_strategy_and_more'),
    ]

    operations = [
        migrations.RunPython(wipe_opportunities, migrations.RunPython.noop),
    ]
