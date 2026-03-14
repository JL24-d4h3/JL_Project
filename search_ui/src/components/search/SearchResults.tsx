import type { SnippetCard as SnippetCardType } from '../../hooks/useSSESearch'
import SnippetCard from './SnippetCard'

interface Props {
  cards:       SnippetCardType[]
  isStreaming: boolean
}

export default function SearchResults({ cards, isStreaming }: Props) {
  if (!isStreaming && cards.length === 0) return null

  const directCards  = cards.filter(c => !c._related)
  const relatedCards = cards.filter(c => c._related)

  return (
    <div>
      <div className="mb-2 flex items-center gap-2">
        <span className="text-[10px] font-bold uppercase tracking-widest text-slate-400">
          Fuentes del CDN
        </span>
        {cards.length > 0 && (
          <span className="rounded bg-slate-100 px-1.5 py-0.5 text-[10px] font-semibold text-slate-500">
            {cards.length}
          </span>
        )}
        {isStreaming && cards.length === 0 && (
          <svg className="h-3 w-3 animate-spin text-slate-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2.5}>
            <circle cx="12" cy="12" r="10" strokeOpacity={0.2}/>
            <path d="M12 2a10 10 0 0 1 10 10"/>
          </svg>
        )}
      </div>

      {isStreaming && cards.length === 0 ? (
        <div className="space-y-2">
          {[1,2,3].map(i => (
            <div key={i} className="flex items-start gap-3 rounded-lg border border-slate-100 bg-white px-4 py-3">
              <div className="h-10 w-10 flex-shrink-0 animate-pulse rounded-lg bg-slate-100"/>
              <div className="flex-1 space-y-1.5">
                <div className="h-2.5 w-16 animate-pulse rounded bg-slate-100"/>
                <div className="h-3.5 w-4/5 animate-pulse rounded bg-slate-100"/>
                <div className="h-3 w-full animate-pulse rounded bg-slate-100"/>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="space-y-2">
          {directCards.map(card => <SnippetCard key={card.content_id} card={card}/>)}

          {relatedCards.length > 0 && directCards.length > 0 && (
            <div className="flex items-center gap-2 pt-2 pb-1">
              <div className="flex-1 border-t border-dashed border-slate-200"/>
              <span className="text-[10px] font-medium text-slate-400 uppercase tracking-wide">
                Contenido relacionado
              </span>
              <div className="flex-1 border-t border-dashed border-slate-200"/>
            </div>
          )}
          {relatedCards.map(card => <SnippetCard key={card.content_id} card={card}/>)}
        </div>
      )}
    </div>
  )
}
