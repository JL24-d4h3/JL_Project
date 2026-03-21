import { useState } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { BookOpen, Eye, EyeOff, Loader2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { useAuth } from '@/context/AuthContext'

export function AuthPage() {
  const [isSignUp, setIsSignUp] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const navigate = useNavigate()
  const location = useLocation()
  const { login, signup } = useAuth()

  // Formulario SignIn
  const [signInData, setSignInData] = useState({
    email: '',
    password: '',
  })

  // Formulario SignUp
  const [signUpData, setSignUpData] = useState({
    email: '',
    username: '',
    password: '',
    fullName: '',
  })

  const handleSignIn = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)

    try {
      await login(signInData.email, signInData.password)
      const pendingSlug = localStorage.getItem('pendingCourseSlug')
      if (pendingSlug) {
        localStorage.removeItem('pendingCourseSlug')
        navigate(`/course/${pendingSlug}`)
      } else {
        const from = location.state?.from?.pathname || '/'
        navigate(from)
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error al iniciar sesión')
    } finally {
      setLoading(false)
    }
  }

  const handleSignUp = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)

    try {
      await signup(signUpData.email, signUpData.username, signUpData.password, signUpData.fullName)
      const pendingSlug = localStorage.getItem('pendingCourseSlug')
      if (pendingSlug) {
        localStorage.removeItem('pendingCourseSlug')
        navigate(`/course/${pendingSlug}`)
      } else {
        const from = location.state?.from?.pathname || '/'
        navigate(from)
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error al registrarse')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 flex items-center justify-center px-4 py-12">
      <div className="w-full max-w-md">
        {/* Logo */}
        <div className="text-center mb-10">
          <div className="flex items-center justify-center gap-2 mb-4">
            <div className="w-12 h-12 rounded-lg bg-slate-900 flex items-center justify-center">
              <BookOpen className="h-7 w-7 text-white" />
            </div>
            <span className="font-bold text-2xl text-slate-900">CDN Educativa</span>
          </div>
          <p className="text-slate-600">Plataforma educativa de aprendizaje</p>
        </div>

        {/* Card */}
        <div className="bg-white rounded-xl shadow-lg p-8 border border-slate-200">
          {!isSignUp ? (
            // SignIn Form
            <>
              <h2 className="text-2xl font-bold text-slate-900 mb-2">Inicia Sesión</h2>
              <p className="text-slate-600 mb-6">Accede a tus cursos y contenido</p>

              {error && (
                <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg mb-6 text-sm">
                  {error}
                </div>
              )}

              <form onSubmit={handleSignIn}>
                <div className="mb-4">
                  <label className="block text-sm font-medium text-slate-700 mb-2">
                    Email o Usuario
                  </label>
                  <Input
                    type="text"
                    placeholder="ejemplo@email.com"
                    value={signInData.email}
                    onChange={(e) => setSignInData({ ...signInData, email: e.target.value })}
                    className="w-full px-4 py-2 border-2 border-slate-200 rounded-lg focus:border-slate-900 focus:outline-none"
                    required
                  />
                </div>

                <div className="mb-6">
                  <label className="block text-sm font-medium text-slate-700 mb-2">
                    Contraseña
                  </label>
                  <div className="relative">
                    <Input
                      type={showPassword ? 'text' : 'password'}
                      placeholder="••••••••"
                      value={signInData.password}
                      onChange={(e) => setSignInData({ ...signInData, password: e.target.value })}
                      className="w-full px-4 py-2 border-2 border-slate-200 rounded-lg focus:border-slate-900 focus:outline-none"
                      required
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500"
                    >
                      {showPassword ? <EyeOff className="h-5 w-5" /> : <Eye className="h-5 w-5" />}
                    </button>
                  </div>
                </div>

                <Button
                  type="submit"
                  disabled={loading}
                  className="w-full bg-slate-900 hover:bg-slate-800 text-white py-2 rounded-lg font-medium flex items-center justify-center gap-2"
                >
                  {loading && <Loader2 className="h-4 w-4 animate-spin" />}
                  {loading ? 'Iniciando sesión...' : 'Iniciar Sesión'}
                </Button>
              </form>

              <div className="mt-6 text-center">
                <p className="text-slate-600 text-sm">
                  ¿No tienes cuenta?{' '}
                  <button
                    onClick={() => {
                      setIsSignUp(true)
                      setError('')
                    }}
                    className="text-slate-900 hover:text-slate-700 font-medium"
                  >
                    Regístrate aquí
                  </button>
                </p>
              </div>
            </>
          ) : (
            // SignUp Form
            <>
              <h2 className="text-2xl font-bold text-slate-900 mb-2">Crear Cuenta</h2>
              <p className="text-slate-600 mb-6">Únete a nuestra comunidad educativa</p>

              {error && (
                <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg mb-6 text-sm">
                  {error}
                </div>
              )}

              <form onSubmit={handleSignUp}>
                <div className="mb-4">
                  <label className="block text-sm font-medium text-slate-700 mb-2">
                    Nombre Completo
                  </label>
                  <Input
                    type="text"
                    placeholder="Juan Pérez"
                    value={signUpData.fullName}
                    onChange={(e) => setSignUpData({ ...signUpData, fullName: e.target.value })}
                    className="w-full px-4 py-2 border-2 border-slate-200 rounded-lg focus:border-slate-900 focus:outline-none"
                    required
                  />
                </div>

                <div className="mb-4">
                  <label className="block text-sm font-medium text-slate-700 mb-2">
                    Email
                  </label>
                  <Input
                    type="email"
                    placeholder="ejemplo@email.com"
                    value={signUpData.email}
                    onChange={(e) => setSignUpData({ ...signUpData, email: e.target.value })}
                    className="w-full px-4 py-2 border-2 border-slate-200 rounded-lg focus:border-slate-900 focus:outline-none"
                    required
                  />
                </div>

                <div className="mb-4">
                  <label className="block text-sm font-medium text-slate-700 mb-2">
                    Usuario
                  </label>
                  <Input
                    type="text"
                    placeholder="juanperez24"
                    value={signUpData.username}
                    onChange={(e) => setSignUpData({ ...signUpData, username: e.target.value })}
                    className="w-full px-4 py-2 border-2 border-slate-200 rounded-lg focus:border-slate-900 focus:outline-none"
                    required
                  />
                </div>

                <div className="mb-6">
                  <label className="block text-sm font-medium text-slate-700 mb-2">
                    Contraseña
                  </label>
                  <div className="relative">
                    <Input
                      type={showPassword ? 'text' : 'password'}
                      placeholder="••••••••"
                      value={signUpData.password}
                      onChange={(e) => setSignUpData({ ...signUpData, password: e.target.value })}
                      className="w-full px-4 py-2 border-2 border-slate-200 rounded-lg focus:border-slate-900 focus:outline-none"
                      required
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500"
                    >
                      {showPassword ? <EyeOff className="h-5 w-5" /> : <Eye className="h-5 w-5" />}
                    </button>
                  </div>
                </div>

                <Button
                  type="submit"
                  disabled={loading}
                  className="w-full bg-slate-900 hover:bg-slate-800 text-white py-2 rounded-lg font-medium flex items-center justify-center gap-2"
                >
                  {loading && <Loader2 className="h-4 w-4 animate-spin" />}
                  {loading ? 'Registrando...' : 'Crear Cuenta'}
                </Button>
              </form>

              <div className="mt-6 text-center">
                <p className="text-slate-600 text-sm">
                  ¿Ya tienes cuenta?{' '}
                  <button
                    onClick={() => {
                      setIsSignUp(false)
                      setError('')
                    }}
                    className="text-slate-900 hover:text-slate-700 font-medium"
                  >
                    Inicia sesión aquí
                  </button>
                </p>
              </div>
            </>
          )}
        </div>

        {/* Footer */}
        <p className="text-center text-slate-600 text-sm mt-8">
          CDN Educativa PUCP — Plataforma offline para zonas sin conectividad
        </p>
      </div>
    </div>
  )
}
