import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { listCmfs } from '../api/cmfs'
import { formatDate } from '../utils/formatDate'
import '../styles/editorForm.css'

const INITIAL_VALUES = {
  projectCost: '',
  installationCost: '',
  maintenanceCost: '',
  serviceLife: '',
}

export default function AnalysisSetupPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [values, setValues] = useState(INITIAL_VALUES)
  const [customCmfs, setCustomCmfs] = useState([])
  const [selectedCmfIds, setSelectedCmfIds] = useState([])
  const [isLoadingCmfs, setIsLoadingCmfs] = useState(true)
  const [cmfError, setCmfError] = useState('')

  useEffect(() => {
    let cancelled = false
    async function loadCmfs() {
      try {
        const data = await listCmfs()
        if (!cancelled) {
          const availableCmfs = data.filter((cmf) => !cmf.is_builtin)
          setCustomCmfs(availableCmfs)
          setSelectedCmfIds((current) => current.filter((cmfId) => availableCmfs.some((cmf) => cmf.id === cmfId)))
          setCmfError('')
        }
      } catch {
        if (!cancelled) setCmfError('Unable to load your custom CMFs. Please try again.')
      } finally {
        if (!cancelled) setIsLoadingCmfs(false)
      }
    }
    loadCmfs()
    return () => {
      cancelled = true
    }
  }, [])

  function handleChange(event) {
    const { name, value } = event.target
    setValues((current) => ({ ...current, [name]: value }))
  }

  function handleSubmit(event) {
    event.preventDefault()
  }

  return (
    <main className="editor-page">
      <button type="button" className="editor-back" onClick={() => navigate(`/sites/${id}`)}>
        ← Back to Site Editor
      </button>

      <form className="editor-card analysis-setup-card" onSubmit={handleSubmit}>
        <div className="editor-title-row">
          <h1>Analysis Setup</h1>
        </div>

        <label className="editor-field">
          <span className="label">Project cost</span>
          <span className="analysis-currency-input">
            <span>$</span>
            <input type="number" name="projectCost" value={values.projectCost} onChange={handleChange} min="0" step="0.01" required />
          </span>
        </label>

        <label className="editor-field">
          <span className="label">Installation cost (one-time)</span>
          <span className="analysis-currency-input">
            <span>$</span>
            <input type="number" name="installationCost" value={values.installationCost} onChange={handleChange} min="0" step="0.01" required />
          </span>
        </label>

        <label className="editor-field">
          <span className="label">Maintenance &amp; Ops (yearly)</span>
          <span className="analysis-currency-input">
            <span>$</span>
            <input type="number" name="maintenanceCost" value={values.maintenanceCost} onChange={handleChange} min="0" step="0.01" required />
          </span>
        </label>

        <label className="editor-field">
          <span className="label">Service life (years)</span>
          <input type="number" name="serviceLife" value={values.serviceLife} onChange={handleChange} min="0" step="any" required />
        </label>

        <section className="analysis-cmf-selection" aria-labelledby="analysis-cmf-selection-heading">
          <p id="analysis-cmf-selection-heading" className="label">
            Select which custom CMFs to include in your analysis
          </p>
          {cmfError && <p className="form-error" role="alert">{cmfError}</p>}
          {isLoadingCmfs ? (
            <p className="text-sm">Loading custom CMFs…</p>
          ) : customCmfs.length === 0 ? (
            <p className="text-sm">No custom CMFs are available to you yet.</p>
          ) : (
            <div className="analysis-cmf-selection-table-wrapper">
              <table className="analysis-cmf-selection-table">
                <thead>
                  <tr>
                    <th scope="col">Include</th>
                    <th scope="col">Title</th>
                    <th scope="col">Author</th>
                    <th scope="col">Date Last Modified</th>
                    <th scope="col">Date Created</th>
                  </tr>
                </thead>
                <tbody>
                  {customCmfs.map((cmf) => (
                    <tr key={cmf.id}>
                      <td>
                        <input
                          type="checkbox"
                          checked={selectedCmfIds.includes(cmf.id)}
                          onChange={() => setSelectedCmfIds((current) => (
                            current.includes(cmf.id)
                              ? current.filter((cmfId) => cmfId !== cmf.id)
                              : [...current, cmf.id]
                          ))}
                          aria-label={`Include ${cmf.title}`}
                        />
                      </td>
                      <th scope="row">{cmf.title}</th>
                      <td>{cmf.author?.username || '—'}</td>
                      <td>{formatDate(cmf.modified_at)}</td>
                      <td>{formatDate(cmf.created_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          <div className="analysis-cmf-selection-actions">
            <button type="button" onClick={() => setSelectedCmfIds(customCmfs.map((cmf) => cmf.id))}>
              Select All
            </button>
            <button type="button" onClick={() => setSelectedCmfIds([])}>
              Select None
            </button>
          </div>
        </section>

        <button type="submit" className="editor-save">Run Analysis</button>
      </form>
    </main>
  )
}
