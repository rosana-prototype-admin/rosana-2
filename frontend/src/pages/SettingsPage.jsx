import { useState } from 'react'
import { useAuth } from '../hooks/useAuth'
import { listMyGroups } from '../api/groups'
import '../styles/formFeedback.css'
import './SettingsPage.css'

const PREFERENCE_FIELDS = [
  {
    key: 'language',
    label: 'Language',
    options: [
      ['en-AU', 'English (Australia)'],
      ['en-CA', 'English (Canada)'],
      ['en-GB', 'English (UK)'],
      ['en-US', 'English (US)'],
      ['fr-CA', 'Français (Canada)'],
      ['es-419', 'Español (Latinoamericano)'],
    ],
  },
  {
    key: 'currency',
    label: 'Currency',
    options: [
      ['AUD', 'Australian Dollar ($)'],
      ['GBP', 'British Pound (£)'],
      ['CAD', 'Canadian Dollar ($)'],
      ['EUR', 'Euro (€)'],
      ['MXN', 'México Peso ($)'],
      ['USD', 'US Dollar ($)'],
    ],
  },
  { key: 'length_unit', label: 'Length', options: [['m', 'metres (m)'], ['ft', 'feet (ft)']] },
  { key: 'distance_unit', label: 'Distance', options: [['km', 'kilometres (km)'], ['mi', 'miles (mi)']] },
  {
    key: 'speed_unit',
    label: 'Speed',
    options: [['km/h', 'kilometres per hour (km/h)'], ['mph', 'miles per hour (mph)']],
  },
  {
    key: 'area_small_unit',
    label: 'Area-Small',
    options: [['m2', 'square metres (m²)'], ['sq ft', 'square feet (sq ft)']],
  },
  { key: 'area_large_unit', label: 'Area-Large', options: [['ha', 'hectares (ha)'], ['ac', 'acres (ac)']] },
  {
    key: 'volume_unit',
    label: 'Volume',
    options: [
      ['L', 'litres (L)'],
      ['gal (US)', 'gallons (US)'],
      ['gal (Imp)', 'gallons (Imperial)'],
    ],
  },
]

const DEFAULT_PREFERENCES = Object.fromEntries(PREFERENCE_FIELDS.map(({ key, options }) => [key, options[0][0]]))
DEFAULT_PREFERENCES.language = 'en-US'
DEFAULT_PREFERENCES.currency = 'USD'

const REGIONAL_DEFAULTS = {
  USA: {
    language: 'en-US',
    currency: 'USD',
    length_unit: 'ft',
    distance_unit: 'mi',
    speed_unit: 'mph',
    area_small_unit: 'sq ft',
    area_large_unit: 'ac',
    volume_unit: 'gal (US)',
  },
  CAN: {
    language: 'en-CA',
    currency: 'CAD',
    length_unit: 'm',
    distance_unit: 'km',
    speed_unit: 'km/h',
    area_small_unit: 'm2',
    area_large_unit: 'ha',
    volume_unit: 'L',
  },
}

function preferencesFromUser(user) {
  return PREFERENCE_FIELDS.reduce((preferences, { key }) => {
    preferences[key] = user?.[key] || DEFAULT_PREFERENCES[key]
    return preferences
  }, {})
}

export default function SettingsPage() {
  const { user, updateUser } = useAuth()
  const [preferences, setPreferences] = useState(() => preferencesFromUser(user))
  const [isSaving, setIsSaving] = useState(false)
  const [error, setError] = useState('')
  const [saved, setSaved] = useState(false)
  const [regionalMessage, setRegionalMessage] = useState('')
  const [isLoadingRegionalDefault, setIsLoadingRegionalDefault] = useState(false)

  function handleChange(key) {
    return (event) => {
      setSaved(false)
      setRegionalMessage('')
      setPreferences((current) => ({ ...current, [key]: event.target.value }))
    }
  }

  async function handleRegionalDefault() {
    setError('')
    setSaved(false)
    setRegionalMessage('')
    setIsLoadingRegionalDefault(true)
    try {
      const groups = await listMyGroups()
      const firstGroup = groups[0]
      const firstJcode = firstGroup?.jcodes?.[0]
      const countryCode = firstJcode?.country_code?.alpha_3
      const regionalPreferences = REGIONAL_DEFAULTS[countryCode]

      if (!firstJcode) {
        setRegionalMessage('No affiliated group Jcode is available for a regional default.')
        return
      }

      if (!regionalPreferences) {
        setRegionalMessage('Regional defaults are not available for this country yet.')
        return
      }

      setPreferences((current) => ({ ...current, ...regionalPreferences }))
      setRegionalMessage(
        `Regional defaults selected from ${firstGroup.name}. Click Save Preferences to apply them.`,
      )
    } catch {
      setRegionalMessage('Unable to load your group Jcodes. Please try again.')
    } finally {
      setIsLoadingRegionalDefault(false)
    }
  }

  async function handleSubmit(event) {
    event.preventDefault()
    setIsSaving(true)
    setError('')
    setSaved(false)
    setRegionalMessage('')
    try {
      await updateUser(preferences)
      setSaved(true)
    } catch (err) {
      const responseData = err.response?.data
      const firstError = responseData && typeof responseData === 'object'
        ? Object.values(responseData).flat()[0]
        : null
      setError(firstError || 'Unable to save your preferences. Please try again.')
    } finally {
      setIsSaving(false)
    }
  }

  return (
    <main className="settings-page">
      <div className="settings-page-header">
        <h1>Settings</h1>
        <p>Choose the language, currency, and measurement units used in Rosana.</p>
      </div>

      <form className="settings-card" onSubmit={handleSubmit}>
        {error && <p className="form-error" role="alert">{error}</p>}
        {saved && <p className="form-success" role="status">Preferences saved.</p>}
        {regionalMessage && <p className="settings-regional-message" role="status">{regionalMessage}</p>}

        <div className="settings-grid">
          {PREFERENCE_FIELDS.map(({ key, label, options }) => (
            <label className="settings-field" key={key}>
              <span>{label}</span>
              <select value={preferences[key]} onChange={handleChange(key)} disabled={isSaving}>
                {options.map(([value, optionLabel]) => (
                  <option key={value} value={value}>{optionLabel}</option>
                ))}
              </select>
            </label>
          ))}
        </div>

        <div className="settings-actions">
          <button type="submit" className="settings-save" disabled={isSaving}>
            {isSaving ? 'Saving…' : 'Save Preferences'}
          </button>
          <button
            type="button"
            className="settings-regional-default"
            onClick={handleRegionalDefault}
            disabled={isSaving || isLoadingRegionalDefault}
          >
            {isLoadingRegionalDefault ? 'Loading regional default…' : 'Set to regional default'}
          </button>
        </div>
      </form>
    </main>
  )
}
