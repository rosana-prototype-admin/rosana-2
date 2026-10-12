from focusareas.models import InterventionType

from .models import Intervention


def sync_compatible_interventions(strategy):
    """
    Ensures `strategy` has one Intervention row for every active InterventionType
    compatible with its parent Opportunity's focus area. Existing rows (including
    user-made clones) are left untouched; only missing types are backfilled.
    """
    compatible_type_ids = InterventionType.objects.filter(
        is_active=True,
        focus_areas=strategy.opportunity.focus_area_id,
    ).values_list('id', flat=True)

    existing_type_ids = set(
        strategy.interventions.values_list('intervention_type_id', flat=True)
    )

    for type_id in compatible_type_ids:
        if type_id not in existing_type_ids:
            Intervention.objects.create(strategy=strategy, intervention_type_id=type_id)
