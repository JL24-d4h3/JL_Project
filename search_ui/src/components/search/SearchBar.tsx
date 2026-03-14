import { useState, type FormEvent, type KeyboardEvent } from 'react'
import VoiceButton from './VoiceButton'

interface Props {
  onSearch:    (query: string) => void
  isStreaming: boolean
  compact?:    boolean
}

export default function SearchBar({ onSearch, isStreaming, compact = false }: Props) {
  const [query, setQuery] = useState('')

  function handleSubmit(e: FormEvent) {
    e.preventDefault()
    const q = query.trim()
    if (q) onSearch(q)
  }

  function handleKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      const q = query.trim()
      if (q) onSearch(q)
    }
  }

  function handleVoiceResult(transcribed: string) {
    setQuery(transcribed)
    onSearch(transcribed)
  }

  return (
    <form onSubmit={handleSubmit} className="w-full">
      <div className={[
        'flex items-center gap-2 rounded-xl border bg-white transition-all',
        'focus-within:border-indigo-400 focus-within:ring-2 focus-within:ring-indigo-100',
        compact
          ? 'border-slate-200 px-3 py-2 shadow-sm'
          : 'border-slate-300 px-4 py-3 shadow-sm',
      ].join(' ')}>
        <svg
          className={`flex-shrink-0 text-slate-400 ${compact ? 'h-3.5 w-3.5' : 'h-4 w-4'}`}
          viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round"
        >
          <circle cx="11" cy="11" r="8" /><path d="M21 21l-4.35-4.35" />
        </svg>

        <textarea
          rows={1}
          value={query}
          onChange={e => setQuery(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={compact ? 'Buscar…' : 'Escribe tu pregunta o busca un tema…'}
          className={[
            'flex-1 resize-none bg-transparent outline-none text-slate-800 placeholder-slate-400 leading-snug',
            compact ? 'text-sm' : 'text-sm',
          ].join(' ')}
          disabled={isStreaming}
        />

        <VoiceButton onResult={handleVoiceResult} disabled={isStreaming} />

        <button
          type="submit"
          disabled={isStreaming || !query.trim()}
          className={[
            'flex-shrink-0 rounded-lg font-medium text-white transition-all',
            'bg-indigo-600 hover:bg-indigo-700 disabled:opacity-40 disabled:cursor-not-allowed',
            compact ? 'px-3 py-1.5 text-xs' : 'px-4 py-2 text-sm',
          ].join(' ')}
        >
          {isStreaming
            ? <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2.5}><circle cx="12" cy="12" r="10" strokeOpacity={0.2}/><path d="M12 2a10 10 0 0 1 10 10"/></svg>
            : 'Buscar'
          }
        </button>
      </div>
    </form>
  )
}
