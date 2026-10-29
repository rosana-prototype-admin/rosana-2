import { useEffect, useState } from 'react'
import UserSearchField from './UserSearchField'
import '../styles/dialog.css'
import '../styles/editorForm.css'
import '../styles/formFeedback.css'

/**
 * mode: 'invite' | 'edit'
 * - invite: asks for a username/email plus a role, then calls onSubmit({ identifier, role }).
 * - edit: shows the fixed member (memberLabel) and just a role select, then calls onSubmit({ role }).
 */
export default function MemberDialog({
  isOpen,
  mode,
  memberLabel,
  initialRole = 'stakeholder',
  isBusy = false,
  error,
  onSubmit,
  onCancel,
}) {
  const [identifier, setIdentifier] = useState('')
  const [role, setRole] = useState(initialRole)

  useEffect(() => {
    function resetForm() {
      if (isOpen) {
        setIdentifier('')
        setRole(initialRole)
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

  function handleSubmit(event) {
    event.preventDefault()
    onSubmit(mode === 'invite' ? { identifier: identifier.trim(), role } : { role })
  }

  return (
    <div className="dialog-overlay" onClick={onCancel}>
      <form
        className="dialog-card"
        onClick={(event) => event.stopPropagation()}
        onSubmit={handleSubmit}
        noValidate
      >
        <h3>{mode === 'invite' ? 'Invite a member' : `Edit permissions for ${memberLabel}`}</h3>

        {error && (
          <p className="form-error" role="alert">
            {error}
          </p>
        )}

        {mode === 'invite' && (
          <label className="editor-field">
            <span className="label">Name, username, or email</span>
            <UserSearchField
              value={identifier}
              onChange={setIdentifier}
              placeholder="Start typing to search…"
              autoFocus
            />
          </label>
        )}

        <label className="editor-field">
          <span className="label">Permission</span>
          <select value={role} onChange={(event) => setRole(event.target.value)}>
            <option value="delegate">Delegate (read/write)</option>
            <option value="stakeholder">Stakeholder (read-only)</option>
          </select>
        </label>

        <div className="dialog-actions">
          <button type="button" className="dialog-button dialog-button-cancel" onClick={onCancel} disabled={isBusy}>
            Cancel
          </button>
          <button type="submit" className="dialog-button dialog-button-primary" disabled={isBusy}>
            {isBusy ? 'Saving…' : mode === 'invite' ? 'Invite' : 'Save'}
          </button>
        </div>
      </form>
    </div>
  )
}
