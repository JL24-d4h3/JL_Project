import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import toast, { Toaster } from 'react-hot-toast'
import { apiClient } from '../../lib/apiClient'

type ActionMode = 'idle' | 'reject' | 'curate'

interface ContentDetail {
  id: string
  title: string
  description: string | null
  type: string
  status: string
  file_path: string
  file_size: number | null
  duration_seconds: number | null
  thumbnail_path: string | null
  created_at: string
  category_name: string | null
  created_by_name: string | null
}

function formatBytes(n: number | null) {
  if (n === null || n === undefined) return '—'
  if (n === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(n) / Math.log(k))
  return `${parseFloat((n / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`
}

function formatDuration(s: number | null) {
  if (s === null || s === undefined) return '—'
  if (s === 0) return '0:00'
  const h = Math.floor(s / 3600)
  const m = Math.floor((s % 3600) / 60)
  const sec = s % 60
  if (h > 0) return `${h}:${String(m).padStart(2, '0')}:${String(sec).padStart(2, '0')}`
  return `${m}:${String(sec).padStart(2, '0')}`
}

export default function ReviewDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const qc = useQueryClient()

  const [mode, setMode] = useState<ActionMode>('idle')
  const [rejectReason, setRejectReason] = useState('')
  const [curateTitle, setCurateTitle] = useState('')
  const [curateDesc, setCurateDesc] = useState('')

  const { data, isLoading, isError } = useQuery({
    queryKey: ['contentDetail', id],
    queryFn: () =>
      apiClient
        .get<{ success: boolean; data: ContentDetail }>(`/api/content/${id}`)
        .then(r => r.data.data),
    enabled: !!id,
  })

  const mutation = useMutation({
    mutationFn: (body: Record<string, unknown>) =>
      apiClient.patch(`/api/upload/${id}/review`, body),
    onSuccess: (_res, vars) => {
      const action = vars.action as string
      const label = action === 'approve' ? 'aprobado' : action === 'curate' ? 'curado y aprobado' : 'rechazado'
      toast.success(`Contenido ${label} correctamente.`)
      qc.invalidateQueries({ queryKey: ['pendingQueue'] })
      qc.invalidateQueries({ queryKey: ['pendingCount'] })
      navigate('/')
    },
    onError: (err: any) => {
      const msg = err.response?.data?.message ?? err.response?.data?.error ?? 'Error al procesar la acción.'
      toast.error(msg)
    },
  })

  const approve = () => mutation.mutate({ action: 'approve' })

  const submitCurate = () => {
    if (!curateTitle.trim()) { toast.error('El título no puede estar vacío.'); return }
    mutation.mutate({
      action: 'curate',
      title: curateTitle.trim(),
      description: curateDesc.trim() || undefined,
    })
  }

  const submitReject = () => {
    if (!rejectReason.trim()) { toast.error('Debes ingresar un motivo de rechazo.'); return }
    mutation.mutate({ action: 'reject', reason: rejectReason.trim() })
  }

  const initCurate = () => {
    setCurateTitle(data?.title ?? '')
    setCurateDesc(data?.description ?? '')
    setMode('curate')
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-48">
        <div className="w-6 h-6 border-2 border-indigo-600 border-t-transparent rounded-full animate-spin" />
      </div>
    )
  }

  if (isError || !data) {
    return (
      <div className="flex flex-col items-center justify-center h-48 text-center">
        <p className="text-sm font-semibold text-slate-600">Contenido no encontrado</p>
        <button onClick={() => navigate('/')} className="mt-3 text-xs text-indigo-600 hover:underline">
          ← Volver a la cola
        </button>
      </div>
    )
  }

  const busy = mutation.isPending

  return (
    <>
      <Toaster position="top-right" />
      <div className="max-w-3xl space-y-5">

        {/* Back */}
        <button
          onClick={() => navigate('/')}
          className="flex items-center gap-1.5 text-sm text-slate-500 hover:text-slate-700 transition-colors"
        >
          <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <polyline points="15 18 9 12 15 6" />
          </svg>
          Cola de revisión
        </button>

        {/* Header card */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6 space-y-4">
          <div className="flex items-start justify-between gap-4">
            <div className="flex-1 min-w-0">
              <h2 className="text-lg font-bold text-slate-800 leading-tight">{data.title}</h2>
              {data.description && (
                <p className="text-sm text-slate-500 mt-1">{data.description}</p>
              )}
            </div>
            <span className="shrink-0 text-xs font-semibold px-2.5 py-1 rounded-full bg-amber-100 text-amber-700 capitalize">
              {data.status}
            </span>
          </div>

          {/* Metadata grid */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 pt-2 border-t border-slate-100">
            <div>
              <p className="text-xs text-slate-400 font-medium">Tipo</p>
              <p className="text-sm font-semibold text-slate-700 mt-0.5 capitalize">{data.type}</p>
            </div>
            <div>
              <p className="text-xs text-slate-400 font-medium">Categoría</p>
              <p className="text-sm font-semibold text-slate-700 mt-0.5">{data.category_name ?? '—'}</p>
            </div>
            <div>
              <p className="text-xs text-slate-400 font-medium">Autor</p>
              <p className="text-sm font-semibold text-slate-700 mt-0.5">{data.created_by_name ?? '—'}</p>
            </div>
            <div>
              <p className="text-xs text-slate-400 font-medium">Tamaño</p>
              <p className="text-sm font-semibold text-slate-700 mt-0.5">{formatBytes(data.file_size)}</p>
            </div>
            {data.duration_seconds !== null && (
              <div>
                <p className="text-xs text-slate-400 font-medium">Duración</p>
                <p className="text-sm font-semibold text-slate-700 mt-0.5">{formatDuration(data.duration_seconds)}</p>
              </div>
            )}
            <div>
              <p className="text-xs text-slate-400 font-medium">Archivo</p>
              <p className="text-xs font-medium text-slate-500 mt-0.5 truncate" title={data.file_path}>{data.file_path}</p>
            </div>
          </div>
        </div>

        {/* Action area */}
        {data.status === 'pending' && (
          <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6 space-y-4">
            <h3 className="text-sm font-semibold text-slate-700">Acción de revisión</h3>

            {mode === 'idle' && (
              <div className="flex flex-wrap gap-3">
                <button
                  onClick={approve}
                  disabled={busy}
                  className="flex items-center gap-2 bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 text-white text-sm font-semibold px-4 py-2.5 rounded-lg transition-colors"
                >
                  {busy ? (
                    <svg className="w-4 h-4 animate-spin" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M21 12a9 9 0 1 1-6.219-8.56" /></svg>
                  ) : (
                    <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><polyline points="20 6 9 17 4 12" /></svg>
                  )}
                  Aprobar
                </button>

                <button
                  onClick={initCurate}
                  disabled={busy}
                  className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white text-sm font-semibold px-4 py-2.5 rounded-lg transition-colors"
                >
                  <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" /><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" /></svg>
                  Curar y aprobar
                </button>

                <button
                  onClick={() => setMode('reject')}
                  disabled={busy}
                  className="flex items-center gap-2 bg-red-50 hover:bg-red-100 disabled:opacity-50 text-red-700 text-sm font-semibold px-4 py-2.5 rounded-lg border border-red-200 transition-colors"
                >
                  <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" /></svg>
                  Rechazar
                </button>
              </div>
            )}

            {/* Reject form */}
            {mode === 'reject' && (
              <div className="space-y-3">
                <label className="block text-xs font-semibold text-slate-600">Motivo de rechazo <span className="text-red-500">*</span></label>
                <textarea
                  value={rejectReason}
                  onChange={e => setRejectReason(e.target.value)}
                  rows={3}
                  className="w-full px-3 py-2.5 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-red-500 focus:border-transparent placeholder:text-slate-400 resize-none"
                  placeholder="Explica al docente por qué se rechaza el contenido..."
                />
                <div className="flex gap-2">
                  <button
                    onClick={submitReject}
                    disabled={busy || !rejectReason.trim()}
                    className="flex items-center gap-2 bg-red-600 hover:bg-red-700 disabled:opacity-50 text-white text-sm font-semibold px-4 py-2 rounded-lg transition-colors"
                  >
                    {busy && <svg className="w-4 h-4 animate-spin" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M21 12a9 9 0 1 1-6.219-8.56" /></svg>}
                    Confirmar rechazo
                  </button>
                  <button
                    onClick={() => { setMode('idle'); setRejectReason('') }}
                    disabled={busy}
                    className="text-sm text-slate-500 hover:text-slate-700 px-4 py-2 rounded-lg hover:bg-slate-100 transition-colors"
                  >
                    Cancelar
                  </button>
                </div>
              </div>
            )}

            {/* Curate form */}
            {mode === 'curate' && (
              <div className="space-y-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-600 mb-1.5">Título <span className="text-red-500">*</span></label>
                  <input
                    type="text"
                    value={curateTitle}
                    onChange={e => setCurateTitle(e.target.value)}
                    className="w-full px-3 py-2.5 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-600 mb-1.5">Descripción</label>
                  <textarea
                    value={curateDesc}
                    onChange={e => setCurateDesc(e.target.value)}
                    rows={3}
                    className="w-full px-3 py-2.5 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent resize-none"
                  />
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={submitCurate}
                    disabled={busy || !curateTitle.trim()}
                    className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white text-sm font-semibold px-4 py-2 rounded-lg transition-colors"
                  >
                    {busy && <svg className="w-4 h-4 animate-spin" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M21 12a9 9 0 1 1-6.219-8.56" /></svg>}
                    Guardar y aprobar
                  </button>
                  <button
                    onClick={() => setMode('idle')}
                    disabled={busy}
                    className="text-sm text-slate-500 hover:text-slate-700 px-4 py-2 rounded-lg hover:bg-slate-100 transition-colors"
                  >
                    Cancelar
                  </button>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Already reviewed state */}
        {data.status !== 'pending' && (
          <div className="bg-slate-50 rounded-xl border border-slate-200 p-5 text-center">
            <p className="text-sm text-slate-500">
              Este contenido ya fue revisado (<span className="font-semibold capitalize">{data.status}</span>).
            </p>
          </div>
        )}

      </div>
    </>
  )
}
