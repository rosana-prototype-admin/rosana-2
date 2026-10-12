from django.db import migrations

# Temporary stand-ins until the real Intervention Type catalog (and its
# per-type parameter schema) is defined. Linked to every FocusArea so they
# show up regardless of which focus area a project uses, unblocking
# frontend development of the Intervention table/editor in the meantime.
PLACEHOLDER_TYPES = [
    {
        'name': 'Placeholder Intervention Type A',
        'description': 'Placeholder intervention type pending the real catalog.',
    },
    {
        'name': 'Placeholder Intervention Type B',
        'description': 'Placeholder intervention type pending the real catalog.',
    },
    {
        'name': 'Placeholder Intervention Type C',
        'description': 'Placeholder intervention type pending the real catalog.',
    },
]


def seed_intervention_types(apps, schema_editor):
    InterventionType = apps.get_model('focusareas', 'InterventionType')
    FocusArea = apps.get_model('focusareas', 'FocusArea')
    all_focus_areas = list(FocusArea.objects.all())
    for entry in PLACEHOLDER_TYPES:
        intervention_type = InterventionType.objects.create(**entry)
        intervention_type.focus_areas.set(all_focus_areas)


def unseed_intervention_types(apps, schema_editor):
    InterventionType = apps.get_model('focusareas', 'InterventionType')
    InterventionType.objects.filter(name__in=[entry['name'] for entry in PLACEHOLDER_TYPES]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ('focusareas', '0002_seed_focus_areas'),
    ]

    operations = [
        migrations.RunPython(seed_intervention_types, unseed_intervention_types),
    ]
