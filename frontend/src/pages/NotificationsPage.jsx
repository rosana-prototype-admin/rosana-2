import { useCallback, useEffect, useState } from 'react'
import { acceptNotification, declineNotification, listNotifications } from '../api/notifications'
import { formatDate } from '../utils/formatDate'
import '../styles/formFeedback.css'
import './NotificationsPage.css'

function userLabel(user) {
  return `${user.first_name} ${user.last_name}`.trim() || user.username
}

function describe(notification) {
  if (notification.notification_type === 'group_invite') {
    const roleSuffix = notification.roles.length > 0 ? ` as ${notification.roles.join(', ')}` : ''
    return `You've been invited to join "${notification.group.name}"${roleSuffix}.`
  }
  return `${userLabel(notification.user)} requested to join "${notification.group.name}".`
}

const STATUS_LABEL = {
  accepted: 'Accepted',
  declined: 'Declined',
}

export default function NotificationsPage() {
  const [notifications, setNotifications] = useState([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState('')
  const [busyId, setBusyId] = useState(null)

  const load = useCallback(async () => {
    try {
      const data = await listNotifications()
      setNotifications(data)
      setError('')
    } catch {
      setError('Unable to load notifications. Please try again.')
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    let cancelled = false
    async function run() {
      if (!cancelled) await load()
    }
    run()
    return () => {
      cancelled = true
    }
  }, [load])

  async function handleAccept(id) {
    setBusyId(id)
    setError('')
    try {
      await acceptNotification(id)
      await load()
    } catch (err) {
      setError(err.response?.data?.[0] || 'Unable to accept. Please try again.')
    } finally {
      setBusyId(null)
    }
  }

  async function handleDecline(id) {
    setBusyId(id)
    setError('')
    try {
      await declineNotification(id)
      await load()
    } catch {
      setError('Unable to decline. Please try again.')
    } finally {
      setBusyId(null)
    }
  }

  return (
    <main className="notifications-page">
      <h1>Notifications</h1>

      {error && (
        <p className="form-error" role="alert">
          {error}
        </p>
      )}

      {isLoading ? (
        <p className="text-sm">Loading notifications…</p>
      ) : notifications.length === 0 ? (
        <p className="text-sm">No notifications yet.</p>
      ) : (
        <ul className="notification-list">
          {notifications.map((notification) => (
            <li key={notification.id} className="notification-row">
              <div className="notification-body">
                <p>{describe(notification)}</p>
                <span className="notification-date text-sm">{formatDate(notification.created_at)}</span>
              </div>
              {notification.status === 'pending' ? (
                <div className="notification-actions">
                  <button
                    type="button"
                    onClick={() => handleAccept(notification.id)}
                    disabled={busyId === notification.id}
                  >
                    Accept
                  </button>
                  <button
                    type="button"
                    onClick={() => handleDecline(notification.id)}
                    disabled={busyId === notification.id}
                  >
                    Decline
                  </button>
                </div>
              ) : (
                <span className={`notification-status notification-status-${notification.status}`}>
                  {STATUS_LABEL[notification.status]}
                </span>
              )}
            </li>
          ))}
        </ul>
      )}
    </main>
  )
}
