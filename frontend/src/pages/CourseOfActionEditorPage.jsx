import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { getProject } from '../api/projects'
import { getCourseOfAction, updateCourseOfAction } from '../api/coursesOfAction'
import { useAuth } from '../hooks/useAuth'
import { formatDate } from '../utils/formatDate'
import '../styles/editorForm.css'
import '../styles/formFeedback.css'
import './CourseOfActionEditorPage.css'

const PROJECTION_STATUS_LABELS = {
  pending: 'Pending',
  complete: 'Complete',
  failed: 'Failed',
}

export default function CourseOfActionEditorPage() {
  const { projectId, coaId } = useParams()
  const { user } = useAuth()
  const navigate = useNavigate()

  const [coa, setCoa] = useState(null)
  const [project, setProject] = useState(null)
  const [isLoading, setIsLoading] = useState(true)
  const [loadError, setLoadError] = useState('')

  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [baseline, setBaseline] = useState(null)

  const [saveError, setSaveError] = useState('')
  const [isSaving, setIsSaving] = useState(false)
  const [savedAt, setSavedAt] = useState(null)

  const canWrite =
    project && user && (project.owner === user.id || project.editors?.includes(user.id))

  useEffect(() => {
    let cancelled = false

    async function load() {
      setIsLoading(true)
      setLoadError('')
      try {
        const [coaData, projectData] = await Promise.all([getCourseOfAction(coaId), getProject(projectId)])
        if (cancelled) return

        setCoa(coaData)
        setProject(projectData)
        setName(coaData.name)
        setDescription(coaData.description)
        setBaseline({ name: coaData.name, description: coaData.description })
      } catch (err) {
        if (!cancelled) {
          setLoadError(
            err.response?.status === 404
              ? 'Course of Action not found.'
              : 'Unable to load this Course of Action. You may not have access to it.',
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
  }, [coaId, projectId])

  const isDirty = baseline && (name !== baseline.name || description !== baseline.description)

  function handleBack() {
    if (isDirty && !window.confirm('You have unsaved changes. Leave without saving?')) {
      return
    }
    navigate(`/projects/${projectId}`)
  }

  async function handleSave(event) {
    event.preventDefault()
    setSaveError('')

    if (!name.trim()) {
      setSaveError('Name is required.')
      return
    }

    setIsSaving(true)
    try {
      const updated = await updateCourseOfAction(coaId, { name: name.trim(), description })
      setCoa(updated)
      setBaseline({ name: updated.name, description: updated.description })
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
        <p className="text-sm">Loading Course of Action…</p>
      </main>
    )
  }

  if (loadError) {
    return (
      <main className="editor-page">
        <p className="form-error" role="alert">
          {loadError}
        </p>
        <Link to={`/projects/${projectId}`}>← Back to Project</Link>
      </main>
    )
  }

  return (
    <main className="editor-page">
      <button type="button" className="editor-back" onClick={handleBack}>
        ← Back to {project.name}
      </button>

      <form className="editor-card" onSubmit={handleSave}>
        <div className="editor-title-row">
          <h1>Course of Action Editor</h1>
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

        <dl className="editor-meta">
          <div>
            <dt className="label">Projection</dt>
            <dd>{PROJECTION_STATUS_LABELS[coa.projection?.status] || coa.projection?.status}</dd>
          </div>
          <div>
            <dt className="label">Created</dt>
            <dd>{formatDate(coa.created_at)}</dd>
          </div>
          <div>
            <dt className="label">Last modified</dt>
            <dd>{formatDate(coa.modified_at)}</dd>
          </div>
        </dl>

        {canWrite && (
          <button type="submit" className="editor-save" disabled={!isDirty || isSaving}>
            {isSaving ? 'Saving…' : 'Save'}
          </button>
        )}
      </form>

      <section className="coa-editor-interventions-placeholder text-sm">
        Interventions management is coming in a future update.
      </section>
    </main>
  )
}
