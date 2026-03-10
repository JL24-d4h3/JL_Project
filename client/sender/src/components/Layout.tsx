import { useState, useEffect, Suspense } from 'react'
import { NavLink, Outlet, useLocation, Link } from 'react-router-dom'
import { Toaster } from 'react-hot-toast'
import { LayoutDashboard, Upload, ClipboardList, LogOut, Menu, X, Zap } from 'lucide-react'

const NAV = [
  { to: '/',            label: 'Dashboard',       icon: LayoutDashboard, end: true  },
  { to: '/upload',      label: 'Subir Contenido', icon: Upload,          end: false },
  { to: '/submissions', label: 'Mis Envíos',      icon: ClipboardList,   end: false },
]

function NavLinks({ onClose }: { onClose?: () => void }) {
  return (
    <nav className="flex-1 px-2 py-3 space-y-0.5 overflow-y-auto">
      {NAV.map(({ to, label, icon: Icon, end }) => (
        <NavLink
          key={to}
          to={to}
          end={end}
          onClick={onClose}
          className={({ isActive }) =>
            [
              'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all select-none',
              isActive
                ? 'bg-blue-700 text-white'
                : 'text-slate-400 hover:bg-white/6 hover:text-slate-100',
            ].join(' ')
          }
        >
          {({ isActive }) => (
            <>
              <Icon size={16} strokeWidth={isActive ? 2.5 : 2} className="shrink-0" />
              {label}
            </>
          )}
        </NavLink>
      ))}
    </nav>
  )
}

function Brand() {
  return (
    <div className="flex items-center gap-3 px-4 h-14 border-b border-white/10 shrink-0">
      <div className="w-7 h-7 rounded-md bg-blue-600 flex items-center justify-center shrink-0">
        <Zap size={14} className="text-white" strokeWidth={2.5} />
      </div>
      <div className="leading-tight">
        <p className="text-white text-sm font-semibold">CDN Offline</p>
        <p className="text-slate-500 text-xs">Portal Docente</p>
      </div>
    </div>
  )
}

function UserRow({ compact }: { compact?: boolean }) {
  return (
    <div className={`flex items-center gap-3 border-t border-white/10 shrink-0 ${compact ? 'px-3 py-3' : 'px-4 py-3'}`}>
      <div className="w-8 h-8 rounded-full bg-blue-700/60 border border-blue-600/40 flex items-center justify-center text-blue-200 text-xs font-bold shrink-0 select-none">
        JL
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-slate-200 text-sm font-semibold truncate">Juan León</p>
        <p className="text-slate-500 text-xs truncate">teacher</p>
      </div>
      <button
        className="text-slate-500 hover:text-slate-300 transition-colors p-1.5 rounded-md hover:bg-white/5"
        title="Cerrar sesión"
      >
        <LogOut size={15} />
      </button>
    </div>
  )
}

export default function Layout() {
  const [drawerOpen, setDrawerOpen] = useState(false)
  const { pathname } = useLocation()

  useEffect(() => { setDrawerOpen(false) }, [pathname])
  useEffect(() => {
    document.body.style.overflow = drawerOpen ? 'hidden' : ''
    return () => { document.body.style.overflow = '' }
  }, [drawerOpen])

  return (
    <div className="flex h-screen overflow-hidden bg-slate-100">

      {/* ── Desktop sidebar (≥1024px) ── */}
      <aside className="hidden lg:flex w-60 shrink-0 bg-slate-900 flex-col">
        <Brand />
        <NavLinks />
        <UserRow />
      </aside>

      {/* ── Mobile/tablet: overlay + drawer ── */}
      {drawerOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/50 backdrop-blur-[1px] lg:hidden"
          onClick={() => setDrawerOpen(false)}
        />
      )}
      <aside
        className={[
          'fixed inset-y-0 left-0 z-50 w-64 bg-slate-900 flex flex-col lg:hidden',
          'transition-transform duration-200 ease-out',
          drawerOpen ? 'translate-x-0' : '-translate-x-full',
        ].join(' ')}
      >
        <div className="flex items-center justify-between px-4 h-14 border-b border-white/10 shrink-0">
          <div className="flex items-center gap-3">
            <div className="w-7 h-7 rounded-md bg-blue-600 flex items-center justify-center shrink-0">
              <Zap size={14} className="text-white" strokeWidth={2.5} />
            </div>
            <p className="text-white text-sm font-semibold">CDN Offline</p>
          </div>
          <button
            onClick={() => setDrawerOpen(false)}
            className="text-slate-400 hover:text-white p-1.5 rounded-md transition-colors"
          >
            <X size={18} />
          </button>
        </div>
        <NavLinks onClose={() => setDrawerOpen(false)} />
        <UserRow />
      </aside>

      {/* ── Main column ── */}
      <div className="flex-1 flex flex-col overflow-hidden min-w-0">

        {/* Mobile topbar */}
        <header className="lg:hidden h-14 bg-slate-900 border-b border-white/10 flex items-center px-4 shrink-0 gap-3">
          <button
            onClick={() => setDrawerOpen(true)}
            className="text-slate-400 hover:text-white p-1.5 rounded-md hover:bg-white/10 transition-colors"
            aria-label="Abrir menú"
          >
            <Menu size={20} />
          </button>
          <p className="text-white text-sm font-semibold flex-1 truncate">
            {NAV.find(n => n.end ? pathname === n.to : pathname.startsWith(n.to))?.label ?? 'CDN Offline'}
          </p>
          <Link to="/upload" className="btn-primary !py-1.5 !px-3 !text-xs !gap-1.5">
            <Upload size={13} />
            Subir
          </Link>
        </header>

        {/* Scrollable content */}
        <main className="flex-1 overflow-y-auto">
          <div className="px-6 py-6">
            <Suspense fallback={
              <div className="flex items-center justify-center h-48">
                <div className="w-5 h-5 border-2 border-blue-700 border-t-transparent rounded-full animate-spin" />
              </div>
            }>
              <Outlet />
            </Suspense>
          </div>
        </main>
      </div>

      <Toaster
        position="bottom-right"
        toastOptions={{
          duration: 4000,
          style: { fontSize: '15px', fontFamily: 'Inter, sans-serif', borderRadius: '10px' },
          success: { iconTheme: { primary: '#1d4ed8', secondary: '#fff' } },
        }}
      />
    </div>
  )
}
