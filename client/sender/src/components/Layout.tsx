import { useState, useEffect, Suspense } from 'react'
import { NavLink, Outlet, useLocation, Link } from 'react-router-dom'
import {
  LayoutDashboard,
  Upload,
  ClipboardList,
  LogOut,
  Menu,
  X,
  Zap,
  ChevronRight,
} from 'lucide-react'

const NAV = [
  { to: '/',            label: 'Dashboard',       icon: LayoutDashboard, end: true  },
  { to: '/upload',      label: 'Subir Contenido', icon: Upload,          end: false },
  { to: '/submissions', label: 'Mis Envíos',      icon: ClipboardList,   end: false },
]

function SidebarContent({ onClose }: { onClose?: () => void }) {
  return (
    <div className="flex flex-col h-full">
      {/* Brand */}
      <div className="flex items-center justify-between px-5 h-16 border-b border-white/10 shrink-0">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center shrink-0">
            <Zap size={16} className="text-white" strokeWidth={2.5} />
          </div>
          <div>
            <p className="text-white text-sm font-semibold leading-none">CDN Offline</p>
            <p className="text-slate-400 text-xs mt-0.5">Portal Docente</p>
          </div>
        </div>
        {onClose && (
          <button onClick={onClose} className="text-slate-400 hover:text-white p-1 rounded transition-colors lg:hidden">
            <X size={18} />
          </button>
        )}
      </div>

      {/* Nav */}
      <nav className="flex-1 px-3 py-4 space-y-0.5 overflow-y-auto">
        {NAV.map(({ to, label, icon: Icon, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            onClick={onClose}
            className={({ isActive }) =>
              [
                'group flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all',
                isActive
                  ? 'bg-blue-700 text-white'
                  : 'text-slate-400 hover:bg-white/5 hover:text-white',
              ].join(' ')
            }
          >
            {({ isActive }) => (
              <>
                <Icon size={17} strokeWidth={isActive ? 2.5 : 2} />
                <span className="flex-1">{label}</span>
                {isActive && <ChevronRight size={14} className="opacity-60" />}
              </>
            )}
          </NavLink>
        ))}
      </nav>

      {/* User */}
      <div className="px-3 py-4 border-t border-white/10 shrink-0">
        <div className="flex items-center gap-3 px-3 py-2 rounded-lg">
          <div className="w-8 h-8 rounded-full bg-blue-700/60 border border-blue-600/40 flex items-center justify-center text-blue-200 text-xs font-bold shrink-0 select-none">
            JL
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-slate-200 text-xs font-semibold truncate">Juan León</p>
            <p className="text-slate-500 text-xs truncate">teacher</p>
          </div>
          <button className="text-slate-500 hover:text-slate-300 transition-colors p-1 rounded" title="Cerrar sesión">
            <LogOut size={15} />
          </button>
        </div>
      </div>
    </div>
  )
}

export default function Layout() {
  const [drawerOpen, setDrawerOpen] = useState(false)
  const { pathname } = useLocation()

  // Close drawer on route change
  useEffect(() => { setDrawerOpen(false) }, [pathname])

  // Lock body scroll when drawer is open on mobile
  useEffect(() => {
    document.body.style.overflow = drawerOpen ? 'hidden' : ''
    return () => { document.body.style.overflow = '' }
  }, [drawerOpen])

  const pageTitle = NAV.find(n => n.end ? pathname === n.to : pathname.startsWith(n.to))?.label ?? 'CDN Offline'

  return (
    <div className="flex h-screen bg-slate-50 overflow-hidden">

      {/* ── Desktop sidebar ── */}
      <aside className="hidden lg:flex w-60 shrink-0 bg-slate-900 flex-col">
        <SidebarContent />
      </aside>

      {/* ── Mobile drawer overlay ── */}
      {drawerOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/50 lg:hidden backdrop-blur-sm"
          onClick={() => setDrawerOpen(false)}
        />
      )}

      {/* ── Mobile drawer panel ── */}
      <aside
        className={[
          'fixed inset-y-0 left-0 z-50 w-72 bg-slate-900 flex flex-col lg:hidden',
          'transform transition-transform duration-200 ease-out',
          drawerOpen ? 'translate-x-0' : '-translate-x-full',
        ].join(' ')}
      >
        <SidebarContent onClose={() => setDrawerOpen(false)} />
      </aside>

      {/* ── Main area ── */}
      <div className="flex-1 flex flex-col overflow-hidden min-w-0">

        {/* Top bar */}
        <header className="h-14 bg-white border-b border-slate-200 flex items-center px-4 lg:px-6 shrink-0 gap-3">
          {/* Hamburger (mobile only) */}
          <button
            onClick={() => setDrawerOpen(true)}
            className="lg:hidden text-slate-500 hover:text-slate-700 p-1.5 rounded-lg hover:bg-slate-100 transition-colors mr-1"
            aria-label="Abrir menú"
          >
            <Menu size={20} />
          </button>

          <h1 className="text-slate-800 font-semibold text-sm flex-1">{pageTitle}</h1>

          <Link to="/upload" className="btn-primary text-xs">
            <Upload size={14} />
            <span className="hidden sm:inline">Subir Contenido</span>
            <span className="sm:hidden">Subir</span>
          </Link>
        </header>

        {/* Page content */}
        <main className="flex-1 overflow-auto p-4 lg:p-6">
          <Suspense fallback={
            <div className="flex items-center justify-center h-48">
              <div className="w-5 h-5 border-2 border-blue-700 border-t-transparent rounded-full animate-spin" />
            </div>
          }>
            <Outlet />
          </Suspense>
        </main>
      </div>
    </div>
  )
}
