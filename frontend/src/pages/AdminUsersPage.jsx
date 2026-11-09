import { useCallback, useEffect, useMemo, useState } from 'react'
import DataTable from '../components/DataTable'
import {
  listAdminUsers,
  getAdminSubscription,
  updateAdminSubscription,
  listAdminContracts,
  createAdminContract,
  resendAdminVerification,
  sendAdminPasswordReset,
  updateAdminUser,
} from '../api/admin'
import '../styles/formFeedback.css'
import './AdminUsersPage.css'

const SUBSCRIPTION_OPTIONS = [
  ['none', 'None'],
  ['basic', 'Basic'],
  ['premium', 'Premium'],
  ['admin', 'Admin'],
  ['crossroads', 'Crossroads'],
  ['borough', 'Borough'],
  ['ville', 'Ville'],
  ['shire', 'Shire'],
  ['provincia', 'Provincia'],
  ['comarca', 'Comarca'],
  ['metro', 'Metro'],
  ['commonwealth', 'Commonwealth'],
  ['republic', 'Republic'],
]

const SUBSCRIPTION_STATUS_OPTIONS = [
  ['trialing', 'Trialing'], ['active', 'Active'], ['paused', 'Paused'],
  ['past_due', 'Past due'], ['canceled', 'Canceled'], ['expired', 'Expired'],
]

const CONTRACT_STATUS_OPTIONS = [
  ['draft', 'Draft'], ['pending', 'Pending'], ['active', 'Active'],
  ['expired', 'Expired'], ['terminated', 'Terminated'],
]

function localDateTime(value) {
  return value ? new Date(value).toISOString().slice(0, 16) : ''
}

function apiDateTime(value) {
  return value ? new Date(value).toISOString() : null
}

function statusLabel(user) {
  if (!user.is_active) return 'Inactive'
  if (!user.email_verified) return 'Unverified'
  return 'Active'
}

function displayName(user) {
  return `${user.first_name || ''} ${user.last_name || ''}`.trim() || user.username
}

export default function AdminUsersPage() {
  const [users, setUsers] = useState([])
  const [selectedId, setSelectedId] = useState(null)
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('all')
  const [isLoading, setIsLoading] = useState(true)
  const [isSaving, setIsSaving] = useState(false)
  const [busyAction, setBusyAction] = useState('')
  const [error, setError] = useState('')
  const [saved, setSaved] = useState(false)
  const [subscription, setSubscription] = useState(null)
  const [contracts, setContracts] = useState([])
  const [isLoadingRecords, setIsLoadingRecords] = useState(false)

  const loadUsers = useCallback(async () => {
    setError('')
    try {
      const data = await listAdminUsers()
      setUsers(data)
      setSelectedId((current) => (data.some((user) => user.id === current) ? current : null))
    } catch {
      setError('Unable to load user accounts. Please try again.')
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    let cancelled = false
    async function run() {
      if (!cancelled) await loadUsers()
    }
    run()
    return () => {
      cancelled = true
    }
  }, [loadUsers])

  const filteredUsers = useMemo(() => {
    const query = search.trim().toLowerCase()
    return users.filter((user) => {
      const matchesSearch = !query || [user.username, user.email, user.first_name, user.last_name, user.company]
        .filter(Boolean)
        .some((value) => value.toLowerCase().includes(query))
      const matchesStatus = statusFilter === 'all'
        || (statusFilter === 'active' && user.is_active && user.email_verified)
        || (statusFilter === 'inactive' && !user.is_active)
        || (statusFilter === 'unverified' && user.is_active && !user.email_verified)
      return matchesSearch && matchesStatus
    })
  }, [search, statusFilter, users])

  const selectedUser = users.find((user) => user.id === selectedId) || null

  useEffect(() => {
    if (!selectedUser) return undefined
    let cancelled = false
    Promise.all([getAdminSubscription(selectedUser.id), listAdminContracts(selectedUser.id)])
      .then(([subscriptionData, contractData]) => {
        if (!cancelled) {
          setSubscription(subscriptionData)
          setContracts(contractData)
        }
      })
      .catch(() => {
        if (!cancelled) setError('Unable to load subscription and contract records.')
      })
      .finally(() => {
        if (!cancelled) setIsLoadingRecords(false)
      })
    return () => { cancelled = true }
  }, [selectedUser])

  async function handleSave(event) {
    event.preventDefault()
    if (!selectedUser) return
    setError('')
    setSaved(false)
    setIsSaving(true)
    const formData = new FormData(event.currentTarget)
    try {
      const updated = await updateAdminUser(selectedUser.id, {
        is_active: formData.get('is_active') === 'true',
        email_verified: formData.get('email_verified') === 'true',
        subscription_type: formData.get('subscription_type'),
        first_name: formData.get('first_name'),
        last_name: formData.get('last_name'),
        company: formData.get('company'),
        secondary_email: formData.get('secondary_email'),
      })
      setUsers((current) => current.map((user) => (user.id === updated.id ? updated : user)))
      setSaved(true)
    } catch (err) {
      const data = err.response?.data
      setError(data?.is_active?.[0] || data?.email_verified?.[0] || 'Unable to update this account.')
    } finally {
      setIsSaving(false)
    }
  }

  async function handleLifecycleAction(action) {
    if (!selectedUser) return
    setError('')
    setSaved(false)
    setBusyAction(action)
    try {
      const response = action === 'verification'
        ? await resendAdminVerification(selectedUser.id)
        : await sendAdminPasswordReset(selectedUser.id)
      setSaved(response.detail)
    } catch (err) {
      setError(err.response?.data?.detail || 'Unable to complete this account action.')
    } finally {
      setBusyAction('')
    }
  }

  async function handleSubscriptionSave(event) {
    event.preventDefault()
    if (!selectedUser || !subscription) return
    setError('')
    setSaved(false)
    const form = new FormData(event.currentTarget)
    try {
      const updated = await updateAdminSubscription(selectedUser.id, {
        plan_code: form.get('plan_code'),
        status: form.get('status'),
        starts_at: apiDateTime(form.get('starts_at')),
        ends_at: apiDateTime(form.get('ends_at')),
        external_reference: form.get('external_reference'),
        notes: form.get('notes'),
      })
      setSubscription(updated)
      setUsers((current) => current.map((user) => user.id === selectedUser.id
        ? { ...user, subscription_type: updated.plan_code } : user))
      setSaved('Subscription record updated.')
    } catch (err) {
      setError(err.response?.data?.detail || 'Unable to update the subscription record.')
    }
  }

  async function handleContractCreate(event) {
    event.preventDefault()
    if (!selectedUser) return
    setError('')
    const form = new FormData(event.currentTarget)
    try {
      const created = await createAdminContract(selectedUser.id, {
        title: form.get('title'),
        status: form.get('contract_status'),
        starts_at: apiDateTime(form.get('contract_starts_at')),
        ends_at: apiDateTime(form.get('contract_ends_at')),
        external_reference: form.get('contract_reference'),
        notes: form.get('contract_notes'),
      })
      setContracts((current) => [created, ...current])
      event.currentTarget.reset()
      setSaved('Contract record created.')
    } catch (err) {
      setError(err.response?.data?.detail || 'Unable to create the contract record.')
    }
  }

  const columns = [
    { key: 'username', header: 'Username' },
    { key: 'email', header: 'Email' },
    { key: 'name', header: 'Name', render: displayName, sortable: false },
    { key: 'status', header: 'Status', render: statusLabel, sortValue: statusLabel },
    { key: 'subscription_type', header: 'Subscription' },
  ]

  return (
    <main className="admin-users-page">
      <div className="admin-users-header">
        <div>
          <h1>Account management</h1>
          <p>Review account status and subscription assignments.</p>
        </div>
        <div className="admin-users-filters">
          <input
            type="search"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Search users"
            aria-label="Search users"
          />
          <select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)} aria-label="Filter by status">
            <option value="all">All statuses</option>
            <option value="active">Active</option>
            <option value="unverified">Unverified</option>
            <option value="inactive">Inactive</option>
          </select>
        </div>
      </div>

      {error && <p className="form-error" role="alert">{error}</p>}
      {saved && <p className="form-success" role="status">{typeof saved === 'string' ? saved : 'Account updated.'}</p>}

      {isLoading ? (
        <p className="text-sm">Loading accounts...</p>
      ) : (
        <DataTable
          columns={columns}
          rows={filteredUsers}
          getRowId={(user) => user.id}
          selectedId={selectedId}
          onSelectRow={(id) => { setSelectedId(id); setSaved(false); setIsLoadingRecords(true) }}
          emptyMessage="No accounts match these filters."
        />
      )}

      {selectedUser && (
        <form key={selectedUser.id} className="admin-user-detail" onSubmit={handleSave}>
          <h2>{displayName(selectedUser)}</h2>
          <dl className="admin-user-meta">
            <div><dt>Username</dt><dd>{selectedUser.username}</dd></div>
            <div><dt>Email</dt><dd>{selectedUser.email}</dd></div>
            <div><dt>Platform admin</dt><dd>{selectedUser.is_staff ? 'Yes' : 'No'}</dd></div>
          </dl>
          <div className="admin-user-fields">
            <label>
              <span>First name</span>
              <input name="first_name" type="text" defaultValue={selectedUser.first_name || ''} disabled={isSaving} />
            </label>
            <label>
              <span>Last name</span>
              <input name="last_name" type="text" defaultValue={selectedUser.last_name || ''} disabled={isSaving} />
            </label>
            <label>
              <span>Company</span>
              <input name="company" type="text" defaultValue={selectedUser.company || ''} disabled={isSaving} />
            </label>
            <label>
              <span>Secondary email</span>
              <input name="secondary_email" type="email" defaultValue={selectedUser.secondary_email || ''} disabled={isSaving} />
            </label>
            <label>
              <span>Account status</span>
              <select name="is_active" defaultValue={String(selectedUser.is_active)} disabled={isSaving}>
                <option value="true">Active</option>
                <option value="false">Inactive</option>
              </select>
            </label>
            <label>
              <span>Email verification</span>
              <select name="email_verified" defaultValue={String(selectedUser.email_verified)} disabled={isSaving}>
                <option value="true">Verified</option>
                <option value="false">Unverified</option>
              </select>
            </label>
            <label>
              <span>Subscription</span>
              <select name="subscription_type" defaultValue={selectedUser.subscription_type} disabled={isSaving}>
                {SUBSCRIPTION_OPTIONS.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
              </select>
            </label>
          </div>
          <button type="submit" className="admin-user-save" disabled={isSaving}>
            {isSaving ? 'Saving...' : 'Save account changes'}
          </button>
          <div className="admin-user-actions">
            <button
              type="button"
              onClick={() => handleLifecycleAction('verification')}
              disabled={isSaving || Boolean(busyAction) || selectedUser.email_verified}
            >
              {busyAction === 'verification' ? 'Sending...' : 'Resend verification email'}
            </button>
            <button
              type="button"
              onClick={() => handleLifecycleAction('password')}
              disabled={isSaving || Boolean(busyAction) || !selectedUser.is_active || !selectedUser.email_verified}
            >
              {busyAction === 'password' ? 'Sending...' : 'Send password reset email'}
            </button>
          </div>
        </form>
      )}

      {selectedUser && (
        <section className="admin-user-records">
          <h2>Subscription and contracts</h2>
          {isLoadingRecords ? <p className="text-sm">Loading records...</p> : (
            <>
              {subscription && (
                <form className="admin-record-form" onSubmit={handleSubscriptionSave}>
                  <h3>Current subscription record</h3>
                  <div className="admin-user-fields">
                    <label><span>Plan</span><select name="plan_code" defaultValue={subscription.plan_code}>{SUBSCRIPTION_OPTIONS.map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>
                    <label><span>Status</span><select name="status" defaultValue={subscription.status}>{SUBSCRIPTION_STATUS_OPTIONS.map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>
                    <label><span>Starts</span><input name="starts_at" type="datetime-local" defaultValue={localDateTime(subscription.starts_at)} /></label>
                    <label><span>Ends</span><input name="ends_at" type="datetime-local" defaultValue={localDateTime(subscription.ends_at)} /></label>
                    <label><span>External reference</span><input name="external_reference" defaultValue={subscription.external_reference || ''} /></label>
                    <label><span>Notes</span><input name="notes" defaultValue={subscription.notes || ''} /></label>
                  </div>
                  <button type="submit" className="admin-user-save">Save subscription</button>
                </form>
              )}
              <div className="admin-record-list">
                <h3>Contract records</h3>
                {contracts.length === 0 ? <p className="text-sm">No contracts recorded.</p> : contracts.map((contract) => (
                  <div className="admin-record-card" key={contract.id}>
                    <strong>{contract.title}</strong><span>{contract.status}</span>
                    <small>{contract.starts_at ? new Date(contract.starts_at).toLocaleDateString() : 'No start date'}</small>
                  </div>
                ))}
              </div>
              <form className="admin-record-form" onSubmit={handleContractCreate}>
                <h3>Add contract record</h3>
                <div className="admin-user-fields">
                  <label><span>Title</span><input name="title" required /></label>
                  <label><span>Status</span><select name="contract_status" defaultValue="draft">{CONTRACT_STATUS_OPTIONS.map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>
                  <label><span>Starts</span><input name="contract_starts_at" type="datetime-local" /></label>
                  <label><span>Ends</span><input name="contract_ends_at" type="datetime-local" /></label>
                  <label><span>External reference</span><input name="contract_reference" /></label>
                  <label><span>Notes</span><input name="contract_notes" /></label>
                </div>
                <button type="submit" className="admin-user-save">Add contract</button>
              </form>
            </>
          )}
        </section>
      )}
    </main>
  )
}
