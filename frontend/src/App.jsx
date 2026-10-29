import { Navigate, Route, Routes } from 'react-router-dom'
import AppLayout from './components/AppLayout'
import ProtectedRoute from './components/ProtectedRoute'
import LoginPage from './pages/LoginPage'
import RegisterPage from './pages/RegisterPage'
import SplashPage from './pages/SplashPage'
import OpportunitiesPage from './pages/OpportunitiesPage'
import OpportunityEditorPage from './pages/OpportunityEditorPage'
import OpportunityMembersPage from './pages/OpportunityMembersPage'
import ProjectEditorPage from './pages/ProjectEditorPage'
import AnalysisSetupPage from './pages/AnalysisSetupPage'
import SiteEditorPage from './pages/SiteEditorPage'
import GroupsPage from './pages/GroupsPage'
import GroupEditorPage from './pages/GroupEditorPage'
import NotificationsPage from './pages/NotificationsPage'
import CustomCmfSetupPage from './pages/CustomCmfSetupPage'
import CustomCmfsPage from './pages/CustomCmfsPage'
import SettingsPage from './pages/SettingsPage'

function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route element={<ProtectedRoute />}>
        <Route element={<AppLayout />}>
          <Route path="/" element={<SplashPage />} />
          <Route path="/opportunities" element={<OpportunitiesPage />} />
          <Route path="/opportunities/new" element={<OpportunityEditorPage />} />
          <Route path="/opportunities/:id" element={<OpportunityEditorPage />} />
          <Route path="/opportunities/:id/members" element={<OpportunityMembersPage />} />
          <Route path="/projects/:id">
            <Route index element={<ProjectEditorPage />} />
          </Route>
          <Route path="/sites/:id">
            <Route index element={<SiteEditorPage />} />
            <Route path="analysis" element={<AnalysisSetupPage />} />
          </Route>
          <Route path="/groups" element={<GroupsPage />} />
          <Route path="/groups/:id" element={<GroupEditorPage />} />
          <Route path="/notifications" element={<NotificationsPage />} />
          <Route path="/settings" element={<SettingsPage />} />
          <Route path="/cmfs" element={<CustomCmfsPage />} />
          <Route path="/cmfs/new" element={<CustomCmfSetupPage key="new-cmf" />} />
          <Route path="/cmfs/:id/edit" element={<CustomCmfSetupPage key="edit-cmf" />} />
        </Route>
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}

export default App
