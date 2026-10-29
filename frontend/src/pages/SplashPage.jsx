import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { listMyGroups } from '../api/groups'
import { useAuth } from '../hooks/useAuth'
import './SplashPage.css'

const SUBSCRIPTION_LABELS = {
  none: 'None',
  basic: 'Basic',
  premium: 'Premium',
  admin: 'Admin',
  crossroads: 'Crossroads',
  borough: 'Borough',
  ville: 'Ville',
  shire: 'Shire',
  provincia: 'Provincia',
  comarca: 'Comarca',
  metro: 'Metro',
  commonwealth: 'Commonwealth',
  republic: 'Republic',
}

export default function SplashPage() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const [groups, setGroups] = useState([])

  useEffect(() => {
    let cancelled = false
    listMyGroups()
      .then((data) => {
        if (!cancelled) setGroups(data)
      })
      .catch(() => {
        if (!cancelled) setGroups([])
      })
    return () => {
      cancelled = true
    }
  }, [])

  if (!user) {
    return null
  }

  const fullName = [user.first_name, user.last_name].filter(Boolean).join(' ')
  const jurisdictions = useMemo(() => {
    const seen = new Set()
    return groups.flatMap((group) => group.jcodes || []).filter((jcode) => {
      if (seen.has(jcode.id)) return false
      seen.add(jcode.id)
      return true
    })
  }, [groups])

  return (
    <main className="splash-page">
      <div className="splash-card">
        <div className="splash-header">
          <div>
            <p className="overline splash-eyebrow">Welcome back</p>
            <h1>{fullName || user.username}</h1>
          </div>
        </div>

        <dl className="splash-details">
          <div>
            <dt className="label">Username</dt>
            <dd>{user.username}</dd>
          </div>
          <div>
            <dt className="label">Email</dt>
            <dd>{user.email}</dd>
          </div>
          {user.secondary_email && (
            <div>
              <dt className="label">Secondary email</dt>
              <dd>{user.secondary_email}</dd>
            </div>
          )}
          {user.company && (
            <div>
              <dt className="label">Company</dt>
              <dd>{user.company}</dd>
            </div>
          )}
          <div>
            <dt className="label">Subscription</dt>
            <dd>{SUBSCRIPTION_LABELS[user.subscription_type] ?? user.subscription_type}</dd>
          </div>
          <div>
            <dt className="label">Jurisdictions</dt>
            <dd>
              {jurisdictions.length
                ? jurisdictions.map((jcode) => jcode.place_name_short).join(', ')
                : 'None assigned'}
            </dd>
          </div>
        </dl>

        <button type="button" className="splash-primary" onClick={() => navigate('/opportunities')}>
          Go to Opportunities
        </button>
      </div>
    </main>
  )
}
