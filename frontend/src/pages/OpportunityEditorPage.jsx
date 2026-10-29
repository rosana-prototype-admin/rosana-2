import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { createOpportunity, getOpportunity, updateOpportunity } from '../api/opportunities'
import { listFocusAreaChildren, listFocusAreaOptions } from '../api/focusAreas'
import { getGroup, listGroupMembers } from '../api/groups'
import { createProject, deleteProject, listProjects } from '../api/projects'
import DataTable from '../components/DataTable'
import ConfirmDialog from '../components/ConfirmDialog'
import GroupSearchField from '../components/GroupSearchField'
import Tooltip from '../components/Tooltip'
import { useAuth } from '../hooks/useAuth'
import { formatDate } from '../utils/formatDate'
import '../styles/editorForm.css'
import '../styles/formFeedback.css'
import '../styles/actionToolbar.css'
import './OpportunityEditorPage.css'

const OPPORTUNITY_STATUS_OPTIONS = [
  { value: 'drafting', label: 'Drafting' },
  { value: 'review', label: 'Review' },
  { value: 'implementation', label: 'Implementation' },
  { value: 'completed', label: 'Completed' },
  { value: 'cancelled', label: 'Cancelled' },
]

export default function OpportunityEditorPage() {
  const { id } = useParams()
  const isNew = !id
  const { user } = useAuth()
  const navigate = useNavigate()

  const [opportunity, setOpportunity] = useState(null)
  const [isLoading, setIsLoading] = useState(true)
  const [loadError, setLoadError] = useState('')

  const [title, setTitle] = useState('')
  const [comment, setComment] = useState('')
  const [statusValue, setStatusValue] = useState('drafting')
  const [leadAgency, setLeadAgency] = useState(null)
  const [assocAgencies, setAssocAgencies] = useState([])
  const [managerCandidates, setManagerCandidates] = useState([])
  const [isLoadingManagerCandidates, setIsLoadingManagerCandidates] = useState(false)
  const [managerId, setManagerId] = useState('')

  const [focusAreaOptions, setFocusAreaOptions] = useState([])
  const [selectedL1L2, setSelectedL1L2] = useState('')
  const [childOptions, setChildOptions] = useState([])
  const [selectedChild, setSelectedChild] = useState('')
  const [isLoadingChildren, setIsLoadingChildren] = useState(false)

  const [baseline, setBaseline] = useState(null)
  const [saveError, setSaveError] = useState('')
  const [isSaving, setIsSaving] = useState(false)
  const [savedAt, setSavedAt] = useState(null)

  const [projects, setProjects] = useState([])
  const [isLoadingProjects, setIsLoadingProjects] = useState(false)
  const [projectError, setProjectError] = useState('')
  const [selectedProjectId, setSelectedProjectId] = useState(null)
  const [isCreatingProject, setIsCreatingProject] = useState(false)
  const [isDeletingProject, setIsDeletingProject] = useState(false)
  const [isProjectDeleteDialogOpen, setIsProjectDeleteDialogOpen] = useState(false)

  // Set right after a successful creation, to the newly created id -- lets
  // the load effect below (which still fires because `id` just changed from
  // undefined to a real id) skip re-fetching data we just set ourselves,
  // instead of flashing a loading state or racing the fetch.
  const skipNextLoadRef = useRef(null)

  const canWrite =
    isNew || (opportunity && user && (opportunity.manager === user.id || opportunity.delegates?.includes(user.id)))

  const loadChildren = useCallback(async (parentId) => {
    if (!parentId) {
      setChildOptions([])
      return []
    }
    setIsLoadingChildren(true)
    try {
      const children = await listFocusAreaChildren(parentId)
      setChildOptions(children)
      return children
    } finally {
      setIsLoadingChildren(false)
    }
  }, [])

  const loadProjects = useCallback(async () => {
    if (isNew) return
    setIsLoadingProjects(true)
    try {
      const data = await listProjects(id)
      setProjects(data)
      setProjectError('')
    } catch {
      setProjectError('Unable to load projects. Please try again.')
    } finally {
      setIsLoadingProjects(false)
    }
  }, [id, isNew])

  useEffect(() => {
    let cancelled = false

    async function load() {
      if (skipNextLoadRef.current !== null && skipNextLoadRef.current === Number(id)) {
        skipNextLoadRef.current = null
        return
      }

      setIsLoading(true)
      setLoadError('')
      try {
        const options = await listFocusAreaOptions()
        if (cancelled) return
        setFocusAreaOptions(options)

        if (isNew) {
          setIsLoading(false)
          return
        }

        const opportunityData = await getOpportunity(id)
        if (cancelled) return

        const [leadAgencyData, assocAgencyData] = await Promise.all([
          getGroup(opportunityData.lead_agency),
          Promise.all((opportunityData.assoc_agencies || []).map((groupId) => getGroup(groupId))),
        ])
        if (cancelled) return

        if (opportunityData.specific_focus_area) {
          await loadChildren(opportunityData.focus_area)
          if (cancelled) return
        } else {
          setChildOptions([])
        }

        setOpportunity(opportunityData)
        setTitle(opportunityData.title)
        setComment(opportunityData.comment)
        setStatusValue(opportunityData.status)
        setLeadAgency(leadAgencyData)
        setAssocAgencies(assocAgencyData)
        setSelectedL1L2(opportunityData.focus_area)
        setSelectedChild(opportunityData.specific_focus_area || '')
        setManagerId(opportunityData.manager)
        setBaseline({
          title: opportunityData.title,
          comment: opportunityData.comment,
          status: opportunityData.status,
          leadAgencyId: opportunityData.lead_agency,
          assocAgencyIds: [...(opportunityData.assoc_agencies || [])].sort(),
        })
      } catch (err) {
        if (!cancelled) {
          setLoadError(
            err.response?.status === 404
              ? 'Opportunity not found.'
              : "Unable to load this opportunity. You may not have access to it.",
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
  }, [id, isNew, loadChildren])

  useEffect(() => {
    let cancelled = false
    async function run() {
      if (!cancelled) await loadProjects()
    }
    run()
    return () => {
      cancelled = true
    }
  }, [loadProjects])

  // Manager candidates are the lead agency's admin plus its direct
  // (non-transitive) members, matching the backend's manager-eligibility
  // validation exactly. listGroupMembers already returns this flattened
  // admin+members shape (id, username, first_name, last_name, email, role,
  // roles) directly -- no nested `.user` to unwrap.
  useEffect(() => {
    let cancelled = false

    async function run() {
      if (!leadAgency) {
        setManagerCandidates([])
        return
      }
      setIsLoadingManagerCandidates(true)
      try {
        const candidates = await listGroupMembers(leadAgency.id)
        if (cancelled) return
        setManagerCandidates(candidates)
        setManagerId((current) => {
          if (candidates.some((candidate) => candidate.id === current)) return current
          if (isNew && candidates.some((candidate) => candidate.id === user.id)) return user.id
          return ''
        })
      } catch {
        if (!cancelled) setManagerCandidates([])
      } finally {
        if (!cancelled) setIsLoadingManagerCandidates(false)
      }
    }

    run()
    return () => {
      cancelled = true
    }
  }, [leadAgency, isNew, user])

  async function handleL1L2Change(event) {
    const newId = Number(event.target.value)
    setSelectedL1L2(newId)
    setSelectedChild('')
    await loadChildren(newId)
  }

  function handleSelectLeadAgency(group) {
    setLeadAgency(group)
  }

  function handleAddAssocAgency(group) {
    setAssocAgencies((current) => (current.some((g) => g.id === group.id) ? current : [...current, group]))
  }

  function handleRemoveAssocAgency(groupId) {
    setAssocAgencies((current) => current.filter((g) => g.id !== groupId))
  }

  const isDirty = isNew
    ? Boolean(title.trim() || comment.trim() || leadAgency)
    : baseline &&
      (title !== baseline.title ||
        comment !== baseline.comment ||
        statusValue !== baseline.status ||
        leadAgency?.id !== baseline.leadAgencyId ||
        JSON.stringify(assocAgencies.map((g) => g.id).sort()) !== JSON.stringify(baseline.assocAgencyIds))

  function handleBack() {
    if (isDirty && !window.confirm('You have unsaved changes. Leave without saving?')) {
      return
    }
    navigate('/opportunities')
  }

  async function handleSubmit(event) {
    event.preventDefault()
    setSaveError('')

    if (!title.trim()) {
      setSaveError('Title is required.')
      return
    }
    if (!leadAgency) {
      setSaveError('Lead agency is required.')
      return
    }
    if (isNew && !managerId) {
      setSaveError('Manager is required, and must be a member of the lead agency.')
      return
    }
    if (isLoadingChildren) {
      setSaveError('Still loading focus area options — please try again in a moment.')
      return
    }
    if (isNew && childOptions.length > 0 && !selectedChild) {
      setSaveError('Please select a more specific focus area.')
      return
    }

    setIsSaving(true)
    try {
      const payload = {
        title: title.trim(),
        comment,
        status: statusValue,
        lead_agency: leadAgency.id,
        assoc_agencies: assocAgencies.map((g) => g.id),
      }

      if (isNew) {
        payload.manager = Number(managerId)
        payload.focus_area = selectedL1L2
        if (childOptions.length > 0) payload.specific_focus_area = selectedChild
        const created = await createOpportunity(payload)
        setOpportunity(created)
        setTitle(created.title)
        setComment(created.comment)
        setStatusValue(created.status)
        setManagerId(created.manager)
        setBaseline({
          title: created.title,
          comment: created.comment,
          status: created.status,
          leadAgencyId: created.lead_agency,
          assocAgencyIds: [...(created.assoc_agencies || [])].sort(),
        })
        setSavedAt(new Date())
        skipNextLoadRef.current = created.id
        navigate(`/opportunities/${created.id}`, { replace: true })
        return
      }

      const updated = await updateOpportunity(id, payload)
      setOpportunity(updated)
      setTitle(updated.title)
      setComment(updated.comment)
      setStatusValue(updated.status)
      setBaseline({
        title: updated.title,
        comment: updated.comment,
        status: updated.status,
        leadAgencyId: updated.lead_agency,
        assocAgencyIds: [...(updated.assoc_agencies || [])].sort(),
      })
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

  async function handleNewProject() {
    setProjectError('')
    setIsCreatingProject(true)
    try {
      const project = await createProject(id, { title: 'Untitled Project', comment: '' })
      navigate(`/projects/${project.id}`)
    } catch {
      setProjectError('Unable to create a new project. Please try again.')
    } finally {
      setIsCreatingProject(false)
    }
  }

  function handleEditProject() {
    if (selectedProjectId) navigate(`/projects/${selectedProjectId}`)
  }

  async function handleConfirmDeleteProject() {
    if (!selectedProjectId) return
    setProjectError('')
    setIsDeletingProject(true)
    try {
      await deleteProject(selectedProjectId)
      setSelectedProjectId(null)
      await loadProjects()
    } catch {
      setProjectError('Unable to delete the project. Please try again.')
    } finally {
      setIsDeletingProject(false)
      setIsProjectDeleteDialogOpen(false)
    }
  }

  const selectedProject = projects.find((project) => project.id === selectedProjectId) || null

  const projectColumns = useMemo(
    () => [
      { key: 'title', header: 'Name' },
      { key: 'modified_at', header: 'Last edited', render: (project) => formatDate(project.modified_at) },
      { key: 'created_at', header: 'Created', render: (project) => formatDate(project.created_at) },
    ],
    [],
  )

  const managerLabel = (candidate) => `${candidate.first_name} ${candidate.last_name}`.trim() || candidate.username

  if (isLoading) {
    return (
      <main className="editor-page">
        <p className="text-sm">Loading opportunity…</p>
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
        ← Back to Opportunities
      </button>

      <form className="editor-card" onSubmit={handleSubmit}>
        <div className="editor-title-row">
          <h1>{isNew ? 'New Opportunity' : 'Opportunity Editor'}</h1>
          {!isNew && !canWrite && <span className="editor-readonly-badge">Read-only</span>}
          {!isNew && (
            <Link to={`/opportunities/${id}/members`} className="editor-members-link">
              Members
            </Link>
          )}
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
            disabled={!canWrite}
            maxLength={100}
            required
          />
        </label>

        <label className="editor-field">
          <span className="label">Comment</span>
          <textarea
            rows={4}
            value={comment}
            onChange={(event) => setComment(event.target.value)}
            disabled={!canWrite}
            maxLength={1000}
          />
        </label>

        <label className="editor-field">
          <span className="label">Status</span>
          <select
            value={statusValue}
            onChange={(event) => setStatusValue(event.target.value)}
            disabled={!canWrite}
          >
            {OPPORTUNITY_STATUS_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>

        <div className="editor-field">
          <div className="editor-field-label-row">
            <span className="label">Lead Agency</span>
            <Tooltip>
              Choose the organization assuming primary responsibility for this Opportunity. The organization must be
              registered within Rosana to be selected.
            </Tooltip>
          </div>
          {leadAgency ? (
            <div className="chip-row">
              <span className="chip">
                {leadAgency.name}
                {canWrite && (
                  <button type="button" className="chip-remove" onClick={() => setLeadAgency(null)}>
                    ×
                  </button>
                )}
              </span>
            </div>
          ) : (
            canWrite && <GroupSearchField onSelect={handleSelectLeadAgency} placeholder="Search agencies…" />
          )}
        </div>

        <label className="editor-field">
          <span className="label">Associate agencies</span>
          <div className="chip-row">
            {assocAgencies.map((group) => (
              <span key={group.id} className="chip">
                {group.name}
                {canWrite && (
                  <button
                    type="button"
                    className="chip-remove"
                    onClick={() => handleRemoveAssocAgency(group.id)}
                  >
                    ×
                  </button>
                )}
              </span>
            ))}
          </div>
          {canWrite && <GroupSearchField onSelect={handleAddAssocAgency} placeholder="Search agencies to add…" />}
        </label>

        <label className="editor-field">
          <span className="label">Manager</span>
          {isNew ? (
            <select
              value={managerId}
              onChange={(event) => setManagerId(event.target.value)}
              disabled={!leadAgency || isLoadingManagerCandidates}
            >
              <option value="">{leadAgency ? 'Select…' : 'Pick a lead agency first'}</option>
              {managerCandidates.map((candidate) => (
                <option key={candidate.id} value={candidate.id}>
                  {managerLabel(candidate)}
                </option>
              ))}
            </select>
          ) : (
            <span className="text-sm">
              {managerCandidates.find((candidate) => candidate.id === managerId)
                ? managerLabel(managerCandidates.find((candidate) => candidate.id === managerId))
                : `User #${managerId}`}
              {' — '}
              <Link to={`/opportunities/${id}/members`}>reassign via Members</Link>
            </span>
          )}
        </label>

        <div className="editor-focus-area-row">
          <label className="editor-field">
            <span className="label">Focus area</span>
            <select value={selectedL1L2} onChange={handleL1L2Change} disabled={!canWrite || !isNew}>
              <option value="">Select…</option>
              {focusAreaOptions.map((option) => (
                <option key={option.id} value={option.id}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>

          {(isNew ? childOptions.length > 0 : opportunity?.specific_focus_area) && (
            <label className="editor-field">
              <span className="label">Specific focus area</span>
              <select
                value={selectedChild}
                onChange={(event) => setSelectedChild(event.target.value)}
                disabled={!canWrite || !isNew || isLoadingChildren}
              >
                <option value="">Select…</option>
                {childOptions.map((option) => (
                  <option key={option.id} value={option.id}>
                    {option.name}
                  </option>
                ))}
              </select>
            </label>
          )}
        </div>
        {!isNew && <p className="text-sm">Focus area cannot be changed after creation.</p>}

        {!isNew && opportunity && (
          <dl className="editor-meta">
            <div>
              <dt className="label">Created</dt>
              <dd>{formatDate(opportunity.created_at)}</dd>
            </div>
            <div>
              <dt className="label">Last modified</dt>
              <dd>{formatDate(opportunity.modified_at)}</dd>
            </div>
          </dl>
        )}

        {canWrite && (
          <button type="submit" className="editor-save" disabled={(!isNew && !isDirty) || isSaving || isLoadingChildren}>
            {isSaving ? 'Saving…' : isNew ? 'Create' : 'Save'}
          </button>
        )}
      </form>

      {!isNew && opportunity && (
        <>
          <section className="editor-section">
            <div className="editor-section-header">
              <h2>Projects</h2>
            </div>

            {projectError && (
              <p className="form-error" role="alert">
                {projectError}
              </p>
            )}

            <div className="action-toolbar">
              {canWrite && (
                <button type="button" onClick={handleNewProject} disabled={isCreatingProject}>
                  {isCreatingProject ? 'Creating…' : 'New Project'}
                </button>
              )}
              <button type="button" onClick={handleEditProject} disabled={!selectedProject}>
                Edit
              </button>
              {canWrite && (
                <button
                  type="button"
                  onClick={() => setIsProjectDeleteDialogOpen(true)}
                  disabled={!selectedProject || isDeletingProject}
                >
                  Delete
                </button>
              )}
            </div>

            {isLoadingProjects ? (
              <p className="text-sm">Loading projects…</p>
            ) : (
              <DataTable
                columns={projectColumns}
                rows={projects}
                getRowId={(project) => project.id}
                selectedId={selectedProjectId}
                onSelectRow={setSelectedProjectId}
                emptyMessage="No projects yet."
              />
            )}
          </section>

          <ConfirmDialog
            isOpen={isProjectDeleteDialogOpen}
            title="Delete project?"
            message={`This will permanently delete "${selectedProject?.title}" and all of its Sites and Strategies. This cannot be undone.`}
            confirmLabel="Delete"
            isDangerous
            isBusy={isDeletingProject}
            onConfirm={handleConfirmDeleteProject}
            onCancel={() => setIsProjectDeleteDialogOpen(false)}
          />
        </>
      )}
    </main>
  )
}
