import { useEffect, useState } from 'react'
import {
  createAdminGroupContract,
  assignAdminGroupSeat,
  getAdminGroupSubscription,
  listAdminGroupContracts,
  listAdminGroups,
  listAdminGroupSeats,
  updateAdminGroupSubscription,
} from '../api/admin'
import './AdminGroupsPage.css'

const PLANS = [['none', 'None'], ['basic', 'Basic'], ['premium', 'Premium'], ['crossroads', 'Crossroads'], ['borough', 'Borough'], ['ville', 'Ville'], ['shire', 'Shire'], ['provincia', 'Provincia'], ['comarca', 'Comarca'], ['metro', 'Metro'], ['commonwealth', 'Commonwealth'], ['republic', 'Republic']]
const SUBSCRIPTION_STATUSES = [['trialing', 'Trialing'], ['active', 'Active'], ['paused', 'Paused'], ['past_due', 'Past due'], ['canceled', 'Canceled'], ['expired', 'Expired']]
const CONTRACT_STATUSES = [['draft', 'Draft'], ['pending', 'Pending'], ['active', 'Active'], ['expired', 'Expired'], ['terminated', 'Terminated']]

function dateValue(value) {
  return value ? new Date(value).toISOString().slice(0, 16) : ''
}

function isoValue(value) {
  return value ? new Date(value).toISOString() : null
}

export default function AdminGroupsPage() {
  const [groups, setGroups] = useState([])
  const [selectedId, setSelectedId] = useState(null)
  const [subscription, setSubscription] = useState(null)
  const [contracts, setContracts] = useState([])
  const [seats, setSeats] = useState([])
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')

  useEffect(() => {
    listAdminGroups().then((data) => {
      setGroups(data)
      if (data.length) setSelectedId(data[0].id)
    }).catch(() => setError('Unable to load companies.'))
  }, [])

  const group = groups.find((item) => item.id === selectedId)

  useEffect(() => {
    if (!group) return undefined
    Promise.all([
      getAdminGroupSubscription(group.id),
      listAdminGroupContracts(group.id),
      listAdminGroupSeats(group.id),
    ]).then(([subscriptionData, contractData, seatData]) => {
      setSubscription(subscriptionData)
      setContracts(contractData)
      setSeats(seatData)
    }).catch(() => setError('Unable to load company subscription records.'))
    return undefined
  }, [group])

  async function saveSubscription(event) {
    event.preventDefault()
    const form = new FormData(event.currentTarget)
    try {
      const updated = await updateAdminGroupSubscription(group.id, {
        plan_code: form.get('plan_code'), status: form.get('status'),
        seat_limit: Number(form.get('seat_limit')), starts_at: isoValue(form.get('starts_at')),
        ends_at: isoValue(form.get('ends_at')), external_reference: form.get('external_reference'),
        notes: form.get('notes'),
      })
      setSubscription(updated)
      setMessage('Company subscription saved.')
    } catch { setError('Unable to save the company subscription.') }
  }

  async function addSeat(event) {
    event.preventDefault()
    const form = new FormData(event.currentTarget)
    try {
      const created = await assignAdminGroupSeat(group.id, Number(form.get('user_id')))
      setSeats((current) => [...current, created])
      event.currentTarget.reset()
      setMessage('Seat assigned.')
    } catch { setError('Unable to assign that seat.') }
  }

  async function addContract(event) {
    event.preventDefault()
    const form = new FormData(event.currentTarget)
    try {
      const created = await createAdminGroupContract(group.id, {
        title: form.get('title'), status: form.get('status'), notes: form.get('notes'),
      })
      setContracts((current) => [created, ...current])
      event.currentTarget.reset()
      setMessage('Contract record created.')
    } catch { setError('Unable to create the contract record.') }
  }

  return (
    <main className="admin-groups-page">
      <div><h1>Company subscriptions</h1><p>Manage plans, contracts, and seats at the company level.</p></div>
      {error && <p className="form-error" role="alert">{error}</p>}
      {message && <p className="form-success" role="status">{message}</p>}
      <div className="admin-groups-layout">
        <div className="admin-company-list">
          {groups.map((item) => <button type="button" className={item.id === selectedId ? 'selected' : ''} key={item.id} onClick={() => { setSelectedId(item.id); setMessage(''); setError('') }}><strong>{item.name}</strong><span>{item.member_count} members</span></button>)}
          {!groups.length && <p>No companies found.</p>}
        </div>
        {group && subscription && <section className="admin-company-detail">
          <h2>{group.name}</h2>
          <p>Company administrator: {group.admin?.username}</p>
          <form onSubmit={saveSubscription}>
            <h3>Subscription</h3>
            <div className="admin-company-fields">
              <label>Plan<select name="plan_code" defaultValue={subscription.plan_code}>{PLANS.map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>
              <label>Status<select name="status" defaultValue={subscription.status}>{SUBSCRIPTION_STATUSES.map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>
              <label>Seats<input name="seat_limit" type="number" min="0" defaultValue={subscription.seat_limit} /></label>
              <label>Starts<input name="starts_at" type="datetime-local" defaultValue={dateValue(subscription.starts_at)} /></label>
              <label>Ends<input name="ends_at" type="datetime-local" defaultValue={dateValue(subscription.ends_at)} /></label>
              <label>Reference<input name="external_reference" defaultValue={subscription.external_reference || ''} /></label>
            </div>
            <button type="submit">Save subscription</button>
          </form>
          <form onSubmit={addSeat}>
            <h3>Seats ({seats.length} assigned / {subscription.seat_limit})</h3>
            <select name="user_id" required defaultValue=""><option value="" disabled>Select a company member</option>{group.members.map((member) => <option key={member.id} value={member.id}>{member.username} — {member.email}</option>)}</select>
            <button type="submit">Assign seat</button>
          </form>
          <ul>{seats.map((seat) => <li key={seat.id}>{seat.user.username} — {seat.user.email}</li>)}</ul>
          <form onSubmit={addContract}>
            <h3>New contract</h3>
            <input name="title" placeholder="Contract title" required />
            <select name="status" defaultValue="draft">{CONTRACT_STATUSES.map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select>
            <input name="notes" placeholder="Notes" />
            <button type="submit">Add contract</button>
          </form>
          <ul>{contracts.map((contract) => <li key={contract.id}><strong>{contract.title}</strong> — {contract.status}</li>)}</ul>
        </section>}
      </div>
    </main>
  )
}
