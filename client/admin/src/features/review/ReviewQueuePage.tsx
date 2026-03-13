import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { apiClient } from '../../lib/apiClient'

type ContentType = 'video' | 'audio' | 'pdf' | 'image'

interface PendingItem {
  id: string
  title: string
  description: string | null
  content_type: ContentType
  status: string
  duration: number | null
  file_size_bytes: number | null
  file_path: string
  thumbnail_path: string | null
  created_at: string
  submitted_by_username: string
  submitted_by_name: string
}

const TYPE_LABELS: Record<ContentType, string> = {
  video: 'Video',
  audio: 'Audio',
  pdf: 'PDF',
  image: 'Imagen',
}

const TYPE_COLORS: Record<ContentType, string> = {
  video: 'bg-blue-100 text-blue-700',
  audio: 'bg-purple-100 text-purple-700',
  pdf: 'bg-red-100 text-red-700',
  image: 'bg-green-100 text-green-700',
}

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString('es-PE', {
    year: 'numeric', month: 'short', day: 'numeric',
  })
}

export default function ReviewQueuePage() {
  const navigate = useNavigate()
  const [search, setSearch] = useState('')

  const { data, isLoading, isError } = useQuery({
    queryKey: ['pendingQueue'],
    queryFn: () =>
      apiClient
        .get<{ success: boolean; data: PendingItem[] }>('/api/upload/pending')
        .then(r => r.data.data),
  })

  const items = data ?? []
  const filtered = items.filter(item => {
    if (!search.trim()) return true
    const q = search.trim().toLowerCase()
    return (
      item.title.toLowerCase().includes(q) ||
      item.submitted_by_name.toLowerCase().includes(q) ||
      item.submitted_by_username.toLowerCase().includes(q)
    )
  })

  return (
    <div className="space-y-5">

      {/* Header row */}
      <div className="flex items-center justify-between gap-4">
        <div className="flex items-center gap-2.5">
          {isLoading ? (
            <span className="bg-slate-100 text-slate-500 text-xs font-bold px-2.5 py-1 rounded-full">
              Cargando...
            </span>
          ) : (
            <span className="bg-amber-100 text-amber-800 text-xs font-bold px-2.5 py-1 rounded-full">
              {items.length} {items.length === 1 ? 'pendiente' : 'pendientes'}
            </span>
          )}
        </div>

        {/* Search */}
        <div className="relative flex-1 max-w-sm">
          <svg className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="11" cy="11" r="8" /><line x1="21" y1="21" x2="16.65" y2="16.65" />
          </svg>
          <input
            type="search"
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="Buscar por título o autor..."
            className="w-full pl-9 pr-4 py-2 text-sm border border-slate-200 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent placeholder:text-slate-400"
          />
        </div>
      </div>

      {/* Table */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-100 bg-slate-50">
              <th className="text-left text-xs font-semibold text-slate-500 uppercase tracking-wide px-5 py-3">Contenido</th>
              <th className="text-left text-xs font-semibold text-slate-500 uppercase tracking-wide px-4 py-3">Tipo</th>
              <th className="text-left text-xs font-semibold text-slate-500 uppercase tracking-wide px-4 py-3">Enviado por</th>
              <th className="text-left text-xs font-semibold text-slate-500 uppercase tracking-wide px-4 py-3">Fecha</th>
              <th className="px-4 py-3" />
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {isLoading && (
              <tr>
                <td colSpan={5}>
                  <div className="flex items-center justify-center py-20">
                    <div className="w-6 h-6 border-2 border-indigo-600 border-t-transparent rounded-full animate-spin" />
                  </div>
                </td>
              </tr>
            )}

            {isError && (
              <tr>
                <td colSpan={5}>
                  <div className="flex flex-col items-center justify-center py-16 text-center">
                    <div className="w-12 h-12 rounded-full bg-red-50 flex items-center justify-center mb-3">
                      <svg className="w-6 h-6 text-red-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                        <circle cx="12" cy="12" r="10" /><line x1="12" y1="8" x2="12" y2="12" /><line x1="12" y1="16" x2="12.01" y2="16" />
                      </svg>
                    </div>
                    <p className="text-sm font-semibold text-slate-600">Error al cargar la cola</p>
                    <p className="text-xs text-slate-400 mt-1">Verifica tu sesión y reintenta.</p>
                  </div>
                </td>
              </tr>
            )}

            {!isLoading && !isError && filtered.length === 0 && (
              <tr>
                <td colSpan={5}>
                  <div className="flex flex-col items-center justify-center py-20 text-center">
                    <div className="w-14 h-14 rounded-full bg-slate-100 flex items-center justify-center mb-4">
                      <svg className="w-7 h-7 text-slate-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                        <polyline points="22 12 16 12 14 15 10 15 8 12 2 12" />
                        <path d="M5.45 5.11L2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11z" />
                      </svg>
                    </div>
                    <p className="text-sm font-semibold text-slate-600">
                      {search.trim() ? 'Sin resultados para esta búsqueda' : 'No hay envíos pendientes'}
                    </p>
                    <p className="text-xs text-slate-400 mt-1 max-w-xs">
                      {search.trim()
                        ? 'Prueba con otro término de búsqueda.'
                        : 'Cuando los docentes suban contenido, aparecerá aquí para revisión.'}
                    </p>
                  </div>
                </td>
              </tr>
            )}

            {!isLoading && !isError && filtered.map(item => (
              <tr
                key={item.id}
                onClick={() => navigate(`/review/${item.id}`)}
                className="hover:bg-slate-50 cursor-pointer transition-colors"
              >
                <td className="px-5 py-3.5">
                  <p className="font-medium text-slate-800 line-clamp-1">{item.title}</p>
                  {item.description && (
                    <p className="text-xs text-slate-400 mt-0.5 line-clamp-1">{item.description}</p>
                  )}
                </td>
                <td className="px-4 py-3.5">
                  <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${TYPE_COLORS[item.content_type] ?? 'bg-slate-100 text-slate-600'}`}>
                    {TYPE_LABELS[item.content_type] ?? item.content_type}
                  </span>
                </td>
                <td className="px-4 py-3.5">
                  <p className="text-slate-700 text-xs font-medium">{item.submitted_by_name}</p>
                  <p className="text-slate-400 text-xs">@{item.submitted_by_username}</p>
                </td>
                <td className="px-4 py-3.5 text-xs text-slate-500 whitespace-nowrap">
                  {formatDate(item.created_at)}
                </td>
                <td className="px-4 py-3.5">
                  <div className="flex items-center justify-end">
                    <svg className="w-4 h-4 text-slate-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <polyline points="9 18 15 12 9 6" />
                    </svg>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

    </div>
  )
}
