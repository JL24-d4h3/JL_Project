import { Link, useParams } from 'react-router-dom'
import { ArrowLeft, FileVideo, Music, FileText, AlertTriangle, Clock, CheckCircle2, XCircle, Archive, Loader2 } from 'lucide-react'
import { useMySubmissions } from '../../hooks/queries'
import StatusBadge from '../../components/StatusBadge'
import { formatBytes, formatDate, formatDuration } from '../../utils/format'
import type { ContentStatus } from '../../types'

const STATUS_META: Record<ContentStatus, { icon: React.ReactNode; label: string; color: string; description: string }> = {
  pending:    { icon: <Clock      size={18} />, label: 'Pendiente de revisión', color: 'text-slate-500',   description: 'Tu envío está en cola. El equipo de revisión lo revisará pronto.'                     },
  active:     { icon: <CheckCircle2 size={18} />, label: 'Aprobado',            color: 'text-blue-700',    description: 'Tu contenido fue aprobado y está disponible en la plataforma.'                      },
  rejected:   { icon: <XCircle    size={18} />, label: 'Rechazado',             color: 'text-red-600',     description: 'Tu envío no fue aprobado. Lee el motivo a continuación.'                           },
  processing: { icon: <Loader2   size={18} className="animate-spin" />, label: 'Procesando', color: 'text-slate-500', description: 'El archivo está siendo procesado. Espera unos momentos.' },
  failed:     { icon: <AlertTriangle size={18} />, label: 'Error de proceso',   color: 'text-red-600',     description: 'Ocurrió un error al procesar el archivo. Contacta al soporte.'                    },
  archived:   { icon: <Archive    size={18} />, label: 'Archivado',             color: 'text-slate-400',   description: 'Este contenido ha sido archivado y ya no está disponible públicamente.'            },
}

const TYPE_ICON: Record<string, React.ReactNode> = {
  video:    <FileVideo size={32} className="text-slate-300" />,
  audio:    <Music     size={32} className="text-slate-300" />,
  document: <FileText  size={32} className="text-slate-300" />,
}

export default function SubmissionDetailPage() {
  const { id } = useParams<{ id: string }>()
  const { data: submissions = [], isLoading, isError } = useMySubmissions()

  const sub = submissions.find(s => String(s.id) === id)

  if (isLoading) {
    return (
      <div className="space-y-4">
        <div className="h-5 w-36 bg-slate-100 rounded animate-pulse" />
        <div className="card p-6 space-y-4">
          {[100, 80, 60, 40].map(w => (
            <div key={w} className={`h-4 bg-slate-100 rounded animate-pulse`} style={{ width: `${w}%` }} />
          ))}
        </div>
      </div>
    )
  }

  if (isError || !sub) {
    return (
      <div className="w-full">
        <Link to="/submissions" className="inline-flex items-center gap-2 text-sm text-slate-500 hover:text-slate-700 mb-5">
          <ArrowLeft size={15} /> Volver a mis envíos
        </Link>
        <div className="card p-8 flex flex-col items-center text-center gap-3">
          <AlertTriangle size={32} className="text-slate-300" />
          <p className="font-medium text-slate-700">Envío no encontrado</p>
          <p className="text-sm text-slate-400">No se pudo encontrar este contenido o no tienes acceso.</p>
        </div>
      </div>
    )
  }

  const meta = STATUS_META[sub.status]

  return (
    <div className="space-y-5">

      <Link to="/submissions" className="inline-flex items-center gap-2 text-sm text-slate-500 hover:text-slate-700">
        <ArrowLeft size={15} /> Volver a mis envíos
      </Link>

      {/* Header card */}
      <div className="card p-6">
        <div className="flex items-start gap-4">
          <div className="w-14 h-14 rounded-xl bg-slate-100 flex items-center justify-center shrink-0">
            {TYPE_ICON[sub.content_type] ?? <FileText size={32} className="text-slate-300" />}
          </div>
          <div className="min-w-0 flex-1">
            <h1 className="text-lg font-semibold text-slate-800 leading-snug">{sub.title}</h1>
            {sub.description && (
              <p className="text-sm text-slate-500 mt-1 whitespace-pre-line">{sub.description}</p>
            )}
          </div>
          <StatusBadge status={sub.status} />
        </div>
      </div>

      {/* Status info */}
      <div className={[
        'card p-5 flex items-start gap-3',
        sub.status === 'rejected' ? 'border-red-200 bg-red-50'
          : sub.status === 'active' ? 'border-blue-200 bg-blue-50'
          : '',
      ].join(' ')}>
        <span className={meta.color}>{meta.icon}</span>
        <div className="min-w-0 flex-1">
          <p className={`text-sm font-semibold ${meta.color}`}>{meta.label}</p>
          <p className="text-xs text-slate-500 mt-0.5">{meta.description}</p>
          {sub.status === 'rejected' && sub.rejected_reason && (
            <div className="mt-3 p-3 bg-white border border-red-200 rounded-lg">
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1">Motivo</p>
              <p className="text-sm text-slate-700">{sub.rejected_reason}</p>
            </div>
          )}
        </div>
      </div>

      {/* File metadata */}
      <div className="card p-5">
        <p className="text-xs font-semibold text-slate-400 uppercase tracking-wide mb-4">Información del archivo</p>
        <dl className="grid grid-cols-2 gap-y-4 gap-x-6 sm:grid-cols-3">
          {[
            { label: 'Tipo',       value: sub.content_type },
            { label: 'Tamaño',     value: formatBytes(sub.file_size_bytes) },
            { label: 'Duración',   value: sub.duration ? formatDuration(sub.duration) : '—' },
            { label: 'Enviado',    value: formatDate(sub.created_at) },
            { label: 'Actualizado', value: formatDate(sub.updated_at) },
          ].map(({ label, value }) => (
            <div key={label}>
              <dt className="text-xs text-slate-400 mb-0.5">{label}</dt>
              <dd className="text-sm font-medium text-slate-700 capitalize">{value}</dd>
            </div>
          ))}
        </dl>
      </div>

    </div>
  )
}

