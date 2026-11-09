import { useEffect, useState } from 'react'
import { NavLink } from 'react-router-dom'
import { listAdminAuditEvents } from '../api/admin'
import './AdminAuditPage.css'

export default function AdminAuditPage() {
  const [events, setEvents] = useState([])
  const [error, setError] = useState('')

  useEffect(() => {
    listAdminAuditEvents().then(setEvents).catch(() => setError('Unable to load the audit log.'))
  }, [])

  return (
    <main className="admin-audit-page">
      <nav className="admin-tabs" aria-label="Administration sections">
        <NavLink to="/admin/users">User accounts</NavLink>
        <NavLink to="/admin/subscriptions">Subscriptions</NavLink>
        <NavLink to="/admin/audit">Audit log</NavLink>
      </nav>
      <div><h1>Audit log</h1><p>Recent privileged changes made in the platform.</p></div>
      {error && <p className="form-error" role="alert">{error}</p>}
      {events.length === 0 && !error ? <p className="text-sm">No audit events recorded yet.</p> : (
        <div className="admin-audit-list">
          {events.map((event) => (
            <article className="admin-audit-event" key={event.id}>
              <div><strong>{event.action}</strong><span>{new Date(event.created_at).toLocaleString()}</span></div>
              <p>{event.entity_type} {event.entity_id} · By {event.actor_username || 'Unknown administrator'}{event.group_name ? ` · ${event.group_name}` : ''}</p>
              {(Object.keys(event.before).length > 0 || Object.keys(event.after).length > 0) && (
                <details><summary>View details</summary><pre>{JSON.stringify({ before: event.before, after: event.after }, null, 2)}</pre></details>
              )}
            </article>
          ))}
        </div>
      )}
    </main>
  )
}
