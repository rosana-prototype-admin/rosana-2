import { useEffect } from 'react'
import '../styles/dialog.css'
import '../styles/systemMessageDialog.css'

// type: 'info' | 'user-input' | 'user-input-alt' | 'output' | 'caution' | 'warning' | 'error'
const ICONS = {
  'user-input': '👉',
  'user-input-alt': '👉',
  output: '🧮',
  caution: '🤔',
  warning: '⚠️',
  error: '✋',
}

export default function SystemMessageDialog({ isOpen, type, title, message, closeLabel = 'OK', onClose }) {
  useEffect(() => {
    if (!isOpen) return undefined
    function handleKeyDown(event) {
      if (event.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [isOpen, onClose])

  if (!isOpen) return null

  return (
    <div className="dialog-overlay" onClick={onClose}>
      <div
        className={`system-message-card system-message-${type}`}
        role="alertdialog"
        aria-modal="true"
        aria-labelledby="system-message-title"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="system-message-header">
          {type === 'info' ? (
            <span className="system-message-icon system-message-icon-info" aria-hidden="true">
              i
            </span>
          ) : (
            <span className="system-message-icon" aria-hidden="true">
              {ICONS[type]}
            </span>
          )}
          <h3 id="system-message-title">{title}</h3>
        </div>
        <div className="system-message-body">
          <p>{message}</p>
        </div>
        <div className="system-message-actions">
          <button type="button" className="system-message-close" onClick={onClose}>
            {closeLabel}
          </button>
        </div>
      </div>
    </div>
  )
}
