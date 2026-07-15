from django.db import migrations

# Verbatim encoding of the Focus Area tree from
# "supporting documents/Rosana-focus-areas.txt" (corrected structure: 3 levels
# total — Road Users / Infrastructure & Speed Management / Vehicle Features &
# Conditions / Post-Crash Medical Care are each independent top-level (L1)
# categories, not nested under Road Users). Sibling order here matches
# document order, since the seed sets FocusArea.order from list position.
FOCUS_AREA_TREE = [
    {
        'name': 'Road Users',
        'children': [
            {
                'name': 'Vulnerable Road Users',
                'children': [
                    {'name': 'Pedestrians'},
                    {'name': 'Bicyclists'},
                    {'name': 'Children'},
                    {'name': 'Elders & People with Disabilities'},
                    {'name': 'Underserved Communities'},
                ],
            },
            {
                'name': 'Powersport Vehicle Users',
                'children': [
                    {'name': 'Micromobility (eBikes, eScooters, etc.)'},
                    {'name': 'Motorcycles'},
                    {'name': 'ATVs & UTVs'},
                    {'name': 'Dirt Bikes, Dune Buggies & Snowmobiles'},
                ],
            },
            {
                'name': 'Motor Vehicle Occupant Protection',
                'children': [
                    {'name': 'Child Passenger Restraints'},
                    {'name': 'Seatbelts'},
                ],
            },
            {
                'name': 'Taxis and Passenger Vehicle Fleets',
                'children': [
                    {'name': 'Taxis and Ride Hailing Services'},
                    {'name': 'Government Fleets'},
                    {'name': 'Private Fleets'},
                ],
            },
            {
                'name': 'Heavy Trucks & Buses',
                'children': [
                    {'name': 'Local Freight and Parcel Delivery'},
                    {'name': 'Intercity Trucking'},
                    {'name': 'Hazardous Material Transport'},
                    {'name': 'School Bus'},
                    {'name': 'Urban Bus'},
                    {'name': 'Intercity Bus (Coach)'},
                ],
            },
            {
                'name': 'Driver Age',
                'children': [
                    {'name': 'Young Drivers (≤19 years)'},
                    {'name': 'Elder Drivers (≥65 years)'},
                ],
            },
            {
                'name': 'Impaired Driving',
                'children': [
                    {'name': 'Alcohol'},
                    {'name': 'Cannabis (Marijuana)'},
                    {'name': 'Other Drugs'},
                ],
            },
            {
                'name': 'Other Driving Conditions & Behaviors',
                'children': [
                    {'name': 'Aggressive, Reckless & Stunt Driving'},
                    {'name': 'Distracted Driving'},
                    {'name': 'Drowsy/Fatigued Driving'},
                    {'name': 'Work-Related Driving'},
                ],
            },
            {
                'name': 'Legislation & Enforcement',
                'children': [
                    {'name': 'Automated Enforcement'},
                    {'name': 'Manual Enforcement'},
                    {'name': 'Fines & Penalties'},
                    {'name': 'Traffic Regulations'},
                    {'name': 'General-Purpose Policy Instruments'},
                ],
            },
            {
                'name': 'Driver Education & Public Outreach',
                'children': [
                    {'name': 'Driver Education'},
                    {'name': 'Public Information Campaigns'},
                    {'name': 'Safety Culture Change'},
                ],
            },
        ],
    },
    {
        'name': 'Infrastructure & Speed Management',
        'children': [
            {
                'name': 'Intersections, Junctions & Crossings',
                'children': [
                    {'name': 'Animal Crossings'},
                    {'name': 'Bikeway & Multi-Use Path Crossings'},
                    {'name': 'Pedestrian Crossings'},
                    {'name': 'Intersertions - Rural'},
                    {'name': 'Intersertions - Urban'},
                    {'name': 'Ramp Terminals'},
                    {'name': 'Railway Crossings'},
                ],
            },
            {
                'name': 'Roadway Segments by Facility Type',
                'children': [
                    {'name': 'Freeway/Motorway/Tollway Mainlines'},
                    {'name': 'Other Multi-Lane Divided High-Speed Mainlines'},
                    {'name': 'Ramps'},
                    {'name': 'Primary Rural Highways'},
                    {'name': 'Secondary Rural Highways'},
                    {'name': 'Urban/Suburban Arterials'},
                    {'name': 'Major Collectors'},
                    {'name': 'Minor Collectors'},
                    {'name': 'Local/Neighborhood Streets'},
                    {'name': 'Alleys and Driveways'},
                ],
            },
            {
                'name': 'Special Driving Zones',
                'children': [
                    {'name': 'School Zones'},
                    {'name': 'Work Zones'},
                ],
            },
            {
                'name': 'Weather and Road Maintenance',
                'children': [
                    {'name': 'Winter Driving'},
                    {'name': 'Other Adverse Road Conditions'},
                ],
            },
            {'name': 'Speed Management'},
            {
                'name': 'Roadway Interventions by Manner of Collision',
                'children': [
                    {'name': 'Animal'},
                    {'name': 'Failure to Yield'},
                    {'name': 'Head-On'},
                    {'name': 'Lane/Roadway Departure'},
                    {'name': 'Rear End'},
                    {'name': 'Run Off Road (Single Vehicle)'},
                ],
            },
        ],
    },
    {
        'name': 'Vehicle Features & Conditions',
        'children': [
            {
                'name': 'Vehicle Design & Equipment',
                'children': [
                    {'name': 'Advanced Driver Assistance Systems'},
                    {'name': 'Connected/Autonomous Vehicles'},
                ],
            },
            {'name': 'Vehicle Inspection & Maintenance'},
        ],
    },
    {
        'name': 'Post-Crash Medical Care',
        'children': [
            {'name': 'Post-Crash Medical Care'},
        ],
    },
]


def _create_node(model, node, parent, order):
    obj = model.objects.create(
        name=node['name'],
        parent=parent,
        level=1 if parent is None else parent.level + 1,
        order=order,
    )
    for child_order, child in enumerate(node.get('children', [])):
        _create_node(model, child, obj, child_order)
    return obj


def seed_focus_areas(apps, schema_editor):
    FocusArea = apps.get_model('focusareas', 'FocusArea')
    for order, root in enumerate(FOCUS_AREA_TREE):
        _create_node(FocusArea, root, parent=None, order=order)


def unseed_focus_areas(apps, schema_editor):
    FocusArea = apps.get_model('focusareas', 'FocusArea')
    FocusArea.objects.all().delete()


class Migration(migrations.Migration):
    dependencies = [
        ('focusareas', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(seed_focus_areas, unseed_focus_areas),
    ]
