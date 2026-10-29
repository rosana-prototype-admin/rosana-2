import { useCallback, useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { cloneOpportunity, deleteOpportunity, listOpportunities } from '../api/opportunities'
import { listMyGroups } from '../api/groups'
import DataTable from '../components/DataTable'
import ConfirmDialog from '../components/ConfirmDialog'
import { useAuth } from '../hooks/useAuth'
import { formatDate } from '../utils/formatDate'
import '../styles/formFeedback.css'
import '../styles/actionToolbar.css'
import './OpportunitiesPage.css'

export default function OpportunitiesPage() {
  const { user } = useAuth()
  const navigate = useNavigate()

  const [opportunities, setOpportunities] = useState([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState('')
  const [search, setSearch] = useState('')
  const [selectedId, setSelectedId] = useState(null)
  const [isCloning, setIsCloning] = useState(false)
  const [isDeleting, setIsDeleting] = useState(false)
  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false)
  const [myGroupIds, setMyGroupIds] = useState(new Set())

  const loadOpportunities = useCallback(async () => {
    try {
      const [data, groups] = await Promise.all([
        listOpportunities(),
        listMyGroups().catch(() => []),
      ])
      setOpportunities(data)
      setMyGroupIds(new Set(groups.map((group) => group.id)))
      setError('')
    } catch {
      setError('Unable to load opportunities. Please try again.')
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    let cancelled = false
    async function run() {
      if (!cancelled) await loadOpportunities()
    }
    run()
    return () => {
      cancelled = true
    }
  }, [loadOpportunities])

  const filteredOpportunities = useMemo(() => {
    const query = search.trim().toLowerCase()
    if (!query) return opportunities
    return opportunities.filter(
      (opportunity) =>
        opportunity.title.toLowerCase().includes(query) ||
        opportunity.comment.toLowerCase().includes(query),
    )
  }, [opportunities, search])

  const selectedOpportunity = opportunities.find((opportunity) => opportunity.id === selectedId) || null
  const canWriteSelected =
    selectedOpportunity &&
    user &&
    (selectedOpportunity.manager === user.id || selectedOpportunity.delegates?.includes(user.id))

  function handleNew() {
    navigate('/opportunities/new')
  }

  function handleView() {
    if (selectedOpportunity) navigate(`/opportunities/${selectedOpportunity.id}`)
  }

  async function handleClone() {
    if (!selectedOpportunity) return
    setError('')
    setIsCloning(true)
    try {
      await cloneOpportunity(selectedOpportunity.id)
      await loadOpportunities()
    } catch {
      setError('Unable to clone the opportunity. Please try again.')
    } finally {
      setIsCloning(false)
    }
  }

  async function handleConfirmDelete() {
    if (!selectedOpportunity) return
    setError('')
    setIsDeleting(true)
    try {
      await deleteOpportunity(selectedOpportunity.id)
      setSelectedId(null)
      await loadOpportunities()
    } catch {
      setError('Unable to delete the opportunity. Please try again.')
    } finally {
      setIsDeleting(false)
      setIsDeleteDialogOpen(false)
    }
  }

  const columns = [
    { key: 'title', header: 'Title' },
    {
      key: 'lead_agency_name',
      header: 'Managing agency',
      render: (opportunity) => (
        <span className={myGroupIds.has(opportunity.lead_agency) ? 'opportunities-current-user' : ''}>
          {opportunity.lead_agency_name || '—'}
        </span>
      ),
    },
    {
      key: 'manager_name',
      header: 'Managing user',
      render: (opportunity) => (
        <span className={opportunity.manager === user?.id ? 'opportunities-current-user' : ''}>
          {opportunity.manager_name || '—'}
        </span>
      ),
    },
    {
      key: 'modified_at',
      header: 'Last modified',
      render: (opportunity) => formatDate(opportunity.modified_at),
    },
    {
      key: 'created_at',
      header: 'Created',
      render: (opportunity) => formatDate(opportunity.created_at),
    },
  ]

  return (
    <main className="opportunities-page">
      <div className="opportunities-page-header">
        <h1>Opportunities</h1>
        <input
          type="search"
          className="opportunities-search"
          placeholder="Search opportunities…"
          value={search}
          onChange={(event) => setSearch(event.target.value)}
        />
      </div>

      {error && (
        <p className="form-error" role="alert">
          {error}
        </p>
      )}

      <div className="action-toolbar">
        <button type="button" onClick={handleNew}>
          New Opportunity
        </button>
        <button type="button" onClick={handleView} disabled={!selectedOpportunity}>
          View
        </button>
        <button
          type="button"
          onClick={() => setIsDeleteDialogOpen(true)}
          disabled={!selectedOpportunity || !canWriteSelected || isDeleting}
        >
          Delete
        </button>
        <button type="button" onClick={handleClone} disabled={!selectedOpportunity || isCloning}>
          {isCloning ? 'Cloning…' : 'Clone'}
        </button>
      </div>

      {isLoading ? (
        <p className="text-sm">Loading opportunities…</p>
      ) : (
        <DataTable
          columns={columns}
          rows={filteredOpportunities}
          getRowId={(opportunity) => opportunity.id}
          selectedId={selectedId}
          onSelectRow={setSelectedId}
          emptyMessage={
            opportunities.length === 0
              ? 'No opportunities yet. Create one to get started.'
              : 'No opportunities match your search.'
          }
        />
      )}

      <ConfirmDialog
        isOpen={isDeleteDialogOpen}
        title="Delete opportunity?"
        message={`This will permanently delete "${selectedOpportunity?.title}" and all of its Projects, Sites, and Strategies. This cannot be undone.`}
        confirmLabel="Delete"
        isDangerous
        isBusy={isDeleting}
        onConfirm={handleConfirmDelete}
        onCancel={() => setIsDeleteDialogOpen(false)}
      />
    </main>
  )
}
