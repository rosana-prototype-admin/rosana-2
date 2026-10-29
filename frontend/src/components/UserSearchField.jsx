import { useEffect, useState } from 'react'
import { searchUsers } from '../api/users'
import './UserSearchField.css'

// Mirrors the backend's UserSearchView.MIN_QUERY_LENGTH.
const MIN_QUERY_LENGTH = 2
const DEBOUNCE_MS = 300

/**
 * A text input backed by live user search. Reports the current text value
 * up via onChange either as the user types or when they pick a suggestion
 * (which fills in that user's exact username) -- either way the parent just
 * gets a string, since the backend resolves the final identifier itself.
 * Callers that need the actual picked user (e.g. its numeric id, for an API
 * that takes user_id rather than a username/email identifier) can pass the
 * optional onSelectUser, fired only when a suggestion is clicked.
 */
export default function UserSearchField({ value, onChange, onSelectUser, placeholder, autoFocus }) {
  const [results, setResults] = useState([])
  const [isOpen, setIsOpen] = useState(false)
  const [isSearching, setIsSearching] = useState(false)

  useEffect(() => {
    let cancelled = false
    let timeoutId

    function runSearch() {
      const query = value.trim()
      if (query.length < MIN_QUERY_LENGTH) {
        setResults([])
        setIsSearching(false)
        return
      }

      setIsSearching(true)
      timeoutId = setTimeout(async () => {
        try {
          const data = await searchUsers({ q: query })
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
  }, [value])

  function handleSelect(user) {
    onChange(user.username)
    onSelectUser?.(user)
    setResults([])
    setIsOpen(false)
  }

  const showDropdown = isOpen && value.trim().length >= MIN_QUERY_LENGTH

  return (
    <div className="user-search-field">
      <input
        type="text"
        value={value}
        onChange={(event) => {
          onChange(event.target.value)
          setIsOpen(true)
        }}
        onFocus={() => setIsOpen(true)}
        onBlur={() => setIsOpen(false)}
        placeholder={placeholder}
        autoFocus={autoFocus}
        autoComplete="off"
      />
      {showDropdown && (
        <ul className="user-search-results">
          {isSearching && <li className="user-search-status">Searching…</li>}
          {!isSearching &&
            results.map((user) => (
              <li
                key={user.id}
                className="user-search-result"
                // preventDefault keeps the input from blurring before the
                // click registers, so onBlur doesn't close the dropdown first.
                onMouseDown={(event) => {
                  event.preventDefault()
                  handleSelect(user)
                }}
              >
                <span className="user-search-result-name">
                  {`${user.first_name} ${user.last_name}`.trim() || user.username}
                </span>
                <span className="user-search-result-meta">
                  {user.username} · {user.email}
                </span>
              </li>
            ))}
          {!isSearching && results.length === 0 && (
            <li className="user-search-status">No matches. You can still enter an exact username or email.</li>
          )}
        </ul>
      )}
    </div>
  )
}
