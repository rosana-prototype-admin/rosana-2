import { useMemo, useState } from 'react'
import './DataTable.css'

/**
 * columns: [{ key, header, sortable=true, render?: (row) => node, sortValue?: (row) => primitive }]
 */
export default function DataTable({ columns, rows, getRowId, selectedId, onSelectRow, emptyMessage }) {
  const [sort, setSort] = useState(null) // { key, direction: 'asc' | 'desc' }

  const sortedRows = useMemo(() => {
    if (!sort) return rows
    const column = columns.find((col) => col.key === sort.key)
    if (!column) return rows
    const getValue = column.sortValue || ((row) => row[column.key])
    const sorted = [...rows].sort((a, b) => {
      const valueA = getValue(a)
      const valueB = getValue(b)
      if (valueA < valueB) return -1
      if (valueA > valueB) return 1
      return 0
    })
    return sort.direction === 'desc' ? sorted.reverse() : sorted
  }, [rows, sort, columns])

  function handleHeaderClick(column) {
    if (column.sortable === false) return
    setSort((current) => {
      if (!current || current.key !== column.key) return { key: column.key, direction: 'asc' }
      if (current.direction === 'asc') return { key: column.key, direction: 'desc' }
      return null
    })
  }

  if (rows.length === 0) {
    return <p className="data-table-empty text-sm">{emptyMessage || 'No results.'}</p>
  }

  return (
    <table className="data-table table-bordered">
      <thead>
        <tr>
          {columns.map((column) => {
            const isSorted = sort?.key === column.key
            return (
              <th
                key={column.key}
                className={column.sortable === false ? '' : 'data-table-sortable'}
                onClick={() => handleHeaderClick(column)}
              >
                {column.header}
                {isSorted && <span className="data-table-sort-arrow">{sort.direction === 'asc' ? ' ↑' : ' ↓'}</span>}
              </th>
            )
          })}
        </tr>
      </thead>
      <tbody>
        {sortedRows.map((row) => {
          const rowId = getRowId(row)
          const isSelected = rowId === selectedId
          return (
            <tr
              key={rowId}
              className={isSelected ? 'data-table-row-selected' : ''}
              onClick={() => onSelectRow(isSelected ? null : rowId)}
            >
              {columns.map((column) => (
                <td key={column.key}>{column.render ? column.render(row) : row[column.key]}</td>
              ))}
            </tr>
          )
        })}
      </tbody>
    </table>
  )
}
