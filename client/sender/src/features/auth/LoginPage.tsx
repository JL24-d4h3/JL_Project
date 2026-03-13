import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Zap, Loader2, AlertCircle, Eye, EyeOff } from 'lucide-react'
import { apiClient } from '../../lib/apiClient'

export default function LoginPage() {
  const navigate = useNavigate()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!username.trim() || !password) return

    setLoading(true)
    setError('')

    try {
      const res = await apiClient.post<{
        success: boolean
        data: { token: string; user: { full_name: string; role: string } }
      }>('/api/auth/login', { username: username.trim(), password })

      localStorage.setItem('token', res.data.data.token)
      navigate('/', { replace: true })
    } catch (err: any) {
      const msg = err.response?.data?.message ?? err.response?.data?.error
      if (err.response?.status === 401) {
        setError('Usuario o contraseña incorrectos.')
      } else if (err.response?.status === 423) {
        setError(msg ?? 'Cuenta bloqueada temporalmente. Intenta en unos minutos.')
      } else if (!err.response) {
        setError('No se pudo conectar al servidor. Verifica que esté en ejecución.')
      } else {
        setError(msg ?? 'Error inesperado. Intenta de nuevo.')
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-slate-900 flex items-center justify-center p-4">
      <div className="w-full max-w-sm">

        {/* Logo */}
        <div className="flex flex-col items-center mb-8">
          <div className="w-12 h-12 rounded-xl bg-blue-600 flex items-center justify-center mb-4">
            <Zap size={22} className="text-white" strokeWidth={2.5} />
          </div>
          <h1 className="text-white text-xl font-bold">CDN Offline</h1>
          <p className="text-slate-400 text-sm mt-1">Portal Docente</p>
        </div>

        {/* Card */}
        <div className="bg-white rounded-2xl p-7 shadow-xl">
          <h2 className="text-slate-800 font-semibold text-lg mb-6">Iniciar sesión</h2>

          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Error */}
            {error && (
              <div className="flex items-start gap-2.5 bg-red-50 border border-red-200 rounded-lg px-4 py-3">
                <AlertCircle size={15} className="text-red-500 shrink-0 mt-0.5" />
                <p className="text-sm text-red-700">{error}</p>
              </div>
            )}

            {/* Username */}
            <div>
              <label className="label">Usuario</label>
              <input
                type="text"
                value={username}
                onChange={e => setUsername(e.target.value)}
                className="input"
                placeholder="ej. docente1"
                autoComplete="username"
                autoFocus
                disabled={loading}
              />
            </div>

            {/* Password */}
            <div>
              <label className="label">Contraseña</label>
              <div className="relative">
                <input
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  className="input pr-10"
                  placeholder="••••••••"
                  autoComplete="current-password"
                  disabled={loading}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(v => !v)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 transition-colors"
                  tabIndex={-1}
                >
                  {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
            </div>

            <button
              type="submit"
              disabled={loading || !username.trim() || !password}
              className="btn-primary w-full justify-center mt-2"
            >
              {loading
                ? <><Loader2 size={15} className="animate-spin" /> Ingresando...</>
                : 'Ingresar'}
            </button>
          </form>
        </div>

      </div>
    </div>
  )
}
