import { useEffect, useState } from 'react'
import { interventionTypeLabel } from '../utils/interventionTypeLabel'
import '../styles/dialog.css'
import '../styles/editorForm.css'
import '../styles/formFeedback.css'

/**
 * Strategy rows are auto-provisioned (see api/strategies.js) and their field
 * set isn't defined yet, so this is deliberately just a raw-JSON editor for
 * the `details` blob -- easy to replace with real fields once they exist.
 */
export default function StrategyDetailsDialog({ isOpen, strategy, isBusy = false, error, onSubmit, onCancel }) {
  const [text, setText] = useState('{}')
  const [parseError, setParseError] = useState('')

  useEffect(() => {
    function resetForm() {
      if (isOpen) {
        setText(JSON.stringify(strategy?.details ?? {}, null, 2))
        setParseError('')
      }
    }
    resetForm()
  }, [isOpen, strategy])

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
    let parsed
    try {
      parsed = JSON.parse(text)
    } catch {
      setParseError('Must be valid JSON.')
      return
    }
    if (typeof parsed !== 'object' || parsed === null || Array.isArray(parsed)) {
      setParseError('Must be a JSON object.')
      return
    }
    setParseError('')
    onSubmit(parsed)
  }

  return (
    <div className="dialog-overlay" onClick={onCancel}>
      <form className="dialog-card" onClick={(event) => event.stopPropagation()} onSubmit={handleSubmit} noValidate>
        <h3>Strategy editor{strategy ? ` — ${interventionTypeLabel(strategy.intervention_type)}` : ''}</h3>

        {(parseError || error) && (
          <p className="form-error" role="alert">
            {parseError || error}
          </p>
        )}

        <label className="editor-field">
          <span className="label">Details (JSON)</span>
          <textarea
            rows={10}
            value={text}
            onChange={(event) => setText(event.target.value)}
            style={{ fontFamily: 'var(--mono)' }}
            autoFocus
          />
        </label>
        <p className="text-sm">Strategy fields aren&rsquo;t defined yet -- this is a placeholder raw-JSON editor.</p>

        <div className="dialog-actions">
          <button type="button" className="dialog-button dialog-button-cancel" onClick={onCancel} disabled={isBusy}>
            Cancel
          </button>
          <button type="submit" className="dialog-button dialog-button-primary" disabled={isBusy}>
            {isBusy ? 'Saving…' : 'Save'}
          </button>
        </div>
      </form>
    </div>
  )
}
