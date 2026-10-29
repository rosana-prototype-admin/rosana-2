import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { getSite, listAvailableJcodes, updateSite } from '../api/sites'
import { getProject } from '../api/projects'
import { getOpportunity } from '../api/opportunities'
import { listCrashConversionTables } from '../api/crashdata'
import { getCmfConfig } from '../api/cmfs'
import { listStrategies, updateStrategy } from '../api/strategies'
import StrategyAccordionTable from '../components/StrategyAccordionTable'
import StrategyDetailsDialog from '../components/StrategyDetailsDialog'
import SiteLocationMap from '../components/SiteLocationMap'
import Tooltip from '../components/Tooltip'
import { CMF_FILTERS, INJURY_TYPES, ROAD_USER_TYPES, cmfFiltersFromConfig } from '../constants/cmfOptions'
import { useAuth } from '../hooks/useAuth'
import { formatDate } from '../utils/formatDate'
import { ROAD_CLASS_OPTIONS } from '../utils/roadClasses'
import { formatAnnualOutcome } from '../utils/annualOutcomeDisplay'
import '../styles/editorForm.css'
import '../styles/formFeedback.css'
import '../styles/actionToolbar.css'

const DEFAULT_ROADWAY_FEATURE = 'RFALL'
const DEFAULT_ROADWAY_FEATURE_OPTIONS = CMF_FILTERS.find(({ key }) => key === 'roadwayFeature')?.options ?? []
const SEGMENT_LENGTH_UNITS = ['meters', 'feet', 'kilometers', 'miles']

function normalizeRoadwayFeature(value) {
  return DEFAULT_ROADWAY_FEATURE_OPTIONS.some((option) => option.value === value)
    ? value
    : DEFAULT_ROADWAY_FEATURE
}

function emptyCasualtyArray() {
  return Array(ROAD_USER_TYPES.length * INJURY_TYPES.length).fill(0)
}

function normalizeCasualtyArray(values) {
  const normalized = emptyCasualtyArray()
  if (!Array.isArray(values)) return normalized
  values.slice(0, normalized.length).forEach((value, index) => {
    normalized[index] = value ?? 0
  })
  return normalized
}

const CONVERSION_FACTOR_FIELDS = {
  fatalities: 'deaths_per_crash',
  seriousInjuries: 'serious_injuries_per_crash',
  minorInjuries: 'minor_injuries_per_crash',
  possibleInjuries: 'possible_injuries_per_crash',
  propertyDamage: 'vehicles_involved_per_crash',
}

function calculateCrashAnnualRates(values, conversionRows, timeInYears) {
  if (!conversionRows || timeInYears === 0) return emptyCasualtyArray().map(() => '')

  const factorsByOutput = Object.fromEntries(INJURY_TYPES.map(({ key: outputKey }) => {
    const factorField = CONVERSION_FACTOR_FIELDS[outputKey]
    return [
      outputKey,
      Object.fromEntries(conversionRows.map((row) => [row.crash_severity, Number(row[factorField])])),
    ]
  }))

  return Array.from({ length: emptyCasualtyArray().length }, (_, outputIndex) => {
    const roadUserIndex = Math.floor(outputIndex / INJURY_TYPES.length)
    const outputKey = INJURY_TYPES[outputIndex % INJURY_TYPES.length].key
    const factorsBySeverity = factorsByOutput[outputKey]
    const inputRowStart = roadUserIndex * INJURY_TYPES.length

    // The five input cells in this road-user row map left-to-right to the
    // five values in the selected conversion-table column.
    const convertedValue = INJURY_TYPES.reduce((total, { code }, severityIndex) => {
      const inputValue = values[inputRowStart + severityIndex]
      return total + (inputValue === '' ? 0 : Number(inputValue) * (factorsBySeverity[code] ?? 0))
    }, 0)

    return convertedValue / timeInYears
  })
}

function calculateSelectedStrategyRates(annualRates, strategies) {
  const selectedStrategies = strategies.filter((strategy) => strategy.selected)
  const strategiesWithCmfs = selectedStrategies.filter((strategy) => strategy.intervention_type?.cmf)
  const strategiesWithoutCmfs = selectedStrategies.filter((strategy) => !strategy.intervention_type?.cmf)

  const projectedRates = annualRates.map((value, index) => {
    if (value === '' || value === null || value === undefined) return ''

    const roadUserIndex = Math.floor(index / INJURY_TYPES.length)
    const severityIndex = index % INJURY_TYPES.length
    const factor = strategiesWithCmfs.reduce((product, strategy) => {
      const cell = strategy.intervention_type.cmf.coefficient_array?.[roadUserIndex]?.[severityIndex]
      return product * Number(cell?.[1] ?? 1)
    }, 1)
    return Number(value) * factor
  })

  return {
    projectedRates,
    selectedStrategies,
    strategiesWithCmfs,
    strategiesWithoutCmfs,
  }
}

function numericValue(value) {
  const number = Number(value)
  return Number.isFinite(number) ? number : 0
}

function totalForValues(values, readOnly, formatValue, outcome = 'combined') {
  const total = values.reduce((sum, value) => sum + numericValue(value), 0)
  return readOnly ? formatValue(total, outcome) : total
}

function outcomeForColumn(columnKey) {
  if (columnKey === 'fatalities') return 'fatalities'
  if (columnKey === 'propertyDamage') return 'vehicles'
  return 'injuries'
}

function columnHeaderLabel(column, dataType) {
  if (dataType === 'crash') return `${column.label} [Crashes]`
  return `${column.label} [${column.code === 'O' ? 'Vehicles' : 'Persons'}]`
}

function CasualtyTable({ values, onChange, canWrite, label, columns = INJURY_TYPES, readOnly = false, dataType = 'casualty-damage', formatValue = (value) => value }) {
  const columnTotals = columns.map((_, columnIndex) => totalForValues(
    ROAD_USER_TYPES.map((__, roadUserIndex) => values[roadUserIndex * columns.length + columnIndex]),
    readOnly,
    formatValue,
    outcomeForColumn(columns[columnIndex].key),
  ))
  const grandTotal = totalForValues(values, readOnly, formatValue)
  const numericColumnWidth = `${(76 / (columns.length + 1)).toFixed(4)}%`

  return (
    <fieldset className="editor-field site-casualty-fieldset">
      <legend className="label">{label}</legend>
      <div className="analysis-cmf-table-wrapper">
        <table className="analysis-cmf-table">
          <colgroup>
            <col className="analysis-cmf-emoji-column" style={{ width: '4%' }} />
            <col className="analysis-cmf-label-column" style={{ width: '20%' }} />
            {columns.map(({ key }) => (
              <col className="analysis-cmf-numeric-column" style={{ width: numericColumnWidth }} key={key} />
            ))}
            <col className="analysis-cmf-numeric-column" style={{ width: numericColumnWidth }} />
          </colgroup>
          <thead>
            <tr className="analysis-cmf-emoji-row">
              <th className="analysis-cmf-emoji-cell" aria-hidden="true" />
              <th className="analysis-cmf-label-spacer" aria-hidden="true" />
              {columns.map(({ key, emoji }) => <th className="analysis-cmf-emoji-cell" key={key} aria-hidden="true">{emoji}</th>)}
              <th className="analysis-cmf-total-heading" aria-hidden="true" />
            </tr>
            <tr>
              <th className="analysis-cmf-label-spacer" aria-hidden="true" />
              <th scope="col">
                Road user type
                <Tooltip label="Road user type information">The category of road user associated with each CMF row.</Tooltip>
              </th>
              {columns.map((column) => (
                <th scope="col" key={column.key}>
                  {columnHeaderLabel(column, dataType)}
                  <Tooltip label={`${column.label} information`}>{column.tooltip}</Tooltip>
                </th>
              ))}
              <th scope="col">Total</th>
            </tr>
          </thead>
          <tbody>
            {ROAD_USER_TYPES.map(({ key: roadUserKey, label: roadUserLabel, emoji: roadUserEmoji, tooltip }, roadUserIndex) => (
              <tr key={roadUserKey}>
                <td className="analysis-cmf-emoji-cell" aria-hidden="true">{roadUserEmoji}</td>
                <th scope="row">
                  {roadUserLabel}
                  <Tooltip label={`${roadUserLabel} information`}>{tooltip}</Tooltip>
                </th>
                {columns.map(({ key: injuryKey, label: injuryLabel }, injuryIndex) => {
                  const valueIndex = roadUserIndex * columns.length + injuryIndex
                  return (
                    <td className="analysis-cmf-numeric-cell" key={injuryKey}>
                      {readOnly ? (
                        <output className="analysis-cmf-value" aria-label={`${roadUserLabel} - ${injuryLabel}`}>
                          {formatValue(values[valueIndex], outcomeForColumn(injuryKey))}
                        </output>
                      ) : (
                        <input
                          type="number"
                          min="0"
                          step="1"
                          value={values[valueIndex]}
                          onChange={onChange ? (event) => onChange(valueIndex, event.target.value) : undefined}
                          disabled={!canWrite}
                          aria-label={`${roadUserLabel} - ${injuryLabel}`}
                          required
                        />
                      )}
                    </td>
                  )
                })}
                <td className="analysis-cmf-numeric-cell">
                  <output className="analysis-cmf-value" aria-label={`${roadUserLabel} - total`}>
                    {totalForValues(
                      columns.map((__, injuryIndex) => values[roadUserIndex * columns.length + injuryIndex]),
                      readOnly,
                      formatValue,
                    )}
                  </output>
                </td>
              </tr>
            ))}
          </tbody>
          <tfoot>
            <tr className="analysis-cmf-total-row">
              <td className="analysis-cmf-emoji-cell" aria-hidden="true" />
              <th scope="row">Total</th>
              {columnTotals.map((total, index) => (
                <td className="analysis-cmf-numeric-cell" key={columns[index].key}>
                  <output className="analysis-cmf-value" aria-label={`${columns[index].label} total`}>
                    {total}
                  </output>
                </td>
              ))}
              <td className="analysis-cmf-numeric-cell">
                <output className="analysis-cmf-value" aria-label="Grand total">
                  {grandTotal}
                </output>
              </td>
            </tr>
          </tfoot>
        </table>
      </div>
    </fieldset>
  )
}

export default function SiteEditorPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { user } = useAuth()

  const [site, setSite] = useState(null)
  const [opportunity, setOpportunity] = useState(null)
  const [isLoading, setIsLoading] = useState(true)
  const [loadError, setLoadError] = useState('')

  const [title, setTitle] = useState('')
  const [comment, setComment] = useState('')
  const [roadwayFeature, setRoadwayFeature] = useState(DEFAULT_ROADWAY_FEATURE)
  const [roadwayFeatureOptions, setRoadwayFeatureOptions] = useState(DEFAULT_ROADWAY_FEATURE_OPTIONS)
  const [roadClass, setRoadClass] = useState('')
  const [segmentLength, setSegmentLength] = useState('')
  const [segmentLengthUnit, setSegmentLengthUnit] = useState('meters')
  const [gpsX, setGpsX] = useState('')
  const [gpsY, setGpsY] = useState('')
  const [gpsZ, setGpsZ] = useState(0)
  const [casualtyObs, setCasualtyObs] = useState(emptyCasualtyArray())
  const [casualtyDataType, setCasualtyDataType] = useState('casualty-damage')
  const [conversionTable, setConversionTable] = useState(null)
  const [conversionError, setConversionError] = useState('')
  const [casualtyTimeYears, setCasualtyTimeYears] = useState(1)
  const [casualtyTimeMonths, setCasualtyTimeMonths] = useState(1)
  const [jcode, setJcode] = useState(null)
  const [jcodeCatalog, setJcodeCatalog] = useState([])
  const [isLoadingJcodes, setIsLoadingJcodes] = useState(false)
  const [jcodeError, setJcodeError] = useState('')
  const [selectedJcodeId, setSelectedJcodeId] = useState('')
  const [isUpdatingJcode, setIsUpdatingJcode] = useState(false)
  const [baseline, setBaseline] = useState(null)
  const [saveError, setSaveError] = useState('')
  const [isSaving, setIsSaving] = useState(false)
  const [savedAt, setSavedAt] = useState(null)

  const [strategies, setStrategies] = useState([])
  const [isLoadingStrategies, setIsLoadingStrategies] = useState(false)
  const [strategyError, setStrategyError] = useState('')
  const [selectedStrategyId, setSelectedStrategyId] = useState(null)
  const [isStrategyDialogOpen, setIsStrategyDialogOpen] = useState(false)
  const [isSubmittingStrategy, setIsSubmittingStrategy] = useState(false)
  const [strategyDialogError, setStrategyDialogError] = useState('')

  const loadStrategies = useCallback(async () => {
    setIsLoadingStrategies(true)
    try {
      const data = await listStrategies(id)
      setStrategies(data)
      setStrategyError('')
    } catch {
      setStrategyError('Unable to load strategies. Please try again.')
    } finally {
      setIsLoadingStrategies(false)
    }
  }, [id])

  useEffect(() => {
    let cancelled = false

    async function load() {
      setIsLoading(true)
      setLoadError('')
      try {
        const data = await getSite(id)
        if (cancelled) return
        setSite(data)
        setTitle(data.title)
        setComment(data.comment)
        const normalizedRoadwayFeature = normalizeRoadwayFeature(data.site_type)
        setRoadwayFeature(normalizedRoadwayFeature)
        setRoadClass(data.road_class)
        setSegmentLength(data.segment_length ?? '')
        setSegmentLengthUnit(data.segment_length_unit ?? 'meters')
        setGpsX(data.gps_x ?? '')
        setGpsY(data.gps_y ?? '')
        setGpsZ(data.gps_z)
        const normalizedData = {
          ...data,
          site_type: normalizedRoadwayFeature,
          segment_length: data.segment_length ?? null,
          segment_length_unit: data.segment_length_unit ?? 'meters',
          casualty_obs: normalizeCasualtyArray(data.casualty_obs),
          casualty_data_type: data.casualty_data_type ?? 'casualty-damage',
          casualty_time_years: data.casualty_time_years ?? 1,
          casualty_time_months: data.casualty_time_months ?? 1,
        }
        setCasualtyObs(normalizedData.casualty_obs)
        setCasualtyDataType(normalizedData.casualty_data_type)
        setCasualtyTimeYears(normalizedData.casualty_time_years)
        setCasualtyTimeMonths(normalizedData.casualty_time_months)
        setJcode(data.jcode ?? null)
        setSelectedJcodeId(data.jcode?.id ?? '')
        setBaseline(normalizedData)
        // Needed for the write-permission check below, same chain
        // ProjectEditorPage walks to reach the opportunity manager/delegates.
        const projectData = await getProject(data.project)
        if (cancelled) return
        const opportunityData = await getOpportunity(projectData.opportunity)
        if (cancelled) return
        setOpportunity(opportunityData)
      } catch (err) {
        if (!cancelled) {
          setLoadError(
            err.response?.status === 404 ? 'Site not found.' : 'Unable to load this site. You may not have access to it.',
          )
        }
      } finally {
        if (!cancelled) setIsLoading(false)
      }
    }

    load()
    return () => {
      cancelled = true
    }
  }, [id])

  useEffect(() => {
    let cancelled = false
    getCmfConfig()
      .then((config) => {
        if (cancelled) return
        const roadwayFeatureFilter = cmfFiltersFromConfig(config).find(({ key }) => key === 'roadwayFeature')
        if (roadwayFeatureFilter?.options?.length) setRoadwayFeatureOptions(roadwayFeatureFilter.options)
      })
      .catch(() => {
        // Keep the bundled options as a fallback if the configuration endpoint is unavailable.
      })
    return () => {
      cancelled = true
    }
  }, [])

  const loadJcodeCatalog = useCallback(async () => {
    setIsLoadingJcodes(true)
    setJcodeError('')
    try {
      setJcodeCatalog(await listAvailableJcodes(id))
    } catch {
      setJcodeError('Unable to load Jcodes. Please try again.')
    } finally {
      setIsLoadingJcodes(false)
    }
  }, [id])

  useEffect(() => {
    let cancelled = false
    async function run() {
      if (!cancelled) await loadJcodeCatalog()
    }
    run()
    return () => {
      cancelled = true
    }
  }, [loadJcodeCatalog])

  useEffect(() => {
    let cancelled = false
    async function run() {
      if (!cancelled) await loadStrategies()
    }
    run()
    return () => {
      cancelled = true
    }
  }, [loadStrategies])

  useEffect(() => {
    let cancelled = false

    async function loadConversionTable() {
      try {
        const tables = await listCrashConversionTables()
        const defaultTable = tables.find((table) => (
          table.dataset_key === 'crash-to-casualty' &&
          table.country_code === 'US' &&
          table.geography_level === 'national' &&
          table.is_default
        ))
        if (!defaultTable) throw new Error('No default crash conversion table is available.')
        if (!cancelled) {
          setConversionTable(defaultTable)
          setConversionError('')
        }
      } catch {
        if (!cancelled) setConversionError('Unable to load the crash-to-casualty conversion table.')
      }
    }

    loadConversionTable()
    return () => {
      cancelled = true
    }
  }, [])

  const canWrite =
    opportunity && user && (opportunity.manager === user.id || opportunity.delegates?.includes(user.id))

  const numberOrNull = (value) => (value === '' ? null : Number(value))

  const isDirty =
    baseline &&
    (title !== baseline.title ||
      comment !== baseline.comment ||
      roadwayFeature !== baseline.site_type ||
      roadClass !== baseline.road_class ||
      numberOrNull(segmentLength) !== baseline.segment_length ||
      segmentLengthUnit !== baseline.segment_length_unit ||
      numberOrNull(gpsX) !== baseline.gps_x ||
      numberOrNull(gpsY) !== baseline.gps_y ||
      Number(gpsZ) !== Number(baseline.gps_z) ||
      JSON.stringify(casualtyObs) !== JSON.stringify(baseline.casualty_obs) ||
      casualtyDataType !== baseline.casualty_data_type ||
      Number(casualtyTimeYears) !== Number(baseline.casualty_time_years) ||
      Number(casualtyTimeMonths) !== Number(baseline.casualty_time_months))

  function handleBack() {
    if (isDirty && !window.confirm('You have unsaved changes. Leave without saving?')) {
      return
    }
    navigate(`/projects/${site.project}`)
  }

  function handleCasualtyChange(setter, index, value) {
    setter((current) => current.map((item, i) => (i === index ? (value === '' ? '' : Number(value)) : item)))
  }

  async function handleSave(event) {
    event.preventDefault()
    setSaveError('')

    if (!title.trim()) {
      setSaveError('Title is required.')
      return
    }

    setIsSaving(true)
    try {
      const updated = await updateSite(id, {
        title: title.trim(),
        comment,
        site_type: roadwayFeature,
        road_class: roadClass,
        segment_length: numberOrNull(segmentLength),
        segment_length_unit: segmentLengthUnit,
        gps_x: numberOrNull(gpsX),
        gps_y: numberOrNull(gpsY),
        gps_z: Number(gpsZ) || 0,
        casualty_data_type: casualtyDataType,
        casualty_obs: casualtyObs,
        casualty_time_years: Number(casualtyTimeYears),
        casualty_time_months: Number(casualtyTimeMonths),
      })
      setSite(updated)
      setTitle(updated.title)
      setComment(updated.comment)
      const normalizedRoadwayFeature = normalizeRoadwayFeature(updated.site_type)
      setRoadwayFeature(normalizedRoadwayFeature)
      setRoadClass(updated.road_class)
      setSegmentLength(updated.segment_length ?? '')
      setSegmentLengthUnit(updated.segment_length_unit ?? 'meters')
      setGpsX(updated.gps_x ?? '')
      setGpsY(updated.gps_y ?? '')
      setGpsZ(updated.gps_z)
      setCasualtyObs(normalizeCasualtyArray(updated.casualty_obs))
      setCasualtyDataType(updated.casualty_data_type ?? 'casualty-damage')
      setCasualtyTimeYears(updated.casualty_time_years)
      setCasualtyTimeMonths(updated.casualty_time_months)
      setJcode(updated.jcode ?? null)
      setSelectedJcodeId(updated.jcode?.id ?? '')
      setBaseline({
        ...updated,
        site_type: normalizedRoadwayFeature,
        segment_length: updated.segment_length ?? null,
        segment_length_unit: updated.segment_length_unit ?? 'meters',
        casualty_data_type: updated.casualty_data_type ?? 'casualty-damage',
        casualty_obs: normalizeCasualtyArray(updated.casualty_obs),
      })
      setSavedAt(new Date())
    } catch (err) {
      const data = err.response?.data
      if (data && typeof data === 'object') {
        const firstError = Object.values(data).flat()[0]
        setSaveError(firstError || 'Unable to save changes. Please try again.')
      } else {
        setSaveError('Unable to save changes. Please try again.')
      }
    } finally {
      setIsSaving(false)
    }
  }

  async function handleUpdateJcode() {
    setJcodeError('')
    setIsUpdatingJcode(true)
    try {
      const updated = await updateSite(id, { jcode_id: selectedJcodeId || null })
      setSite(updated)
      setJcode(updated.jcode ?? null)
      setSelectedJcodeId(updated.jcode?.id ?? '')
    } catch (err) {
      const data = err.response?.data
      const firstError = data && typeof data === 'object' ? Object.values(data).flat()[0] : null
      setJcodeError(firstError || 'Unable to update the site Jcode. Please try again.')
    } finally {
      setIsUpdatingJcode(false)
    }
  }

  useEffect(() => {
    if (!isDirty) return undefined
    function handleBeforeUnload(event) {
      event.preventDefault()
      event.returnValue = ''
    }
    window.addEventListener('beforeunload', handleBeforeUnload)
    return () => window.removeEventListener('beforeunload', handleBeforeUnload)
  }, [isDirty])

  const casualtyTimeInYears = Number(casualtyTimeYears) + Number(casualtyTimeMonths) / 12
  const annualCasualtyObs = casualtyDataType === 'crash'
    ? calculateCrashAnnualRates(casualtyObs, conversionTable?.rows, casualtyTimeInYears)
    : casualtyObs.map((value) => (
      value === '' || casualtyTimeInYears === 0 ? '' : Number(value) / casualtyTimeInYears
    ))
  const strategyProjection = useMemo(
    () => calculateSelectedStrategyRates(annualCasualtyObs, strategies),
    [annualCasualtyObs, strategies],
  )
  const selectedStrategy = strategies.find((strategy) => strategy.id === selectedStrategyId) || null

  async function handleToggleSelected(strategy) {
    setStrategyError('')
    try {
      const updated = await updateStrategy(strategy.id, { selected: !strategy.selected })
      setStrategies((current) => current.map((row) => (row.id === updated.id ? updated : row)))
    } catch {
      setStrategyError('Unable to update this strategy. Please try again.')
    }
  }

  async function handleSubmitStrategyDetails(details) {
    if (!selectedStrategy) return
    setStrategyDialogError('')
    setIsSubmittingStrategy(true)
    try {
      const updated = await updateStrategy(selectedStrategy.id, { details })
      setStrategies((current) => current.map((row) => (row.id === updated.id ? updated : row)))
      setIsStrategyDialogOpen(false)
    } catch {
      setStrategyDialogError('Unable to save this strategy. Please try again.')
    } finally {
      setIsSubmittingStrategy(false)
    }
  }

  if (isLoading) {
    return (
      <main className="editor-page">
        <p className="text-sm">Loading site…</p>
      </main>
    )
  }

  if (loadError) {
    return (
      <main className="editor-page">
        <p className="form-error" role="alert">
          {loadError}
        </p>
        <Link to="/opportunities">← Back to Opportunities</Link>
      </main>
    )
  }

  return (
    <main className="editor-page">
      <button type="button" className="editor-back" onClick={handleBack}>
        ← Back to Project
      </button>

      <form className="editor-card site-editor-card" onSubmit={handleSave}>
        <div className="editor-title-row">
          <h1>Site Editor</h1>
          {!canWrite && <span className="editor-readonly-badge">Read-only</span>}
        </div>

        {saveError && (
          <p className="form-error" role="alert">
            {saveError}
          </p>
        )}
        {savedAt && !isDirty && !saveError && <p className="form-success text-sm">Saved.</p>}

        <label className="editor-field">
          <span className="label">Title</span>
          <input
            type="text"
            value={title}
            onChange={(event) => setTitle(event.target.value)}
            maxLength={100}
            disabled={!canWrite}
            required
          />
        </label>

        <label className="editor-field">
          <span className="label">Comment</span>
          <textarea
            rows={3}
            value={comment}
            onChange={(event) => setComment(event.target.value)}
            maxLength={1000}
            disabled={!canWrite}
          />
        </label>

        <div className="editor-focus-area-row">
          <label className="editor-field">
            <span className="label">Roadway feature type</span>
            <select
              value={roadwayFeature}
              onChange={(event) => setRoadwayFeature(event.target.value)}
              disabled={!canWrite}
            >
              {roadwayFeatureOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>

          <label className="editor-field">
            <span className="label">Road class</span>
            <select
              value={roadClass}
              onChange={(event) => setRoadClass(event.target.value)}
              disabled={!canWrite}
            >
              <option value="">Select a road class…</option>
              {ROAD_CLASS_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.value} — {option.label}
                </option>
              ))}
            </select>
          </label>
        </div>

        <label className="editor-field site-segment-length-field">
          <span className="label">Segment length</span>
          <span className="site-segment-length-control">
            <input
              type="number"
              min="0"
              step="any"
              value={segmentLength}
              onChange={(event) => setSegmentLength(event.target.value)}
              disabled={!canWrite}
            />
            <select
              value={segmentLengthUnit}
              onChange={(event) => setSegmentLengthUnit(event.target.value)}
              disabled={!canWrite}
            >
              {SEGMENT_LENGTH_UNITS.map((unit) => <option key={unit} value={unit}>{unit}</option>)}
            </select>
          </span>
        </label>

        <div className="editor-focus-area-row">
          <label className="editor-field">
            <span className="label">GPS latitude (y)</span>
            <input
              type="number"
              step="any"
              value={gpsY}
              onChange={(event) => setGpsY(event.target.value)}
              disabled={!canWrite}
            />
          </label>
          <label className="editor-field">
            <span className="label">GPS longitude (x)</span>
            <input
              type="number"
              step="any"
              value={gpsX}
              onChange={(event) => setGpsX(event.target.value)}
              disabled={!canWrite}
            />
          </label>
          <label className="editor-field">
            <span className="label">GPS elevation (z)</span>
            <input
              type="number"
              step="any"
              value={gpsZ}
              onChange={(event) => setGpsZ(event.target.value)}
              disabled={!canWrite}
            />
          </label>
        </div>

        <SiteLocationMap
          gpsX={gpsX}
          gpsY={gpsY}
          canWrite={canWrite}
          onPositionChange={(latitude, longitude) => {
            setGpsX(String(longitude))
            setGpsY(String(latitude))
          }}
        />

        <h2 className="site-casualty-section-heading">Input your historical crash data</h2>

        <div className="site-time-bracket">
          <div className="editor-field-label-row">
            <span className="label">Time bracket</span>
            <Tooltip label="Time bracket information">Select the scope of time that your data encompasses.</Tooltip>
          </div>
          <div className="editor-focus-area-row">
            <label className="editor-field">
              <span className="label">Years</span>
              <select value={casualtyTimeYears} onChange={(event) => setCasualtyTimeYears(event.target.value)} disabled={!canWrite}>
                {Array.from({ length: 26 }, (_, index) => index).map((year) => <option key={year} value={year}>{year}</option>)}
              </select>
            </label>
            <label className="editor-field">
              <span className="label">Months</span>
              <select value={casualtyTimeMonths} onChange={(event) => setCasualtyTimeMonths(event.target.value)} disabled={!canWrite}>
                {Array.from({ length: 12 }, (_, index) => index).map((month) => <option key={month} value={month}>{month}</option>)}
              </select>
            </label>
          </div>
        </div>

        <div className="site-casualty-data-row">
          <label className="editor-field">
            <span className="label">My data are</span>
            <select value={casualtyDataType} onChange={(event) => setCasualtyDataType(event.target.value)} disabled={!canWrite}>
              <option value="casualty-damage">casualty/damage counts</option>
              <option value="crash">crash counts</option>
            </select>
          </label>
          <Tooltip label="Observed casualty data information">
            Select <strong>casualty/damage counts</strong> if your data represent the number of people killed/injured and the number of vehicles damaged. Select <strong>crash counts</strong> if your data represent the number of crashes.
          </Tooltip>
        </div>
        {conversionError && casualtyDataType === 'crash' && (
          <p className="form-error" role="alert">{conversionError}</p>
        )}
        <CasualtyTable
          values={casualtyObs}
          onChange={(index, value) => handleCasualtyChange(setCasualtyObs, index, value)}
          canWrite={canWrite}
          label={casualtyDataType === 'crash' ? 'Observed crash counts' : 'Observed casualty counts'}
          dataType={casualtyDataType}
        />

        <section className="site-casualty-rates" aria-labelledby="calculated-annual-rates-heading">
          <CasualtyTable
            values={annualCasualtyObs}
            canWrite={false}
            readOnly
            label="Calculated annual casualty/damage rates"
            dataType="casualty-damage"
            formatValue={formatAnnualOutcome}
          />
        </section>

        {strategyProjection.selectedStrategies.length > 0 && (
          <section className="site-casualty-rates" aria-labelledby="projected-annual-rates-heading">
            <CasualtyTable
              values={strategyProjection.projectedRates}
              canWrite={false}
              readOnly
              label="Projected annual casualty/damage rates with selected strategies"
              dataType="casualty-damage"
              formatValue={formatAnnualOutcome}
            />
            {strategyProjection.strategiesWithoutCmfs.length > 0 && (
              <p className="text-sm">
                {strategyProjection.strategiesWithoutCmfs.length} selected strategy(ies) do not have an associated CMF and were not applied.
              </p>
            )}
          </section>
        )}

        <dl className="editor-meta">
          <div>
            <dt className="label">Created</dt>
            <dd>{formatDate(site.created_at)}</dd>
          </div>
          <div>
            <dt className="label">Last modified</dt>
            <dd>{formatDate(site.modified_at)}</dd>
          </div>
        </dl>

        {canWrite && (
          <button type="submit" className="editor-save" disabled={!isDirty || isSaving}>
            {isSaving ? 'Saving…' : 'Save'}
          </button>
        )}
      </form>

      <div className="action-toolbar">
        <button type="button" onClick={() => navigate('analysis')}>
          Construct Analysis
        </button>
      </div>

      <section className="editor-section">
        <div className="editor-section-header">
          <h2>Jcodes</h2>
        </div>

        {jcodeError && (
          <p className="form-error" role="alert">
            {jcodeError}
          </p>
        )}

        {canWrite ? (
          <div className="jcode-selection">
            <label className="editor-field">
              <span className="label">Jcode</span>
              <select
                value={selectedJcodeId}
                onChange={(event) => setSelectedJcodeId(event.target.value)}
                disabled={isLoadingJcodes || isUpdatingJcode}
              >
                <option value="">No Jcode selected</option>
                {jcodeCatalog.map((availableJcode) => (
                  <option key={availableJcode.id} value={availableJcode.id}>
                    {availableJcode.id} — {availableJcode.place_name_short}, {availableJcode.state}
                  </option>
                ))}
              </select>
            </label>
            <button
              type="button"
              className="editor-save"
              onClick={handleUpdateJcode}
              disabled={isLoadingJcodes || isUpdatingJcode || selectedJcodeId === (jcode?.id ?? '')}
            >
              {isUpdatingJcode ? 'Saving…' : 'Save Jcode'}
            </button>
          </div>
        ) : null}

        {isLoadingJcodes ? (
          <p className="text-sm">Loading available Jcodes…</p>
        ) : jcode ? (
          <p className="text-sm">
            Assigned Jcode: {jcode.id} — {jcode.place_name_short}, {jcode.state}
          </p>
        ) : (
          <p className="text-sm">No Jcode is assigned to this site.</p>
        )}
      </section>

      <section className="editor-section">
        <div className="editor-section-header">
          <h2>Strategies</h2>
        </div>
        <p className="text-sm">
          Strategies compatible with this site&rsquo;s focus area are listed automatically. Check the ones that
          apply; select a row and click Edit to add details.
        </p>

        {strategyError && (
          <p className="form-error" role="alert">
            {strategyError}
          </p>
        )}

        {canWrite && (
          <div className="action-toolbar">
            <button
              type="button"
              onClick={() => {
                setStrategyDialogError('')
                setIsStrategyDialogOpen(true)
              }}
              disabled={!selectedStrategy}
            >
              Edit
            </button>
          </div>
        )}

        {isLoadingStrategies ? (
          <p className="text-sm">Loading strategies…</p>
        ) : (
          <StrategyAccordionTable
            strategies={strategies}
            selectedId={selectedStrategyId}
            onSelectRow={setSelectedStrategyId}
            onToggleSelected={handleToggleSelected}
            emptyMessage="No strategies are compatible with this site's focus area."
            readOnly={!canWrite}
          />
        )}
      </section>

      <StrategyDetailsDialog
        isOpen={isStrategyDialogOpen}
        strategy={selectedStrategy}
        isBusy={isSubmittingStrategy}
        error={strategyDialogError}
        onSubmit={handleSubmitStrategyDetails}
        onCancel={() => setIsStrategyDialogOpen(false)}
      />
    </main>
  )
}
