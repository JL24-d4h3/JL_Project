import { useQuery } from '@tanstack/react-query'
import { apiClient } from '../../lib/apiClient'

interface User {
  id: string
  username: string
  email: string | null
  full_name: string | null
  role: string
  is_active: boolean
  last_login: string | null
  created_at: string
}

const ROLE_STYLES: Record<string, string> = {
  superadmin: 'bg-purple-100 text-purple-700',
  admin:      'bg-indigo-100 text-indigo-700',
  teacher:    'bg-blue-100 text-blue-700',
  student:    'bg-slate-100 text-slate-600',
}

const ROLE_LABELS: Record<string, string> = {
  superadmin: 'Superadmin',
  admin: 'Administrador',
  teacher: 'Docente',
  student: 'Estudiante',
}

function formatDate(iso: string | null) {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString('es-PE', {
    year: 'numeric', month: 'short', day: 'numeric',
  })
}

export default function UsersPage() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['users'],
    queryFn: () =>
      apiClient
        .get<{ success: boolean; data: User[]; count: number }>('/api/auth/users')
        .then(r => r.data.data),
  })

  const users = data ?? []

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold text-slate-500">
          {isLoading ? 'Cargando...' : `${users.length} usuarios registrados`}
        </span>
      </div>

      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-slate-50 border-b border-slate-100">
              <th className="text-left text-xs font-semibold text-slate-500 uppercase tracking-wide px-5 py-3">Usuario</th>
              <th className="text-left text-xs font-semibold text-slate-500 uppercase tracking-wide px-4 py-3">Rol</th>
              <th className="text-left text-xs font-semibold text-slate-500 uppercase tracking-wide px-4 py-3">Estado</th>
              <th className="text-left text-xs font-semibold text-slate-500 uppercase tracking-wide px-4 py-3">Último acceso</th>
              <th className="text-left text-xs font-semibold text-slate-500 uppercase tracking-wide px-4 py-3">Creado</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {isLoading && (
              <tr><td colSpan={5}>
                <div className="flex items-center justify-center py-20">
                  <div className="w-6 h-6 border-2 border-indigo-600 border-t-transparent rounded-full animate-spin" />
                </div>
              </td></tr>
            )}
            {isError && (
              <tr><td colSpan={5}>
                <div className="flex flex-col items-center justify-center py-16 text-center">
                  <p className="text-sm font-semibold text-slate-600">No se pudo conectar con el servidor</p>
                  <p className="text-xs text-slate-400 mt-1">Verifica que el servidor esté ejecutándose y tu sesión sea válida.</p>
                </div>
              </td></tr>
            )}
            {!isLoading && !isError && users.length === 0 && (
              <tr><td colSpan={5}>
                <div className="flex items-center justify-center py-16">
                  <p className="text-sm text-slate-500">No hay usuarios registrados.</p>
                </div>
              </td></tr>
            )}
            {!isLoading && !isError && users.map(user => {
              const initials = (user.full_name ?? user.username)
                .split(' ').map((w: string) => w[0]).slice(0, 2).join('').toUpperCase()
              return (
                <tr key={user.id} className="hover:bg-slate-50 transition-colors">
                  <td className="px-5 py-3.5">
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 rounded-full bg-indigo-100 flex items-center justify-center text-xs font-bold text-indigo-700 shrink-0">
                        {initials}
                      </div>
                      <div className="min-w-0">
                        <p className="font-medium text-slate-800 text-sm truncate">{user.full_name ?? user.username}</p>
                        <p className="text-xs text-slate-400 truncate">@{user.username}{user.email ? ` · ${user.email}` : ''}</p>
                      </div>
                    </div>
                  </td>
                  <td className="px-4 py-3.5">
                    <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${ROLE_STYLES[user.role] ?? 'bg-slate-100 text-slate-600'}`}>
                      {ROLE_LABELS[user.role] ?? user.role}
                    </span>
                  </td>
                  <td className="px-4 py-3.5">
                    <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${user.is_active ? 'bg-emerald-100 text-emerald-700' : 'bg-red-100 text-red-700'}`}>
                      {user.is_active ? 'Activo' : 'Inactivo'}
                    </span>
                  </td>
                  <td className="px-4 py-3.5 text-xs text-slate-500 whitespace-nowrap">{formatDate(user.last_login)}</td>
                  <td className="px-4 py-3.5 text-xs text-slate-500 whitespace-nowrap">{formatDate(user.created_at)}</td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}
