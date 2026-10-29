import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { getProject, updateProject } from '../api/projects'
import { getOpportunity } from '../api/opportunities'
import { createSite, deleteSite, listSites } from '../api/sites'
import DataTable from '../components/DataTable'
import ConfirmDialog from '../components/ConfirmDialog'
import CommentThread from '../components/CommentThread'
import { useAuth } from '../hooks/useAuth'
import { formatDate } from '../utils/formatDate'
import '../styles/editorForm.css'
import '../styles/formFeedback.css'
import '../styles/actionToolbar.css'

export default function ProjectEditorPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { user } = useAuth()

  const [project, setProject] = useState(null)
  const [opportunity, setOpportunity] = useState(null)
  const [isLoading, setIsLoading] = useState(true)
  const [loadError, setLoadError] = useState('')

  const [title, setTitle] = useState('')
  const [comment, setComment] = useState('')
  const [statusValue, setStatusValue] = useState(0)
  const [baseline, setBaseline] = useState(null)
  const [saveError, setSaveError] = useState('')
  const [isSaving, setIsSaving] = useState(false)
  const [savedAt, setSavedAt] = useState(null)

  const [sites, setSites] = useState([])
  const [isLoadingSites, setIsLoadingSites] = useState(false)
  const [siteError, setSiteError] = useState('')
  const [selectedSiteId, setSelectedSiteId] = useState(null)
  const [isCreatingSite, setIsCreatingSite] = useState(false)
  const [isDeletingSite, setIsDeletingSite] = useState(false)
  const [isSiteDeleteDialogOpen, setIsSiteDeleteDialogOpen] = useState(false)

  const loadSites = useCallback(async () => {
    setIsLoadingSites(true)
    try {
      const data = await listSites(id)
      setSites(data)
      setSiteError('')
    } catch {
      setSiteError('Unable to load sites. Please try again.')
    } finally {
      setIsLoadingSites(false)
    }
  }, [id])

  useEffect(() => {
    let cancelled = false

    async function load() {
      setIsLoading(true)
      setLoadError('')
      try {
        const data = await getProject(id)
        if (cancelled) return
        setProject(data)
        setTitle(data.title)
        setComment(data.comment)
        setStatusValue(data.status)
        setBaseline({ title: data.title, comment: data.comment, status: data.status })
        // Needed for the Comments section's moderator check (opportunity
        // manager), same as OpportunityEditorPage computes for its own page.
        const opportunityData = await getOpportunity(data.opportunity)
        if (cancelled) return
        setOpportunity(opportunityData)
      } catch (err) {
        if (!cancelled) {
          setLoadError(
            err.response?.status === 404 ? 'Project not found.' : 'Unable to load this project. You may not have access to it.',
          )
        }
      } finally {
        if (!cancelled) setIsLoading(false)
      }
    }

    load()
    return () => {
      cancelled = true
    }
  }, [id])

  useEffect(() => {
    let cancelled = false
    async function run() {
      if (!cancelled) await loadSites()
    }
    run()
    return () => {
      cancelled = true
    }
  }, [loadSites])

  const canWrite =
    opportunity && user && (opportunity.manager === user.id || opportunity.delegates?.includes(user.id))

  const isDirty =
    baseline && (title !== baseline.title || comment !== baseline.comment || Number(statusValue) !== Number(baseline.status))

  function handleBack() {
    if (isDirty && !window.confirm('You have unsaved changes. Leave without saving?')) {
      return
    }
    navigate(`/opportunities/${project.opportunity}`)
  }

  async function handleSave(event) {
    event.preventDefault()
    setSaveError('')

    if (!title.trim()) {
      setSaveError('Title is required.')
      return
    }

    setIsSaving(true)
    try {
      const updated = await updateProject(id, { title: title.trim(), comment, status: Number(statusValue) || 0 })
      setProject(updated)
      setTitle(updated.title)
      setComment(updated.comment)
      setStatusValue(updated.status)
      setBaseline({ title: updated.title, comment: updated.comment, status: updated.status })
      setSavedAt(new Date())
    } catch (err) {
      const data = err.response?.data
      if (data && typeof data === 'object') {
        const firstError = Object.values(data).flat()[0]
        setSaveError(firstError || 'Unable to save changes. Please try again.')
      } else {
        setSaveError('Unable to save changes. Please try again.')
      }
    } finally {
      setIsSaving(false)
    }
  }

  useEffect(() => {
    if (!isDirty) return undefined
    function handleBeforeUnload(event) {
      event.preventDefault()
      event.returnValue = ''
    }
    window.addEventListener('beforeunload', handleBeforeUnload)
    return () => window.removeEventListener('beforeunload', handleBeforeUnload)
  }, [isDirty])

  async function handleNewSite() {
    setSiteError('')
    setIsCreatingSite(true)
    try {
      const site = await createSite(id, { title: 'Untitled Site', comment: '' })
      navigate(`/sites/${site.id}`)
    } catch {
      setSiteError('Unable to create a new site. Please try again.')
    } finally {
      setIsCreatingSite(false)
    }
  }

  function handleEditSite() {
    if (selectedSiteId) navigate(`/sites/${selectedSiteId}`)
  }

  async function handleConfirmDeleteSite() {
    if (!selectedSiteId) return
    setSiteError('')
    setIsDeletingSite(true)
    try {
      await deleteSite(selectedSiteId)
      setSelectedSiteId(null)
      await loadSites()
    } catch {
      setSiteError('Unable to delete the site. Please try again.')
    } finally {
      setIsDeletingSite(false)
      setIsSiteDeleteDialogOpen(false)
    }
  }

  const selectedSite = sites.find((site) => site.id === selectedSiteId) || null

  const siteColumns = useMemo(
    () => [
      { key: 'title', header: 'Name' },
      { key: 'modified_at', header: 'Last edited', render: (site) => formatDate(site.modified_at) },
      { key: 'created_at', header: 'Created', render: (site) => formatDate(site.created_at) },
    ],
    [],
  )

  const projectJcodes = useMemo(() => {
    const uniqueJcodes = new Map()
    sites.forEach((site) => {
      if (site.jcode) uniqueJcodes.set(site.jcode.id, site.jcode)
    })
    return [...uniqueJcodes.values()]
  }, [sites])

  const projectJcodeColumns = useMemo(
    () => [
      { key: 'id', header: 'Jcode' },
      { key: 'state', header: 'State' },
      { key: 'county', header: 'County', render: (jcode) => jcode.county || '—' },
      { key: 'place_name_short', header: 'Region' },
    ],
    [],
  )

  if (isLoading) {
    return (
      <main className="editor-page">
        <p className="text-sm">Loading project…</p>
      </main>
    )
  }

  if (loadError) {
    return (
      <main className="editor-page">
        <p className="form-error" role="alert">
          {loadError}
        </p>
        <Link to="/opportunities">← Back to Opportunities</Link>
      </main>
    )
  }

  return (
    <main className="editor-page">
      <button type="button" className="editor-back" onClick={handleBack}>
        ← Back to Opportunity
      </button>

      <form className="editor-card" onSubmit={handleSave}>
        <div className="editor-title-row">
          <h1>Project Editor</h1>
          {!canWrite && <span className="editor-readonly-badge">Read-only</span>}
        </div>

        {saveError && (
          <p className="form-error" role="alert">
            {saveError}
          </p>
        )}
        {savedAt && !isDirty && !saveError && <p className="form-success text-sm">Saved.</p>}

        <label className="editor-field">
          <span className="label">Title</span>
          <input
            type="text"
            value={title}
            onChange={(event) => setTitle(event.target.value)}
            maxLength={100}
            disabled={!canWrite}
            required
          />
        </label>

        <label className="editor-field">
          <span className="label">Comment</span>
          <textarea
            rows={4}
            value={comment}
            onChange={(event) => setComment(event.target.value)}
            maxLength={1000}
            disabled={!canWrite}
          />
        </label>

        <label className="editor-field">
          <span className="label">Status</span>
          <input
            type="number"
            value={statusValue}
            onChange={(event) => setStatusValue(event.target.value)}
            disabled={!canWrite}
          />
        </label>

        <dl className="editor-meta">
          <div>
            <dt className="label">Created</dt>
            <dd>{formatDate(project.created_at)}</dd>
          </div>
          <div>
            <dt className="label">Last modified</dt>
            <dd>{formatDate(project.modified_at)}</dd>
          </div>
        </dl>

        {canWrite && (
          <button type="submit" className="editor-save" disabled={!isDirty || isSaving}>
            {isSaving ? 'Saving…' : 'Save'}
          </button>
        )}
      </form>

      <section className="editor-section">
        <div className="editor-section-header">
          <h2>Sites</h2>
        </div>

        {siteError && (
          <p className="form-error" role="alert">
            {siteError}
          </p>
        )}

        <div className="action-toolbar">
          {canWrite && (
            <button type="button" onClick={handleNewSite} disabled={isCreatingSite}>
              {isCreatingSite ? 'Creating…' : 'New Site'}
            </button>
          )}
          <button type="button" onClick={handleEditSite} disabled={!selectedSite}>
            Edit
          </button>
          {canWrite && (
            <button
              type="button"
              onClick={() => setIsSiteDeleteDialogOpen(true)}
              disabled={!selectedSite || isDeletingSite}
            >
              Delete
            </button>
          )}
        </div>

        {isLoadingSites ? (
          <p className="text-sm">Loading sites…</p>
        ) : (
          <DataTable
            columns={siteColumns}
            rows={sites}
            getRowId={(site) => site.id}
            selectedId={selectedSiteId}
            onSelectRow={setSelectedSiteId}
            emptyMessage="No sites yet."
          />
        )}
      </section>

      <section className="editor-section">
        <div className="editor-section-header">
          <h2>Associated Jurisdictions</h2>
        </div>

        {isLoadingSites ? (
          <p className="text-sm">Loading Jcodes…</p>
        ) : (
          <DataTable
            columns={projectJcodeColumns}
            rows={projectJcodes}
            getRowId={(jcode) => jcode.id}
            selectedId={null}
            onSelectRow={() => {}}
            emptyMessage="No Jcodes are assigned to this project's sites."
          />
        )}
      </section>

      {opportunity && (
        <section className="editor-section">
          <div className="editor-section-header">
            <h2>Comments</h2>
          </div>
          <CommentThread
            projectId={id}
            isOwner={opportunity.manager === user.id}
            commentsEnabled={project.comments_enabled}
          />
        </section>
      )}

      <ConfirmDialog
        isOpen={isSiteDeleteDialogOpen}
        title="Delete site?"
        message={`This will permanently delete "${selectedSite?.title}" and all of its Strategies. This cannot be undone.`}
        confirmLabel="Delete"
        isDangerous
        isBusy={isDeletingSite}
        onConfirm={handleConfirmDeleteSite}
        onCancel={() => setIsSiteDeleteDialogOpen(false)}
      />
    </main>
  )
}
