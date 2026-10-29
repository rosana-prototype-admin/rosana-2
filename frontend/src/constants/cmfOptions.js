export const INJURY_TYPES = [
  { key: 'fatalities', code: 'K', label: 'Fatalities (K)', emoji: '⚰️', tooltip: 'Fatalities' },
  { key: 'seriousInjuries', code: 'A', label: 'Serious Injuries (A)', emoji: '🦽', tooltip: 'Serious/major injuries: overnight hospital stay required' },
  { key: 'minorInjuries', code: 'B', label: 'Minor Injuries (B)', emoji: '🩺', tooltip: 'Minor injuries: treated and released at hospital emergency department' },
  { key: 'possibleInjuries', code: 'C', label: 'Possible Injuries (C)', emoji: '🩹', tooltip: 'Possible injuries: self-treated or refused treatment - might require subsequent medical attention' },
  { key: 'propertyDamage', code: 'O', label: 'Property Damage (O)', emoji: '💥', tooltip: 'Property damage only' },
]

export const ROAD_USER_TYPES = [
  {
    key: 'motorVehicleOccupants',
    category: 1,
    label: 'Motor Vehicle Occupants',
    emoji: '🚗🚛🚎',
    tooltip: 'Drivers and passengers of automobiles, light trucks, SUVs, heavy trucks, and buses',
  },
  {
    key: 'motorcyclists',
    category: 2,
    label: 'Motorcyclists',
    emoji: '🏍️🛵',
    tooltip: 'Drivers and passengers of motorcycles, mopeds, powered scooters, and high-horsepower e-bikes',
  },
  {
    key: 'bicyclists',
    category: 3,
    label: 'Bicyclists',
    emoji: '🚴',
    tooltip: 'Riders of human-powered bicycles and low horsepower e-Bikes',
  },
  {
    key: 'pedestrians',
    category: 4,
    label: 'Pedestrians',
    emoji: '🚶🛴',
    tooltip: 'Pedestrians and riders of human-powered wheeled toys such as inline skates, skateboards, and kick scooters',
  },
  {
    key: 'otherRoadUsers',
    category: 5,
    label: 'Other Road Users',
    emoji: '🚋🏇',
    tooltip: 'Other road users, specifically operators and passengers on street-running trams/trolleys/light rail, equestrians, and animal-drawn wagons, buggies, and carriages',
  },
]

export const AGE_GROUP_OPTIONS = [
  { label: '0-4', value: '0-4' },
  { label: '5-9', value: '5-9' },
  { label: '10-14', value: '10-14' },
  { label: '15-19', value: '15-19' },
  { label: '20-64', value: '20-64' },
  { label: '65+', value: '65+' },
]

export const CMF_LIMITS = {
  lower: 0,
  upper: 1,
}

export const CMF_FILTERS = [
  {
    key: 'roadwayFeature',
    label: 'Roadway Feature Type',
    options: [
      { label: 'All Roadway Features', value: 'RFALL' },
      { label: 'Roadway Segments Only (not intersections/junctions)', value: 'RFSEG' },
      { label: 'Ramps Only', value: 'RFRMP' },
      { label: 'Intersections Only', value: 'RFISN' },
      { label: 'Two-Way Stop Intersections Only', value: 'RF2WS' },
      { label: 'All-Way Stop Intersections Only', value: 'RFAWS' },
      { label: 'Signalized Intersections Only', value: 'RFSIG' },
      { label: 'Roundabouts Only', value: 'RFRAB' },
      { label: 'Railway Grade Crossings (Level Crossings) Only', value: 'RFRRX' },
      { label: 'Bike/Ped Crossings Only', value: 'RFPDX' },
      { label: 'School Zones Only', value: 'RFSCH' },
      { label: 'Work Zones Only', value: 'RFWZN' },
    ],
  },
  {
    key: 'vehicle',
    label: 'Vehicle Type',
    options: [
      { label: 'All Motor Vehicle Types', value: 'VTALL' },
      { label: 'Cars, Light Trucks, and SUVs Only', value: 'VTPAS' },
      { label: 'School Buses Only', value: 'VTSCH' },
      { label: 'Transit Buses & Intercity Motorcoaches Only', value: 'VTBUS' },
      { label: 'Heavy Trucks Only', value: 'VTTRK' },
      { label: 'Hazardous Material Transporters Only', value: 'VTHMT' },
    ],
  },
  {
    key: 'mannerOfCollision',
    label: 'Manner of Collision',
    options: [
      { label: 'All Manners of Collision', value: 'MCALL' },
      { label: 'Single Vehicle Only (run off road / road departure)', value: 'MCSV' },
      { label: 'Angle Collision Only', value: 'MCAN' },
      { label: 'Front to Front Collision Only', value: 'MCFF' },
      { label: 'Front-to-Rear or Rear-to-Front Collisions Only', value: 'MCFR' },
      { label: 'Rear to Rear Collisions Only', value: 'MCRR' },
      { label: 'Rear-to-Side or Side-to-Rear Collisions Only', value: 'MCRS' },
      { label: 'Sideswipe - Opposite Direction Only', value: 'MCSO' },
      { label: 'Sideswipe - Same Direction Only', value: 'MCSS' },
    ],
  },
  {
    key: 'contributingCircumstance',
    label: 'Contributing Circumstances',
    options: [
      { label: 'No special circumstance', value: 'CCNON' },
      { label: 'Animal Involved Crashes Only (e.g., deer crashes)', value: 'CCANI' },
      { label: 'Debris on Road Only', value: 'CCDBR' },
      { label: 'Secondary to Prior Incident Only', value: 'CCSEC' },
      { label: 'Congestion-Related Crashes Only', value: 'CCCGN' },
      { label: 'Road Maintenance Issues Only (e.g., ruts, potholes, etc.)', value: 'CCMNT' },
      { label: 'Visual Obstruction(s) Only', value: 'CCVIS' },
      { label: 'Adverse Weather Only (any type of adverse weather)', value: 'CCWEA' },
      { label: 'Fog Only', value: 'CCWFG' },
      { label: 'Wet Weather Only', value: 'CCWWT' },
      { label: 'Snow/Ice Only', value: 'CCWSN' },
      { label: 'Police Pursuit Only', value: 'CCPLP' },
    ],
  },
  {
    key: 'intoxicationStatus',
    label: 'Intoxication: Attributable Fraction of Casualties',
    options: [
      { label: 'Any intoxication status (including not intoxicated)', value: 'IXALL' },
      { label: 'Not Intoxicated', value: 'IXNON' },
      { label: 'Intoxicated: Any Substance', value: 'IXANY' },
      { label: 'Intoxicated: Alcohol', value: 'IXALC' },
      { label: 'Intoxicated: Cannabis/Marijuana', value: 'IXTHC' },
      { label: 'Intoxicated: Opioid', value: 'IXOPI' },
      { label: 'Intoxicated: Stimulant (cocaine, methamphetamine, ectasy, etc.)', value: 'IXAMP' },
      { label: 'Intoxicated: Other Drugs (hallucinogens, solvents, dissociatives, etc.)', value: 'IXOTH' },
      { label: 'Intoxicated: Polysubstance (simultaneous use of 2+ drugs)', value: 'IXPLY' },
    ],
  },
  { key: 'ageGroup', label: 'Age Groups', options: AGE_GROUP_OPTIONS },
]

export function cmfFiltersFromConfig(config) {
  if (!Array.isArray(config?.cmf_filters)) return CMF_FILTERS

  const configuredFilters = Object.fromEntries(
    config.cmf_filters.map((filter) => [filter.key, filter]),
  )

  return CMF_FILTERS.map((fallbackFilter) => {
    const configuredFilter = configuredFilters[fallbackFilter.key]
    if (!configuredFilter || !Array.isArray(configuredFilter.options)) return fallbackFilter

    return {
      ...fallbackFilter,
      label: configuredFilter.label,
      modCode: configuredFilter.mod_code,
      options: configuredFilter.options.map(({ label, code }) => ({ label, value: code })),
    }
  })
}

export function createInitialCmfValues() {
  return Object.fromEntries(
    ROAD_USER_TYPES.map(({ key }) => [
      key,
      Object.fromEntries(INJURY_TYPES.map(({ key: injuryKey }) => [injuryKey, '1'])),
    ]),
  )
}

export function createInitialCmfCoefficients() {
  return Object.fromEntries(
    ROAD_USER_TYPES.map(({ key: roadUserKey }) => [
      roadUserKey,
      Object.fromEntries(INJURY_TYPES.map(({ key: injuryKey }) => [
        injuryKey,
        { a: '0', b: '1', c: '0' },
      ])),
    ]),
  )
}

export function createInitialCmfSetup() {
  return {
    title: '',
    description: '',
    cmfGroup1: '',
    cmfGroup2: '',
    cmfGroup3: '',
    descrEnUs: '',
    cmfMath: 'Q',
    modCode1: '',
    modCode2: '',
    modCode3: '',
    modCode4: '',
    modCode5: '',
    age0004: false,
    age0509: false,
    age1014: false,
    age1519: false,
    age2064: false,
    age65up: false,
    roadwayFeature: 'RFALL',
    vehicle: 'VTALL',
    mannerOfCollision: 'MCALL',
    contributingCircumstance: 'CCNON',
    intoxicationStatus: 'IXALL',
    ageGroup: [],
    coefficients: createInitialCmfCoefficients(),
    baseCmf: null,
  }
}

const TRAVEL_MODE_KEYS = Object.fromEntries(
  ROAD_USER_TYPES.map(({ key }, index) => [index + 1, key]),
)
const SEVERITY_KEYS = Object.fromEntries(
  ['K', 'A', 'B', 'C', 'O'].map((code, index) => [code, INJURY_TYPES[index].key]),
)

function cmfCoefficientsFromApi(coefficients, fallbackValues) {
  const values = createInitialCmfCoefficients()
  if (!Array.isArray(coefficients)) {
    Object.entries(fallbackValues).forEach(([roadUserKey, injuries]) => {
      Object.entries(injuries).forEach(([injuryKey, value]) => {
        values[roadUserKey][injuryKey].b = String(value ?? 0)
      })
    })
    return values
  }

  coefficients.forEach((cell) => {
    const roadUserKey = TRAVEL_MODE_KEYS[cell.travel_mode]
    const injuryKey = SEVERITY_KEYS[cell.severity]
    if (!roadUserKey || !injuryKey) return
    values[roadUserKey][injuryKey] = {
      a: String(cell.coefficient_a ?? 0),
      b: String(cell.coefficient_b ?? 0),
      c: String(cell.coefficient_c ?? 0),
    }
  })
  return values
}

function coefficientRowsFromSetup(coefficients) {
  return ROAD_USER_TYPES.flatMap(({ key: roadUserKey }, travelModeIndex) => (
    INJURY_TYPES.map(({ key: injuryKey, code }) => {
      const cell = coefficients[roadUserKey][injuryKey]
      return {
        travel_mode: travelModeIndex + 1,
        severity: code,
        coefficient_a: 0,
        coefficient_b: Number(cell.b),
        coefficient_c: 0,
      }
    })
  ))
}

export function cmfFromApi(cmf) {
  const fallbackValues = { ...createInitialCmfValues(), ...(cmf.crash_modification_factors || {}) }
  return {
    title: cmf.title || cmf.cmf_group1 || '',
    description: cmf.description || cmf.descr_en_us || '',
    cmfGroup1: cmf.cmf_group1 || cmf.title || '',
    cmfGroup2: cmf.cmf_group2 || '',
    cmfGroup3: cmf.cmf_group3 || '',
    descrEnUs: cmf.descr_en_us || cmf.description || '',
    cmfMath: cmf.cmf_math || 'Q',
    modCode1: cmf.mod_code1 || cmf.roadway_feature || '',
    modCode2: cmf.mod_code2 || cmf.vehicle || '',
    modCode3: cmf.mod_code3 || cmf.manner_of_collision || '',
    modCode4: cmf.mod_code4 || cmf.contributing_circumstance || '',
    modCode5: cmf.mod_code5 || cmf.intoxication_status || '',
    age0004: Boolean(cmf.age_0004),
    age0509: Boolean(cmf.age_0509),
    age1014: Boolean(cmf.age_1014),
    age1519: Boolean(cmf.age_1519),
    age2064: Boolean(cmf.age_2064),
    age65up: Boolean(cmf.age_65up),
    roadwayFeature: cmf.roadway_feature || cmf.mod_code1 || 'RFALL',
    vehicle: cmf.vehicle || cmf.mod_code2 || 'VTALL',
    mannerOfCollision: cmf.manner_of_collision || cmf.mod_code3 || 'MCALL',
    contributingCircumstance: cmf.contributing_circumstance || cmf.mod_code4 || 'CCNON',
    intoxicationStatus: cmf.intoxication_status || cmf.mod_code5 || 'IXALL',
    ageGroup: cmf.age_groups || [],
    coefficients: cmfCoefficientsFromApi(cmf.coefficients, fallbackValues),
    baseCmf: cmf.base_cmf,
  }
}

export function cmfToApi(setup) {
  const ageValues = {
    age_0004: Boolean(setup.age0004 ?? setup.ageGroup.includes('0-4')),
    age_0509: Boolean(setup.age0509 ?? setup.ageGroup.includes('5-9')),
    age_1014: Boolean(setup.age1014 ?? setup.ageGroup.includes('10-14')),
    age_1519: Boolean(setup.age1519 ?? setup.ageGroup.includes('15-19')),
    age_2064: Boolean(setup.age2064 ?? setup.ageGroup.includes('20-64')),
    age_65up: Boolean(setup.age65up ?? setup.ageGroup.includes('65+')),
  }
  return {
    title: setup.title.trim(),
    description: setup.description,
    cmf_group1: setup.cmfGroup1.trim(),
    cmf_group2: setup.cmfGroup2.trim() || null,
    cmf_group3: setup.cmfGroup2.trim() ? (setup.cmfGroup3.trim() || null) : null,
    descr_en_us: setup.description,
    cmf_math: 'Q',
    mod_code1: setup.modCode1 || setup.roadwayFeature,
    mod_code2: setup.modCode2 || setup.vehicle,
    mod_code3: setup.modCode3 || setup.mannerOfCollision,
    mod_code4: setup.modCode4 || setup.contributingCircumstance,
    mod_code5: setup.modCode5 || setup.intoxicationStatus,
    ...ageValues,
    roadway_feature: setup.roadwayFeature,
    vehicle: setup.vehicle,
    manner_of_collision: setup.mannerOfCollision,
    contributing_circumstance: setup.contributingCircumstance,
    intoxication_status: setup.intoxicationStatus,
    age_groups: setup.ageGroup,
    coefficients: coefficientRowsFromSetup(setup.coefficients),
    ...(setup.baseCmf ? { base_cmf: setup.baseCmf } : {}),
  }
}
