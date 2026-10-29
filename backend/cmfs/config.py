from decimal import Decimal


# Data-analysis bounds. These are inclusive and are shared by API validation
# and the frontend setup form through the CMF config endpoint.
CMF_LOWER_LIMIT = Decimal('0.1')
CMF_UPPER_LIMIT = Decimal('2.5')

CMF_MATH_CONFIG = [
    {'code': 'E', 'label': 'Exponential: y = a*exp(bx) + c'},
    {'code': 'L', 'label': 'Logarithmic: y = a + b ln(x)'},
    {'code': 'P', 'label': 'Power: y = a*x^b + c'},
    {'code': 'Q', 'label': 'Quadratic: y = a*x^2 + bx + c'},
]


# The label is shown to users; the code is stored on the CMF and consumed by
# the analytics pipeline. Keep these pairings in the backend configuration so
# the UI and analysis services use the same identifiers.
CMF_FILTER_CONFIG = [
    {
        'key': 'roadwayFeature',
        'label': 'Roadway Feature Type',
        'mod_code': 'ModCode1',
        'options': [
            {'label': 'All Roadway Features', 'code': 'RFALL'},
            {'label': 'Roadway Segments Only (not intersections/junctions)', 'code': 'RFSEG'},
            {'label': 'Ramps Only', 'code': 'RFRMP'},
            {'label': 'Intersections Only', 'code': 'RFISN'},
            {'label': 'Two-Way Stop Intersections Only', 'code': 'RF2WS'},
            {'label': 'All-Way Stop Intersections Only', 'code': 'RFAWS'},
            {'label': 'Signalized Intersections Only', 'code': 'RFSIG'},
            {'label': 'Roundabouts Only', 'code': 'RFRAB'},
            {'label': 'Railway Grade Crossings (Level Crossings) Only', 'code': 'RFRRX'},
            {'label': 'Bike/Ped Crossings Only', 'code': 'RFPDX'},
            {'label': 'School Zones Only', 'code': 'RFSCH'},
            {'label': 'Work Zones Only', 'code': 'RFWZN'},
        ],
    },
    {
        'key': 'vehicle',
        'label': 'Vehicle Subtype',
        'mod_code': 'ModCode2',
        'options': [
            {'label': 'All Motor Vehicle Types', 'code': 'VTALL'},
            {'label': 'Cars, Light Trucks, and SUVs Only', 'code': 'VTPAS'},
            {'label': 'School Buses Only', 'code': 'VTSCH'},
            {'label': 'Transit Buses & Intercity Motorcoaches Only', 'code': 'VTBUS'},
            {'label': 'Heavy Trucks Only', 'code': 'VTTRK'},
            {'label': 'Hazardous Material Transporters Only', 'code': 'VTHMT'},
        ],
    },
    {
        'key': 'mannerOfCollision',
        'label': 'Manner of Collision',
        'mod_code': 'ModCode3',
        'options': [
            {'label': 'All Manners of Collision', 'code': 'MCALL'},
            {'label': 'Single Vehicle Only (run off road / road departure)', 'code': 'MCSV'},
            {'label': 'Angle Collision Only', 'code': 'MCAN'},
            {'label': 'Front to Front Collision Only', 'code': 'MCFF'},
            {'label': 'Front-to-Rear or Rear-to-Front Collisions Only', 'code': 'MCFR'},
            {'label': 'Rear to Rear Collisions Only', 'code': 'MCRR'},
            {'label': 'Rear-to-Side or Side-to-Rear Collisions Only', 'code': 'MCRS'},
            {'label': 'Sideswipe - Opposite Direction Only', 'code': 'MCSO'},
            {'label': 'Sideswipe - Same Direction Only', 'code': 'MCSS'},
        ],
    },
    {
        'key': 'contributingCircumstance',
        'label': 'Contributing Circumstances',
        'mod_code': 'ModCode4',
        'options': [
            {'label': 'No special circumstance', 'code': 'CCNON'},
            {'label': 'Animal Involved Crashes Only (e.g., deer crashes)', 'code': 'CCANI'},
            {'label': 'Debris on Road Only', 'code': 'CCDBR'},
            {'label': 'Secondary to Prior Incident Only', 'code': 'CCSEC'},
            {'label': 'Congestion-Related Crashes Only', 'code': 'CCCGN'},
            {'label': 'Road Maintenance Issues Only (e.g., ruts, potholes, etc.)', 'code': 'CCMNT'},
            {'label': 'Visual Obstruction(s) Only', 'code': 'CCVIS'},
            {'label': 'Adverse Weather Only (any type of adverse weather)', 'code': 'CCWEA'},
            {'label': 'Fog Only', 'code': 'CCWFG'},
            {'label': 'Wet Weather Only', 'code': 'CCWWT'},
            {'label': 'Snow/Ice Only', 'code': 'CCWSN'},
            {'label': 'Police Pursuit Only', 'code': 'CCPLP'},
        ],
    },
    {
        'key': 'intoxicationStatus',
        'label': 'Intoxication: Attributable Fraction of Casualties',
        'mod_code': 'ModCode5',
        'options': [
            {'label': 'Any intoxication status (including not intoxicated)', 'code': 'IXALL'},
            {'label': 'Not Intoxicated', 'code': 'IXNON'},
            {'label': 'Intoxicated: Any Substance', 'code': 'IXANY'},
            {'label': 'Intoxicated: Alcohol', 'code': 'IXALC'},
            {'label': 'Intoxicated: Cannabis/Marijuana', 'code': 'IXTHC'},
            {'label': 'Intoxicated: Opioid', 'code': 'IXOPI'},
            {'label': 'Intoxicated: Stimulant (cocaine, methamphetamine, ectasy, etc.)', 'code': 'IXAMP'},
            {'label': 'Intoxicated: Other Drugs (hallucinogens, solvents, dissociatives, etc.)', 'code': 'IXOTH'},
            {'label': 'Intoxicated: Polysubstance (simultaneous use of 2+ drugs)', 'code': 'IXPLY'},
        ],
    },
]


CMF_MOD_CODE_OPTIONS = {
    filter_config['mod_code']: tuple(option['code'] for option in filter_config['options'])
    for filter_config in CMF_FILTER_CONFIG
}
