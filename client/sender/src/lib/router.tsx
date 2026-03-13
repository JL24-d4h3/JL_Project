import { lazy } from 'react'
import { createBrowserRouter } from 'react-router-dom'
import App from '../App'

const LoginPage      = lazy(() => import('../features/auth/LoginPage'))
const DashboardPage  = lazy(() => import('../features/dashboard/DashboardPage'))
const UploadPage     = lazy(() => import('../features/upload/UploadPage'))
const SubmissionsPage = lazy(() => import('../features/submissions/SubmissionsPage'))
const SubmissionDetailPage = lazy(() => import('../features/submissions/SubmissionDetailPage'))

export const router = createBrowserRouter([
  // Login: sin Layout (página completa independiente)
  {
    path: '/login',
    element: <LoginPage />,
  },
  // Resto: dentro del Layout con sidebar
  {
    path: '/',
    element: <App />,
    children: [
      { index: true,             element: <DashboardPage /> },
      { path: 'upload',          element: <UploadPage /> },
      { path: 'submissions',     element: <SubmissionsPage /> },
      { path: 'submissions/:id', element: <SubmissionDetailPage /> },
    ],
  },
])
