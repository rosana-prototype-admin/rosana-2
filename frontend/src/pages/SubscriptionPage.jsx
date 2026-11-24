import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { getMyEntitlements } from '../api/users'
import {
  assignOrganizationSeat,
  getOrganizationSubscription,
  listOrganizationSubscriptionUsers,
  releaseOrganizationSeat,
  updateOrganizationSubscription,
} from '../api/subscriptions'
import './SubscriptionPage.css'
import AccessStatusCard from '../components/AccessStatusCard'

const STATUS_OPTIONS = [
  ['trialing', 'Trialing'],
  ['active', 'Active'],
  ['paused', 'Paused'],
  ['past_due', 'Past due'],
  ['canceled', 'Canceled'],
  ['expired', 'Expired'],
]

function dateValue(value) {
  return value ? new Date(value).toISOString().slice(0, 16) : ''
}

function isoValue(value) {
  return value ? new Date(value).toISOString() : null
}

function label(value) {
  return (value || 'platform admin').replaceAll('_', ' ')
}

export default function SubscriptionPage() {
  const [organizations, setOrganizations] = useState([])
  const [selectedId, setSelectedId] = useState('')
  const [summary, setSummary] = useState(null)
  const [users, setUsers] = useState([])
  const [canManageSeats, setCanManageSeats] = useState(false)
  const [selectedSeatUserId, setSelectedSeatUserId] = useState('')
  const [isUpdatingSeat, setIsUpdatingSeat] = useState(false)
  const [form, setForm] = useState(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isSaving, setIsSaving] = useState(false)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')

  const selectedOrganization = useMemo(
    () => organizations.find((organization) => String(organization.group_id) === String(selectedId)),
    [organizations, selectedId],
  )
  const canChange = Boolean(summary?.can_change_subscription)

  useEffect(() => {
    let cancelled = false
    getMyEntitlements().then((records) => {
      if (cancelled) return
      const accessible = Array.from(
        records
          .filter((item) => (
            item.is_platform_admin ||
            item.rosana_role === 'financial_admin' || item.rosana_role === 'technical_admin'
          ))
          .reduce((organizationsById, item) => {
            const organizationId = item.organization_id || item.group_id
            if (!organizationsById.has(organizationId)) {
              organizationsById.set(organizationId, {
                ...item,
                group_id: organizationId,
                group_name: item.organization_name || item.group_name,
              })
            }
            return organizationsById
          }, new Map())
          .values(),
      )
      setOrganizations(accessible)
      if (accessible.length) setSelectedId(String(accessible[0].group_id))
    }).catch(() => {
      if (!cancelled) setError('Unable to load your organization subscriptions.')
    }).finally(() => {
      if (!cancelled) setIsLoading(false)
    })
    return () => { cancelled = true }
  }, [])

  useEffect(() => {
    if (!selectedId) return undefined
    let cancelled = false
    Promise.all([
      getOrganizationSubscription(selectedId),
      listOrganizationSubscriptionUsers(selectedId),
    ]).then(([subscriptionData, usersData]) => {
      if (cancelled) return
      setSummary(subscriptionData)
      setUsers(usersData.users || [])
      setCanManageSeats(Boolean(usersData.can_manage_seats))
      setSelectedSeatUserId('')
      const subscription = subscriptionData.subscription
      setForm({
        plan_id: subscription?.plan_id ? String(subscription.plan_id) : '',
        status: subscription?.status || 'active',
        seat_limit: subscription?.seat_limit ?? 1,
        starts_at: dateValue(subscription?.starts_at),
        ends_at: dateValue(subscription?.ends_at),
      })
    }).catch(() => {
      if (!cancelled) setError('Unable to load subscription details.')
    })
    return () => { cancelled = true }
  }, [selectedId])

  function updateField(event) {
    const { name, value } = event.target
    setForm((current) => ({ ...current, [name]: value }))
  }

  async function saveSubscription(event) {
    event.preventDefault()
    setError('')
    setMessage('')
    setIsSaving(true)
    try {
      const updated = await updateOrganizationSubscription(selectedId, {
        plan_id: form.plan_id ? Number(form.plan_id) : null,
        status: form.status,
        seat_limit: Number(form.seat_limit),
        starts_at: isoValue(form.starts_at),
        ends_at: isoValue(form.ends_at),
      })
      setSummary((current) => ({ ...current, subscription: updated }))
      setForm({
        plan_id: updated.plan_id ? String(updated.plan_id) : '',
        status: updated.status,
        seat_limit: updated.seat_limit,
        starts_at: dateValue(updated.starts_at),
        ends_at: dateValue(updated.ends_at),
      })
      setMessage('Subscription changes saved.')
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'Unable to save subscription changes.')
    } finally {
      setIsSaving(false)
    }
  }

  async function assignSeat() {
    if (!selectedSeatUserId) return
    setError('')
    setMessage('')
    setIsUpdatingSeat(true)
    try {
      const seat = await assignOrganizationSeat(selectedId, Number(selectedSeatUserId))
      const userId = seat.user?.id || Number(selectedSeatUserId)
      setUsers((current) => current.map((user) => (
        user.id === userId
          ? { ...user, seat_id: seat.id, seat_type: seat.seat_type }
          : user
      )))
      setSelectedSeatUserId('')
      setMessage('Technical seat assigned.')
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'Unable to assign the technical seat.')
    } finally {
      setIsUpdatingSeat(false)
    }
  }

  async function releaseSeat(user) {
    if (!user.seat_id) return
    setError('')
    setMessage('')
    setIsUpdatingSeat(true)
    try {
      await releaseOrganizationSeat(selectedId, user.seat_id)
      setUsers((current) => current.map((item) => (
        item.id === user.id ? { ...item, seat_id: null, seat_type: null } : item
      )))
      setMessage('Technical seat released.')
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'Unable to release the technical seat.')
    } finally {
      setIsUpdatingSeat(false)
    }
  }

  if (isLoading) return <main className="subscription-page"><p>Loading subscriptions...</p></main>

  return (
    <main className="subscription-page">
      <div className="subscription-page-heading">
        <div>
          <h1>Subscriptions</h1>
          <p>Review your organization&apos;s plan, seats, and subscription access.</p>
        </div>
        <Link to="/settings">Account settings</Link>
      </div>

      {error && <p className="form-error" role="alert">{error}</p>}
      {message && <p className="form-success" role="status">{message}</p>}

      {!organizations.length ? (
        <section className="subscription-card">
          <h2>No billing administration access</h2>
          <p>Only a Financial Admin or Technical Admin can view organization subscription details.</p>
        </section>
      ) : (
        <div className="subscription-layout">
          <nav className="subscription-organization-list" aria-label="Organizations">
            {organizations.map((organization) => (
              <button
                type="button"
                key={organization.group_id}
                className={String(organization.group_id) === String(selectedId) ? 'selected' : ''}
                onClick={() => {
                  setSummary(null)
                  setUsers([])
                  setCanManageSeats(false)
                  setSelectedSeatUserId('')
                  setError('')
                  setSelectedId(String(organization.group_id))
                }}
              >
                <strong>{organization.group_name}</strong>
                <span>{label(organization.rosana_role)}</span>
              </button>
            ))}
          </nav>

          <section className="subscription-content">
            <div className="subscription-card">
              <h2>{summary?.organization?.name || selectedOrganization?.organization_name}</h2>
              <p className="subscription-note">
                Payment processing is not configured. Changes on this page are simulated subscription records.
              </p>
              {summary?.subscription && (
                <div className="subscription-summary">
                  <div><span>Current plan</span><strong>{summary.subscription.plan_name || summary.subscription.plan_code}</strong></div>
                  <div><span>Status</span><strong>{label(summary.subscription.status)}</strong></div>
                  <div><span>Seats</span><strong>{summary.subscription.seat_limit}</strong></div>
                </div>
              )}
              {selectedOrganization && <AccessStatusCard entitlement={selectedOrganization} groupId={selectedId} compact />}

              {form && (
                <form onSubmit={saveSubscription} className="subscription-form">
                  <h3>{summary?.subscription ? 'Manage subscription' : 'Set up subscription'}</h3>
                  <label>
                    Plan
                    <select name="plan_id" value={form.plan_id} onChange={updateField} disabled={!canChange} required>
                      <option value="" disabled>Select a plan</option>
                      {(summary?.plans || []).map((plan) => <option key={plan.id} value={plan.id}>{plan.name}</option>)}
                    </select>
                  </label>
                  <label>
                    Status
                    <select name="status" value={form.status} onChange={updateField} disabled={!canChange}>
                      {STATUS_OPTIONS.map(([value, text]) => <option key={value} value={value}>{text}</option>)}
                    </select>
                  </label>
                  <label>
                    Technical seats
                    <input name="seat_limit" type="number" min="0" value={form.seat_limit} onChange={updateField} disabled={!canChange} />
                  </label>
                  <label>
                    Starts
                    <input name="starts_at" type="datetime-local" value={form.starts_at} onChange={updateField} disabled={!canChange} />
                  </label>
                  <label>
                    Ends
                    <input name="ends_at" type="datetime-local" value={form.ends_at} onChange={updateField} disabled={!canChange} />
                  </label>
                  {canChange ? <button type="submit" disabled={isSaving}>{isSaving ? 'Saving...' : 'Save subscription'}</button> : <p className="subscription-readonly">Technical Admins can view this information but cannot change billing details.</p>}
                </form>
              )}
            </div>

            <section className="subscription-card">
              <h2>Organization users and seats</h2>
              <p>Technical seats are assigned separately from group membership.</p>
              {canManageSeats && summary?.subscription && (
                <div className="seat-assignment-controls">
                  <label>
                    Assign a technical seat
                    <select value={selectedSeatUserId} onChange={(event) => setSelectedSeatUserId(event.target.value)} disabled={isUpdatingSeat}>
                      <option value="">Select a user without a seat</option>
                      {users.filter((user) => !user.seat_type).map((user) => (
                        <option key={user.id} value={user.id}>{user.username} ({user.email})</option>
                      ))}
                    </select>
                  </label>
                  <button
                    type="button"
                    onClick={assignSeat}
                    disabled={isUpdatingSeat || !selectedSeatUserId || users.filter((user) => user.seat_type).length >= summary.subscription.seat_limit}
                  >
                    {isUpdatingSeat ? 'Saving...' : 'Assign seat'}
                  </button>
                  {users.filter((user) => user.seat_type).length >= summary.subscription.seat_limit && <p className="subscription-readonly">All technical seats are assigned.</p>}
                </div>
              )}
              <div className="subscription-user-table-wrap">
                <table className="subscription-user-table">
                  <thead><tr><th>User</th><th>Email</th><th>Rosana Role</th><th>Seat</th><th>Access</th>{canManageSeats && <th>Actions</th>}</tr></thead>
                  <tbody>
                    {users.map((user) => (
                      <tr key={user.id}>
                        <td>{user.username}</td>
                        <td>{user.email}</td>
                        <td>{label(user.rosana_role || 'member')}</td>
                        <td>{user.seat_type ? label(user.seat_type) : 'No seat'}</td>
                        <td>{user.rosana_role === 'technical_user' && !user.seat_type ? 'Seat required for analysis' : user.rosana_role === 'commenter' ? 'Comment access' : 'Full technical access'}</td>
                        {canManageSeats && <td>{user.seat_id && <button type="button" onClick={() => releaseSeat(user)} disabled={isUpdatingSeat}>Release</button>}</td>}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          </section>
        </div>
      )}
    </main>
  )
}
