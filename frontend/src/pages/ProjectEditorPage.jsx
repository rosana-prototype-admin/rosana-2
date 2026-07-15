import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { getProject, updateProject } from '../api/projects'
import { getFocusArea, listFocusAreaChildren, listFocusAreaOptions } from '../api/focusAreas'
import {
  cloneCourseOfAction,
  createCourseOfAction,
  deleteCourseOfAction,
  listCoursesOfAction,
} from '../api/coursesOfAction'
import DataTable from '../components/DataTable'
import ConfirmDialog from '../components/ConfirmDialog'
import { useAuth } from '../hooks/useAuth'
import { formatDate } from '../utils/formatDate'
import '../styles/editorForm.css'
import '../styles/formFeedback.css'
import '../styles/actionToolbar.css'
import './ProjectEditorPage.css'

export default function ProjectEditorPage() {
  const { id } = useParams()
  const { user } = useAuth()
  const navigate = useNavigate()

  const [project, setProject] = useState(null)
  const [isLoading, setIsLoading] = useState(true)
  const [loadError, setLoadError] = useState('')

  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [focusAreaOptions, setFocusAreaOptions] = useState([])
  const [selectedL1L2, setSelectedL1L2] = useState('')
  const [childOptions, setChildOptions] = useState([])
  const [selectedChild, setSelectedChild] = useState('')

  const [baseline, setBaseline] = useState(null)
  const [saveError, setSaveError] = useState('')
  const [isSaving, setIsSaving] = useState(false)
  const [savedAt, setSavedAt] = useState(null)
  const [isLoadingChildren, setIsLoadingChildren] = useState(false)

  const [coursesOfAction, setCoursesOfAction] = useState([])
  const [isLoadingCoas, setIsLoadingCoas] = useState(true)
  const [coaError, setCoaError] = useState('')
  const [selectedCoaId, setSelectedCoaId] = useState(null)
  const [isCreatingCoa, setIsCreatingCoa] = useState(false)
  const [isCloningCoa, setIsCloningCoa] = useState(false)
  const [isDeletingCoa, setIsDeletingCoa] = useState(false)
  const [isCoaDeleteDialogOpen, setIsCoaDeleteDialogOpen] = useState(false)

  const canWrite =
    project && user && (project.owner === user.id || project.editors?.includes(user.id))

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

  useEffect(() => {
    let cancelled = false

    async function load() {
      setIsLoading(true)
      setLoadError('')
      try {
        const [projectData, options] = await Promise.all([getProject(id), listFocusAreaOptions()])
        if (cancelled) return

        const focusArea = await getFocusArea(projectData.focus_area)
        const l1l2Id = focusArea.level === 2 ? focusArea.id : focusArea.parent
        await loadChildren(l1l2Id)
        if (cancelled) return

        setProject(projectData)
        setFocusAreaOptions(options)
        setName(projectData.name)
        setDescription(projectData.description)
        setSelectedL1L2(l1l2Id)
        setSelectedChild(focusArea.level === 3 ? focusArea.id : '')
        setBaseline({
          name: projectData.name,
          description: projectData.description,
          focusAreaId: projectData.focus_area,
        })
      } catch (err) {
        if (!cancelled) {
          setLoadError(
            err.response?.status === 404
              ? 'Project not found.'
              : "Unable to load this project. You may not have access to it.",
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
  }, [id, loadChildren])

  const loadCoursesOfAction = useCallback(async () => {
    try {
      const data = await listCoursesOfAction(id)
      setCoursesOfAction(data)
      setCoaError('')
    } catch {
      setCoaError('Unable to load Courses of Action. Please try again.')
    } finally {
      setIsLoadingCoas(false)
    }
  }, [id])

  useEffect(() => {
    let cancelled = false
    async function run() {
      if (!cancelled) await loadCoursesOfAction()
    }
    run()
    return () => {
      cancelled = true
    }
  }, [loadCoursesOfAction])

  async function handleNewCoa() {
    setCoaError('')
    setIsCreatingCoa(true)
    try {
      const coa = await createCourseOfAction(id, { name: 'Untitled Course of Action', description: '' })
      navigate(`/projects/${id}/courses-of-action/${coa.id}`)
    } catch {
      setCoaError('Unable to create a new Course of Action. Please try again.')
    } finally {
      setIsCreatingCoa(false)
    }
  }

  const selectedCoa = coursesOfAction.find((coa) => coa.id === selectedCoaId) || null

  function handleEditCoa() {
    if (selectedCoa) navigate(`/projects/${id}/courses-of-action/${selectedCoa.id}`)
  }

  async function handleCloneCoa() {
    if (!selectedCoa) return
    setCoaError('')
    setIsCloningCoa(true)
    try {
      await cloneCourseOfAction(selectedCoa.id)
      await loadCoursesOfAction()
    } catch {
      setCoaError('Unable to clone the Course of Action. Please try again.')
    } finally {
      setIsCloningCoa(false)
    }
  }

  async function handleConfirmDeleteCoa() {
    if (!selectedCoa) return
    setCoaError('')
    setIsDeletingCoa(true)
    try {
      await deleteCourseOfAction(selectedCoa.id)
      setSelectedCoaId(null)
      await loadCoursesOfAction()
    } catch {
      setCoaError('Unable to delete the Course of Action. Please try again.')
    } finally {
      setIsDeletingCoa(false)
      setIsCoaDeleteDialogOpen(false)
    }
  }

  const coaColumns = useMemo(
    () => [
      { key: 'name', header: 'Name' },
      {
        key: 'description',
        header: 'Description',
        render: (coa) => coa.description || <span className="text-sm">—</span>,
      },
      {
        key: 'projection',
        header: 'Projection',
        sortValue: (coa) => coa.projection?.status || '',
        render: (coa) => coa.projection?.status || '—',
      },
      {
        key: 'modified_at',
        header: 'Last modified',
        render: (coa) => formatDate(coa.modified_at),
      },
    ],
    [],
  )

  async function handleL1L2Change(event) {
    const newId = Number(event.target.value)
    setSelectedL1L2(newId)
    setSelectedChild('')
    await loadChildren(newId)
  }

  const finalFocusAreaId = childOptions.length > 0 ? selectedChild : selectedL1L2

  const isDirty =
    baseline &&
    (name !== baseline.name ||
      description !== baseline.description ||
      Number(finalFocusAreaId) !== Number(baseline.focusAreaId))

  function handleBack() {
    if (isDirty && !window.confirm('You have unsaved changes. Leave without saving?')) {
      return
    }
    navigate('/projects')
  }

  async function handleSave(event) {
    event.preventDefault()
    setSaveError('')

    if (!name.trim()) {
      setSaveError('Name is required.')
      return
    }
    if (isLoadingChildren) {
      setSaveError('Still loading focus area options — please try again in a moment.')
      return
    }
    if (childOptions.length > 0 && !selectedChild) {
      setSaveError('Please select a more specific focus area.')
      return
    }

    setIsSaving(true)
    try {
      const updated = await updateProject(id, {
        name: name.trim(),
        description,
        focus_area: finalFocusAreaId,
      })
      setProject(updated)
      setBaseline({ name: updated.name, description: updated.description, focusAreaId: updated.focus_area })
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
        <Link to="/projects">← Back to Projects</Link>
      </main>
    )
  }

  return (
    <main className="editor-page">
      <button type="button" className="editor-back" onClick={handleBack}>
        ← Back to Projects
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
          <span className="label">Name</span>
          <input
            type="text"
            value={name}
            onChange={(event) => setName(event.target.value)}
            disabled={!canWrite}
            required
          />
        </label>

        <label className="editor-field">
          <span className="label">Description</span>
          <textarea
            rows={4}
            value={description}
            onChange={(event) => setDescription(event.target.value)}
            disabled={!canWrite}
          />
        </label>

        <div className="editor-focus-area-row">
          <label className="editor-field">
            <span className="label">Focus area</span>
            <select value={selectedL1L2} onChange={handleL1L2Change} disabled={!canWrite}>
              {focusAreaOptions.map((option) => (
                <option key={option.id} value={option.id}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>

          {childOptions.length > 0 && (
            <label className="editor-field">
              <span className="label">Specific focus area</span>
              <select
                value={selectedChild}
                onChange={(event) => setSelectedChild(event.target.value)}
                disabled={!canWrite || isLoadingChildren}
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
          <button type="submit" className="editor-save" disabled={!isDirty || isSaving || isLoadingChildren}>
            {isSaving ? 'Saving…' : 'Save'}
          </button>
        )}
      </form>

      <section className="coa-section">
        <div className="coa-section-header">
          <h2>Courses of Action</h2>
        </div>

        {coaError && (
          <p className="form-error" role="alert">
            {coaError}
          </p>
        )}

        {canWrite && (
          <div className="action-toolbar">
            <button type="button" onClick={handleNewCoa} disabled={isCreatingCoa}>
              {isCreatingCoa ? 'Creating…' : 'New'}
            </button>
            <button type="button" onClick={handleEditCoa} disabled={!selectedCoa}>
              Edit
            </button>
            <button
              type="button"
              onClick={() => setIsCoaDeleteDialogOpen(true)}
              disabled={!selectedCoa || isDeletingCoa}
            >
              Delete
            </button>
            <button type="button" onClick={handleCloneCoa} disabled={!selectedCoa || isCloningCoa}>
              {isCloningCoa ? 'Cloning…' : 'Clone'}
            </button>
          </div>
        )}

        {isLoadingCoas ? (
          <p className="text-sm">Loading Courses of Action…</p>
        ) : (
          <DataTable
            columns={coaColumns}
            rows={coursesOfAction}
            getRowId={(coa) => coa.id}
            selectedId={selectedCoaId}
            onSelectRow={setSelectedCoaId}
            emptyMessage="No Courses of Action yet."
          />
        )}
      </section>

      <ConfirmDialog
        isOpen={isCoaDeleteDialogOpen}
        title="Delete Course of Action?"
        message={`This will permanently delete "${selectedCoa?.name}" along with all of its Interventions. This cannot be undone.`}
        confirmLabel="Delete"
        isDangerous
        isBusy={isDeletingCoa}
        onConfirm={handleConfirmDeleteCoa}
        onCancel={() => setIsCoaDeleteDialogOpen(false)}
      />
    </main>
  )
}
