import { useCallback, useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { createGroup, deleteGroup, listGroupMembers, listMyGroups, updateGroupJcodes } from '../api/groups'
import { listJcodes } from '../api/jcodes'
import ConfirmDialog from '../components/ConfirmDialog'
import DataTable from '../components/DataTable'
import JcodeSelectionTable from '../components/JcodeSelectionTable'
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
  const [groups, setGroups] = useState([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState('')
  const [search, setSearch] = useState('')
  const [selectedId, setSelectedId] = useState(null)
  const [members, setMembers] = useState([])
  const [isLoadingMembers, setIsLoadingMembers] = useState(false)
  const [isCreating, setIsCreating] = useState(false)
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
      const data = await listMyGroups()
      setGroups(data)
      setSelectedId((current) => (data.some((group) => group.id === current) ? current : null))
      setError('')
    } catch {
      setError('Unable to load your groups. Please try again.')
    } finally {
      setIsLoading(false)
    }
  }, [])

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
  const isSelectedGroupAdmin = selectedGroup?.user_role === 'admin'
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
    try {
      const group = await createGroup({ name: 'Untitled Group', parent: null })
      navigate(`/groups/${group.id}`)
    } catch {
      setError('Unable to create a new group. Please try again.')
    } finally {
      setIsCreating(false)
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
    { key: 'user_role', header: "User's role", render: (group) => group.user_role === 'admin' ? 'Admin' : 'Member' },
  ]

  const memberColumns = [
    { key: 'name', header: 'Name', sortValue: (member) => displayUserName(member), render: displayUserName },
    { key: 'email', header: 'Email' },
    { key: 'role', header: 'Role', render: (member) => member.role === 'admin' ? 'Admin' : 'Member' },
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
      </div>

      {error && <p className="form-error" role="alert">{error}</p>}

      <div className="action-toolbar">
        <button type="button" onClick={handleNew} disabled={isCreating}>
          {isCreating ? 'Creating…' : 'New Group'}
        </button>
        <button
          type="button"
          onClick={() => setIsDeleteDialogOpen(true)}
          disabled={!isSelectedGroupAdmin || isDeleting}
        >
          Delete
        </button>
      </div>

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
        title="Delete group?"
        message={`This will permanently delete "${selectedGroup?.name}" along with all of its subgroups and memberships. This cannot be undone.`}
        confirmLabel="Delete"
        isDangerous
        isBusy={isDeleting}
        onConfirm={handleConfirmDelete}
        onCancel={() => setIsDeleteDialogOpen(false)}
      />
    </main>
  )
}
