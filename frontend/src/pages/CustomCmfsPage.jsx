import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { deleteCmf, listCmfs } from '../api/cmfs'
import ConfirmDialog from '../components/ConfirmDialog'
import DataTable from '../components/DataTable'
import { useAuth } from '../hooks/useAuth'
import { formatDate } from '../utils/formatDate'
import '../styles/actionToolbar.css'
import '../styles/formFeedback.css'
import './CustomCmfsPage.css'

function displayUserName(user) {
  return `${user?.first_name || ''} ${user?.last_name || ''}`.trim() || user?.username || '—'
}

export default function CustomCmfsPage() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const [cmfs, setCmfs] = useState([])
  const [selectedId, setSelectedId] = useState(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isDeleting, setIsDeleting] = useState(false)
  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false)
  const [error, setError] = useState('')

  const loadCmfs = useCallback(async () => {
    try {
      const data = await listCmfs()
      setCmfs(data.filter((cmf) => !cmf.is_builtin && cmf.author?.id === user?.id))
      setSelectedId((current) => (data.some((cmf) => !cmf.is_builtin && cmf.id === current) ? current : null))
      setError('')
    } catch {
      setError('Unable to load your custom CMFs. Please try again.')
    } finally {
      setIsLoading(false)
    }
  }, [user?.id])

  useEffect(() => {
    let cancelled = false
    async function run() {
      if (!cancelled) await loadCmfs()
    }
    run()
    return () => {
      cancelled = true
    }
  }, [loadCmfs])

  const selectedCmf = cmfs.find((cmf) => cmf.id === selectedId) || null

  function handleEdit() {
    if (selectedCmf) navigate(`/cmfs/${selectedCmf.id}/edit`)
  }

  function handleNew() {
    navigate('/cmfs/new')
  }

  async function handleConfirmDelete() {
    if (!selectedCmf) return
    setError('')
    setIsDeleting(true)
    try {
      await deleteCmf(selectedCmf.id)
      setCmfs((current) => current.filter((cmf) => cmf.id !== selectedCmf.id))
      setSelectedId(null)
      setIsDeleteDialogOpen(false)
    } catch {
      setError('Unable to delete this custom CMF. Please try again.')
    } finally {
      setIsDeleting(false)
    }
  }

  const columns = [
    { key: 'title', header: 'Title' },
    { key: 'author', header: 'Author', render: (cmf) => displayUserName(cmf.author) },
    { key: 'modified_at', header: 'Date Last Modified', render: (cmf) => formatDate(cmf.modified_at) },
    { key: 'created_at', header: 'Date Created', render: (cmf) => formatDate(cmf.created_at) },
  ]

  return (
    <main className="custom-cmfs-page">
      <h1>Custom CMFs</h1>

      {error && <p className="form-error" role="alert">{error}</p>}

      <div className="action-toolbar">
        <button type="button" onClick={handleNew}>New CMF</button>
        <button type="button" onClick={handleEdit} disabled={!selectedCmf}>Edit CMF</button>
        <button type="button" onClick={() => setIsDeleteDialogOpen(true)} disabled={!selectedCmf || isDeleting}>Delete</button>
      </div>

      {isLoading ? (
        <p className="text-sm">Loading custom CMFs…</p>
      ) : (
        <DataTable
          columns={columns}
          rows={cmfs}
          getRowId={(cmf) => cmf.id}
          selectedId={selectedId}
          onSelectRow={setSelectedId}
          emptyMessage="You have not created any custom CMFs yet."
        />
      )}

      <ConfirmDialog
        isOpen={isDeleteDialogOpen}
        title="Delete custom CMF?"
        message={`This will permanently delete "${selectedCmf?.title}". This cannot be undone.`}
        confirmLabel="Delete"
        isDangerous
        isBusy={isDeleting}
        onConfirm={handleConfirmDelete}
        onCancel={() => setIsDeleteDialogOpen(false)}
      />
    </main>
  )
}
