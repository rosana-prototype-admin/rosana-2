from django.db import migrations


AGE_FIELDS = ('age_0004', 'age_0509', 'age_1014', 'age_1519', 'age_2064', 'age_65up')
PLAN_FIELDS = (
    'crossroads', 'borough', 'ville', 'shire', 'provincia',
    'comarca', 'metro', 'commonwealth', 'republic',
)


CMF_SEEDS = {
    'cmf-rrfb': {
        'title': 'Rectangular Rapid Flashing Beacon (RRFB)',
        'groups': (
            'Vulnerable Road Users --> Pedestrians',
            'Intersections, Junctions & Crossings --> Pedestrian Crossings',
            'Special Driving Zones--> School Zones',
        ),
        'codes': ('RFPDX', 'VTALL', 'MCALL', 'CCNON', 'IXALL'),
        'ages': (1.0, 1.0, 1.0, 1.0, 1.0, 1.0),
        'permissions': (True, False, True, False, True, True, True, True, True),
        'coefficients': [
            [1.0, 1.0, 1.0, 1.0, 1.0],
            [1.0, 1.0, 1.0, 1.0, 1.0],
            [0.75, 0.75, 0.75, 0.75, 0.9],
            [0.75, 0.75, 0.75, 0.75, 0.9],
            [1.0, 1.0, 1.0, 1.0, 1.0],
        ],
    },
    'cmf-phb': {
        'title': 'Pedestrian Hybrid Beacon (PHB)',
        'groups': (
            'Vulnerable Road Users --> Pedestrians',
            'Intersections, Junctions & Crossings --> Pedestrian Crossings',
            'Special Driving Zones--> School Zones',
        ),
        'codes': ('RFPDX', 'VTALL', 'MCALL', 'CCNON', 'IXALL'),
        'ages': (1.0, 1.0, 1.0, 1.0, 1.0, 1.0),
        'permissions': (True, False, True, False, True, True, True, True, True),
        'coefficients': [
            [1.0, 1.0, 1.0, 1.0, 1.0],
            [1.0, 1.0, 1.0, 1.0, 1.0],
            [0.6, 0.6, 0.6, 0.6, 0.8],
            [0.6, 0.6, 0.6, 0.6, 0.8],
            [1.0, 1.0, 1.0, 1.0, 1.0],
        ],
    },
    'cmf-motorcycle-helmets': {
        'title': 'Mandatory Use of Motorcycle Helmets',
        'groups': ('Powersport Vehicle Users --> Motorcycles', None, None),
        'codes': ('RFALL', 'VTALL', 'MCALL', 'CCNON', 'IXALL'),
        # The source workbook uses -1/User Input for these cells. The
        # approved import rule replaces each with 0.85.
        'ages': (0.85, 0.85, 0.85, 0.85, 0.85, 0.85),
        'permissions': (True, True, True, True, True, True, True, True, True),
        'coefficients': [
            [1.0, 1.0, 1.0, 1.0, 1.0],
            [0.85, 0.85, 0.85, 0.85, 0.95],
            [1.0, 1.0, 1.0, 1.0, 1.0],
            [1.0, 1.0, 1.0, 1.0, 1.0],
            [1.0, 1.0, 1.0, 1.0, 1.0],
        ],
    },
    'cmf-signalized-intersection-roundabout': {
        'title': 'Convert Signalized Intersection to Roundabout',
        'groups': (
            'Intersections, Junctions & Crossings --> Intersections - Rural',
            'Intersections, Junctions & Crossings --> Intersections - Urban',
            'Intersections, Junctions & Crossings --> Intersections - Ramp Terminals',
        ),
        'codes': ('RFSIG', 'VTALL', 'MCALL', 'CCNON', 'IXALL'),
        'ages': (1.0, 1.0, 1.0, 1.0, 1.0, 1.0),
        'permissions': (False, False, True, True, True, True, True, True, True),
        'coefficients': [
            [0.65, 0.65, 0.65, 0.65, 1.25],
            [0.65, 0.65, 0.65, 0.65, 1.25],
            [1.0, 1.0, 1.0, 1.0, 1.0],
            [1.0, 1.0, 1.0, 1.0, 1.0],
            [0.65, 0.65, 0.65, 0.65, 1.25],
        ],
    },
}


def seed_cmfs_and_interventions(apps, schema_editor):
    CMF = apps.get_model('cmfs', 'CMF')
    CMFMetadata = apps.get_model('cmfs', 'CMFMetadata')
    CMFCoefficient = apps.get_model('cmfs', 'CMFCoefficient')
    CMFUserPermission = apps.get_model('cmfs', 'CMFUserPermission')
    InterventionType = apps.get_model('focusareas', 'InterventionType')
    FocusArea = apps.get_model('focusareas', 'FocusArea')

    cmfs = {}
    for code, seed in CMF_SEEDS.items():
        cmf, _ = CMF.objects.update_or_create(
            code=code,
            defaults={
                'title': seed['title'],
                'is_builtin': True,
                'author_id': None,
                'base_cmf_id': None,
                'permission_scope': 'global',
                'cmf_source': 'Sample_CMFs.xlsx',
            },
        )
        cmfs[code] = cmf
        group1, group2, group3 = seed['groups']
        metadata, _ = CMFMetadata.objects.update_or_create(
            cmf_id=cmf.pk,
            defaults={
                'cmf_group1': group1,
                'cmf_group2': group2,
                'cmf_group3': group3 if group2 else None,
                'descr_en_us': '',
                'descr_en_au': '',
                'descr_en_ca': '',
                'descr_fr_ca': '',
                'descr_es': '',
                'cmf_math': 'Q',
                'mod_code1': seed['codes'][0],
                'mod_code2': seed['codes'][1],
                'mod_code3': seed['codes'][2],
                'mod_code4': seed['codes'][3],
                'mod_code5': seed['codes'][4],
                **dict(zip(AGE_FIELDS, seed['ages'])),
            },
        )

        CMFCoefficient.objects.filter(cmf_id=cmf.pk).delete()
        CMFCoefficient.objects.bulk_create([
            CMFCoefficient(
                cmf_id=cmf.pk,
                travel_mode=travel_mode,
                severity=severity,
                coefficient_a=0.0,
                coefficient_b=value,
                coefficient_c=0.0,
            )
            for travel_mode, row in enumerate(seed['coefficients'], start=1)
            for severity, value in zip(('K', 'A', 'B', 'C', 'O'), row)
        ])
        CMFUserPermission.objects.update_or_create(
            cmf_id=cmf.pk,
            defaults=dict(zip(PLAN_FIELDS, seed['permissions'])),
        )

    intervention_specs = {
        'Rectangular Rapid Flashing Beacons (RRFBs)': 'cmf-rrfb',
        'Pedestrian Hybrid Beacons (PHBs)': 'cmf-phb',
        'Universal Motorcycle Helmet Laws': 'cmf-motorcycle-helmets',
        'Convert Signalized Intersection to Roundabout': 'cmf-signalized-intersection-roundabout',
    }
    category = 'Infrastructure, Traffic Engineering, and Speed Management'
    policy_category = 'Policy'
    for name, code in intervention_specs.items():
        intervention_category = policy_category if name == 'Universal Motorcycle Helmet Laws' else category
        intervention, _ = InterventionType.objects.get_or_create(
            name=name,
            category=intervention_category,
            defaults={'description': ''},
        )
        intervention.cmf_id = cmfs[code].pk
        intervention.save(update_fields=['cmf'])

    roundabout = InterventionType.objects.get(
        name='Convert Signalized Intersection to Roundabout',
        category=category,
    )
    focus_areas = FocusArea.objects.filter(
        name__in=('Intersertions - Rural', 'Intersertions - Urban', 'Ramp Terminals')
    )
    roundabout.focus_areas.add(*focus_areas)


class Migration(migrations.Migration):

    dependencies = [
        ('cmfs', '0011_age_applicability_weights'),
        ('focusareas', '0006_interventiontype_cmf'),
    ]

    operations = [
        migrations.RunPython(seed_cmfs_and_interventions, migrations.RunPython.noop),
    ]
