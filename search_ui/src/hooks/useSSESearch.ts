import { useState, useCallback, useRef } from 'react'

export interface SnippetCard {
  content_id:      string
  content_type:    'video' | 'pdf' | 'audio' | 'document'
  title:           string
  snippet:         string
  thumbnail_url:   string
  /** URL externa — puede apuntar a client/, biblioteca, proyectos, etc. */
  viewer_url:      string
  upload_date:     string
  requires_auth:   boolean
  relevance_score: number
  _related?:       boolean   // true = contenido relacionado, no coincidencia directa
}

interface SearchState {
  cards:           SnippetCard[]
  overview:        string
  suggestions:     string[]
  spellSuggestion: string | null
  level:           string   // 'L1' | 'L2' | 'L3' | 'L4' | ''
  isStreaming:     boolean
  error:           string | null
}

export function useSSESearch() {
  const [state, setState] = useState<SearchState>({
    cards: [], overview: '', suggestions: [], spellSuggestion: null, level: '', isStreaming: false, error: null,
  })
  const abortRef = useRef<AbortController | null>(null)

  const search = useCallback(async (query: string) => {
    abortRef.current?.abort()
    abortRef.current = new AbortController()

    setState({ cards: [], overview: '', suggestions: [], spellSuggestion: null, level: '', isStreaming: true, error: null })

    const token = localStorage.getItem('cdn_token') ?? ''

    try {
      const res = await fetch('/api/ai/search/stream', {
        method:  'POST',
        headers: {
          'Content-Type':  'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body:   JSON.stringify({ query }),
        signal: abortRef.current.signal,
      })

      if (!res.ok) throw new Error(`HTTP ${res.status}`)

      const reader  = res.body!.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() ?? ''

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          const msg = JSON.parse(line.slice(6))

          if (msg.type === 'cdn_results') {
            setState(s => ({ ...s, cards: msg.data as SnippetCard[] }))
          } else if (msg.type === 'token') {
            setState(s => ({ ...s, overview: s.overview + (msg.text as string) }))
          } else if (msg.type === 'done') {
            setState(s => ({
              ...s,
              isStreaming:     false,
              level:           (msg.level as string) ?? '',
              suggestions:     (msg.suggestions as string[]) ?? [],
              spellSuggestion: (msg.spell_suggestion as string | null) ?? null,
            }))
          }
        }
      }
    } catch (err: unknown) {
      if (err instanceof Error && err.name !== 'AbortError') {
        setState(s => ({ ...s, isStreaming: false, error: err.message }))
      }
    }
  }, [])

  const cancel = useCallback(() => {
    abortRef.current?.abort()
    setState(s => ({ ...s, isStreaming: false }))
  }, [])

  return { ...state, search, cancel }
}
