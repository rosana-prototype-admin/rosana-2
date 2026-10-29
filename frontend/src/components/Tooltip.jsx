import { useId } from 'react'
import './Tooltip.css'

export default function Tooltip({ children, label = 'More information' }) {
  const tooltipId = useId()

  return (
    <span className="tooltip">
      <button
        type="button"
        className="tooltip-trigger"
        aria-label={label}
        aria-describedby={tooltipId}
      >
        <span aria-hidden="true">i</span>
      </button>
      <span id={tooltipId} className="tooltip-content" role="tooltip">
        {children}
      </span>
    </span>
  )
}
