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
  initialRosanaRole = 'commenter',
  initialRole = '',
  initialPermissions = {},
  permissionDefinitions = [],
  showPermissions = false,
  canEditRosanaRole = false,
  permissionsLocked = false,
  isBusy = false,
  error,
  onSubmit,
  onCancel,
}) {
  const [query, setQuery] = useState('')
  const [selectedUser, setSelectedUser] = useState(null)
  const [rosanaRole, setRosanaRole] = useState(initialRosanaRole)
  const [organizationalRole, setOrganizationalRole] = useState(initialRole)
  const [permissions, setPermissions] = useState(initialPermissions)

  useEffect(() => {
    function resetForm() {
      if (isOpen) {
        setQuery('')
        setSelectedUser(null)
        setRosanaRole(initialRosanaRole)
        setOrganizationalRole(initialRole)
        setPermissions(initialPermissions)
      }
    }
    resetForm()
  }, [isOpen, initialRosanaRole, initialRole, initialPermissions])

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
      ? { userId: selectedUser.id, organizationalRole: organizationalRole.trim(), rosanaRole, permissions }
      : { organizationalRole: organizationalRole.trim(), rosanaRole, permissions })
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

        {mode === 'edit' && (
          <label className="editor-field">
            <span className="label">Rosana Role</span>
            <select
              value={rosanaRole}
              onChange={(event) => setRosanaRole(event.target.value)}
              disabled={!canEditRosanaRole}
            >
              <option value="financial_admin">Financial Admin</option>
              <option value="technical_admin">Technical Admin</option>
              <option value="technical_user">Technical User</option>
              <option value="commenter">Commenter</option>
            </select>
            {!canEditRosanaRole && <span className="text-sm">Only the group administrator can change this role.</span>}
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

        {showPermissions && (
          <fieldset className="editor-field" disabled={permissionsLocked}>
            <legend className="label">Permissions</legend>
            {Object.entries(
              permissionDefinitions.reduce((categories, definition) => {
                const category = categories[definition.category] || []
                category.push(definition)
                return { ...categories, [definition.category]: category }
              }, {}),
            ).map(([category, definitions]) => (
              <div key={category} className="permission-group">
                <strong>{category}</strong>
                {definitions.map((definition) => (
                  <label key={definition.code} className="permission-option">
                    <input
                      type="checkbox"
                      checked={Boolean(permissions[definition.code])}
                      onChange={(event) => setPermissions((current) => ({
                        ...current,
                        [definition.code]: event.target.checked,
                      }))}
                    />
                    {definition.label}
                  </label>
                ))}
              </div>
            ))}
            {permissionsLocked && <span className="text-sm">The group administrator always has all permissions.</span>}
          </fieldset>
        )}

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
