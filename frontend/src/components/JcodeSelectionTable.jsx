import './JcodeSelectionTable.css'

export default function JcodeSelectionTable({ rows, selectedIds, onToggle, emptyMessage }) {
  if (rows.length === 0) {
    return <p className="data-table-empty text-sm">{emptyMessage || 'No Jcodes found.'}</p>
  }

  return (
    <table className="data-table table-bordered jcode-selection-table">
      <thead>
        <tr>
          <th className="jcode-selection-checkbox-column">Select</th>
          <th>Jcode</th>
          <th>State</th>
          <th>County</th>
          <th>Place</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((jcode) => {
          const isSelected = selectedIds.includes(jcode.id)
          return (
            <tr key={jcode.id} className={isSelected ? 'data-table-row-selected' : ''}>
              <td className="jcode-selection-checkbox-cell">
                <input
                  type="checkbox"
                  checked={isSelected}
                  aria-label={`Select ${jcode.id}`}
                  onChange={() => onToggle(jcode.id)}
                />
              </td>
              <td>{jcode.id}</td>
              <td>{jcode.state}</td>
              <td>{jcode.county || '—'}</td>
              <td>{jcode.place_name_short}</td>
            </tr>
          )
        })}
      </tbody>
    </table>
  )
}
