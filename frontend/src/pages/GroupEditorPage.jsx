import { useCallback, useEffect, useMemo, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import {
  changeGroupMemberRoles,
  createGroup,
  getGroup,
  inviteGroupMember,
  listGroupMembers,
  listGroups,
  removeGroupMember,
  setGroupAdmin,
  updateGroup,
} from '../api/groups'
import DataTable from '../components/DataTable'
import ConfirmDialog from '../components/ConfirmDialog'
import GroupMemberDialog from '../components/GroupMemberDialog'
import { useAuth } from '../hooks/useAuth'
import { formatDate } from '../utils/formatDate'
import '../styles/editorForm.css'
import '../styles/formFeedback.css'
import '../styles/actionToolbar.css'

// Excludes the group itself and all of its descendants from the parent
// picker -- a lighter-weight, client-side mirror of the same cycle check the
// backend (groups.serializers.GroupSerializer.validate) always re-enforces.
function collectExcludedIds(groups, groupId) {
  if (groupId == null) return new Set()
  const excluded = new Set([groupId])
  let frontier = [groupId]
  while (frontier.length > 0) {
    const children = groups.filter((group) => frontier.includes(group.parent)).map((group) => group.id)
    children.forEach((id) => excluded.add(id))
    frontier = children
  }
  return excluded
}

function memberLabel(member) {
  return `${member.first_name} ${member.last_name}`.trim() || member.username
}

export default function GroupEditorPage() {
  const { id } = useParams()
  const { user } = useAuth()
  const navigate = useNavigate()

  const [group, setGroup] = useState(null)
  const [allGroups, setAllGroups] = useState([])
  const [isLoading, setIsLoading] = useState(true)
  const [loadError, setLoadError] = useState('')

  const [name, setName] = useState('')
  const [parent, setParent] = useState('')
  const [baseline, setBaseline] = useState(null)

  const [saveError, setSaveError] = useState('')
  const [isSaving, setIsSaving] = useState(false)
  const [savedAt, setSavedAt] = useState(null)

  const [members, setMembers] = useState([])
  const [isLoadingMembers, setIsLoadingMembers] = useState(false)
  const [memberError, setMemberError] = useState('')
  const [inviteSuccessMessage, setInviteSuccessMessage] = useState('')
  const [selectedMemberId, setSelectedMemberId] = useState(null)
  const [isMemberDialogOpen, setIsMemberDialogOpen] = useState(false)
  const [memberDialogMode, setMemberDialogMode] = useState('invite')
  const [isSubmittingMember, setIsSubmittingMember] = useState(false)
  const [memberDialogError, setMemberDialogError] = useState('')
  const [isRemoveMemberDialogOpen, setIsRemoveMemberDialogOpen] = useState(false)
  const [isRemovingMember, setIsRemovingMember] = useState(false)

  const [selectedSubgroupId, setSelectedSubgroupId] = useState(null)
  const [isCreatingSubgroup, setIsCreatingSubgroup] = useState(false)
  const [subgroupError, setSubgroupError] = useState('')

  const canManage = group && user && group.admin?.id === user.id

  const loadMembers = useCallback(async () => {
    setIsLoadingMembers(true)
    try {
      const data = await listGroupMembers(id)
      setMembers(data)
      setMemberError('')
    } catch {
      setMemberError('Unable to load members. Please try again.')
    } finally {
      setIsLoadingMembers(false)
    }
  }, [id])

  useEffect(() => {
    let cancelled = false

    async function load() {
      setIsLoading(true)
      setLoadError('')
      try {
        const [groupData, groupsData] = await Promise.all([getGroup(id), listGroups()])
        if (cancelled) return

        setGroup(groupData)
        setAllGroups(groupsData)
        setName(groupData.name)
        setParent(groupData.parent ?? '')
        setBaseline({ name: groupData.name, parent: groupData.parent })
      } catch (err) {
        if (!cancelled) {
          setLoadError(
            err.response?.status === 404
              ? 'Group not found.'
              : 'Unable to load this Group. You may not have access to it.',
          )
        }
      } finally {
        if (!cancelled) setIsLoading(false)
      }
    }

    load()
    return () => {
      cancelled = true
    }
  }, [id])

  useEffect(() => {
    let cancelled = false
    async function run() {
      if (!cancelled) await loadMembers()
    }
    run()
    return () => {
      cancelled = true
    }
  }, [loadMembers])

  const excludedIds = useMemo(() => collectExcludedIds(allGroups, group?.id), [allGroups, group])
  const parentOptions = useMemo(
    () => allGroups.filter((candidate) => !excludedIds.has(candidate.id)),
    [allGroups, excludedIds],
  )
  const subgroups = useMemo(
    () => allGroups.filter((candidate) => candidate.parent === Number(id)),
    [allGroups, id],
  )

  const isDirty = baseline && (name !== baseline.name || Number(parent || 0) !== Number(baseline.parent || 0))

  function handleBack() {
    if (isDirty && !window.confirm('You have unsaved changes. Leave without saving?')) {
      return
    }
    navigate('/groups')
  }

  async function handleSave(event) {
    event.preventDefault()
    setSaveError('')

    if (!name.trim()) {
      setSaveError('Name is required.')
      return
    }

    setIsSaving(true)
    try {
      const updated = await updateGroup(id, {
        name: name.trim(),
        parent: parent === '' ? null : Number(parent),
      })
      setGroup((prev) => ({ ...prev, ...updated }))
      setBaseline({ name: updated.name, parent: updated.parent })
      setSavedAt(new Date())
    } catch (err) {
      const data = err.response?.data
      if (data && typeof data === 'object') {
        const firstError = Object.values(data).flat()[0]
        setSaveError(firstError || 'Unable to save changes. Please try again.')
      } else {
        setSaveError('Unable to save changes. Please try again.')
      }
    } finally {
      setIsSaving(false)
    }
  }

  useEffect(() => {
    if (!isDirty) return undefined
    function handleBeforeUnload(event) {
      event.preventDefault()
      event.returnValue = ''
    }
    window.addEventListener('beforeunload', handleBeforeUnload)
    return () => window.removeEventListener('beforeunload', handleBeforeUnload)
  }, [isDirty])

  const selectedMember = members.find((member) => member.id === selectedMemberId) || null

  async function handleSubmitMemberDialog({ userId, role }) {
    setMemberDialogError('')
    setIsSubmittingMember(true)
    try {
      if (memberDialogMode === 'invite') {
        await inviteGroupMember(id, { userId, roles: role ? [role] : [] })
        setIsMemberDialogOpen(false)
        // The invitee hasn't joined yet -- they still need to accept it from
        // their Notifications page -- so there's no new member to reload.
        setInviteSuccessMessage('Invitation sent.')
      } else {
        await changeGroupMemberRoles(id, selectedMember.id, role ? [role] : [])
        setIsMemberDialogOpen(false)
        await loadMembers()
      }
    } catch (err) {
      const data = err.response?.data
      const message = Array.isArray(data?.non_field_errors)
        ? data.non_field_errors[0]
        : 'Unable to save this member. Please try again.'
      setMemberDialogError(message)
    } finally {
      setIsSubmittingMember(false)
    }
  }

  async function handleConfirmRemoveMember() {
    if (!selectedMember) return
    setIsRemovingMember(true)
    try {
      await removeGroupMember(id, selectedMember.id)
      setSelectedMemberId(null)
      setIsRemoveMemberDialogOpen(false)
      await loadMembers()
    } catch {
      setMemberError('Unable to remove this member. Please try again.')
      setIsRemoveMemberDialogOpen(false)
    } finally {
      setIsRemovingMember(false)
    }
  }

  async function handleMakeAdmin() {
    if (!selectedMember) return
    setMemberError('')
    try {
      const updated = await setGroupAdmin(id, selectedMember.id)
      setGroup((prev) => ({ ...prev, ...updated }))
      setSelectedMemberId(null)
      await loadMembers()
    } catch {
      setMemberError('Unable to make this member the admin. Please try again.')
    }
  }

  async function handleNewSubgroup() {
    setSubgroupError('')
    setIsCreatingSubgroup(true)
    try {
      const subgroup = await createGroup({ name: 'Untitled Group', parent: Number(id) })
      navigate(`/groups/${subgroup.id}`)
    } catch {
      setSubgroupError('Unable to create a new subgroup. Please try again.')
    } finally {
      setIsCreatingSubgroup(false)
    }
  }

  function handleEditSubgroup() {
    if (selectedSubgroupId) navigate(`/groups/${selectedSubgroupId}`)
  }

  const memberColumns = [
    { key: 'name', header: 'Name', sortValue: memberLabel, render: memberLabel },
    { key: 'email', header: 'Email' },
    {
      key: 'role',
      header: 'Role',
      render: (member) => (member.role === 'admin' ? 'Admin' : member.roles.join(', ') || '—'),
    },
  ]

  const subgroupColumns = [
    { key: 'name', header: 'Name' },
    { key: 'members', header: 'Members', render: (subgroup) => subgroup.members.length },
    { key: 'modified_at', header: 'Last modified', render: (subgroup) => formatDate(subgroup.modified_at) },
  ]

  if (isLoading) {
    return (
      <main className="editor-page">
        <p className="text-sm">Loading Group…</p>
      </main>
    )
  }

  if (loadError) {
    return (
      <main className="editor-page">
        <p className="form-error" role="alert">
          {loadError}
        </p>
        <button type="button" className="editor-back" onClick={() => navigate('/groups')}>
          ← Back to Groups
        </button>
      </main>
    )
  }

  return (
    <main className="editor-page">
      <button type="button" className="editor-back" onClick={handleBack}>
        ← Back to Groups
      </button>

      <form className="editor-card" onSubmit={handleSave}>
        <div className="editor-title-row">
          <h1>Group Editor</h1>
          {!canManage && <span className="editor-readonly-badge">Read-only</span>}
        </div>

        {saveError && (
          <p className="form-error" role="alert">
            {saveError}
          </p>
        )}
        {savedAt && !isDirty && !saveError && <p className="form-success text-sm">Saved.</p>}

        <label className="editor-field">
          <span className="label">Name</span>
          <input
            type="text"
            value={name}
            onChange={(event) => setName(event.target.value)}
            disabled={!canManage}
            required
          />
        </label>

        <label className="editor-field">
          <span className="label">Parent group</span>
          <select value={parent} onChange={(event) => setParent(event.target.value)} disabled={!canManage}>
            <option value="">— None (top-level) —</option>
            {parentOptions.map((option) => (
              <option key={option.id} value={option.id}>
                {option.name}
              </option>
            ))}
          </select>
        </label>

        <dl className="editor-meta">
          <div>
            <dt className="label">Admin</dt>
            <dd>{memberLabel(group.admin)}</dd>
          </div>
          <div>
            <dt className="label">Created</dt>
            <dd>{formatDate(group.created_at)}</dd>
          </div>
          <div>
            <dt className="label">Last modified</dt>
            <dd>{formatDate(group.modified_at)}</dd>
          </div>
        </dl>

        {canManage && (
          <button type="submit" className="editor-save" disabled={!isDirty || isSaving}>
            {isSaving ? 'Saving…' : 'Save'}
          </button>
        )}
      </form>

      <section className="editor-section">
        <div className="editor-section-header">
          <h2>Members</h2>
        </div>

        {memberError && (
          <p className="form-error" role="alert">
            {memberError}
          </p>
        )}
        {inviteSuccessMessage && <p className="form-success text-sm">{inviteSuccessMessage}</p>}

        {canManage && (
          <div className="action-toolbar">
            <button
              type="button"
              onClick={() => {
                setMemberDialogMode('invite')
                setMemberDialogError('')
                setInviteSuccessMessage('')
                setIsMemberDialogOpen(true)
              }}
            >
              Invite User
            </button>
            <button
              type="button"
              onClick={() => {
                setMemberDialogMode('edit')
                setMemberDialogError('')
                setInviteSuccessMessage('')
                setIsMemberDialogOpen(true)
              }}
              disabled={!selectedMember || selectedMember.role === 'admin'}
            >
              Edit Role
            </button>
            <button
              type="button"
              onClick={() => setIsRemoveMemberDialogOpen(true)}
              disabled={!selectedMember || selectedMember.role === 'admin' || isRemovingMember}
            >
              Remove
            </button>
            <button
              type="button"
              onClick={handleMakeAdmin}
              disabled={!selectedMember || selectedMember.role === 'admin'}
            >
              Make Admin
            </button>
          </div>
        )}

        {isLoadingMembers ? (
          <p className="text-sm">Loading members…</p>
        ) : (
          <DataTable
            columns={memberColumns}
            rows={members}
            getRowId={(member) => member.id}
            selectedId={selectedMemberId}
            onSelectRow={setSelectedMemberId}
            emptyMessage="No members yet."
          />
        )}
      </section>

      <section className="editor-section">
        <div className="editor-section-header">
          <h2>Subgroups</h2>
        </div>

        {subgroupError && (
          <p className="form-error" role="alert">
            {subgroupError}
          </p>
        )}

        {canManage && (
          <div className="action-toolbar">
            <button type="button" onClick={handleNewSubgroup} disabled={isCreatingSubgroup}>
              {isCreatingSubgroup ? 'Creating…' : 'New Subgroup'}
            </button>
            <button type="button" onClick={handleEditSubgroup} disabled={!selectedSubgroupId}>
              Edit
            </button>
          </div>
        )}

        <DataTable
          columns={subgroupColumns}
          rows={subgroups}
          getRowId={(subgroup) => subgroup.id}
          selectedId={selectedSubgroupId}
          onSelectRow={setSelectedSubgroupId}
          emptyMessage="No subgroups yet."
        />
      </section>

      <GroupMemberDialog
        isOpen={isMemberDialogOpen}
        mode={memberDialogMode}
        memberLabel={selectedMember ? memberLabel(selectedMember) : ''}
        initialRole={memberDialogMode === 'edit' ? (selectedMember?.roles[0] ?? '') : ''}
        isBusy={isSubmittingMember}
        error={memberDialogError}
        onSubmit={handleSubmitMemberDialog}
        onCancel={() => setIsMemberDialogOpen(false)}
      />

      <ConfirmDialog
        isOpen={isRemoveMemberDialogOpen}
        title="Remove member?"
        message={`This will remove ${
          selectedMember ? memberLabel(selectedMember) : 'this member'
        } from the group. They will lose access immediately.`}
        confirmLabel="Remove"
        isDangerous
        isBusy={isRemovingMember}
        onConfirm={handleConfirmRemoveMember}
        onCancel={() => setIsRemoveMemberDialogOpen(false)}
      />
    </main>
  )
}
