import { useCallback, useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { cloneProject, createProject, deleteProject, listProjects } from '../api/projects'
import { listFocusAreaChildren, listFocusAreaOptions } from '../api/focusAreas'
import DataTable from '../components/DataTable'
import ConfirmDialog from '../components/ConfirmDialog'
import { useAuth } from '../hooks/useAuth'
import { formatDate } from '../utils/formatDate'
import '../styles/formFeedback.css'
import '../styles/actionToolbar.css'
import './ProjectsPage.css'

export default function ProjectsPage() {
  const { user } = useAuth()
  const navigate = useNavigate()

  const [projects, setProjects] = useState([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState('')
  const [search, setSearch] = useState('')
  const [selectedId, setSelectedId] = useState(null)
  const [isCreating, setIsCreating] = useState(false)
  const [isCloning, setIsCloning] = useState(false)
  const [isDeleting, setIsDeleting] = useState(false)
  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false)

  const loadProjects = useCallback(async () => {
    try {
      const data = await listProjects()
      setProjects(data)
      setError('')
    } catch {
      setError('Unable to load projects. Please try again.')
    } finally {
      setIsLoading(false)
    }
  }, [])

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

  const filteredProjects = useMemo(() => {
    const query = search.trim().toLowerCase()
    if (!query) return projects
    return projects.filter(
      (project) =>
        project.name.toLowerCase().includes(query) ||
        project.description.toLowerCase().includes(query),
    )
  }, [projects, search])

  const selectedProject = projects.find((project) => project.id === selectedId) || null
  const canWriteSelected =
    selectedProject &&
    user &&
    (selectedProject.owner === user.id || selectedProject.editors?.includes(user.id))

  async function handleNew() {
    setError('')
    setIsCreating(true)
    try {
      const options = await listFocusAreaOptions()
      if (!options.length) {
        setError('No focus areas are configured. Contact an administrator.')
        return
      }
      // options[0] may be a non-leaf L1-L2 node (one with children); default
      // to its first child so the new project starts on a genuine leaf and
      // isn't immediately unsavable until the user picks a specific one.
      const children = await listFocusAreaChildren(options[0].id)
      const defaultFocusAreaId = children.length > 0 ? children[0].id : options[0].id
      const project = await createProject({
        name: 'Untitled Project',
        description: '',
        focus_area: defaultFocusAreaId,
      })
      navigate(`/projects/${project.id}`)
    } catch {
      setError('Unable to create a new project. Please try again.')
    } finally {
      setIsCreating(false)
    }
  }

  function handleView() {
    if (selectedProject) navigate(`/projects/${selectedProject.id}`)
  }

  async function handleClone() {
    if (!selectedProject) return
    setError('')
    setIsCloning(true)
    try {
      await cloneProject(selectedProject.id)
      await loadProjects()
    } catch {
      setError('Unable to clone the project. Please try again.')
    } finally {
      setIsCloning(false)
    }
  }

  async function handleConfirmDelete() {
    if (!selectedProject) return
    setError('')
    setIsDeleting(true)
    try {
      await deleteProject(selectedProject.id)
      setSelectedId(null)
      await loadProjects()
    } catch {
      setError('Unable to delete the project. Please try again.')
    } finally {
      setIsDeleting(false)
      setIsDeleteDialogOpen(false)
    }
  }

  const columns = [
    { key: 'name', header: 'Title' },
    {
      key: 'description',
      header: 'Description',
      render: (project) => project.description || <span className="text-sm">—</span>,
    },
    {
      key: 'modified_at',
      header: 'Last modified',
      render: (project) => formatDate(project.modified_at),
    },
    {
      key: 'created_at',
      header: 'Created',
      render: (project) => formatDate(project.created_at),
    },
  ]

  return (
    <main className="projects-page">
      <div className="projects-page-header">
        <h1>Projects</h1>
        <input
          type="search"
          className="projects-search"
          placeholder="Search projects…"
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
        <button type="button" onClick={handleNew} disabled={isCreating}>
          {isCreating ? 'Creating…' : 'New Project'}
        </button>
        <button type="button" onClick={handleView} disabled={!selectedProject}>
          View
        </button>
        <button
          type="button"
          onClick={() => setIsDeleteDialogOpen(true)}
          disabled={!selectedProject || !canWriteSelected || isDeleting}
        >
          Delete
        </button>
        <button type="button" onClick={handleClone} disabled={!selectedProject || isCloning}>
          {isCloning ? 'Cloning…' : 'Clone'}
        </button>
      </div>

      {isLoading ? (
        <p className="text-sm">Loading projects…</p>
      ) : (
        <DataTable
          columns={columns}
          rows={filteredProjects}
          getRowId={(project) => project.id}
          selectedId={selectedId}
          onSelectRow={setSelectedId}
          emptyMessage={
            projects.length === 0
              ? 'No projects yet. Create one to get started.'
              : 'No projects match your search.'
          }
        />
      )}

      <ConfirmDialog
        isOpen={isDeleteDialogOpen}
        title="Delete project?"
        message={`This will permanently delete "${selectedProject?.name}" along with all of its Courses of Action and Interventions. This cannot be undone.`}
        confirmLabel="Delete"
        isDangerous
        isBusy={isDeleting}
        onConfirm={handleConfirmDelete}
        onCancel={() => setIsDeleteDialogOpen(false)}
      />
    </main>
  )
}
