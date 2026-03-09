import { useState, useEffect, Suspense } from 'react'
import { NavLink, Outlet, useLocation, Link } from 'react-router-dom'
import { Toaster } from 'react-hot-toast'
import { LayoutDashboard, Upload, ClipboardList, LogOut, Menu, X, Zap } from 'lucide-react'

const NAV = [
  { to: '/',            label: 'Dashboard',       icon: LayoutDashboard, end: true  },
  { to: '/upload',      label: 'Subir Contenido', icon: Upload,          end: false },
  { to: '/submissions', label: 'Mis Envíos',      icon: ClipboardList,   end: false },
]

export default function Layout() {
  const [menuOpen, setMenuOpen] = useState(false)
  const { pathname } = useLocation()

  useEffect(() => { setMenuOpen(false) }, [pathname])
  useEffect(() => {
    document.body.style.overflow = menuOpen ? 'hidden' : ''
    return () => { document.body.style.overflow = '' }
  }, [menuOpen])

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col">

      {/* ── Top navbar ── */}
      <header className="sticky top-0 z-30 h-14 bg-slate-900 border-b border-white/10 flex items-center px-4 sm:px-6 gap-4">

        {/* Brand */}
        <Link to="/" className="flex items-center gap-2.5 shrink-0">
          <div className="w-7 h-7 rounded-md bg-blue-600 flex items-center justify-center">
            <Zap size={14} className="text-white" strokeWidth={2.5} />
          </div>
          <span className="text-white text-sm font-semibold hidden sm:block">CDN Offline</span>
        </Link>

        {/* Desktop nav links */}
        <nav className="hidden md:flex items-center gap-1 flex-1 ml-2">
          {NAV.map(({ to, label, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) =>
                [
                  'flex items-center gap-2 px-3.5 py-2 rounded-lg text-sm font-medium transition-all',
                  isActive
                    ? 'bg-blue-700 text-white'
                    : 'text-slate-400 hover:bg-white/5 hover:text-white',
                ].join(' ')
              }
            >
              {({ isActive }) => (
                <>
                  <Icon size={15} strokeWidth={isActive ? 2.5 : 2} />
                  {label}
                </>
              )}
            </NavLink>
          ))}
        </nav>

        <div className="flex-1 md:hidden" />

        {/* User (desktop) */}
        <div className="hidden md:flex items-center gap-1 ml-auto">
          <div className="flex items-center gap-2 px-2 py-1.5 rounded-lg">
            <div className="w-7 h-7 rounded-full bg-blue-700/70 border border-blue-600/40 flex items-center justify-center text-blue-200 text-xs font-bold select-none">
              JL
            </div>
            <div className="leading-tight">
              <p className="text-slate-200 text-xs font-semibold">Juan León</p>
              <p className="text-slate-500 text-xs">teacher</p>
            </div>
          </div>
          <button className="text-slate-500 hover:text-slate-300 p-1.5 rounded-lg hover:bg-white/5 transition-colors" title="Cerrar sesión">
            <LogOut size={15} />
          </button>
        </div>

        {/* Hamburger (mobile) */}
        <button
          onClick={() => setMenuOpen(v => !v)}
          className="md:hidden text-slate-400 hover:text-white p-1.5 rounded-lg hover:bg-white/10 transition-colors"
          aria-label="Menú"
        >
          {menuOpen ? <X size={20} /> : <Menu size={20} />}
        </button>
      </header>

      {/* ── Mobile dropdown ── */}
      {menuOpen && (
        <>
          <div
            className="fixed inset-0 z-20 bg-black/40 md:hidden"
            onClick={() => setMenuOpen(false)}
          />
          <div className="fixed top-14 inset-x-0 z-20 md:hidden bg-slate-900 border-b border-white/10 shadow-xl">
            <nav className="flex flex-col px-3 py-2 gap-0.5">
              {NAV.map(({ to, label, icon: Icon, end }) => (
                <NavLink
                  key={to}
                  to={to}
                  end={end}
                  className={({ isActive }) =>
                    [
                      'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all',
                      isActive ? 'bg-blue-700 text-white' : 'text-slate-400 hover:bg-white/5 hover:text-white',
                    ].join(' ')
                  }
                >
                  {({ isActive }) => (
                    <>
                      <Icon size={16} strokeWidth={isActive ? 2.5 : 2} />
                      {label}
                    </>
                  )}
                </NavLink>
              ))}
            </nav>
            <div className="flex items-center gap-3 px-5 py-3 border-t border-white/10">
              <div className="w-7 h-7 rounded-full bg-blue-700/70 border border-blue-600/40 flex items-center justify-center text-blue-200 text-xs font-bold select-none">
                JL
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-slate-200 text-xs font-semibold">Juan León</p>
                <p className="text-slate-500 text-xs">teacher</p>
              </div>
              <button className="text-slate-500 hover:text-slate-300 transition-colors p-1.5" title="Cerrar sesión">
                <LogOut size={15} />
              </button>
            </div>
          </div>
        </>
      )}

      {/* ── Page content ── */}
      <main className="flex-1 w-full">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 py-6">
          <Suspense fallback={
            <div className="flex items-center justify-center h-48">
              <div className="w-5 h-5 border-2 border-blue-700 border-t-transparent rounded-full animate-spin" />
            </div>
          }>
            <Outlet />
          </Suspense>
        </div>
      </main>

      <Toaster
        position="bottom-right"
        toastOptions={{
          duration: 4000,
          style: { fontSize: '13px', fontFamily: 'Inter, sans-serif', borderRadius: '10px' },
          success: { iconTheme: { primary: '#1d4ed8', secondary: '#fff' } },
        }}
      />
    </div>
  )
}
