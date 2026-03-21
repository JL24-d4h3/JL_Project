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

  function handleKeyDown(e: KeyboardEvent<HTMLInputElement>) {
    if (e.key === 'Enter') {
      e.preventDefault()
      const q = query.trim()
      if (q) onSearch(q)
    }
  }

  function handleVoiceResult(transcribed: string) {
    setQuery(transcribed)
    onSearch(transcribed)
  }

  // Estilo compacto para el header cuando hay resultados
  if (compact) {
    return (
      <form onSubmit={handleSubmit} className="w-full">
        <div className="relative">
          <svg
            className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400"
            viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round"
          >
            <circle cx="11" cy="11" r="8" /><path d="M21 21l-4.35-4.35" />
          </svg>
          <input
            type="text"
            value={query}
            onChange={e => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Buscar..."
            className="w-full h-10 pl-10 pr-4 text-sm rounded-md border border-slate-200 bg-white shadow-sm
              focus:outline-none focus:ring-1 focus:ring-slate-900 focus:border-slate-900 transition"
            disabled={isStreaming}
          />
        </div>
      </form>
    )
  }

  // Estilo principal (hero) - igual que educational platform
  return (
    <form onSubmit={handleSubmit} className="w-full">
      <div className="relative">
        <svg
          className="absolute left-4 top-1/2 -translate-y-1/2 h-5 w-5 text-slate-400"
          viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round"
        >
          <circle cx="11" cy="11" r="8" /><path d="M21 21l-4.35-4.35" />
        </svg>
        <input
          type="text"
          value={query}
          onChange={e => setQuery(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Buscar contenido educativo..."
          className="w-full h-14 pl-12 pr-32 text-lg rounded-full border-2 border-slate-300 bg-white shadow-sm
            focus:outline-none focus:border-slate-900 transition"
          disabled={isStreaming}
        />
        <div className="absolute right-2 top-1/2 -translate-y-1/2 flex items-center gap-1">
          <VoiceButton onResult={handleVoiceResult} disabled={isStreaming} />
          <button
            type="submit"
            disabled={isStreaming || !query.trim()}
            className="h-10 px-6 rounded-full font-medium text-white bg-slate-900 hover:bg-slate-800
              disabled:opacity-50 disabled:cursor-not-allowed transition"
          >
            {isStreaming ? (
              <svg className="h-5 w-5 animate-spin" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2.5}>
                <circle cx="12" cy="12" r="10" strokeOpacity={0.2}/>
                <path d="M12 2a10 10 0 0 1 10 10"/>
              </svg>
            ) : (
              'Buscar'
            )}
          </button>
        </div>
      </div>
    </form>
  )
}
