import { BookOpen, LogOut, User, ChevronDown } from 'lucide-react'
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { useAuth } from '@/context/AuthContext'

export function Navbar() {
  const navigate = useNavigate()
  const { isAuthenticated, user, logout } = useAuth()
  const [isMenuOpen, setIsMenuOpen] = useState(false)

  const handleLogout = () => {
    logout()
    setIsMenuOpen(false)
    navigate('/')
  }

  return (
    <header className="border-b border-slate-200 bg-white sticky top-0 z-50">
      <div className="container mx-auto px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3 cursor-pointer" onClick={() => navigate('/')}>
          <div className="w-10 h-10 rounded-lg bg-slate-900 flex items-center justify-center">
            <BookOpen className="h-6 w-6 text-white" />
          </div>
          <span className="font-bold text-lg text-slate-900">CDN Educativa</span>
        </div>

        <nav className="hidden md:flex gap-8">
          <a href="#" className="text-slate-600 hover:text-slate-900 font-medium">
            Inicio
          </a>
          <a href="#" className="text-slate-600 hover:text-slate-900 font-medium">
            Biblioteca
          </a>
          <a href="#" className="text-slate-600 hover:text-slate-900 font-medium">
            Proyectos
          </a>
        </nav>

        {!isAuthenticated ? (
          <Button
            onClick={() => navigate('/auth')}
            className="bg-slate-900 hover:bg-slate-800 text-white"
            size="sm"
          >
            Acceder
          </Button>
        ) : (
          <div className="relative">
            <button
              onClick={() => setIsMenuOpen(!isMenuOpen)}
              className="flex items-center gap-2 px-4 py-2 rounded-lg border border-slate-200 hover:bg-slate-50 transition"
            >
              <div className="w-8 h-8 rounded-full bg-slate-900 flex items-center justify-center">
                <User className="h-4 w-4 text-white" />
              </div>
              <span className="text-sm font-medium text-slate-900">{user?.username}</span>
              <ChevronDown className={`h-4 w-4 text-slate-600 transition ${isMenuOpen ? 'rotate-180' : ''}`} />
            </button>

            {isMenuOpen && (
              <div className="absolute right-0 mt-2 w-48 bg-white border border-slate-200 rounded-lg shadow-lg">
                <div className="px-4 py-3 border-b border-slate-200">
                  <p className="text-xs text-slate-600">Conectado como</p>
                  <p className="font-semibold text-slate-900">{user?.full_name}</p>
                  <p className="text-xs text-slate-500">{user?.email}</p>
                </div>
                <button
                  onClick={handleLogout}
                  className="w-full text-left px-4 py-3 flex items-center gap-2 text-slate-700 hover:bg-slate-50 transition"
                >
                  <LogOut className="h-4 w-4" />
                  Cerrar sesión
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    </header>
  )
}
