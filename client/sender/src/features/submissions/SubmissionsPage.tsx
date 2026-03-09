import { useState } from 'react'
import { Link } from 'react-router-dom'
import { FileVideo, FileText, Music, ArrowRight, Upload, Loader2, AlertCircle } from 'lucide-react'
import { useMySubmissions } from '../../hooks/queries'
import StatusBadge from '../../components/StatusBadge'
import { formatDate, formatBytes } from '../../utils/format'
import type { ContentStatus } from '../../types'

const FILTERS: { label: string; value: ContentStatus | 'all' }[] = [
  { label: 'Todos',      value: 'all'       },
  { label: 'Pendientes', value: 'pending'   },
  { label: 'Aprobados',  value: 'active'    },
  { label: 'Rechazados', value: 'rejected'  },
]

const TYPE_ICON: Record<string, React.ReactNode> = {
  video:    <FileVideo size={15} className="text-slate-400 shrink-0" />,
  audio:    <Music    size={15} className="text-slate-400 shrink-0" />,
  document: <FileText size={15} className="text-slate-400 shrink-0" />,
}

export default function SubmissionsPage() {
  const [filter, setFilter] = useState<ContentStatus | 'all'>('all')
  const [search, setSearch] = useState('')

  const { data: submissions = [], isLoading, isError, refetch } = useMySubmissions()

  const filtered = submissions.filter(s => {
    const matchesFilter = filter === 'all' || s.status === filter
    const q = search.trim().toLowerCase()
    const matchesSearch = !q || s.title.toLowerCase().includes(q)
    return matchesFilter && matchesSearch
  })

  return (
    <div className="max-w-5xl space-y-4">

      {/* Toolbar */}
      <div className="flex flex-col sm:flex-row sm:items-center gap-3">
        {/* Filter tabs */}
        <div className="flex gap-1 bg-white border border-slate-200 rounded-lg p-1 w-fit shadow-sm shrink-0">
          {FILTERS.map(f => (
            <button
              key={f.value}
              onClick={() => setFilter(f.value)}
              className={[
                'px-3.5 py-1.5 rounded-md text-xs font-semibold transition-all',
                filter === f.value
                  ? 'bg-slate-900 text-white shadow-sm'
                  : 'text-slate-500 hover:text-slate-700',
              ].join(' ')}
            >
              {f.label}
            </button>
          ))}
        </div>

        <div className="relative flex-1 max-w-sm">
          <input
            type="search"
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="Buscar por título..."
            className="input pl-3 pr-4 py-2 text-sm"
          />
        </div>

        <Link to="/upload" className="btn-primary text-xs shrink-0 self-start sm:self-auto">
          <Upload size={14} />
          Nuevo envío
        </Link>
      </div>

      {/* Table */}
      <div className="card overflow-hidden">
        {isError && (
          <div className="flex items-center gap-3 px-5 py-4 bg-red-50 border-b border-red-100">
            <AlertCircle size={16} className="text-red-500 shrink-0" />
            <p className="text-sm text-red-700 flex-1">No se pudieron cargar tus envíos.</p>
            <button onClick={() => refetch()} className="text-xs text-red-700 underline">Reintentar</button>
          </div>
        )}

        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-slate-50 border-b border-slate-100">
                <th className="text-left text-xs font-semibold text-slate-400 uppercase tracking-wide px-5 py-3">Título</th>
                <th className="text-left text-xs font-semibold text-slate-400 uppercase tracking-wide px-4 py-3 hidden sm:table-cell">Tipo</th>
                <th className="text-left text-xs font-semibold text-slate-400 uppercase tracking-wide px-4 py-3 hidden md:table-cell">Tamaño</th>
                <th className="text-left text-xs font-semibold text-slate-400 uppercase tracking-wide px-4 py-3 hidden lg:table-cell">Fecha</th>
                <th className="text-left text-xs font-semibold text-slate-400 uppercase tracking-wide px-4 py-3">Estado</th>
                <th className="w-10 px-4 py-3" />
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-50">
              {isLoading ? (
                Array.from({ length: 4 }).map((_, i) => (
                  <tr key={i}>
                    <td colSpan={6} className="px-5 py-3.5">
                      <div className="h-4 bg-slate-100 rounded animate-pulse" style={{ width: `${60 + i * 8}%` }} />
                    </td>
                  </tr>
                ))
              ) : filtered.length === 0 ? (
                <tr>
                  <td colSpan={6}>
                    <div className="flex flex-col items-center justify-center py-14 text-center">
                      <div className="w-11 h-11 rounded-full bg-slate-100 flex items-center justify-center mb-3">
                        {isLoading ? (
                          <Loader2 size={20} className="text-slate-400 animate-spin" />
                        ) : (
                          <Upload size={20} className="text-slate-400" />
                        )}
                      </div>
                      <p className="text-sm font-medium text-slate-600">
                        {search ? 'Sin resultados para tu búsqueda' : 'Sin envíos todavía'}
                      </p>
                      {!search && (
                        <p className="text-xs text-slate-400 mt-1">
                          <Link to="/upload" className="text-blue-700 hover:underline">Sube tu primer contenido</Link>
                        </p>
                      )}
                    </div>
                  </td>
                </tr>
              ) : (
                filtered.map(sub => (
                  <tr key={sub.id} className="hover:bg-slate-50 transition-colors group">
                    <td className="px-5 py-3.5">
                      <div className="flex items-center gap-2.5">
                        {TYPE_ICON[sub.content_type] ?? <FileText size={15} className="text-slate-400 shrink-0" />}
                        <div className="min-w-0">
                          <p className="font-medium text-slate-800 truncate max-w-[180px] md:max-w-[300px]">
                            {sub.title}
                          </p>
                          {sub.status === 'rejected' && sub.rejected_reason && (
                            <p className="text-xs text-red-600 mt-0.5 truncate max-w-[240px]">
                              {sub.rejected_reason}
                            </p>
                          )}
                        </div>
                      </div>
                    </td>
                    <td className="px-4 py-3.5 hidden sm:table-cell">
                      <span className="text-xs text-slate-400 capitalize">{sub.content_type}</span>
                    </td>
                    <td className="px-4 py-3.5 text-xs text-slate-400 hidden md:table-cell">
                      {formatBytes(sub.file_size_bytes)}
                    </td>
                    <td className="px-4 py-3.5 text-xs text-slate-400 hidden lg:table-cell">
                      {formatDate(sub.created_at)}
                    </td>
                    <td className="px-4 py-3.5">
                      <StatusBadge status={sub.status} />
                    </td>
                    <td className="px-4 py-3.5">
                      <Link
                        to={`/submissions/${sub.id}`}
                        className="opacity-0 group-hover:opacity-100 transition-opacity text-slate-400 hover:text-blue-700 p-1 rounded"
                        title="Ver detalle"
                      >
                        <ArrowRight size={14} />
                      </Link>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Footer count */}
        {!isLoading && !isError && filtered.length > 0 && (
          <div className="px-5 py-3 border-t border-slate-100 bg-slate-50">
            <p className="text-xs text-slate-400">
              {filtered.length} {filtered.length === 1 ? 'envío' : 'envíos'}
              {filter !== 'all' && ` · filtrado por ${FILTERS.find(f => f.value === filter)?.label.toLowerCase()}`}
            </p>
          </div>
        )}
      </div>

    </div>
  )
}
