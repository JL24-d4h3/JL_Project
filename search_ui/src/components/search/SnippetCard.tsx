import type { SnippetCard as SnippetCardType } from '../../hooks/useSSESearch'
import type { ReactElement } from 'react'

const TYPE_CONFIG: Record<string, { label: string; icon: ReactElement }> = {
  video: {
    label: 'Video',
    icon: <svg className="h-5 w-5 text-slate-400" viewBox="0 0 24 24" fill="currentColor"><path d="M8 5v14l11-7L8 5z"/></svg>,
  },
  pdf: {
    label: 'PDF',
    icon: <svg className="h-5 w-5 text-slate-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}><path strokeLinecap="round" strokeLinejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/></svg>,
  },
  audio: {
    label: 'Audio',
    icon: <svg className="h-5 w-5 text-slate-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}><path strokeLinecap="round" d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2z"/></svg>,
  },
  document: {
    label: 'Doc',
    icon: <svg className="h-5 w-5 text-slate-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}><path strokeLinecap="round" d="M4 6h16M4 10h16M4 14h10"/></svg>,
  },
}

function extractTs(url: string): number | null {
  try { const t = new URL(url,'http://x').searchParams.get('t'); return t?Math.floor(+t):null } catch{return null}
}
function fmtTime(s:number){return`${Math.floor(s/60)}:${(s%60).toString().padStart(2,'0')}`}
function fmtDate(iso:string){
  try{return new Date(iso).toLocaleDateString('es-PE',{day:'numeric',month:'short',year:'numeric'})}catch{return''}
}

export default function SnippetCard({ card }: { card: SnippetCardType }) {
  const cfg = TYPE_CONFIG[card.content_type] ?? TYPE_CONFIG['document']
  const ts  = card.content_type === 'video' ? extractTs(card.viewer_url) : null

  return (
    <a
      href={card.viewer_url} target="_blank" rel="noopener noreferrer"
      className="group flex items-start gap-3 rounded-lg border border-slate-200 bg-white px-4 py-3
        hover:border-slate-300 hover:shadow-sm transition-all duration-100"
    >
      {/* Icono / thumb */}
      <div className="relative mt-0.5 flex-shrink-0">
        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-slate-50 border border-slate-100">
          {card.thumbnail_url ? (
            <img src={card.thumbnail_url} alt="" className="h-full w-full rounded-lg object-cover"
              onError={e => { (e.currentTarget as HTMLImageElement).style.display='none' }} />
          ) : cfg.icon}
        </div>
        {ts !== null && (
          <span className="absolute -bottom-2 left-0 right-0 flex justify-center">
            <span className="rounded bg-slate-800 px-1.5 py-px text-[9px] font-mono text-white leading-none whitespace-nowrap">
              {fmtTime(ts)}
            </span>
          </span>
        )}
      </div>

      {/* Text */}
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-1.5 mb-0.5">
          <span className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">
            {cfg.label}
          </span>
          {card.requires_auth && (
            <span className="text-[10px] text-amber-600">&#9679; restringido</span>
          )}
        </div>
        <p className="text-sm font-medium text-slate-800 leading-snug line-clamp-2
          group-hover:text-indigo-700 transition-colors">
          {card.title}
        </p>
        <p className="mt-0.5 text-xs text-slate-400 line-clamp-2 leading-relaxed">
          {card.snippet}
        </p>
        {card.upload_date && (
          <p className="mt-1 text-[10px] text-slate-300">{fmtDate(card.upload_date)}</p>
        )}
      </div>
    </a>
  )
}
