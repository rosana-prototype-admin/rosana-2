import { useState } from 'react'
import { useAuth } from '../hooks/useAuth'
import { listMyGroups } from '../api/groups'
import { changeCurrentPassword, deactivateCurrentAccount, revokeAllSessions } from '../api/users'
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

function profileFromUser(user) {
  return {
    first_name: user?.first_name || '',
    last_name: user?.last_name || '',
    secondary_email: user?.secondary_email || '',
    company: user?.company || '',
  }
}

export default function SettingsPage() {
  const { user, updateUser, logout } = useAuth()
  const [profile, setProfile] = useState(() => profileFromUser(user))
  const [preferences, setPreferences] = useState(() => preferencesFromUser(user))
  const [isSavingProfile, setIsSavingProfile] = useState(false)
  const [isSavingPreferences, setIsSavingPreferences] = useState(false)
  const [passwords, setPasswords] = useState({ current_password: '', new_password: '', confirm_password: '' })
  const [isChangingPassword, setIsChangingPassword] = useState(false)
  const [passwordSaved, setPasswordSaved] = useState(false)
  const [isSigningOutAll, setIsSigningOutAll] = useState(false)
  const [isDeactivating, setIsDeactivating] = useState(false)
  const [deactivationPassword, setDeactivationPassword] = useState('')
  const [deactivationConfirmed, setDeactivationConfirmed] = useState(false)
  const [error, setError] = useState('')
  const [profileSaved, setProfileSaved] = useState(false)
  const [preferencesSaved, setPreferencesSaved] = useState(false)
  const [regionalMessage, setRegionalMessage] = useState('')
  const [isLoadingRegionalDefault, setIsLoadingRegionalDefault] = useState(false)

  function handleProfileChange(key) {
    return (event) => {
      setProfileSaved(false)
      setError('')
      setProfile((current) => ({ ...current, [key]: event.target.value }))
    }
  }

  function handleChange(key) {
    return (event) => {
      setPreferencesSaved(false)
      setRegionalMessage('')
      setPreferences((current) => ({ ...current, [key]: event.target.value }))
    }
  }

  function handlePasswordChange(key) {
    return (event) => {
      setPasswordSaved(false)
      setError('')
      setPasswords((current) => ({ ...current, [key]: event.target.value }))
    }
  }

  async function handleRegionalDefault() {
    setError('')
    setPreferencesSaved(false)
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
    setIsSavingPreferences(true)
    setError('')
    setPreferencesSaved(false)
    setRegionalMessage('')
    try {
      await updateUser(preferences)
      setPreferencesSaved(true)
    } catch (err) {
      const responseData = err.response?.data
      const firstError = responseData && typeof responseData === 'object'
        ? Object.values(responseData).flat()[0]
        : null
      setError(firstError || 'Unable to save your preferences. Please try again.')
    } finally {
      setIsSavingPreferences(false)
    }
  }

  async function handleProfileSubmit(event) {
    event.preventDefault()
    setIsSavingProfile(true)
    setError('')
    setProfileSaved(false)
    try {
      await updateUser(profile)
      setProfileSaved(true)
    } catch (err) {
      const responseData = err.response?.data
      const firstError = responseData && typeof responseData === 'object'
        ? Object.values(responseData).flat()[0]
        : null
      setError(firstError || 'Unable to save your profile. Please try again.')
    } finally {
      setIsSavingProfile(false)
    }
  }

  async function handlePasswordSubmit(event) {
    event.preventDefault()
    setIsChangingPassword(true)
    setError('')
    setPasswordSaved(false)
    try {
      await changeCurrentPassword(passwords)
      setPasswords({ current_password: '', new_password: '', confirm_password: '' })
      setPasswordSaved(true)
    } catch (err) {
      const responseData = err.response?.data
      const firstError = responseData && typeof responseData === 'object'
        ? Object.values(responseData).flat()[0]
        : null
      setError(firstError || 'Unable to change your password. Please try again.')
    } finally {
      setIsChangingPassword(false)
    }
  }

  async function handleSignOutAll() {
    if (!window.confirm('Sign out of Rosana on every device and browser?')) return
    setIsSigningOutAll(true)
    setError('')
    try {
      await revokeAllSessions()
      await logout()
    } catch (err) {
      const detail = err.response?.data?.detail
      setError(detail || 'Unable to sign out of all sessions. Please try again.')
    } finally {
      setIsSigningOutAll(false)
    }
  }

  async function handleDeactivate(event) {
    event.preventDefault()
    if (!window.confirm('Deactivate your account? You will be signed out and will need an administrator to reactivate it.')) return
    setIsDeactivating(true)
    setError('')
    try {
      await deactivateCurrentAccount({
        current_password: deactivationPassword,
        confirm_deactivation: deactivationConfirmed,
      })
      await logout()
    } catch (err) {
      const responseData = err.response?.data
      const firstError = responseData && typeof responseData === 'object'
        ? Object.values(responseData).flat()[0]
        : null
      setError(firstError || 'Unable to deactivate your account. Please try again.')
    } finally {
      setIsDeactivating(false)
    }
  }

  return (
    <main className="settings-page">
      <div className="settings-page-header">
        <h1>Settings</h1>
        <p>Manage your profile and the language, currency, and measurement units used in Rosana.</p>
      </div>

      <form className="settings-card" onSubmit={handleProfileSubmit}>
        <div className="settings-section-heading">
          <h2>Profile</h2>
          <p>Your primary email and username are managed as account identifiers.</p>
        </div>
        {error && <p className="form-error" role="alert">{error}</p>}
        {profileSaved && <p className="form-success" role="status">Profile saved.</p>}
        <div className="settings-profile-meta">
          <div><span>Username</span><strong>{user?.username || '—'}</strong></div>
          <div><span>Primary email</span><strong>{user?.email || '—'}</strong></div>
        </div>
        <div className="settings-grid">
          <label className="settings-field"><span>First name</span><input type="text" value={profile.first_name} onChange={handleProfileChange('first_name')} maxLength={150} disabled={isSavingProfile} /></label>
          <label className="settings-field"><span>Last name</span><input type="text" value={profile.last_name} onChange={handleProfileChange('last_name')} maxLength={150} disabled={isSavingProfile} /></label>
          <label className="settings-field"><span>Secondary email</span><input type="email" value={profile.secondary_email} onChange={handleProfileChange('secondary_email')} maxLength={254} disabled={isSavingProfile} /></label>
          <label className="settings-field"><span>Company or organization</span><input type="text" value={profile.company} onChange={handleProfileChange('company')} maxLength={255} disabled={isSavingProfile} /></label>
        </div>
        <div className="settings-actions">
          <button type="submit" className="settings-save" disabled={isSavingProfile}>
            {isSavingProfile ? 'Saving...' : 'Save Profile'}
          </button>
        </div>
      </form>

      <form className="settings-card" onSubmit={handlePasswordSubmit}>
        <div className="settings-section-heading">
          <h2>Change password</h2>
          <p>Enter your current password, then choose a new password.</p>
        </div>
        {error && <p className="form-error" role="alert">{error}</p>}
        {passwordSaved && <p className="form-success" role="status">Password changed successfully.</p>}
        <div className="settings-grid">
          <label className="settings-field"><span>Current password</span><input type="password" value={passwords.current_password} onChange={handlePasswordChange('current_password')} autoComplete="current-password" disabled={isChangingPassword} required /></label>
          <label className="settings-field"><span>New password</span><input type="password" value={passwords.new_password} onChange={handlePasswordChange('new_password')} autoComplete="new-password" disabled={isChangingPassword} required /></label>
          <label className="settings-field"><span>Confirm new password</span><input type="password" value={passwords.confirm_password} onChange={handlePasswordChange('confirm_password')} autoComplete="new-password" disabled={isChangingPassword} required /></label>
        </div>
        <div className="settings-actions">
          <button type="submit" className="settings-save" disabled={isChangingPassword}>
            {isChangingPassword ? 'Changing...' : 'Change Password'}
          </button>
        </div>
      </form>

      <form className="settings-card" onSubmit={handleSubmit}>
        <div className="settings-section-heading">
          <h2>Preferences</h2>
          <p>Choose the display and measurement conventions used by Rosana.</p>
        </div>
        {error && <p className="form-error" role="alert">{error}</p>}
        {preferencesSaved && <p className="form-success" role="status">Preferences saved.</p>}
        {regionalMessage && <p className="settings-regional-message" role="status">{regionalMessage}</p>}

        <div className="settings-grid">
          {PREFERENCE_FIELDS.map(({ key, label, options }) => (
            <label className="settings-field" key={key}>
              <span>{label}</span>
              <select value={preferences[key]} onChange={handleChange(key)} disabled={isSavingPreferences}>
                {options.map(([value, optionLabel]) => (
                  <option key={value} value={value}>{optionLabel}</option>
                ))}
              </select>
            </label>
          ))}
        </div>

        <div className="settings-actions">
          <button type="submit" className="settings-save" disabled={isSavingPreferences}>
            {isSavingPreferences ? 'Saving…' : 'Save Preferences'}
          </button>
          <button
            type="button"
            className="settings-regional-default"
            onClick={handleRegionalDefault}
            disabled={isSavingPreferences || isLoadingRegionalDefault}
          >
            {isLoadingRegionalDefault ? 'Loading regional default…' : 'Set to regional default'}
          </button>
        </div>
      </form>

      <section className="settings-card settings-danger-zone">
        <div className="settings-section-heading">
          <h2>Account security and lifecycle</h2>
          <p>Manage active sessions or deactivate this account.</p>
        </div>
        {error && <p className="form-error" role="alert">{error}</p>}
        <div className="settings-security-action">
          <div>
            <h3>Sign out of all sessions</h3>
            <p>Revoke every refresh session, including this browser. Short-lived access tokens may remain valid briefly.</p>
          </div>
          <button type="button" className="settings-secondary-action" onClick={handleSignOutAll} disabled={isSigningOutAll || isDeactivating}>
            {isSigningOutAll ? 'Signing out...' : 'Sign out everywhere'}
          </button>
        </div>
        <form className="settings-deactivate-form" onSubmit={handleDeactivate}>
          <div>
            <h3>Deactivate account</h3>
            <p>Deactivation prevents sign-in. You must transfer administration of any active groups first.</p>
          </div>
          <label className="settings-field"><span>Current password</span><input type="password" value={deactivationPassword} onChange={(event) => setDeactivationPassword(event.target.value)} autoComplete="current-password" disabled={isDeactivating || isSigningOutAll} required /></label>
          <label className="settings-confirmation"><input type="checkbox" checked={deactivationConfirmed} onChange={(event) => setDeactivationConfirmed(event.target.checked)} disabled={isDeactivating || isSigningOutAll} /> <span>I understand that my account will be deactivated.</span></label>
          <button type="submit" className="settings-danger-action" disabled={isDeactivating || isSigningOutAll || !deactivationConfirmed}>
            {isDeactivating ? 'Deactivating...' : 'Deactivate account'}
          </button>
        </form>
      </section>
    </main>
  )
}
