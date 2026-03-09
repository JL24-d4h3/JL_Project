import type { ContentStatus } from '../types'

const CONFIGS: Record<ContentStatus, { label: string; className: string }> = {
  pending:    { label: 'Pendiente',     className: 'bg-slate-100 text-slate-600 border border-slate-200' },
  active:     { label: 'Aprobado',      className: 'bg-blue-50 text-blue-700 border border-blue-200' },
  rejected:   { label: 'Rechazado',     className: 'bg-red-50 text-red-700 border border-red-200' },
  processing: { label: 'Procesando',    className: 'bg-slate-100 text-slate-500 border border-slate-200' },
  failed:     { label: 'Error',         className: 'bg-red-50 text-red-600 border border-red-200' },
  archived:   { label: 'Archivado',     className: 'bg-slate-100 text-slate-500 border border-slate-200' },
}

interface Props { status: ContentStatus }

export default function StatusBadge({ status }: Props) {
  const { label, className } = CONFIGS[status] ?? CONFIGS.processing
  return (
    <span className={`badge ${className}`}>
      <span className={[
        'w-1.5 h-1.5 rounded-full shrink-0',
        status === 'active'     ? 'bg-blue-500'    :
        status === 'rejected'   ? 'bg-red-500'     :
        status === 'processing' ? 'bg-slate-400'   :
        'bg-slate-400'
      ].join(' ')} />
      {label}
    </span>
  )
}
