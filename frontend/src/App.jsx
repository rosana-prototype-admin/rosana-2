import { Navigate, Route, Routes } from 'react-router-dom'
import AppLayout from './components/AppLayout'
import ProtectedRoute from './components/ProtectedRoute'
import LoginPage from './pages/LoginPage'
import SplashPage from './pages/SplashPage'
import ProjectsPage from './pages/ProjectsPage'
import ProjectEditorPage from './pages/ProjectEditorPage'
import CourseOfActionEditorPage from './pages/CourseOfActionEditorPage'

function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route element={<ProtectedRoute />}>
        <Route element={<AppLayout />}>
          <Route path="/" element={<SplashPage />} />
          <Route path="/projects" element={<ProjectsPage />} />
          <Route path="/projects/:id" element={<ProjectEditorPage />} />
          <Route path="/projects/:projectId/courses-of-action/:coaId" element={<CourseOfActionEditorPage />} />
        </Route>
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}

export default App
