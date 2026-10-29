from django.db import migrations


def wipe_groups(apps, schema_editor):
    # 2 existing Opportunity rows reference Groups via the required, PROTECTed
    # lead_agency field -- those (and their cascade of Projects/Sites/
    # Strategies/Comments) have to go first, or deleting the Groups below
    # would raise ProtectedError. Per explicit approval: wipe both, no
    # backfill, since there's no non-arbitrary admin to assign the existing
    # Groups anyway.
    Opportunity = apps.get_model('projects', 'Opportunity')
    Opportunity.objects.all().delete()

    Membership = apps.get_model('groups', 'Membership')
    Group = apps.get_model('groups', 'Group')
    Membership.objects.all().delete()
    Group.objects.all().delete()


class Migration(migrations.Migration):
    """
    Deletes all existing Group/Membership rows (and any dependent Opportunity
    rows) ahead of 0004, which adds a required `admin` field with no sensible
    default for pre-existing rows. Same technique used for the Opportunity
    rework's 0009_wipe_opportunities.
    """

    dependencies = [
        ('groups', '0002_group_jcodes'),
        ('projects', '0012_strategy_selected_details'),
    ]

    operations = [
        migrations.RunPython(wipe_groups, migrations.RunPython.noop),
    ]
