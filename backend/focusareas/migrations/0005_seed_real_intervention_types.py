from django.db import migrations

# Real intervention catalog (supersedes the temporary "Placeholder
# Intervention Type A/B/C" catalog seeded in 0003_seed_intervention_types.py)
# -- verbatim from "Interventions cleaned.csv". Rows are
# (specific_focus_area, category, name). The same (category, name) pair
# legitimately recurs for more than one focus area (e.g. "Drug-Impaired
# Driving Laws" / "Policy" applies to both Cannabis and Other Drugs, and
# "Sobriety Checkpoints" appears under both "Enforcement" and "Policy" for
# Alcohol) -- seed_real_intervention_types() below folds recurrences of the
# same (name, category) pair into one InterventionType row spanning multiple
# focus_areas, rather than creating duplicate rows.
INTERVENTIONS = [
    ('Pedestrians', 'Infrastructure, Traffic Engineering, and Speed Management', 'Sidewalk'),
    (
        'Pedestrians',
        'Infrastructure, Traffic Engineering, and Speed Management',
        'Traffic Calming (e.g., chicaine, speed hump, etc.)',
    ),
    ('Pedestrians', 'Infrastructure, Traffic Engineering, and Speed Management', 'Crosswalk Markings'),
    ('Pedestrians', 'Infrastructure, Traffic Engineering, and Speed Management', 'Belisha Beacon'),
    ('Pedestrians', 'Infrastructure, Traffic Engineering, and Speed Management', 'Enhanced Amber Beacons'),
    (
        'Pedestrians',
        'Infrastructure, Traffic Engineering, and Speed Management',
        'Pedestrian Hybrid Beacons (PHBs)',
    ),
    (
        'Pedestrians',
        'Infrastructure, Traffic Engineering, and Speed Management',
        'Rectangular Rapid Flashing Beacons (RRFBs)',
    ),
    (
        'Pedestrians',
        'Infrastructure, Traffic Engineering, and Speed Management',
        'Mid-Block Pedestrian Signal (MBPS)',
    ),
    ('Pedestrians', 'Infrastructure, Traffic Engineering, and Speed Management', 'Intersection Pedestrian Signal'),
    ('Pedestrians', 'Infrastructure, Traffic Engineering, and Speed Management', 'Grade Separation'),
    ('Pedestrians', 'Law Enforcement & Criminal Justice', 'Intersection Traffic Enforcement Campaign'),
    ('Pedestrians', 'Law Enforcement & Criminal Justice', 'Automated Red Light Cameras'),
    ('Pedestrians', 'Law Enforcement & Criminal Justice', 'Automated Speed Camera Enforcement'),
    ('Pedestrians', 'Education & Public Outreach', 'Teach Children to Cross Streets Safely'),
    ('Pedestrians', 'Education & Public Outreach', 'Community-Wide Ped Safety Outreach'),
    ('Pedestrians', 'Vehicle Technology', 'Intelligent Speed Assistance'),
    ('Pedestrians', 'Vehicle Technology', 'Pedestrian Audible Alerts'),
    ('Bicyclists', 'Policy', 'Bicycle Helmet Laws for Children'),
    ('Motorcycles', 'Policy', 'Universal Motorcycle Helmet Laws'),
    ('Alcohol', 'Enforcement', 'Alcohol Vendor Compliance Checks'),
    ('Alcohol', 'Enforcement', 'Change Enforcement Level of Effort'),
    ('Alcohol', 'Enforcement', 'Integrated Enforcement'),
    ('Alcohol', 'Enforcement', 'Saturation Patrols'),
    ('Alcohol', 'Enforcement', 'Sobriety Checkpoints'),
    ('Alcohol', 'Enforcement', 'Zero-Tolerance Law Enforcement'),
    ('Alcohol', 'Education & Public Outreach', 'Alternative Transportation'),
    ('Alcohol', 'Education & Public Outreach', 'Designated Driver Campaign'),
    ('Alcohol', 'Education & Public Outreach', 'Media Campaign'),
    ('Alcohol', 'Policy', 'Administrative License Revocation/Suspension'),
    ('Alcohol', 'Policy', 'Alcohol Ignition Interlocks'),
    ('Alcohol', 'Policy', 'BAC Test Refusal Penalties'),
    ('Alcohol', 'Policy', 'Change Alcohol Tax Rate'),
    ('Alcohol', 'Policy', 'Change Statutory Blood Alcohol Limits'),
    ('Alcohol', 'Policy', 'Change Statutory Drinking Age'),
    ('Alcohol', 'Policy', 'Court Monitoring'),
    ('Alcohol', 'Policy', 'DWI/OWI Courts'),
    ('Alcohol', 'Policy', 'DWI/OWI Offender Monitoring'),
    ('Alcohol', 'Policy', 'High BAC Sanctions'),
    ('Alcohol', 'Policy', 'Ignition Interlocks'),
    ('Alcohol', 'Policy', 'In-Person License Renewal'),
    ('Alcohol', 'Policy', 'License Plate Impoundment'),
    ('Alcohol', 'Policy', 'Limits on Diversion & Plea Agreements'),
    ('Alcohol', 'Policy', 'Open Container Law'),
    ('Alcohol', 'Policy', 'Sobriety Checkpoints'),
    ('Alcohol', 'Policy', 'Vehicle Impoundment'),
    ('Alcohol', 'Treatment', 'Alcohol Problem Assessment and Treatment'),
    ('Alcohol', 'Treatment', 'Screening, Brief Intervention & Referral to Treatment (SBIRT)'),
    ('Cannabis (Marijuana)', 'Policy', 'Change Legal Status of Cannabis/Marijuana'),
    ('Cannabis (Marijuana)', 'Policy', 'Drug-Impaired Driving Laws'),
    ('Cannabis (Marijuana)', 'Policy', 'Enforcement of Drug-Impaired Driving'),
    ('Cannabis (Marijuana)', 'Education & Public Outreach', 'Public Outreach - DUIC'),
    ('Cannabis (Marijuana)', 'Enforcement', 'Screening, Brief Intervention & Referral to Treatment (SBIRT)'),
    ('Other Drugs', 'Policy', 'Drug-Impaired Driving Laws'),
    ('Other Drugs', 'Policy', 'Enforcement of Drug-Impaired Driving'),
    ('Other Drugs', 'Policy', 'Screening, Brief Intervention & Referral to Treatment (SBIRT)'),
]


def seed_real_intervention_types(apps, schema_editor):
    InterventionType = apps.get_model('focusareas', 'InterventionType')
    FocusArea = apps.get_model('focusareas', 'FocusArea')
    Intervention = apps.get_model('projects', 'Intervention')

    # Intervention.intervention_type is PROTECT, and any existing Intervention
    # rows were auto-synced (see projects.services.sync_compatible_interventions)
    # against the placeholder catalog being replaced here -- they're
    # meaningless once their type is gone, and get freshly re-synced from the
    # real catalog the next time each Strategy's interventions are listed.
    Intervention.objects.all().delete()
    InterventionType.objects.all().delete()

    focus_area_cache = {}
    for focus_area_name, category, name in INTERVENTIONS:
        if focus_area_name not in focus_area_cache:
            focus_area_cache[focus_area_name] = FocusArea.objects.get(name=focus_area_name)
        focus_area = focus_area_cache[focus_area_name]

        intervention_type, _ = InterventionType.objects.get_or_create(name=name, category=category)
        intervention_type.focus_areas.add(focus_area)


def unseed_real_intervention_types(apps, schema_editor):
    InterventionType = apps.get_model('focusareas', 'InterventionType')
    InterventionType.objects.all().delete()


class Migration(migrations.Migration):
    dependencies = [
        ('focusareas', '0004_alter_interventiontype_options_and_more'),
        ('projects', '0007_delete_organization_alter_project_organizations'),
    ]

    # This migration's apps.get_model('projects', 'Intervention') requires that
    # model to still exist -- projects.0008 deletes it, and nothing otherwise
    # orders these two relative to each other (both only depend on projects.0007),
    # so without this the migration graph's topological sort is free to run
    # 0008 first, breaking this migration. Pin it explicitly.
    run_before = [
        ('projects', '0008_remove_project_organizations_remove_project_strategy_and_more'),
    ]

    operations = [
        migrations.RunPython(seed_real_intervention_types, unseed_real_intervention_types),
    ]
