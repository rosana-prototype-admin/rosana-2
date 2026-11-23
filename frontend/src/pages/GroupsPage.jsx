import { useCallback, useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  deleteGroup,
  listGroupMembers,
  listMyGroups,
  requestToJoinGroup,
  restoreGroup,
  searchGroups,
  updateGroupJcodes,
} from '../api/groups'
import { listJcodes } from '../api/jcodes'
import { getOrganizationSubscription } from '../api/subscriptions'
import ConfirmDialog from '../components/ConfirmDialog'
import DataTable from '../components/DataTable'
import JcodeSelectionTable from '../components/JcodeSelectionTable'
import { useAuth } from '../hooks/useAuth'
import '../styles/formFeedback.css'
import '../styles/actionToolbar.css'
import './GroupsPage.css'

function displayUserName(user) {
  return `${user?.first_name || ''} ${user?.last_name || ''}`.trim() || user?.username || '—'
}

function toggleId(ids, id) {
  return ids.includes(id) ? ids.filter((value) => value !== id) : [...ids, id]
}

export default function GroupsPage() {
  const navigate = useNavigate()
  const { user } = useAuth()
  const [groups, setGroups] = useState([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState('')
  const [search, setSearch] = useState('')
  const [showArchived, setShowArchived] = useState(false)
  const [selectedId, setSelectedId] = useState(null)
  const [members, setMembers] = useState([])
  const [groupSubscription, setGroupSubscription] = useState(null)
  const [isLoadingMembers, setIsLoadingMembers] = useState(false)
  const [isCreating, setIsCreating] = useState(false)
  const [isGroupFinderOpen, setIsGroupFinderOpen] = useState(false)
  const [groupFinderQuery, setGroupFinderQuery] = useState('')
  const [groupFinderResults, setGroupFinderResults] = useState([])
  const [isSearchingGroups, setIsSearchingGroups] = useState(false)
  const [groupFinderError, setGroupFinderError] = useState('')
  const [joinRequestIds, setJoinRequestIds] = useState(new Set())
  const [joiningGroupId, setJoiningGroupId] = useState(null)
  const [isDeleting, setIsDeleting] = useState(false)
  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false)
  const [selectedJcodeIds, setSelectedJcodeIds] = useState([])
  const [isSavingJcodes, setIsSavingJcodes] = useState(false)
  const [isJcodePickerOpen, setIsJcodePickerOpen] = useState(false)
  const [jcodeCatalog, setJcodeCatalog] = useState([])
  const [isLoadingJcodes, setIsLoadingJcodes] = useState(false)
  const [pickerSearch, setPickerSearch] = useState('')
  const [pickerState, setPickerState] = useState('')
  const [pickerCounty, setPickerCounty] = useState('')
  const [pickerSelectedIds, setPickerSelectedIds] = useState([])

  const loadGroups = useCallback(async () => {
    try {
      const data = await listMyGroups(showArchived)
      setGroups(data)
      setSelectedId((current) => (data.some((group) => group.id === current) ? current : null))
      setError('')
    } catch {
      setError('Unable to load your groups. Please try again.')
    } finally {
      setIsLoading(false)
    }
  }, [showArchived])

  useEffect(() => {
    let cancelled = false
    async function run() {
      if (!cancelled) await loadGroups()
    }
    run()
    return () => {
      cancelled = true
    }
  }, [loadGroups])

  const selectedGroup = groups.find((group) => group.id === selectedId) || null
  const isSelectedGroupAdmin = !selectedGroup?.archived_at && (selectedGroup?.user_role === 'admin' || user?.is_staff)
  const assignedJcodes = useMemo(() => selectedGroup?.jcodes || [], [selectedGroup])

  useEffect(() => {
    let cancelled = false
    async function run() {
      setSelectedJcodeIds([])
      setMembers([])
      if (!selectedGroup || !isSelectedGroupAdmin) return

      setIsLoadingMembers(true)
      try {
        const data = await listGroupMembers(selectedGroup.id)
        if (!cancelled) setMembers(data)
      } catch {
        if (!cancelled) setError('Unable to load the group members. Please try again.')
      } finally {
        if (!cancelled) setIsLoadingMembers(false)
      }
    }
    run()

    return () => {
      cancelled = true
    }
  }, [selectedGroup, isSelectedGroupAdmin])

  useEffect(() => {
    let cancelled = false
    if (!selectedGroup) {
      return undefined
    }
    getOrganizationSubscription(selectedGroup.id).then((data) => {
      if (!cancelled) setGroupSubscription({ ...data, requestedGroupId: selectedGroup.id })
    }).catch(() => {
      // Subscription visibility is supplementary to the group page. A user
      // without organization membership should still be able to use the page.
      if (!cancelled) setGroupSubscription({ requestedGroupId: selectedGroup.id, subscription: null })
    })
    return () => {
      cancelled = true
    }
  }, [selectedGroup])

  const subscriptionForSelectedGroup = groupSubscription?.requestedGroupId === selectedGroup?.id
    ? groupSubscription
    : null

  const filteredGroups = useMemo(() => {
    const query = search.trim().toLowerCase()
    if (!query) return groups
    return groups.filter((group) => (
      group.name.toLowerCase().includes(query)
      || displayUserName(group.admin).toLowerCase().includes(query)
      || (group.user_role || '').toLowerCase().includes(query)
    ))
  }, [groups, search])

  const states = useMemo(
    () => [...new Set(jcodeCatalog.map((jcode) => jcode.state).filter(Boolean))].sort(),
    [jcodeCatalog],
  )

  const counties = useMemo(() => [...new Set(
    jcodeCatalog
      .filter((jcode) => !pickerState || jcode.state === pickerState)
      .map((jcode) => jcode.county)
      .filter(Boolean),
  )].sort(), [jcodeCatalog, pickerState])

  const availableJcodes = useMemo(() => {
    const assignedIds = new Set(assignedJcodes.map((jcode) => jcode.id))
    const query = pickerSearch.trim().toLowerCase()
    return jcodeCatalog.filter((jcode) => {
      if (assignedIds.has(jcode.id)) return false
      if (pickerState && jcode.state !== pickerState) return false
      if (pickerCounty && jcode.county !== pickerCounty) return false
      if (!query) return true
      return [jcode.id, jcode.state, jcode.county, jcode.place_name_short, jcode.place_name_long]
        .filter(Boolean)
        .some((value) => value.toLowerCase().includes(query))
    })
  }, [assignedJcodes, jcodeCatalog, pickerCounty, pickerSearch, pickerState])

  async function handleNew() {
    setError('')
    setIsCreating(true)
    navigate('/groups/new')
    setIsCreating(false)
  }

  async function handleFindGroups(event) {
    event.preventDefault()
    setGroupFinderError('')
    setIsSearchingGroups(true)
    try {
      setGroupFinderResults(await searchGroups(groupFinderQuery.trim()))
    } catch {
      setGroupFinderError('Unable to search for groups. Please try again.')
    } finally {
      setIsSearchingGroups(false)
    }
  }

  async function handleRequestToJoin(groupId) {
    setGroupFinderError('')
    setJoiningGroupId(groupId)
    try {
      await requestToJoinGroup(groupId)
      setJoinRequestIds((current) => new Set([...current, groupId]))
    } catch (err) {
      const detail = err.response?.data?.non_field_errors?.[0] || err.response?.data?.detail
      setGroupFinderError(detail || 'Unable to request to join this group. Please try again.')
    } finally {
      setJoiningGroupId(null)
    }
  }

  async function handleConfirmDelete() {
    if (!selectedGroup) return
    setError('')
    setIsDeleting(true)
    try {
      await deleteGroup(selectedGroup.id)
      setSelectedId(null)
      await loadGroups()
    } catch {
      setError('Unable to delete the group. Please try again.')
    } finally {
      setIsDeleting(false)
      setIsDeleteDialogOpen(false)
    }
  }

  async function handleRestore() {
    if (!selectedGroup) return
    setError('')
    try {
      await restoreGroup(selectedGroup.id)
      await loadGroups()
    } catch {
      setError('Unable to restore the group. Please try again.')
    }
  }

  async function saveJcodes(jcodeIds) {
    if (!selectedGroup) return
    setError('')
    setIsSavingJcodes(true)
    try {
      const updatedGroup = await updateGroupJcodes(selectedGroup.id, jcodeIds)
      setGroups((current) => current.map((group) => (
        group.id === updatedGroup.id ? updatedGroup : group
      )))
      setSelectedJcodeIds([])
      setPickerSelectedIds([])
      setIsJcodePickerOpen(false)
    } catch {
      setError('Unable to update the group Jcodes. Please try again.')
    } finally {
      setIsSavingJcodes(false)
    }
  }

  async function handleRemoveSelectedJcodes() {
    const selected = new Set(selectedJcodeIds)
    await saveJcodes(assignedJcodes.filter((jcode) => !selected.has(jcode.id)).map((jcode) => jcode.id))
  }

  async function openJcodePicker() {
    setError('')
    setPickerSearch('')
    setPickerState('')
    setPickerCounty('')
    setPickerSelectedIds([])
    setIsJcodePickerOpen(true)
    if (jcodeCatalog.length > 0) return
    setIsLoadingJcodes(true)
    try {
      setJcodeCatalog(await listJcodes())
    } catch {
      setError('Unable to load Jcodes. Please try again.')
    } finally {
      setIsLoadingJcodes(false)
    }
  }

  const groupColumns = [
    { key: 'name', header: 'Group name' },
    { key: 'admin', header: 'Admin', sortValue: (group) => displayUserName(group.admin), render: (group) => displayUserName(group.admin) },
    { key: 'user_role', header: "User's role", render: (group) => group.archived_at ? 'Archived' : (group.user_role === 'admin' ? 'Admin' : 'Member') },
  ]

  const memberColumns = [
    { key: 'name', header: 'Name', sortValue: (member) => displayUserName(member), render: displayUserName },
    { key: 'email', header: 'Email' },
    { key: 'group_admin_status', header: 'Group Admin Status', render: (member) => member.group_admin_status === 'admin' ? 'Admin' : 'Member' },
    {
      key: 'rosana_role',
      header: 'Rosana Role',
      render: (member) => ({
        financial_admin: 'Financial Admin',
        technical_admin: 'Technical Admin',
        technical_user: 'Technical User',
        commenter: 'Commenter',
      }[member.rosana_role] || member.rosana_role),
    },
  ]

  return (
    <main className="groups-page">
      <div className="groups-page-header">
        <h1>Groups</h1>
        <input
          type="search"
          className="groups-search"
          placeholder="Search your groups…"
          value={search}
          onChange={(event) => setSearch(event.target.value)}
        />
        {user?.is_staff && (
          <label className="groups-archived-toggle">
            <input type="checkbox" checked={showArchived} onChange={(event) => setShowArchived(event.target.checked)} />
            Show archived
          </label>
        )}
      </div>

      {error && <p className="form-error" role="alert">{error}</p>}

      <div className="action-toolbar">
        <button type="button" onClick={handleNew} disabled={isCreating}>
          {isCreating ? 'Creating…' : 'New Group'}
        </button>
        <button
          type="button"
          onClick={() => {
            setIsGroupFinderOpen((current) => !current)
            setGroupFinderError('')
          }}
        >
          Find group to join
        </button>
        <button
          type="button"
          onClick={() => setIsDeleteDialogOpen(true)}
          disabled={!isSelectedGroupAdmin || isDeleting}
        >
          Archive
        </button>
        {selectedGroup?.archived_at && user?.is_staff && (
          <button type="button" onClick={handleRestore}>Restore</button>
        )}
      </div>

      {isGroupFinderOpen && (
        <section className="group-finder" aria-labelledby="group-finder-heading">
          <div className="group-section-heading">
            <div>
              <h2 id="group-finder-heading">Find a group to join</h2>
              <p className="text-sm">Search for a group and send a request to its administrator.</p>
            </div>
            <button type="button" onClick={() => setIsGroupFinderOpen(false)}>Close</button>
          </div>
          <form className="group-finder-form" onSubmit={handleFindGroups}>
            <input
              type="search"
              value={groupFinderQuery}
              onChange={(event) => setGroupFinderQuery(event.target.value)}
              placeholder="Search by group name"
              aria-label="Search by group name"
            />
            <button type="submit" disabled={isSearchingGroups}>
              {isSearchingGroups ? 'Searching…' : 'Search'}
            </button>
          </form>
          {groupFinderError && <p className="form-error" role="alert">{groupFinderError}</p>}
          {groupFinderResults.length > 0 ? (
            <ul className="group-finder-results">
              {groupFinderResults.map((group) => {
                const isMember = groups.some((ownedGroup) => ownedGroup.id === group.id)
                const requestSent = joinRequestIds.has(group.id)
                return (
                  <li key={group.id} className="group-finder-result">
                    <div>
                      <strong>{group.name}</strong>
                      <span>Administrator: {displayUserName(group.admin)}</span>
                    </div>
                    {isMember ? (
                      <span className="text-sm">Already a member</span>
                    ) : requestSent ? (
                      <span className="text-sm">Request sent</span>
                    ) : (
                      <button
                        type="button"
                        onClick={() => handleRequestToJoin(group.id)}
                        disabled={joiningGroupId === group.id}
                      >
                        {joiningGroupId === group.id ? 'Sending…' : 'Request to join'}
                      </button>
                    )}
                  </li>
                )
              })}
            </ul>
          ) : (
            !isSearchingGroups && groupFinderQuery.trim() && <p className="text-sm">No groups found.</p>
          )}
        </section>
      )}

      {isLoading ? (
        <p className="text-sm">Loading groups…</p>
      ) : (
        <DataTable
          columns={groupColumns}
          rows={filteredGroups}
          getRowId={(group) => group.id}
          selectedId={selectedId}
          onSelectRow={setSelectedId}
          emptyMessage={groups.length === 0 ? 'You are not a member of any groups.' : 'No groups match your search.'}
        />
      )}

      {selectedGroup && (
        <section className="group-detail-card" aria-labelledby="selected-group-heading">
          <div className="group-detail-heading">
            <h2 id="selected-group-heading">{selectedGroup.name}</h2>
            <button type="button" onClick={() => navigate(`/groups/${selectedGroup.id}`)}>Open group editor</button>
          </div>
          <dl className="group-detail-meta">
            <div><dt>Admin</dt><dd>{displayUserName(selectedGroup.admin)}</dd></div>
            <div><dt>Your role</dt><dd>{selectedGroup.user_role === 'admin' ? 'Admin' : 'Member'}</dd></div>
          </dl>

          <section className="group-subscription-summary" aria-labelledby="group-subscription-heading">
            <div className="group-section-heading">
              <div>
                <h3 id="group-subscription-heading">Subscription</h3>
                <p className="text-sm">This group uses its top-level organization&apos;s subscription.</p>
              </div>
              {subscriptionForSelectedGroup?.can_view_billing && <button type="button" onClick={() => navigate('/subscription')}>View subscription details</button>}
            </div>
            {!subscriptionForSelectedGroup ? <p className="text-sm">Loading subscription information...</p> : subscriptionForSelectedGroup.subscription ? (
              <dl className="group-detail-meta">
                <div><dt>Plan</dt><dd>{subscriptionForSelectedGroup.subscription.plan_name || subscriptionForSelectedGroup.subscription.plan_code}</dd></div>
                <div><dt>Status</dt><dd>{subscriptionForSelectedGroup.subscription.status.replaceAll('_', ' ')}</dd></div>
                <div><dt>Seats</dt><dd>{subscriptionForSelectedGroup.subscription.seat_limit}</dd></div>
                <div><dt>Ends</dt><dd>{subscriptionForSelectedGroup.subscription.ends_at ? new Date(subscriptionForSelectedGroup.subscription.ends_at).toLocaleDateString() : 'No end date'}</dd></div>
              </dl>
            ) : <p className="text-sm">No subscription is currently assigned to this organization.</p>}
          </section>

          {isSelectedGroupAdmin && (
            <div className="group-admin-sections">
              <section>
                <h3>Users in this group</h3>
                {isLoadingMembers ? <p className="text-sm">Loading members…</p> : (
                  <DataTable
                    columns={memberColumns}
                    rows={members}
                    getRowId={(member) => member.id}
                    selectedId={null}
                    onSelectRow={() => {}}
                    emptyMessage="This group has no users."
                  />
                )}
              </section>

              <section>
                <div className="group-section-heading">
                  <h3>Jcodes assigned to this group</h3>
                  <div className="action-toolbar">
                    <button
                      type="button"
                      onClick={() => setSelectedJcodeIds(assignedJcodes.map((jcode) => jcode.id))}
                      disabled={assignedJcodes.length === 0 || isSavingJcodes}
                    >
                      Select All
                    </button>
                    <button type="button" onClick={() => setSelectedJcodeIds([])} disabled={isSavingJcodes}>
                      Select None
                    </button>
                    <button type="button" onClick={handleRemoveSelectedJcodes} disabled={selectedJcodeIds.length === 0 || isSavingJcodes}>
                      Remove selected Jcodes
                    </button>
                    <button type="button" onClick={openJcodePicker} disabled={isSavingJcodes}>
                      Add new Jcodes
                    </button>
                  </div>
                </div>
                <JcodeSelectionTable
                  rows={assignedJcodes}
                  selectedIds={selectedJcodeIds}
                  onToggle={(id) => setSelectedJcodeIds((current) => toggleId(current, id))}
                  emptyMessage="No Jcodes are assigned to this group."
                />
              </section>
            </div>
          )}
        </section>
      )}

      {isJcodePickerOpen && (
        <section className="group-jcode-picker" aria-labelledby="jcode-picker-heading">
          <h2 id="jcode-picker-heading">Add new Jcodes</h2>
          <div className="group-picker-actions">
            <button
              type="button"
              onClick={() => setPickerSelectedIds(availableJcodes.map((jcode) => jcode.id))}
              disabled={availableJcodes.length === 0 || isSavingJcodes || isLoadingJcodes}
            >
              Select All
            </button>
            <button type="button" onClick={() => setPickerSelectedIds([])} disabled={isSavingJcodes || isLoadingJcodes}>
              Select None
            </button>
            <button type="button" onClick={() => setIsJcodePickerOpen(false)} disabled={isSavingJcodes}>Cancel</button>
            <button type="button" onClick={() => saveJcodes([...new Set([...assignedJcodes.map((jcode) => jcode.id), ...pickerSelectedIds])])} disabled={pickerSelectedIds.length === 0 || isSavingJcodes}>
              Add
            </button>
          </div>
          <div className="jcode-picker-filters">
            <label className="editor-field">
              <span>State</span>
              <select value={pickerState} onChange={(event) => { setPickerState(event.target.value); setPickerCounty('') }}>
                <option value="">All states</option>
                {states.map((state) => <option key={state} value={state}>{state}</option>)}
              </select>
            </label>
            <label className="editor-field">
              <span>County</span>
              <select value={pickerCounty} onChange={(event) => setPickerCounty(event.target.value)} disabled={!pickerState}>
                <option value="">All counties</option>
                {counties.map((county) => <option key={county} value={county}>{county}</option>)}
              </select>
            </label>
            <label className="editor-field jcode-picker-search">
              <span>Search Jcodes</span>
              <input type="search" value={pickerSearch} onChange={(event) => setPickerSearch(event.target.value)} placeholder="Search by code, place, county, or state" />
            </label>
          </div>
          {isLoadingJcodes ? <p className="text-sm">Loading Jcodes…</p> : (
            <JcodeSelectionTable
              rows={availableJcodes}
              selectedIds={pickerSelectedIds}
              onToggle={(id) => setPickerSelectedIds((current) => toggleId(current, id))}
              emptyMessage="No matching unassigned Jcodes found."
            />
          )}
        </section>
      )}

      <ConfirmDialog
        isOpen={isDeleteDialogOpen}
        title="Archive group?"
        message={`This will archive "${selectedGroup?.name}" and its subgroups. Members and historical data will be preserved.`}
        confirmLabel="Archive"
        isDangerous
        isBusy={isDeleting}
        onConfirm={handleConfirmDelete}
        onCancel={() => setIsDeleteDialogOpen(false)}
      />
    </main>
  )
}
