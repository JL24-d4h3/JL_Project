import { Navigate, Routes, Route } from 'react-router-dom'
import { HomePage } from './features/educational-platform/HomePage'
import { SearchPage } from './features/educational-platform/SearchPage'
import { CategoryPage } from './features/educational-platform/CategoryPage'
import { AuthPage } from './features/educational-platform/AuthPage'
import { CoursePage } from './features/educational-platform/CoursePage'
import { AuthProvider, useAuth } from './context/AuthContext'

function ProtectedRoute({ element }: { element: React.ReactElement }) {
  const { isAuthenticated, loading } = useAuth()

  if (loading) {
    return <div className="min-h-screen flex items-center justify-center">Cargando...</div>
  }

  if (!isAuthenticated) {
    return <Navigate to="/auth" replace />
  }

  return element
}

function AppRoutes() {
  return (
    <Routes>
      <Route path="/" element={<HomePage />} />
      <Route path="/search" element={<SearchPage />} />
      <Route path="/category/:slug" element={<CategoryPage />} />
      <Route path="/auth" element={<AuthPage />} />
      <Route path="/course/:slug" element={<ProtectedRoute element={<CoursePage />} />} />
    </Routes>
  )
}

export default function App() {
  return (
    <AuthProvider>
      <AppRoutes />
    </AuthProvider>
  )
}
