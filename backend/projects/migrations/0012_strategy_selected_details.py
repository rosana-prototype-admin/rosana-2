from django.db import migrations, models


class Migration(migrations.Migration):
    """
    Collapses the "pick an Intervention to create a Strategy" workflow:
    Strategy rows are now auto-provisioned per Site (see Site.sync_strategies)
    for every InterventionType compatible with the Site's Opportunity's focus
    area, rather than manually created/deleted. `selected` is the user-facing
    checkbox; `details` is a placeholder for fields not yet defined.
    """

    dependencies = [
        ('projects', '0011_project_site_strategy'),
    ]

    operations = [
        migrations.AddField(
            model_name='strategy',
            name='selected',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='strategy',
            name='details',
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddConstraint(
            model_name='strategy',
            constraint=models.UniqueConstraint(
                fields=['site', 'intervention_type'], name='unique_strategy_per_site_intervention_type'
            ),
        ),
    ]
