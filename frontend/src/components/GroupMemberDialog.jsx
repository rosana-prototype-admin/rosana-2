import { useEffect, useState } from 'react'
import UserSearchField from './UserSearchField'
import '../styles/dialog.css'
import '../styles/editorForm.css'
import '../styles/formFeedback.css'

/**
 * mode: 'invite' | 'edit'
 * - invite: search for a user (must pick an actual suggestion -- the Group
 *   members API takes a numeric user_id, not a username/email identifier
 *   like Opportunity's invite does) plus a free-text organizational role,
 *   then calls onSubmit({ userId, organizationalRole }).
 * - edit: shows the fixed member (memberLabel) and just the organizational
 *   role input, then calls onSubmit({ organizationalRole }).
 */
export default function GroupMemberDialog({
  isOpen,
  mode,
  memberLabel,
  initialRole = '',
  isBusy = false,
  error,
  onSubmit,
  onCancel,
}) {
  const [query, setQuery] = useState('')
  const [selectedUser, setSelectedUser] = useState(null)
  const [organizationalRole, setOrganizationalRole] = useState(initialRole)

  useEffect(() => {
    function resetForm() {
      if (isOpen) {
        setQuery('')
        setSelectedUser(null)
        setOrganizationalRole(initialRole)
      }
    }
    resetForm()
  }, [isOpen, initialRole])

  useEffect(() => {
    if (!isOpen) return undefined
    function handleKeyDown(event) {
      if (event.key === 'Escape') onCancel()
    }
    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [isOpen, onCancel])

  if (!isOpen) return null

  function handleQueryChange(value) {
    setQuery(value)
    setSelectedUser(null)
  }

  function handleSubmit(event) {
    event.preventDefault()
    onSubmit(mode === 'invite'
      ? { userId: selectedUser.id, organizationalRole: organizationalRole.trim() }
      : { organizationalRole: organizationalRole.trim() })
  }

  return (
    <div className="dialog-overlay" onClick={onCancel}>
      <form
        className="dialog-card"
        onClick={(event) => event.stopPropagation()}
        onSubmit={handleSubmit}
        noValidate
      >
        <h3>{mode === 'invite' ? 'Invite a user' : `Edit organizational role for ${memberLabel}`}</h3>

        {error && (
          <p className="form-error" role="alert">
            {error}
          </p>
        )}

        {mode === 'invite' && (
          <label className="editor-field">
            <span className="label">Name, username, or email</span>
            <UserSearchField
              value={query}
              onChange={handleQueryChange}
              onSelectUser={setSelectedUser}
              placeholder="Start typing to search…"
              autoFocus
            />
          </label>
        )}

        <label className="editor-field">
          <span className="label">Organizational Role</span>
          <input
            type="text"
            value={organizationalRole}
            onChange={(event) => setOrganizationalRole(event.target.value)}
            placeholder="e.g. Coordinator"
          />
        </label>

        <div className="dialog-actions">
          <button type="button" className="dialog-button dialog-button-cancel" onClick={onCancel} disabled={isBusy}>
            Cancel
          </button>
          <button
            type="submit"
            className="dialog-button dialog-button-primary"
            disabled={isBusy || (mode === 'invite' && !selectedUser)}
          >
            {isBusy ? 'Saving…' : mode === 'invite' ? 'Invite' : 'Save'}
          </button>
        </div>
      </form>
    </div>
  )
}
