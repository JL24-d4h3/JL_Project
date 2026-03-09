import { Link } from 'react-router-dom'
import { Upload, Clock, CheckCircle, XCircle, ArrowRight, FileVideo, FileText, Music } from 'lucide-react'
import { useMySubmissions } from '../../hooks/queries'
import StatusBadge from '../../components/StatusBadge'
import { formatDate, formatBytes } from '../../utils/format'
import type { Submission } from '../../types'

const TYPE_ICON: Record<string, React.ReactNode> = {
  video:    <FileVideo size={14} className="text-slate-400" />,
  audio:    <Music size={14} className="text-slate-400" />,
  document: <FileText size={14} className="text-slate-400" />,
}

function StatCard({
  icon, label, value, sub, loading,
}: {
  icon: React.ReactNode
  label: string
  value: number | string
  sub: string
  loading?: boolean
}) {
  return (
    <div className="card p-5">
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide">{label}</p>
          {loading ? (
            <div className="h-8 w-16 bg-slate-100 rounded animate-pulse mt-2" />
          ) : (
            <p className="text-3xl font-bold text-slate-800 mt-1.5">{value}</p>
          )}
          <p className="text-xs text-slate-400 mt-1">{sub}</p>
        </div>
        <div className="w-9 h-9 rounded-lg bg-slate-50 border border-slate-100 flex items-center justify-center shrink-0 ml-3">
          {icon}
        </div>
      </div>
    </div>
  )
}

export default function DashboardPage() {
  const { data: submissions = [], isLoading, isError } = useMySubmissions()

  const stats = {
    total:    submissions.length,
    pending:  submissions.filter(s => s.status === 'pending').length,
    active:   submissions.filter(s => s.status === 'active').length,
    rejected: submissions.filter(s => s.status === 'rejected').length,
  }

  const recent: Submission[] = submissions.slice(0, 5)

  return (
    <div className="space-y-6 max-w-5xl">

      {/* Stat cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 lg:gap-4">
        <StatCard icon={<Upload size={18} className="text-slate-500" />}    label="Total enviados" value={stats.total}    sub="todos los estados"       loading={isLoading} />
        <StatCard icon={<Clock size={18} className="text-slate-500" />}     label="Pendientes"     value={stats.pending}   sub="en espera de revisión"   loading={isLoading} />
        <StatCard icon={<CheckCircle size={18} className="text-blue-600" />} label="Aprobados"    value={stats.active}    sub="publicados y activos"    loading={isLoading} />
        <StatCard icon={<XCircle size={18} className="text-slate-400" />}   label="Rechazados"    value={stats.rejected}  sub="requieren corrección"    loading={isLoading} />
      </div>

      {/* CTA */}
      <div className="bg-slate-900 rounded-xl p-5 lg:p-6 flex flex-col sm:flex-row sm:items-center gap-4 sm:gap-6">
        <div className="flex-1">
          <p className="text-white font-semibold text-base">Comparte tu conocimiento</p>
          <p className="text-slate-400 text-sm mt-1">
            Sube un video, PDF o audio para que el equipo lo revise y publique.
          </p>
        </div>
        <Link to="/upload" className="btn-primary shrink-0 self-start sm:self-auto">
          Subir contenido
          <ArrowRight size={15} />
        </Link>
      </div>

      {/* Recent submissions */}
      <div className="card overflow-hidden">
        <div className="flex items-center justify-between px-5 py-4 border-b border-slate-100">
          <p className="text-sm font-semibold text-slate-700">Envíos recientes</p>
          <Link to="/submissions" className="text-xs text-blue-700 hover:text-blue-800 font-medium flex items-center gap-1">
            Ver todos <ArrowRight size={12} />
          </Link>
        </div>

        {isError && (
          <div className="px-5 py-4 text-sm text-red-600">
            No se pudo cargar. Verifica que el servidor esté activo y hayas iniciado sesión.
          </div>
        )}

        {isLoading ? (
          <div className="divide-y divide-slate-50">
            {Array.from({ length: 3 }).map((_, i) => (
              <div key={i} className="px-5 py-4 flex items-center gap-4">
                <div className="h-4 bg-slate-100 rounded animate-pulse flex-1" />
                <div className="h-4 w-20 bg-slate-100 rounded animate-pulse" />
                <div className="h-4 w-16 bg-slate-100 rounded animate-pulse" />
              </div>
            ))}
          </div>
        ) : recent.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-14 text-center">
            <div className="w-11 h-11 rounded-full bg-slate-100 flex items-center justify-center mb-3">
              <Upload size={20} className="text-slate-400" />
            </div>
            <p className="text-sm font-medium text-slate-600">Todavía no tienes envíos</p>
            <p className="text-xs text-slate-400 mt-1">Tus archivos subidos aparecerán aquí</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-slate-50 border-b border-slate-100">
                  <th className="text-left text-xs font-semibold text-slate-400 uppercase tracking-wide px-5 py-3">Título</th>
                  <th className="text-left text-xs font-semibold text-slate-400 uppercase tracking-wide px-4 py-3 hidden sm:table-cell">Tamaño</th>
                  <th className="text-left text-xs font-semibold text-slate-400 uppercase tracking-wide px-4 py-3 hidden md:table-cell">Fecha</th>
                  <th className="text-left text-xs font-semibold text-slate-400 uppercase tracking-wide px-4 py-3">Estado</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-50">
                {recent.map(sub => (
                  <tr key={sub.id} className="hover:bg-slate-50 transition-colors">
                    <td className="px-5 py-3.5">
                      <div className="flex items-center gap-2.5">
                        {TYPE_ICON[sub.content_type] ?? <FileText size={14} className="text-slate-400" />}
                        <Link to={`/submissions/${sub.id}`} className="font-medium text-slate-800 hover:text-blue-700 transition-colors truncate max-w-[180px] sm:max-w-none">
                          {sub.title}
                        </Link>
                      </div>
                    </td>
                    <td className="px-4 py-3.5 text-slate-500 text-xs hidden sm:table-cell">{formatBytes(sub.file_size_bytes)}</td>
                    <td className="px-4 py-3.5 text-slate-500 text-xs hidden md:table-cell">{formatDate(sub.created_at)}</td>
                    <td className="px-4 py-3.5"><StatusBadge status={sub.status} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

    </div>
  )
}
