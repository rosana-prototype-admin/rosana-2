import { useEffect, useState } from 'react'
import GroupSearchField from './GroupSearchField'
import '../styles/dialog.css'
import '../styles/editorForm.css'
import '../styles/formFeedback.css'

/**
 * Adds every member of a Group to the Opportunity as a stakeholder (read-only
 * viewer) in one action -- unlike MemberDialog's invite mode, there's no role
 * choice here, since inviting a group specifically means "as viewers".
 */
export default function GroupInviteDialog({ isOpen, isBusy = false, error, onSubmit, onCancel }) {
  const [selectedGroup, setSelectedGroup] = useState(null)

  useEffect(() => {
    function resetForm() {
      if (isOpen) setSelectedGroup(null)
    }
    resetForm()
  }, [isOpen])

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
    onSubmit({ group_id: selectedGroup.id })
  }

  return (
    <div className="dialog-overlay" onClick={onCancel}>
      <form className="dialog-card" onClick={(event) => event.stopPropagation()} onSubmit={handleSubmit} noValidate>
        <h3>Invite a group</h3>

        {error && (
          <p className="form-error" role="alert">
            {error}
          </p>
        )}

        <label className="editor-field">
          <span className="label">Group</span>
          {selectedGroup ? (
            <div className="chip-row">
              <span className="chip">
                {selectedGroup.name}
                <button type="button" className="chip-remove" onClick={() => setSelectedGroup(null)}>
                  ×
                </button>
              </span>
            </div>
          ) : (
            <GroupSearchField onSelect={setSelectedGroup} placeholder="Start typing to search…" autoFocus />
          )}
        </label>

        <p className="text-sm">All members of this group will be added as viewers (read-only) of the opportunity.</p>

        <div className="dialog-actions">
          <button type="button" className="dialog-button dialog-button-cancel" onClick={onCancel} disabled={isBusy}>
            Cancel
          </button>
          <button type="submit" className="dialog-button dialog-button-primary" disabled={isBusy || !selectedGroup}>
            {isBusy ? 'Inviting…' : 'Invite'}
          </button>
        </div>
      </form>
    </div>
  )
}
