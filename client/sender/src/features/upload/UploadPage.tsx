import { useState, useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import { useForm, Controller } from 'react-hook-form'
import { z } from 'zod'
import { zodResolver } from '@hookform/resolvers/zod'
import { useNavigate } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import {
  UploadCloud, FileVideo, FileText, Music, Image,
  X, CheckCircle2, AlertCircle, Loader2,
  ChevronDown, File,
} from 'lucide-react'
import { useCategories } from '../../hooks/queries'
import { formatBytes } from '../../utils/format'

// ── Schema ────────────────────────────────────────────────────
const schema = z.object({
  title:       z.string().min(3, 'El título debe tener al menos 3 caracteres'),
  description: z.string().max(500, 'Máximo 500 caracteres').optional(),
  category_id: z.string().min(1, 'Selecciona una categoría'),
})
type FormValues = z.infer<typeof schema>

// ── Accepted MIME types ───────────────────────────────────────
// Cada entrada lista las extensiones explícitas para que el OS no las oculte.
const ACCEPTED: Record<string, string[]> = {
  // Video
  'video/mp4':        ['.mp4'],
  'video/webm':       ['.webm'],
  'video/ogg':        ['.ogv'],
  'video/quicktime':  ['.mov'],
  'video/x-msvideo':  ['.avi'],
  'video/x-matroska': ['.mkv'],
  // Audio
  'audio/mpeg':   ['.mp3'],
  'audio/wav':    ['.wav'],
  'audio/ogg':    ['.oga', '.ogg'],
  'audio/mp4':    ['.m4a'],
  'audio/flac':   ['.flac'],
  'audio/aac':    ['.aac'],
  'audio/x-flac': ['.flac'],
  // Images
  'image/jpeg': ['.jpg', '.jpeg'],
  'image/png':  ['.png'],
  'image/gif':  ['.gif'],
  'image/webp': ['.webp'],
  'image/svg+xml': ['.svg'],
  'image/bmp':  ['.bmp'],
  // Documents
  'application/pdf':  ['.pdf'],
  'application/msword': ['.doc'],
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
  'application/vnd.ms-excel': ['.xls'],
  'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
  'application/vnd.ms-powerpoint': ['.ppt'],
  'application/vnd.openxmlformats-officedocument.presentationml.presentation': ['.pptx'],
  // Code / text — se incluyen extensiones para que el OS las muestre en el explorador
  'text/plain':       ['.txt', '.log'],
  'text/html':        ['.html', '.htm'],
  'text/css':         ['.css'],
  'text/javascript':  ['.js', '.mjs', '.cjs'],
  'application/json': ['.json'],
  'application/xml':  ['.xml'],
  'text/xml':         ['.xml'],
  'text/markdown':    ['.md', '.markdown'],
  'text/x-python':          ['.py', '.pyw'],
  'text/x-script.python':   ['.py'],
  'text/x-java-source':     ['.java'],
  'text/x-java':            ['.java'],
  'text/x-c':       ['.c', '.h'],
  'text/x-c++':     ['.cpp', '.cc', '.cxx', '.hpp'],
  'text/x-csrc':    ['.c'],
  'text/x-c++src':  ['.cpp', '.cc'],
  'text/x-csharp':  ['.cs'],
  'text/x-go':      ['.go'],
  'text/x-ruby':    ['.rb'],
  'text/x-script.ruby': ['.rb'],
  'text/x-php':     ['.php'],
  'application/x-php': ['.php'],
  'text/x-rust':    ['.rs'],
  'text/x-sh':      ['.sh', '.bash'],
  'application/x-sh': ['.sh'],
  'application/javascript':   ['.js', '.mjs'],
  'application/x-javascript': ['.js'],
  'application/typescript':   ['.ts', '.tsx'],
  'text/typescript':          ['.ts', '.tsx'],
  // Configuración / datos
  'application/x-yaml': ['.yaml', '.yml'],
  'text/yaml':          ['.yaml', '.yml'],
  'application/toml':   ['.toml'],
  'text/x-sql':         ['.sql'],
  // Archives
  'application/zip':             ['.zip'],
  'application/x-zip-compressed':['.zip'],
  'application/x-rar-compressed':['.rar'],
  'application/x-7z-compressed': ['.7z'],
  'application/x-tar':           ['.tar'],
  'application/gzip':            ['.gz', '.tgz'],
  // Extensiones comunes que el OS reporta como octet-stream
  'application/octet-stream': [
    '.py', '.pyw', '.rs', '.go', '.java', '.cs', '.ts', '.tsx',
    '.rb', '.php', '.sh', '.bash', '.sql', '.toml', '.yaml', '.yml',
    '.ini', '.cfg', '.conf', '.env',
  ],
}

function fileIcon(mime: string) {
  if (mime.startsWith('video/'))       return <FileVideo size={20} className="text-blue-600" />
  if (mime.startsWith('audio/'))       return <Music size={20} className="text-blue-600" />
  if (mime.startsWith('image/'))       return <Image size={20} className="text-blue-600" />
  if (mime === 'application/pdf')      return <FileText size={20} className="text-red-500" />
  if (mime.includes('spreadsheet') || mime.includes('excel'))
                                       return <FileText size={20} className="text-green-600" />
  if (mime.includes('presentationml') || mime.includes('powerpoint'))
                                       return <FileText size={20} className="text-orange-500" />
  if (mime.includes('wordprocessing') || mime === 'application/msword')
                                       return <FileText size={20} className="text-blue-500" />
  if (mime.startsWith('text/') || mime === 'application/json' || mime === 'application/xml')
                                       return <File size={20} className="text-slate-500" />
  return <FileText size={20} className="text-blue-600" />
}

// ── XHR upload with progress ──────────────────────────────────
function uploadWithProgress(
  file: File,
  fields: FormValues,
  onProgress: (pct: number) => void,
): Promise<void> {
  return new Promise((resolve, reject) => {
    const fd = new FormData()
    fd.append('file', file)
    fd.append('title',       fields.title)
    fd.append('description', fields.description ?? '')
    fd.append('category_id', fields.category_id)

    const xhr = new XMLHttpRequest()
    xhr.open('POST', '/api/upload')
    xhr.withCredentials = true

    const token = localStorage.getItem('token')
    if (token) xhr.setRequestHeader('Authorization', `Bearer ${token}`)

    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable) onProgress(Math.round((e.loaded / e.total) * 100))
    }
    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) resolve()
      else {
        try {
          const body = JSON.parse(xhr.responseText)
          reject(new Error(body.message ?? `Error ${xhr.status}`))
        } catch {
          reject(new Error(`Error ${xhr.status}`))
        }
      }
    }
    xhr.onerror = () => reject(new Error('Error de red'))
    xhr.send(fd)
  })
}

// ── Component ─────────────────────────────────────────────────
export default function UploadPage() {
  const navigate    = useNavigate()
  const qc          = useQueryClient()
  const { data: categories = [], isLoading: loadingCats } = useCategories()

  const [file,     setFile]     = useState<File | null>(null)
  const [progress, setProgress] = useState(0)
  const [status,   setStatus]   = useState<'idle' | 'uploading' | 'success' | 'error'>('idle')
  const [errMsg,   setErrMsg]   = useState('')

  const {
    register, handleSubmit, control, reset,
    formState: { errors, isValid },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    mode: 'onChange',
  })

  // Build hierarchical structure for dropdown
  const rootCats = categories.filter(c => c.parent_id === null)
  const subCats  = (parentId: string) => categories.filter(c => c.parent_id === parentId)

  const onDrop = useCallback((accepted: File[]) => {
    if (accepted[0]) { setFile(accepted[0]); setErrMsg('') }
  }, [])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: ACCEPTED,
    maxFiles: 1,
    maxSize: 500 * 1024 * 1024, // 500 MB
    onDropRejected: (rej) => {
      const err = rej[0]?.errors[0]
      if (err?.code === 'file-too-large') setErrMsg('El archivo supera el límite de 500 MB.')
      else setErrMsg('Tipo de archivo no permitido. Consulta los formatos aceptados.')
    },
  })

  const clearFile = (e: React.MouseEvent) => {
    e.stopPropagation()
    setFile(null)
    setStatus('idle')
    setErrMsg('')
  }

  const onSubmit = async (values: FormValues) => {
    if (!file) { setErrMsg('Selecciona un archivo'); return }
    setStatus('uploading')
    setProgress(0)
    setErrMsg('')
    try {
      await uploadWithProgress(file, values, setProgress)
      setStatus('success')
      qc.invalidateQueries({ queryKey: ['submissions', 'mine'] })
      setTimeout(() => navigate('/submissions'), 1500)
    } catch (err) {
      setStatus('error')
      setErrMsg(err instanceof Error ? err.message : 'Error al subir')
    }
  }

  // ── Success screen ──────────────────────────────────────────
  if (status === 'success') {
    return (
      <div className="mt-16 text-center">
        <div className="w-14 h-14 rounded-full bg-blue-50 border border-blue-200 flex items-center justify-center mx-auto mb-4">
          <CheckCircle2 size={28} className="text-blue-600" />
        </div>
        <p className="text-slate-800 font-semibold text-lg">¡Enviado correctamente!</p>
        <p className="text-slate-500 text-sm mt-1">
          Tu contenido fue enviado y está pendiente de revisión. Te notificaremos cuando sea aprobado.
        </p>
        <div className="mt-6 animate-pulse text-xs text-slate-400">Redirigiendo a tus envíos...</div>
      </div>
    )
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">

      {/* ── Dropzone ─────────────────────────────────────── */}
      <div
        {...getRootProps()}
        className={[
          'card cursor-pointer transition-all',
          isDragActive
            ? 'border-2 border-blue-600 bg-blue-50/50'
            : file
            ? 'border-2 border-blue-200 bg-blue-50/20'
            : 'border-2 border-dashed border-slate-200 hover:border-blue-400 hover:bg-slate-50',
        ].join(' ')}
      >
        <input {...getInputProps()} />

        {file ? (
          <div className="flex items-center gap-4 px-5 py-4">
            <div className="w-10 h-10 rounded-lg bg-blue-100 flex items-center justify-center shrink-0">
              {fileIcon(file.type)}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-semibold text-slate-800 truncate">{file.name}</p>
              <p className="text-xs text-slate-500 mt-0.5">{formatBytes(file.size)}</p>
            </div>
            <button
              type="button"
              onClick={clearFile}
              className="text-slate-400 hover:text-slate-600 p-1.5 rounded-lg hover:bg-slate-100 transition-colors shrink-0"
              title="Quitar archivo"
            >
              <X size={16} />
            </button>
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center py-12 px-6 text-center">
            <div className="w-12 h-12 rounded-full bg-slate-100 flex items-center justify-center mb-3">
              <UploadCloud size={22} className="text-slate-400" />
            </div>
            <p className="text-sm font-semibold text-slate-700">
              {isDragActive ? 'Suelta el archivo aquí' : 'Arrastra tu archivo aquí'}
            </p>
            <p className="text-xs text-slate-400 mt-1.5">
              o <span className="text-blue-700 font-medium cursor-pointer">selecciona desde tu equipo</span>
            </p>
            <p className="text-xs text-slate-400 mt-3 bg-slate-50 px-3 py-1.5 rounded-full">
              Video · Audio · Imagen · PDF · Word · Excel · PowerPoint · Código · ZIP &nbsp;·&nbsp; Máx. 500 MB
            </p>
          </div>
        )}
      </div>

      {/* ── Form fields ──────────────────────────────────── */}
      <div className="card p-6 space-y-5">
        <div className="border-b border-slate-100 pb-4">
          <p className="text-sm font-semibold text-slate-800">Información del contenido</p>
          <p className="text-xs text-slate-500 mt-0.5">Completa los datos para que el equipo pueda revisarlo correctamente.</p>
        </div>

        {/* Title */}
        <div>
          <label className="label">Título <span className="text-red-500">*</span></label>
          <input
            {...register('title')}
            type="text"
            placeholder="Ej. Introducción a la fotosíntesis"
            className={`input ${errors.title ? 'border-red-400 focus:border-red-500 focus:ring-red-500' : ''}`}
            autoComplete="off"
          />
          {errors.title && (
            <p className="flex items-center gap-1.5 text-xs text-red-600 mt-1.5">
              <AlertCircle size={12} /> {errors.title.message}
            </p>
          )}
        </div>

        {/* Description */}
        <div>
          <label className="label">Descripción <span className="text-slate-400 font-normal">(opcional)</span></label>
          <textarea
            {...register('description')}
            rows={3}
            placeholder="Describe brevemente el contenido: tema, nivel educativo, objetivos..."
            className={`input resize-none ${errors.description ? 'border-red-400' : ''}`}
          />
          {errors.description && (
            <p className="flex items-center gap-1.5 text-xs text-red-600 mt-1.5">
              <AlertCircle size={12} /> {errors.description.message}
            </p>
          )}
        </div>

        {/* Category — hierarchical optgroup */}
        <div>
          <label className="label">Categoría <span className="text-red-500">*</span></label>
          <div className="relative">
            <Controller
              name="category_id"
              control={control}
              defaultValue=""
              render={({ field }) => (
                <select
                  {...field}
                  disabled={loadingCats}
                  className={`input appearance-none pr-9 ${errors.category_id ? 'border-red-400' : ''} ${loadingCats ? 'opacity-50' : ''}`}
                >
                  <option value="">
                    {loadingCats ? 'Cargando categorías...' : 'Seleccionar categoría'}
                  </option>
                  {rootCats.map(root => {
                    const children = subCats(root.id)
                    if (children.length === 0) {
                      // Root category without children — selectable
                      return (
                        <option key={root.id} value={root.id}>{root.name}</option>
                      )
                    }
                    return (
                      <optgroup key={root.id} label={root.name}>
                        {children.map(child => (
                          <option key={child.id} value={child.id}>{child.name}</option>
                        ))}
                      </optgroup>
                    )
                  })}
                </select>
              )}
            />
            <ChevronDown size={15} className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-slate-400" />
          </div>
          {errors.category_id && (
            <p className="flex items-center gap-1.5 text-xs text-red-600 mt-1.5">
              <AlertCircle size={12} /> {errors.category_id.message}
            </p>
          )}
        </div>
      </div>

      {/* ── Progress bar ─────────────────────────────────── */}
      {status === 'uploading' && (
        <div className="card p-4">
          <div className="flex items-center justify-between mb-2">
            <p className="text-xs font-semibold text-slate-700">Subiendo archivo...</p>
            <p className="text-xs text-slate-500">{progress}%</p>
          </div>
          <div className="w-full h-1.5 bg-slate-100 rounded-full overflow-hidden">
            <div
              className="h-full bg-blue-700 rounded-full transition-all duration-200"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>
      )}

      {/* ── Error message ─────────────────────────────────── */}
      {(errMsg || status === 'error') && (
        <div className="flex items-start gap-3 bg-red-50 border border-red-200 rounded-lg px-4 py-3">
          <AlertCircle size={16} className="text-red-500 shrink-0 mt-0.5" />
          <p className="text-sm text-red-700">{errMsg || 'Ocurrió un error al subir el archivo'}</p>
        </div>
      )}

      {/* ── Actions ──────────────────────────────────────── */}
      <div className="flex items-center justify-between gap-3 pt-1">
        <button
          type="button"
          onClick={() => { reset(); setFile(null); setStatus('idle'); setErrMsg('') }}
          className="btn-ghost"
        >
          Limpiar formulario
        </button>

        <button
          type="submit"
          disabled={!file || !isValid || status === 'uploading'}
          className="btn-primary"
        >
          {status === 'uploading' ? (
            <><Loader2 size={15} className="animate-spin" /> Subiendo...</>
          ) : (
            <><UploadCloud size={15} /> Enviar para revisión</>
          )}
        </button>
      </div>

    </form>
  )
}
