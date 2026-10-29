import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { createCmf, getCmf, getCmfConfig, updateCmf } from '../api/cmfs'
import { listFocusAreas } from '../api/focusAreas'
import Tooltip from '../components/Tooltip'
import {
  CMF_FILTERS,
  CMF_LIMITS,
  AGE_GROUP_OPTIONS,
  INJURY_TYPES,
  ROAD_USER_TYPES,
  cmfFiltersFromConfig,
  cmfFromApi,
  cmfToApi,
  createInitialCmfSetup,
} from '../constants/cmfOptions'
import '../styles/editorForm.css'
import '../styles/formFeedback.css'
import './CustomCmfSetupPage.css'

const CMF_CAUTION = '⚠️ One of your entries looks unusual. CMF values are typically between .5 and 1.'
const AGE_VALUE_FIELDS = ['age0004', 'age0509', 'age1014', 'age1519', 'age2064', 'age65up']

function isUnusualCmf(value) {
  if (value === '') return false
  const numericValue = Number(value)
  return Number.isFinite(numericValue) && (numericValue < 0.5 || numericValue > 1)
}

export default function CustomCmfSetupPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const isEditing = Boolean(id)
  const [setup, setSetup] = useState(createInitialCmfSetup)
  const [isLoading, setIsLoading] = useState(true)
  const [isSaving, setIsSaving] = useState(false)
  const [error, setError] = useState('')
  const [savedMessage, setSavedMessage] = useState('')
  const [cmfLimits, setCmfLimits] = useState(CMF_LIMITS)
  const [cmfFilters, setCmfFilters] = useState(CMF_FILTERS)
  const [focusAreas, setFocusAreas] = useState([])

  useEffect(() => {
    let cancelled = false
    async function load() {
      setIsLoading(true)
      try {
        const [config, cmf, areas] = await Promise.all([
          getCmfConfig().catch(() => null),
          id ? getCmf(id) : Promise.resolve(null),
          listFocusAreas().catch(() => []),
        ])
        if (!cancelled) {
          if (config) {
            setCmfLimits({ lower: config.cmf_lower_limit, upper: config.cmf_upper_limit })
            setCmfFilters(cmfFiltersFromConfig(config))
          }
          if (cmf) setSetup(cmfFromApi(cmf))
          setFocusAreas(areas)
          setError('')
        }
      } catch (err) {
        if (!cancelled) {
          setError(err.response?.status === 404 ? 'CMF not found.' : 'Unable to load this CMF.')
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

  function handleTextChange(event) {
    const { name, value } = event.target
    setSetup((current) => ({ ...current, [name]: value }))
    setSavedMessage('')
  }

  function handleFilterChange(event) {
    const { name, value, multiple, selectedOptions } = event.target
    const nextValue = multiple ? [...selectedOptions].map((option) => option.value) : value
    setSetup((current) => ({ ...current, [name]: nextValue }))
    setSavedMessage('')
  }

  function handleFocusAreaChange(event) {
    const { name, value } = event.target
    setSetup((current) => ({
      ...current,
      [name]: value,
      ...(name === 'cmfGroup2' && !value ? { cmfGroup3: '' } : {}),
    }))
    setSavedMessage('')
  }

  function handleCmfChange(roadUserType, injuryType, value) {
    setSetup((current) => ({
      ...current,
      coefficients: {
        ...current.coefficients,
        [roadUserType]: {
          ...current.coefficients[roadUserType],
          [injuryType]: {
            ...current.coefficients[roadUserType][injuryType],
            b: value,
          },
        },
      },
    }))
    setSavedMessage('')
  }

  async function handleSubmit(event) {
    event.preventDefault()
    setError('')
    setSavedMessage('')
    setIsSaving(true)
    try {
      const saved = isEditing
        ? await updateCmf(id, cmfToApi(setup))
        : await createCmf(cmfToApi(setup))
      setSavedMessage('Custom CMF saved.')
      navigate(`/cmfs/${saved.id}/edit`, { replace: true })
    } catch (err) {
      const data = err.response?.data
      if (data && typeof data === 'object') {
        const firstError = Object.values(data).flat()[0]
        setError(firstError || 'Unable to save this custom CMF. Please try again.')
      } else {
        setError('Unable to save this custom CMF. Please try again.')
      }
    } finally {
      setIsSaving(false)
    }
  }

  if (isLoading) {
    return <main className="editor-page"><p className="text-sm">Loading CMF…</p></main>
  }

  if (error && isEditing && !setup.title) {
    return (
      <main className="editor-page">
        <button type="button" className="editor-back" onClick={() => navigate('/cmfs')}>← Back to Custom CMFs</button>
        <p className="form-error" role="alert">{error}</p>
      </main>
    )
  }

  const hasUnusualCmfValue = Object.values(setup.coefficients).some((row) =>
    Object.values(row).some((cell) => isUnusualCmf(cell.b)),
  )
  const hasInvalidCmfValue = Object.values(setup.coefficients).some((row) =>
    Object.values(row).some((cell) => {
      const value = cell.b
      if (value === '') return false
      const numericValue = Number(value)
      return !Number.isFinite(numericValue) || numericValue < cmfLimits.lower || numericValue > cmfLimits.upper
    }),
  )
  const focusAreasById = Object.fromEntries(focusAreas.map((area) => [area.id, area]))
  function focusAreaLabel(area) {
    const ancestors = []
    let current = area
    while (current) {
      ancestors.unshift(current.name)
      current = focusAreasById[current.parent]
    }
    return ancestors.join(' - ')
  }
  const focusAreaOptions = focusAreas.map((area) => ({
    value: area.name,
    label: focusAreaLabel(area),
  }))
  const savedFocusAreas = [setup.cmfGroup1, setup.cmfGroup2, setup.cmfGroup3]
  savedFocusAreas.forEach((value) => {
    if (value && !focusAreaOptions.some((option) => option.value === value)) {
      focusAreaOptions.push({ value, label: value })
    }
  })

  return (
    <main className="editor-page custom-cmf-page">
      <button type="button" className="editor-back" onClick={() => navigate('/cmfs')}>← Back to Custom CMFs</button>

      <details className="cmf-help">
        <summary>How do CMFs work? 🤔</summary>
        <div className="cmf-help-content">
          <p>A crash modification factor (CMF) is a number used to estimate the expected change in crash statistics after adding a safety improvement to a road.</p>
          <p>Most CMFs are between 0.50 and 1.00</p>
          <ul>
            <li>0 = Complete elimination of casualties</li>
            <li>0.5 = 50% reduction in casualties</li>
            <li>1 = No change</li>
            <li>2 = Doubling of casualties</li>
          </ul>
          <p>Casualty Reduction Factors (CRFs) can be converted CMFs using:</p>
          <p><strong>CMF = 1 - CRF</strong></p>
          <p>Example: 10% reduction in casualties → CMF = 0.9</p>
          <p><strong>NOTE:</strong> CMF array coefficients are bounded between {cmfLimits.lower} and {cmfLimits.upper}. Custom CMFs use the table value as quadratic coefficient b.</p>
        </div>
      </details>

      <form className="editor-card cmf-setup-card" onSubmit={handleSubmit}>
        <div className="editor-title-row">
          <h1>Custom CMF Setup</h1>
        </div>
        <p className="cmf-setup-intro">{isEditing ? 'Edit your custom crash modification factors.' : 'Create a reusable set of custom crash modification factors for analysis.'}</p>

        {error && <p className="form-error" role="alert">{error}</p>}
        {savedMessage && <p className="form-success text-sm" role="status">{savedMessage}</p>}

        <label className="editor-field">
          <span className="label">CMF title</span>
          <input name="title" type="text" value={setup.title} onChange={handleTextChange} maxLength={64} required />
        </label>

        <label className="editor-field">
          <span className="label">CMF Group 1</span>
          <select name="cmfGroup1" value={setup.cmfGroup1} onChange={handleFocusAreaChange} required>
            <option value="">Select a focus area…</option>
            {focusAreaOptions.map((option) => <option key={`${option.value}-${option.label}`} value={option.value}>{option.label}</option>)}
          </select>
        </label>

        <label className="editor-field">
          <span className="label">CMF Group 2</span>
          <select name="cmfGroup2" value={setup.cmfGroup2} onChange={handleFocusAreaChange}>
            <option value="">None</option>
            {focusAreaOptions.map((option) => <option key={`${option.value}-${option.label}`} value={option.value}>{option.label}</option>)}
          </select>
        </label>

        <label className="editor-field">
          <span className="label">CMF Group 3</span>
          <select name="cmfGroup3" value={setup.cmfGroup3} onChange={handleFocusAreaChange} disabled={!setup.cmfGroup2}>
            <option value="">None</option>
            {focusAreaOptions.map((option) => <option key={`${option.value}-${option.label}`} value={option.value}>{option.label}</option>)}
          </select>
        </label>

        <label className="editor-field">
          <span className="label">Description (American English)</span>
          <textarea name="description" rows={4} value={setup.description} onChange={handleTextChange} maxLength={1000} />
        </label>

        <div className="analysis-filter-grid">
          {cmfFilters.map(({ key, label, options }) => (
            <div className="editor-field" key={key}>
              <span className="label">{label}</span>
              {key === 'ageGroup' ? (
                <div className="analysis-age-values">
                  {AGE_GROUP_OPTIONS.map((option, index) => (
                    <label className="editor-field" key={option.value}>
                      <span className="label">{option.label}</span>
                      <input
                        name={AGE_VALUE_FIELDS[index]}
                        type="checkbox"
                        checked={Boolean(setup[AGE_VALUE_FIELDS[index]])}
                        onChange={(event) => setSetup((current) => ({
                          ...current,
                          [AGE_VALUE_FIELDS[index]]: event.target.checked,
                        }))}
                      />
                    </label>
                  ))}
                </div>
              ) : (
                <select name={key} value={setup[key]} onChange={handleFilterChange}>
                  {options.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
                </select>
              )}
            </div>
          ))}
        </div>

        <fieldset className="editor-field">
          <legend className="label">Crash modification factors</legend>
          <div className="analysis-cmf-table-wrapper">
            <table className="analysis-cmf-table">
              <thead>
                <tr className="analysis-cmf-emoji-row">
                  <th className="analysis-cmf-emoji-cell" aria-hidden="true" />
                  <th className="analysis-cmf-label-spacer" aria-hidden="true" />
                  {INJURY_TYPES.map(({ key, emoji }) => <th className="analysis-cmf-emoji-cell" key={key} aria-hidden="true">{emoji}</th>)}
                </tr>
                <tr>
                  <th className="analysis-cmf-label-spacer" aria-hidden="true" />
                  <th scope="col">
                    Road user type
                    <Tooltip label="Road user type information">The category of road user associated with each CMF row.</Tooltip>
                  </th>
                  {INJURY_TYPES.map(({ key, label, tooltip }) => (
                    <th scope="col" key={key}>
                      {label}
                      <Tooltip label={`${label} information`}>{tooltip}</Tooltip>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {ROAD_USER_TYPES.map(({ key: roadUserKey, label: roadUserLabel, emoji: roadUserEmoji, tooltip }) => (
                  <tr key={roadUserKey}>
                    <td className="analysis-cmf-emoji-cell" aria-hidden="true">{roadUserEmoji}</td>
                    <th scope="row">
                      {roadUserLabel}
                      <Tooltip label={`${roadUserLabel} information`}>{tooltip}</Tooltip>
                    </th>
                    {INJURY_TYPES.map(({ key: injuryKey, label: injuryLabel }) => (
                      <td key={injuryKey}>
                        <div className="analysis-cmf-coefficients">
                          <label>
                            <input
                              type="number"
                              value={setup.coefficients[roadUserKey][injuryKey].b}
                              onChange={(event) => handleCmfChange(roadUserKey, injuryKey, event.target.value)}
                              min={cmfLimits.lower}
                              max={cmfLimits.upper}
                              step="any"
                              aria-label={`${roadUserLabel} - ${injuryLabel} coefficient b`}
                              required
                            />
                          </label>
                        </div>
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {hasUnusualCmfValue && <p className="analysis-cmf-caution">{CMF_CAUTION}</p>}
          {hasInvalidCmfValue && (
            <p className="analysis-cmf-error" role="alert">
              🚨 CMF values must be between {cmfLimits.lower} and {cmfLimits.upper}.
            </p>
          )}
        </fieldset>

        <div className="cmf-form-actions">
          <button type="submit" className="editor-save" disabled={isSaving || hasInvalidCmfValue || !setup.cmfGroup1}>
            {isSaving ? 'Saving…' : isEditing ? 'Save Changes' : 'Save Custom CMF'}
          </button>
          <button type="button" className="cmf-secondary-button" onClick={() => navigate('/cmfs')} disabled={isSaving}>Cancel</button>
        </div>
      </form>
    </main>
  )
}
