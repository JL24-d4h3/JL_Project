import { lazy } from 'react'
import { createBrowserRouter } from 'react-router-dom'
import App from '../App'

const LoginPage        = lazy(() => import('../features/auth/LoginPage'))
const ReviewQueuePage  = lazy(() => import('../features/review/ReviewQueuePage'))
const ReviewDetailPage = lazy(() => import('../features/review/ReviewDetailPage'))
const ContentPage      = lazy(() => import('../features/content/ContentPage'))
const CategoriesPage   = lazy(() => import('../features/categories/CategoriesPage'))
const UsersPage        = lazy(() => import('../features/users/UsersPage'))
const DashboardPage    = lazy(() => import('../features/dashboard/DashboardPage'))

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
      { index: true,          element: <ReviewQueuePage /> },
      { path: 'review/:id',   element: <ReviewDetailPage /> },
      { path: 'content',      element: <ContentPage /> },
      { path: 'categories',   element: <CategoriesPage /> },
      { path: 'users',        element: <UsersPage /> },
      { path: 'dashboard',    element: <DashboardPage /> },
    ],
  },
])
