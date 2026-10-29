import { useEffect, useState } from 'react'
import { searchGroups } from '../api/groups'
import './GroupSearchField.css'

const DEBOUNCE_MS = 300

/**
 * A text input backed by live Group search. Unlike UserSearchField, this
 * doesn't hand a string back up -- it reports the picked {id, name} Group
 * via onSelect and then clears itself, since the parent is responsible for
 * displaying the current selection (LeadAgency's single value, or
 * AssocAgency's chip list).
 */
export default function GroupSearchField({ onSelect, placeholder, autoFocus }) {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState([])
  const [isOpen, setIsOpen] = useState(false)
  const [isSearching, setIsSearching] = useState(false)

  useEffect(() => {
    let cancelled = false
    let timeoutId

    function runSearch() {
      const trimmed = query.trim()
      if (!trimmed) {
        setResults([])
        setIsSearching(false)
        return
      }

      setIsSearching(true)
      timeoutId = setTimeout(async () => {
        try {
          const data = await searchGroups(trimmed)
          if (!cancelled) setResults(data)
        } catch {
          if (!cancelled) setResults([])
        } finally {
          if (!cancelled) setIsSearching(false)
        }
      }, DEBOUNCE_MS)
    }

    runSearch()

    return () => {
      cancelled = true
      clearTimeout(timeoutId)
    }
  }, [query])

  function handleSelect(group) {
    onSelect(group)
    setQuery('')
    setResults([])
    setIsOpen(false)
  }

  const showDropdown = isOpen && query.trim().length > 0

  return (
    <div className="group-search-field">
      <input
        type="text"
        value={query}
        onChange={(event) => {
          setQuery(event.target.value)
          setIsOpen(true)
        }}
        onFocus={() => setIsOpen(true)}
        onBlur={() => setIsOpen(false)}
        placeholder={placeholder}
        autoFocus={autoFocus}
        autoComplete="off"
      />
      {showDropdown && (
        <ul className="group-search-results">
          {isSearching && <li className="group-search-status">Searching…</li>}
          {!isSearching &&
            results.map((group) => (
              <li
                key={group.id}
                className="group-search-result"
                // preventDefault keeps the input from blurring before the
                // click registers, so onBlur doesn't close the dropdown first.
                onMouseDown={(event) => {
                  event.preventDefault()
                  handleSelect(group)
                }}
              >
                {group.name}
              </li>
            ))}
          {!isSearching && results.length === 0 && (
            <li className="group-search-status">No matching groups.</li>
          )}
        </ul>
      )}
    </div>
  )
}
