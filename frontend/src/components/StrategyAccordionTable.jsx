import { Fragment, useMemo, useState } from 'react'
import { interventionTypeLabel } from '../utils/interventionTypeLabel'
import { formatDate } from '../utils/formatDate'
import './StrategyAccordionTable.css'

function groupByCategory(strategies) {
  const byCategory = new Map()
  for (const strategy of strategies) {
    const category = strategy.intervention_type.category || 'Uncategorized'
    if (!byCategory.has(category)) byCategory.set(category, [])
    byCategory.get(category).push(strategy)
  }
  return [...byCategory.entries()]
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([category, items]) => ({
      category,
      items: [...items].sort((a, b) => a.intervention_type.name.localeCompare(b.intervention_type.name)),
    }))
}

/**
 * Groups Strategy rows by intervention_type.category into a collapsible
 * accordion (category headers with an expand/collapse arrow; individual
 * strategies underneath, selectable exactly like a flat DataTable row).
 * Replaces the old flat "category — name" single-column layout.
 */
export default function StrategyAccordionTable({
  strategies,
  selectedId,
  onSelectRow,
  onToggleSelected,
  emptyMessage,
  readOnly = false,
}) {
  const groups = useMemo(() => groupByCategory(strategies), [strategies])

  // Categories with an already-selected strategy start expanded, so a
  // checked strategy is never invisible on load; everything else starts
  // collapsed. Only seeded once -- toggling afterwards is fully user-driven.
  const [expanded, setExpanded] = useState(
    () => new Set(groups.filter((group) => group.items.some((strategy) => strategy.selected)).map((group) => group.category)),
  )

  function toggleCategory(category) {
    setExpanded((current) => {
      const next = new Set(current)
      if (next.has(category)) {
        next.delete(category)
      } else {
        next.add(category)
      }
      return next
    })
  }

  if (strategies.length === 0) {
    return <p className="data-table-empty text-sm">{emptyMessage || 'No results.'}</p>
  }

  return (
    <table className="data-table table-bordered strategy-accordion">
      <thead>
        <tr>
          <th></th>
          <th>Strategy</th>
          <th>CMF</th>
          <th>Last edited</th>
          <th>Created</th>
        </tr>
      </thead>
      <tbody>
        {groups.map((group) => {
          const isExpanded = expanded.has(group.category)
          return (
            <Fragment key={group.category}>
              <tr className="strategy-category-row">
                <td colSpan={5}>
                  <button
                    type="button"
                    className="strategy-category-toggle"
                    aria-expanded={isExpanded}
                    onClick={() => toggleCategory(group.category)}
                  >
                    <span className="strategy-category-arrow" aria-hidden="true">
                      ▸
                    </span>
                    {group.category} ({group.items.length})
                  </button>
                </td>
              </tr>
              {isExpanded &&
                group.items.map((strategy) => {
                  const isSelected = strategy.id === selectedId
                  return (
                    <tr
                      key={strategy.id}
                      className={isSelected ? 'strategy-row data-table-row-selected' : 'strategy-row'}
                      onClick={() => onSelectRow(isSelected ? null : strategy.id)}
                    >
                      <td>
                        <input
                          type="checkbox"
                          checked={strategy.selected}
                          onChange={() => onToggleSelected(strategy)}
                          onClick={(event) => event.stopPropagation()}
                          disabled={readOnly}
                          aria-label={`Select ${interventionTypeLabel(strategy.intervention_type)}`}
                        />
                      </td>
                      <td className="strategy-name-cell">{strategy.intervention_type.name}</td>
                      <td>{strategy.intervention_type.cmf?.title || 'Not assigned'}</td>
                      <td>{formatDate(strategy.modified_at)}</td>
                      <td>{formatDate(strategy.created_at)}</td>
                    </tr>
                  )
                })}
            </Fragment>
          )
        })}
      </tbody>
    </table>
  )
}
