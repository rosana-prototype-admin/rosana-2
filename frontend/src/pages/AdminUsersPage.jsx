import { useCallback, useEffect, useMemo, useState } from 'react'
import DataTable from '../components/DataTable'
import { listAdminUsers, updateAdminUser } from '../api/admin'
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
  const [error, setError] = useState('')
  const [saved, setSaved] = useState(false)

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
      {saved && <p className="form-success" role="status">Account updated.</p>}

      {isLoading ? (
        <p className="text-sm">Loading accounts...</p>
      ) : (
        <DataTable
          columns={columns}
          rows={filteredUsers}
          getRowId={(user) => user.id}
          selectedId={selectedId}
          onSelectRow={(id) => { setSelectedId(id); setSaved(false) }}
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
        </form>
      )}
    </main>
  )
}
