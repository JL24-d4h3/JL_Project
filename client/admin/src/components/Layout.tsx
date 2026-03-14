import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom'
import { Suspense } from 'react'
import { useQuery } from '@tanstack/react-query'
import { apiClient } from '../lib/apiClient'

// ── Inline SVG icons ─────────────────────────────────────
const IconInbox = () => (
  <svg className="w-5 h-5 shrink-0" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="22 12 16 12 14 15 10 15 8 12 2 12"/>
    <path d="M5.45 5.11L2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11z"/>
  </svg>
)
const IconFilm = () => (
  <svg className="w-5 h-5 shrink-0" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <rect x="2" y="2" width="20" height="20" rx="2.18" ry="2.18"/>
    <line x1="7" y1="2" x2="7" y2="22"/><line x1="17" y1="2" x2="17" y2="22"/>
    <line x1="2" y1="12" x2="22" y2="12"/><line x1="2" y1="7" x2="7" y2="7"/>
    <line x1="2" y1="17" x2="7" y2="17"/><line x1="17" y1="17" x2="22" y2="17"/>
    <line x1="17" y1="7" x2="22" y2="7"/>
  </svg>
)
const IconTag = () => (
  <svg className="w-5 h-5 shrink-0" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M20.59 13.41l-7.17 7.17a2 2 0 0 1-2.83 0L2 12V2h10l8.59 8.59a2 2 0 0 1 0 2.82z"/>
    <line x1="7" y1="7" x2="7.01" y2="7"/>
  </svg>
)
const IconUsers = () => (
  <svg className="w-5 h-5 shrink-0" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>
    <circle cx="9" cy="7" r="4"/>
    <path d="M23 21v-2a4 4 0 0 0-3-3.87"/>
    <path d="M16 3.13a4 4 0 0 1 0 7.75"/>
  </svg>
)
const IconBarChart = () => (
  <svg className="w-5 h-5 shrink-0" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <line x1="18" y1="20" x2="18" y2="10"/>
    <line x1="12" y1="20" x2="12" y2="4"/>
    <line x1="6" y1="20" x2="6" y2="14"/>
    <line x1="2" y1="20" x2="22" y2="20"/>
  </svg>
)
const IconLogout = () => (
  <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/>
    <polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/>
  </svg>
)

const NAV = [
  { to: '/',           label: 'Cola de Revisión', icon: <IconInbox />,    end: true },
  { to: '/content',    label: 'Contenido',        icon: <IconFilm />,    end: false },
  { to: '/categories', label: 'Categorías',       icon: <IconTag />,     end: false },
  { to: '/users',      label: 'Usuarios',         icon: <IconUsers />,   end: false },
  { to: '/dashboard',  label: 'Estadísticas',     icon: <IconBarChart />,end: false },
]

const PAGE_TITLES: Record<string, string> = {
  '/':           'Cola de Revisión',
  '/content':    'Contenido publicado',
  '/categories': 'Categorías',
  '/users':      'Usuarios',
  '/dashboard':  'Estadísticas',
}

export default function Layout() {
  const { pathname } = useLocation()
  const navigate = useNavigate()
  const base = '/' + pathname.split('/')[1]
  const title = PAGE_TITLES[base] ?? 'Panel Administrativo'

  // Real user from localStorage
  const user = (() => {
    try { return JSON.parse(localStorage.getItem('user') ?? 'null') } catch { return null }
  })()
  const displayName: string = user?.full_name ?? user?.username ?? 'Administrador'
  const displayUsername: string = user?.username ?? 'admin'
  const initials = displayName.split(' ').map((w: string) => w[0]).slice(0, 2).join('').toUpperCase()

  // Pending count for badge
  const { data: pendingCount } = useQuery({
    queryKey: ['pendingCount'],
    queryFn: () =>
      apiClient
        .get<{ success: boolean; count: number }>('/api/upload/pending/count')
        .then(r => r.data.count),
    refetchInterval: 30_000,
  })

  const handleLogout = () => {
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    navigate('/login', { replace: true })
  }

  return (
    <div className="flex h-screen bg-slate-100 overflow-hidden">
      {/* ── Sidebar ─────────────────────────────────── */}
      <aside className="w-60 shrink-0 bg-slate-900 flex flex-col">
        {/* Logo */}
        <div className="px-5 py-5 border-b border-slate-800">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-indigo-600 flex items-center justify-center shrink-0">
              <svg className="w-5 h-5 text-white" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>
              </svg>
            </div>
            <div className="leading-tight">
              <p className="text-white text-sm font-semibold">CDN Offline</p>
              <p className="text-slate-400 text-xs">Panel Admin</p>
            </div>
          </div>
        </div>

        {/* Nav */}
        <nav className="flex-1 px-3 py-4 space-y-0.5 overflow-y-auto">
          {NAV.map(({ to, label, icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) =>
                [
                  'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all',
                  isActive
                    ? 'bg-indigo-600 text-white shadow-sm'
                    : 'text-slate-400 hover:bg-slate-800 hover:text-slate-100',
                ].join(' ')
              }
            >
              {icon}
              <span className="flex-1">{label}</span>
              {to === '/' && pendingCount !== undefined && pendingCount > 0 && (
                <span className="bg-amber-500 text-white text-xs font-bold px-1.5 py-0.5 rounded-full min-w-[20px] text-center">
                  {pendingCount}
                </span>
              )}
            </NavLink>
          ))}
        </nav>

        {/* User */}
        <div className="px-3 py-4 border-t border-slate-800">
          <div className="flex items-center gap-3 px-3 py-2.5 rounded-lg">
            <div className="w-8 h-8 rounded-full bg-indigo-700 flex items-center justify-center text-white text-xs font-bold shrink-0">
              {initials}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-slate-200 text-xs font-medium truncate">{displayName}</p>
              <p className="text-slate-500 text-xs truncate">@{displayUsername}</p>
            </div>
            <button
              onClick={handleLogout}
              className="text-slate-500 hover:text-slate-300 transition-colors"
              title="Cerrar sesión"
            >
              <IconLogout />
            </button>
          </div>
        </div>
      </aside>

      {/* ── Main area ────────────────────────────────── */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Top bar */}
        <header className="h-14 bg-white border-b border-slate-200 flex items-center px-6 shrink-0 gap-3">
          <h1 className="text-slate-800 font-semibold text-sm flex-1">{title}</h1>
        </header>

        {/* Page content */}
        <main className="flex-1 overflow-auto p-6">
          <Suspense fallback={
            <div className="flex items-center justify-center h-48">
              <div className="w-6 h-6 border-2 border-indigo-600 border-t-transparent rounded-full animate-spin" />
            </div>
          }>
            <Outlet />
          </Suspense>
        </main>
      </div>
    </div>
  )
}
