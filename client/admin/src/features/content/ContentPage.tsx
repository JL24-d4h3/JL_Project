import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { apiClient } from '../../lib/apiClient'

interface ContentItem {
  id: string
  title: string
  description: string | null
  type: string
  thumbnail_path: string | null
  duration_seconds: number | null
  file_size: number | null
  access_count: number
  average_rating: number | null
  created_at: string
  category_name: string | null
}

interface ContentResponse {
  success: boolean
  data: ContentItem[]
  pagination: { total: number; total_pages: number; page: number; limit: number }
}

const TYPE_COLORS: Record<string, string> = {
  video: 'bg-blue-100 text-blue-700',
  audio: 'bg-purple-100 text-purple-700',
  pdf:   'bg-red-100 text-red-700',
  image: 'bg-green-100 text-green-700',
}

function formatBytes(n: number | null) {
  if (n === null || n === undefined) return '—'
  if (n === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(n) / Math.log(k))
  return `${parseFloat((n / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`
}

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString('es-PE', { year: 'numeric', month: 'short', day: 'numeric' })
}

export default function ContentPage() {
  const [search, setSearch] = useState('')

  const { data, isLoading, isError } = useQuery({
    queryKey: ['activeContent'],
    queryFn: () =>
      apiClient
        .get<ContentResponse>('/api/content?limit=100&sort=recent')
        .then(r => r.data),
  })

  const items = data?.data ?? []
  const total = data?.pagination.total ?? 0

  const filtered = items.filter(item => {
    if (!search.trim()) return true
    const q = search.trim().toLowerCase()
    return (
      item.title.toLowerCase().includes(q) ||
      (item.category_name ?? '').toLowerCase().includes(q) ||
      item.type.toLowerCase().includes(q)
    )
  })

  return (
    <div className="space-y-5">
      {/* Toolbar */}
      <div className="flex items-center justify-between gap-4">
        <span className="text-xs font-semibold text-slate-500">
          {isLoading ? 'Cargando...' : `${total} contenidos activos`}
        </span>

        <div className="relative flex-1 max-w-sm">
          <svg className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="11" cy="11" r="8" /><line x1="21" y1="21" x2="16.65" y2="16.65" />
          </svg>
          <input
            type="search"
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="Buscar contenido..."
            className="w-full pl-9 pr-4 py-2 text-sm border border-slate-200 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent placeholder:text-slate-400"
          />
        </div>
      </div>

      {/* Table */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-100 bg-slate-50">
              <th className="text-left text-xs font-semibold text-slate-500 uppercase tracking-wide px-5 py-3">Título</th>
              <th className="text-left text-xs font-semibold text-slate-500 uppercase tracking-wide px-4 py-3">Tipo</th>
              <th className="text-left text-xs font-semibold text-slate-500 uppercase tracking-wide px-4 py-3">Categoría</th>
              <th className="text-left text-xs font-semibold text-slate-500 uppercase tracking-wide px-4 py-3">Tamaño</th>
              <th className="text-left text-xs font-semibold text-slate-500 uppercase tracking-wide px-4 py-3">Fecha</th>
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
            {!isLoading && !isError && filtered.length === 0 && (
              <tr><td colSpan={5}>
                <div className="flex flex-col items-center justify-center py-20 text-center">
                  <div className="w-12 h-12 rounded-full bg-slate-100 flex items-center justify-center mb-3">
                    <svg className="w-6 h-6 text-slate-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                      <rect x="2" y="2" width="20" height="20" rx="2.18" ry="2.18" /><line x1="7" y1="2" x2="7" y2="22" />
                    </svg>
                  </div>
                  <p className="text-sm font-medium text-slate-600">
                    {search.trim() ? 'Sin resultados para esta búsqueda' : 'No hay contenido publicado'}
                  </p>
                  <p className="text-xs text-slate-400 mt-1">
                    {search.trim() ? 'Prueba con otro término.' : 'Aprueba envíos desde la Cola de Revisión.'}
                  </p>
                </div>
              </td></tr>
            )}
            {!isLoading && !isError && filtered.map(item => (
              <tr key={item.id} className="hover:bg-slate-50 transition-colors">
                <td className="px-5 py-3.5">
                  <p className="font-medium text-slate-800 line-clamp-1">{item.title}</p>
                </td>
                <td className="px-4 py-3.5">
                  <span className={`text-xs font-semibold px-2 py-0.5 rounded-full capitalize ${TYPE_COLORS[item.type] ?? 'bg-slate-100 text-slate-600'}`}>
                    {item.type}
                  </span>
                </td>
                <td className="px-4 py-3.5 text-xs text-slate-500">{item.category_name ?? '—'}</td>
                <td className="px-4 py-3.5 text-xs text-slate-500">{formatBytes(item.file_size)}</td>
                <td className="px-4 py-3.5 text-xs text-slate-500 whitespace-nowrap">{formatDate(item.created_at)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
