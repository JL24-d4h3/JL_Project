import { useQuery } from '@tanstack/react-query'
import { apiClient } from '../../lib/apiClient'

interface PendingCountResponse { success: boolean; count: number }
interface ContentListResponse {
  success: boolean
  data: any[]
  pagination: { total: number }
}

export default function DashboardPage() {
  const { data: pendingData } = useQuery({
    queryKey: ['pendingCount'],
    queryFn: () =>
      apiClient
        .get<PendingCountResponse>('/api/upload/pending/count')
        .then(r => r.data.count),
  })

  const { data: contentData } = useQuery({
    queryKey: ['contentStats'],
    queryFn: () =>
      apiClient
        .get<ContentListResponse>('/api/content?limit=1')
        .then(r => r.data.pagination.total),
  })

  const pending = pendingData ?? null
  const active  = contentData ?? null

  const stats = [
    {
      label: 'Contenido activo',
      value: active !== null ? String(active) : '—',
      color: 'text-emerald-700',
      bg: 'bg-emerald-50',
      Icon: () => (
        <svg className="w-5 h-5 text-emerald-600" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <polyline points="20 6 9 17 4 12" />
        </svg>
      ),
    },
    {
      label: 'Pendientes de revisión',
      value: pending !== null ? String(pending) : '—',
      color: 'text-amber-700',
      bg: 'bg-amber-50',
      Icon: () => (
        <svg className="w-5 h-5 text-amber-600" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <circle cx="12" cy="12" r="10" /><polyline points="12 6 12 12 16 14" />
        </svg>
      ),
    },
    {
      label: 'Total en revisión/activo',
      value: active !== null && pending !== null ? String(active + pending) : '—',
      color: 'text-slate-700',
      bg: 'bg-slate-100',
      Icon: () => (
        <svg className="w-5 h-5 text-slate-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <rect x="2" y="2" width="20" height="20" rx="2.18" ry="2.18" />
          <line x1="7" y1="2" x2="7" y2="22" /><line x1="17" y1="2" x2="17" y2="22" />
          <line x1="2" y1="12" x2="22" y2="12" />
        </svg>
      ),
    },
  ]

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {stats.map((s) => (
          <div key={s.label} className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm flex items-center gap-4">
            <div className={`w-10 h-10 rounded-lg ${s.bg} flex items-center justify-center shrink-0`}>
              <s.Icon />
            </div>
            <div>
              <p className={`text-2xl font-bold ${s.color}`}>{s.value}</p>
              <p className="text-xs font-semibold text-slate-500 mt-0.5">{s.label}</p>
            </div>
          </div>
        ))}
      </div>

      <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-8 flex flex-col items-center justify-center text-center py-20">
        <svg className="w-10 h-10 text-slate-300 mb-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
          <line x1="18" y1="20" x2="18" y2="10" /><line x1="12" y1="20" x2="12" y2="4" />
          <line x1="6" y1="20" x2="6" y2="14" /><line x1="2" y1="20" x2="22" y2="20" />
        </svg>
        <p className="text-sm font-medium text-slate-500">Gráficos y métricas detalladas — próximamente</p>
      </div>
    </div>
  )
}
