import { Link } from 'react-router-dom'
import './AccessStatusCard.css'

const ROLE_LABELS = {
  financial_admin: 'Financial Admin',
  technical_admin: 'Technical Admin',
  technical_user: 'Technical User',
  commenter: 'Commenter',
}

const ACCESS_LABELS = {
  active: 'Full active access',
  unlicensed: 'No active subscription',
  expired_grace: 'Renewal grace period',
  expired_restricted: 'Restricted access',
  expired_locked: 'Locked access',
  archive_due: 'Pending archive',
}

function accessTone(entitlement) {
  if (entitlement.access_state !== 'active') return 'warning'
  if (entitlement.rosana_role === 'technical_user' && !entitlement.has_technical_seat) return 'warning'
  return 'success'
}

export default function AccessStatusCard({ entitlement, groupId, compact = false }) {
  if (!entitlement) return null
  const needsSeat = entitlement.rosana_role === 'technical_user' && !entitlement.has_technical_seat
  const roleLabel = ROLE_LABELS[entitlement.rosana_role] || entitlement.rosana_role || 'Member'
  const accessLabel = needsSeat ? 'Technical seat required' : (ACCESS_LABELS[entitlement.access_state] || 'Access status unavailable')
  const featureSummary = needsSeat
    ? 'View and comment access are available. Analysis features are unavailable until a Technical User seat is assigned.'
    : entitlement.access_state === 'active'
      ? 'Your organization subscription is active for your current role.'
      : 'Major account features are restricted until the organization subscription is renewed or resolved.'

  return (
    <section className={`access-status-card access-status-${accessTone(entitlement)}${compact ? ' access-status-compact' : ''}`} aria-labelledby={`access-status-${entitlement.group_id || groupId}`}>
      <div className="access-status-heading">
        <div>
          <p className="access-status-eyebrow">Your access</p>
          <h2 id={`access-status-${entitlement.group_id || groupId}`}>{entitlement.group_name || 'Organization access'}</h2>
        </div>
        <strong className="access-status-badge">{accessLabel}</strong>
      </div>
      <dl className="access-status-details">
        <div><dt>Rosana Role</dt><dd>{roleLabel}</dd></div>
        <div><dt>Plan</dt><dd>{entitlement.plan_name || entitlement.plan_code || 'None assigned'}</dd></div>
        <div><dt>Technical seat</dt><dd>{entitlement.rosana_role === 'technical_user' ? (entitlement.has_technical_seat ? 'Assigned' : 'Not assigned') : 'Not required'}</dd></div>
        <div><dt>Access</dt><dd>{accessLabel}</dd></div>
      </dl>
      <p className="access-status-message">{featureSummary}</p>
      <div className="access-status-actions">
        <Link to={`/groups/${entitlement.group_id || groupId}`}>View group</Link>
        <Link to="/subscription">View subscription and seats</Link>
      </div>
    </section>
  )
}
