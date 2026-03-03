import { useState } from 'react'
import SearchBar     from '../components/search/SearchBar'
import AIOverview    from '../components/search/AIOverview'
import SearchResults from '../components/search/SearchResults'
import { useSSESearch } from '../hooks/useSSESearch'

export default function SearchPage() {
  const { cards, overview, suggestions, spellSuggestion, level, isStreaming, error, search, cancel } = useSSESearch()
  const [lastQuery, setLastQuery] = useState('')

  const searched   = !!lastQuery
  const emptyState = searched && !isStreaming && cards.length === 0 && !overview && !error

  function handleSearch(query: string) {
    setLastQuery(query)
    search(query)
  }

  return (
    <div className="min-h-screen bg-[#f8f9fb] font-sans">

      {/* ========== HEADER ========== */}
      {searched && (
        <header className="sticky top-0 z-20 border-b border-slate-200 bg-white/95 backdrop-blur-sm">
          <div className="mx-auto flex max-w-6xl items-center gap-4 px-6 py-3">
            <a
              href="/"
              onClick={e => { e.preventDefault(); setLastQuery('') }}
              className="flex-shrink-0 flex items-baseline gap-1.5 group select-none"
            >
              <span className="text-sm font-bold text-slate-800 tracking-tight group-hover:text-indigo-700 transition-colors">
                GTR-PUCP
              </span>
              <span className="rounded bg-indigo-600 px-1.5 py-px text-[10px] font-bold text-white tracking-wider">
                IA
              </span>
            </a>

            <div className="flex-1 max-w-xl">
              <SearchBar onSearch={handleSearch} isStreaming={isStreaming} compact />
            </div>

            {isStreaming && (
              <button
                onClick={cancel}
                className="ml-auto flex-shrink-0 flex items-center gap-1.5 rounded-lg px-3 py-1.5
                  text-xs text-slate-500 hover:bg-slate-100 transition"
              >
                <svg className="h-3.5 w-3.5" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0
                    111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10
                    11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0
                    010-1.414z" clipRule="evenodd" />
                </svg>
                Detener
              </button>
            )}
          </div>
        </header>
      )}

      {/* ========== HERO (estado inicial) ========== */}
      {!searched && (
        <div className="flex min-h-screen flex-col items-center justify-center gap-10 px-4 pb-16">
          <div className="text-center">
            <div className="inline-flex items-baseline gap-2.5 mb-4">
              <span className="text-5xl font-extrabold tracking-tight text-slate-900">GTR-PUCP</span>
              <span className="rounded bg-indigo-600 px-2 py-0.5 text-sm font-bold text-white tracking-widest">IA</span>
            </div>
            <h1 className="text-xl font-medium text-slate-500">
              Busca en el CDN educativo o haz cualquier pregunta
            </h1>
          </div>

          <div className="w-full max-w-2xl">
            <SearchBar onSearch={handleSearch} isStreaming={isStreaming} />
          </div>

          <div className="flex flex-wrap justify-center gap-2 mt-2">
            {[
              'Transformada de Fourier',
              'Redes TCP/IP',
              'Cálculo diferencial',
              'Deep Learning',
              'Instalar Kali Linux',
            ].map(s => (
              <button
                key={s}
                onClick={() => handleSearch(s)}
                className="rounded-full border border-slate-200 bg-white px-4 py-1.5 text-sm
                  text-slate-600 shadow-sm hover:border-indigo-300 hover:text-indigo-700 transition"
              >
                {s}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* ========== RESULTADOS ========== */}
      {searched && (
        <main className="mx-auto max-w-6xl px-6 py-8">

          {/* Query + status */}
          <div className="mb-6 flex items-center gap-3">
            <p className="text-xs text-slate-400">Resultados para</p>
            <p className="text-sm font-semibold text-slate-700">"{lastQuery}"</p>
            {isStreaming && (
              <span className="ml-auto flex items-center gap-1.5 text-[11px] text-indigo-500">
                <svg className="h-3 w-3 animate-spin" viewBox="0 0 24 24" fill="none"
                  stroke="currentColor" strokeWidth={3}>
                  <circle cx="12" cy="12" r="10" strokeOpacity={0.2}/>
                  <path d="M12 2a10 10 0 0 1 10 10"/>
                </svg>
                analizando…
              </span>
            )}
          </div>

          {/* ¿Quisiste decir...? */}
          {spellSuggestion && !isStreaming && (
            <div className="mb-5 flex items-center gap-2 text-sm text-slate-500">
              <svg className="h-4 w-4 flex-shrink-0 text-amber-400" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M8.485 2.495c.673-1.167 2.357-1.167 3.03 0l6.28 10.875c.673
                  1.167-.17 2.625-1.516 2.625H3.72c-1.347 0-2.189-1.458-1.515-2.625L8.485
                  2.495zM10 5a.75.75 0 01.75.75v3.5a.75.75 0 01-1.5 0v-3.5A.75.75 0 0110
                  5zm0 9a1 1 0 100-2 1 1 0 000 2z" clipRule="evenodd" />
              </svg>
              <span>¿Quisiste decir:</span>
              <button
                onClick={() => handleSearch(spellSuggestion)}
                className="font-semibold text-indigo-600 hover:underline"
              >
                {spellSuggestion}
              </button>
              <span className="text-slate-300">?</span>
            </div>
          )}

          {/* Error de conexión */}
          {error && (
            <div className="mb-6 rounded-xl border border-red-200 bg-red-50 px-5 py-4">
              <p className="text-sm font-semibold text-red-700">No se pudo conectar con el AI Engine</p>
              <p className="mt-0.5 text-xs text-red-500">{error}</p>
              <p className="mt-2 text-xs text-red-400">
                Inicia el servidor:&nbsp;
                <code className="font-mono bg-red-100 rounded px-1 py-0.5">
                  uvicorn ai_engine.mock_main:app --port 8000
                </code>
              </p>
            </div>
          )}

          {/* Layout de dos columnas en pantallas grandes */}
          <div className="flex flex-col gap-8 lg:grid lg:grid-cols-5 lg:gap-10">

            {/* Columna izquierda — respuesta IA */}
            <div className="lg:col-span-3 flex flex-col gap-5">
              {!error && (
                <AIOverview text={overview} isStreaming={isStreaming} hasError={!!error} level={level} />
              )}

              {/* Estado vacío */}
              {emptyState && (
                <div className="flex flex-col items-center gap-3 rounded-xl border border-dashed
                  border-slate-200 py-16 text-center">
                  <svg className="h-10 w-10 text-slate-300" fill="none" viewBox="0 0 24 24"
                    stroke="currentColor" strokeWidth={1}>
                    <circle cx="11" cy="11" r="8"/>
                    <path strokeLinecap="round" d="M21 21l-4.35-4.35"/>
                  </svg>
                  <p className="text-sm font-medium text-slate-400">
                    Sin resultados para "{lastQuery}"
                  </p>
                  <p className="text-xs text-slate-300">
                    Intenta con otras palabras o una pregunta más específica
                  </p>
                </div>
              )}

              {/* Sugerencias */}
              {suggestions.length > 0 && !isStreaming && (
                <div className="pt-1">
                  <p className="mb-2.5 text-[10px] font-bold uppercase tracking-widest text-slate-400">
                    Búsquedas relacionadas
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {suggestions.map(s => (
                      <button
                        key={s}
                        onClick={() => handleSearch(s)}
                        className="rounded-full border border-slate-200 bg-white px-3.5 py-1.5
                          text-xs text-slate-600 shadow-sm hover:border-indigo-300
                          hover:text-indigo-700 transition"
                      >
                        {s}
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Columna derecha — fuentes del CDN */}
            <div className="lg:col-span-2">
              {cards.length > 0 || isStreaming ? (
                <SearchResults cards={cards} isStreaming={isStreaming} />
              ) : (overview && !isStreaming) ? (
                <div className="rounded-xl border border-slate-200 bg-slate-50 px-6 py-8 text-center">
                  <svg className="mx-auto h-9 w-9 text-slate-300 mb-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M5 19a2 2 0 01-2-2V7a2 2 0 012-2h4l2 2h4a2 2 0 012 2v1M5 19h14a2 2 0 002-2v-5a2 2 0 00-2-2H9a2 2 0 00-2 2v5a2 2 0 01-2 2z" />
                  </svg>
                  <p className="text-sm font-semibold text-slate-500">Sin recursos locales</p>
                  <p className="mt-1.5 text-xs text-slate-400 leading-relaxed">
                    No hay archivos sobre este tema<br />en el repositorio CDN GTR-PUCP
                  </p>
                  <div className="mt-4 border-t border-slate-200 pt-4">
                    <p className="text-[11px] text-slate-400 leading-relaxed">
                      Un administrador puede subir material<br />
                      <span className="font-medium text-slate-500">desde el panel de ingesta</span>
                    </p>
                  </div>
                </div>
              ) : null}
            </div>

          </div>
        </main>
      )}

      {!searched && (
        <footer className="fixed bottom-0 left-0 right-0 py-3 text-center text-[10px] text-slate-300">
          GTR-PUCP · CDN Educativa Offline · 2026
        </footer>
      )}
    </div>
  )
}
