import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import './AppHeader.css'

export default function AppHeader() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  async function handleLogout() {
    await logout()
    navigate('/login', { replace: true })
  }

  return (
    <header className="app-header">
      <Link to="/" className="app-header-brand">
        Rosana
      </Link>
      <nav className="app-header-nav">
        <Link to="/projects">Projects</Link>
      </nav>
      <div className="app-header-user">
        <span className="text-sm">{user?.username}</span>
        <button type="button" className="app-header-logout" onClick={handleLogout}>
          Sign out
        </button>
      </div>
    </header>
  )
}
