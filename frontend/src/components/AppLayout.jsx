import { Outlet } from 'react-router-dom'
import AppHeader from './AppHeader'
import './AppLayout.css'

export default function AppLayout() {
  return (
    <div className="app-shell">
      <AppHeader />
      <div className="app-content">
        <Outlet />
      </div>
    </div>
  )
}
