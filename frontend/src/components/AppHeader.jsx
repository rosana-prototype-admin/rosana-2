import { useCallback, useEffect, useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { listNotifications } from '../api/notifications'
import { useAuth } from '../hooks/useAuth'
import './AppHeader.css'

const POLL_INTERVAL_MS = 60000

export default function AppHeader() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [pendingCount, setPendingCount] = useState(0)

  const refreshPendingCount = useCallback(async () => {
    try {
      const data = await listNotifications()
      setPendingCount(data.filter((notification) => notification.status === 'pending').length)
    } catch {
      // Non-critical: the badge just stays at its last known value.
    }
  }, [])

  useEffect(() => {
    let cancelled = false
    async function run() {
      if (!cancelled) await refreshPendingCount()
    }
    run()
    return () => {
      cancelled = true
    }
  }, [refreshPendingCount, location])

  useEffect(() => {
    const interval = setInterval(refreshPendingCount, POLL_INTERVAL_MS)
    return () => clearInterval(interval)
  }, [refreshPendingCount])

  async function handleLogout() {
    await logout()
    navigate('/login', { replace: true })
  }

  return (
    <header className="app-header">
      <Link to="/" className="app-header-brand">
        Rosana
      </Link>
      <nav className="app-header-nav">
        <Link to="/opportunities">Opportunities</Link>
        <Link to="/groups">Groups</Link>
        <Link to="/cmfs">Custom CMFs</Link>
        <Link to="/notifications" className="app-header-notifications">
          Notifications
          {pendingCount > 0 && <span className="notification-badge">{pendingCount}</span>}
        </Link>
        <button type="button" className="app-header-settings" onClick={() => navigate('/settings')}>
          Settings
        </button>
      </nav>
      <div className="app-header-user">
        <span className="text-sm">{user?.username}</span>
        <button type="button" className="app-header-logout" onClick={handleLogout}>
          Sign out
        </button>
      </div>
    </header>
  )
}
