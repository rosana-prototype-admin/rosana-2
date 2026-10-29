import { useCallback, useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { getOpportunity } from '../api/opportunities'
import { changeMemberRole, inviteGroup, inviteMember, listMembers, removeMember } from '../api/opportunityMembers'
import DataTable from '../components/DataTable'
import ConfirmDialog from '../components/ConfirmDialog'
import MemberDialog from '../components/MemberDialog'
import GroupInviteDialog from '../components/GroupInviteDialog'
import { useAuth } from '../hooks/useAuth'
import '../styles/editorForm.css'
import '../styles/formFeedback.css'
import '../styles/actionToolbar.css'

const ROLE_LABELS = {
  manager: 'Manager',
  delegate: 'Delegate (read/write)',
  stakeholder: 'Stakeholder (read-only)',
}

export default function OpportunityMembersPage() {
  const { id } = useParams()
  const { user } = useAuth()
  const navigate = useNavigate()

  const [opportunity, setOpportunity] = useState(null)
  const [members, setMembers] = useState([])
  const [isLoading, setIsLoading] = useState(true)
  const [loadError, setLoadError] = useState('')
  const [error, setError] = useState('')

  const [selectedUserId, setSelectedUserId] = useState(null)
  const [isInviteOpen, setIsInviteOpen] = useState(false)
  const [isInviteGroupOpen, setIsInviteGroupOpen] = useState(false)
  const [isEditOpen, setIsEditOpen] = useState(false)
  const [isRemoveOpen, setIsRemoveOpen] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [dialogError, setDialogError] = useState('')
  const [inviteGroupError, setInviteGroupError] = useState('')

  const canManageMembers = opportunity && user && opportunity.manager === user.id

  const loadMembers = useCallback(async () => {
    try {
      const data = await listMembers(id)
      setMembers(data)
      setError('')
    } catch {
      setError('Unable to load members. Please try again.')
    }
  }, [id])

  useEffect(() => {
    let cancelled = false

    async function load() {
      setIsLoading(true)
      setLoadError('')
      try {
        const [opportunityData, memberData] = await Promise.all([getOpportunity(id), listMembers(id)])
        if (cancelled) return
        setOpportunity(opportunityData)
        setMembers(memberData)
      } catch (err) {
        if (!cancelled) {
          setLoadError(
            err.response?.status === 404
              ? 'Opportunity not found.'
              : 'Unable to load this opportunity. You may not have access to it.',
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

  const selectedMember = members.find((member) => member.id === selectedUserId) || null

  async function handleInvite({ identifier, role }) {
    setDialogError('')
    if (!identifier) {
      setDialogError('Enter a username or email.')
      return
    }
    setIsSubmitting(true)
    try {
      await inviteMember(id, { identifier, role })
      setIsInviteOpen(false)
      await loadMembers()
    } catch (err) {
      const data = err.response?.data
      const message = Array.isArray(data?.non_field_errors)
        ? data.non_field_errors[0]
        : Array.isArray(data?.identifier)
          ? data.identifier[0]
          : 'Unable to invite this user. Please try again.'
      setDialogError(message)
    } finally {
      setIsSubmitting(false)
    }
  }

  async function handleInviteGroup({ group_id: groupId }) {
    setInviteGroupError('')
    setIsSubmitting(true)
    try {
      await inviteGroup(id, groupId)
      setIsInviteGroupOpen(false)
      await loadMembers()
    } catch (err) {
      const data = err.response?.data
      const message = Array.isArray(data?.group_id)
        ? data.group_id[0]
        : Array.isArray(data?.non_field_errors)
          ? data.non_field_errors[0]
          : 'Unable to invite this group. Please try again.'
      setInviteGroupError(message)
    } finally {
      setIsSubmitting(false)
    }
  }

  async function handleChangeRole({ role }) {
    if (!selectedMember) return
    setDialogError('')
    setIsSubmitting(true)
    try {
      await changeMemberRole(id, selectedMember.id, role)
      setIsEditOpen(false)
      await loadMembers()
    } catch {
      setDialogError('Unable to update this member. Please try again.')
    } finally {
      setIsSubmitting(false)
    }
  }

  async function handleConfirmRemove() {
    if (!selectedMember) return
    setIsSubmitting(true)
    try {
      await removeMember(id, selectedMember.id)
      setSelectedUserId(null)
      setIsRemoveOpen(false)
      await loadMembers()
    } catch {
      setError('Unable to remove this member. Please try again.')
      setIsRemoveOpen(false)
    } finally {
      setIsSubmitting(false)
    }
  }

  const columns = [
    {
      key: 'name',
      header: 'Name',
      sortValue: (member) => `${member.first_name} ${member.last_name}`.trim() || member.username,
      render: (member) => `${member.first_name} ${member.last_name}`.trim() || member.username,
    },
    { key: 'email', header: 'Email' },
    {
      key: 'role',
      header: 'Permission',
      render: (member) => ROLE_LABELS[member.role] || member.role,
    },
  ]

  if (isLoading) {
    return (
      <main className="editor-page">
        <p className="text-sm">Loading members…</p>
      </main>
    )
  }

  if (loadError) {
    return (
      <main className="editor-page">
        <p className="form-error" role="alert">
          {loadError}
        </p>
        <button type="button" className="editor-back" onClick={() => navigate(`/opportunities/${id}`)}>
          ← Back to Opportunity
        </button>
      </main>
    )
  }

  return (
    <main className="editor-page">
      <button type="button" className="editor-back" onClick={() => navigate(`/opportunities/${id}`)}>
        ← Back to {opportunity.title}
      </button>

      <section className="editor-section">
        <div className="editor-section-header">
          <h1>Members</h1>
        </div>

        {error && (
          <p className="form-error" role="alert">
            {error}
          </p>
        )}

        {canManageMembers && (
          <div className="action-toolbar">
            <button type="button" onClick={() => setIsInviteOpen(true)}>
              Invite User
            </button>
            <button type="button" onClick={() => setIsInviteGroupOpen(true)}>
              Invite Group
            </button>
            <button
              type="button"
              onClick={() => setIsEditOpen(true)}
              disabled={!selectedMember || selectedMember.role === 'manager'}
            >
              Edit Permissions
            </button>
            <button
              type="button"
              onClick={() => setIsRemoveOpen(true)}
              disabled={!selectedMember || selectedMember.role === 'manager'}
            >
              Remove
            </button>
          </div>
        )}

        <DataTable
          columns={columns}
          rows={members}
          getRowId={(member) => member.id}
          selectedId={selectedUserId}
          onSelectRow={setSelectedUserId}
          emptyMessage="No members yet."
        />
      </section>

      <MemberDialog
        isOpen={isInviteOpen}
        mode="invite"
        isBusy={isSubmitting}
        error={dialogError}
        onSubmit={handleInvite}
        onCancel={() => {
          setIsInviteOpen(false)
          setDialogError('')
        }}
      />

      <GroupInviteDialog
        isOpen={isInviteGroupOpen}
        isBusy={isSubmitting}
        error={inviteGroupError}
        onSubmit={handleInviteGroup}
        onCancel={() => {
          setIsInviteGroupOpen(false)
          setInviteGroupError('')
        }}
      />

      <MemberDialog
        isOpen={isEditOpen}
        mode="edit"
        memberLabel={
          selectedMember ? `${selectedMember.first_name} ${selectedMember.last_name}`.trim() || selectedMember.username : ''
        }
        initialRole={selectedMember?.role === 'manager' ? 'stakeholder' : selectedMember?.role}
        isBusy={isSubmitting}
        error={dialogError}
        onSubmit={handleChangeRole}
        onCancel={() => {
          setIsEditOpen(false)
          setDialogError('')
        }}
      />

      <ConfirmDialog
        isOpen={isRemoveOpen}
        title="Remove member?"
        message={`This will remove ${
          selectedMember ? `${selectedMember.first_name} ${selectedMember.last_name}`.trim() || selectedMember.username : 'this member'
        } from the opportunity. They will lose access immediately.`}
        confirmLabel="Remove"
        isDangerous
        isBusy={isSubmitting}
        onConfirm={handleConfirmRemove}
        onCancel={() => setIsRemoveOpen(false)}
      />
    </main>
  )
}
