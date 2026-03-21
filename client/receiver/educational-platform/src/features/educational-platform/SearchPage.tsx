import { useState, useEffect } from 'react'
import { useSearchParams, useNavigate, Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Search, ArrowLeft, FileText, Video, Code, Loader2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardDescription, CardTitle } from '@/components/ui/card'
import { searchContent, type SearchResult } from '@/lib/api'

function ContentIcon({ type }: { type: string }) {
  switch (type) {
    case 'video': return <Video className="h-5 w-5" />
    case 'code': return <Code className="h-5 w-5" />
    default: return <FileText className="h-5 w-5" />
  }
}

function ResultCard({ result }: { result: SearchResult }) {
  return (
    <Card className="hover:shadow-md transition-shadow">
      <CardContent className="p-4 flex gap-4">
        {result.thumbnail_url && (
          <img 
            src={result.thumbnail_url} 
            alt={result.title}
            className="w-24 h-24 object-cover rounded-lg flex-shrink-0"
            onError={(e) => { (e.target as HTMLImageElement).style.display = 'none' }}
          />
        )}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <ContentIcon type={result.content_type} />
            <span className="text-xs text-muted-foreground uppercase">{result.content_type}</span>
            <span className="text-xs text-green-600 ml-auto">
              {Math.round(result.relevance_score * 100)}% relevancia
            </span>
          </div>
          <CardTitle className="text-lg mb-1 truncate">{result.title}</CardTitle>
          <CardDescription className="line-clamp-2">{result.snippet}</CardDescription>
          <Button variant="link" size="sm" className="p-0 h-auto mt-2" asChild>
            <a href={result.viewer_url}>Ver contenido →</a>
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}

export function SearchPage() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const initialQuery = searchParams.get('q') || ''
  const [query, setQuery] = useState(initialQuery)

  const { data, isLoading, error } = useQuery({
    queryKey: ['search', initialQuery],
    queryFn: () => searchContent(initialQuery),
    enabled: !!initialQuery,
  })

  useEffect(() => {
    setQuery(initialQuery)
  }, [initialQuery])

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    if (query.trim()) {
      navigate(`/search?q=${encodeURIComponent(query)}`)
    }
  }

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Header */}
      <header className="border-b bg-white sticky top-0 z-50">
        <div className="container mx-auto px-4 py-3">
          <div className="flex items-center gap-4">
            <Button variant="ghost" size="icon" asChild>
              <Link to="/"><ArrowLeft className="h-5 w-5" /></Link>
            </Button>
            <form onSubmit={handleSearch} className="flex-1 max-w-2xl">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  type="text"
                  placeholder="Buscar..."
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  className="pl-10 pr-4"
                />
              </div>
            </form>
          </div>
        </div>
      </header>

      {/* Results */}
      <main className="container mx-auto px-4 py-6">
        {isLoading && (
          <div className="flex items-center justify-center py-20">
            <Loader2 className="h-8 w-8 animate-spin text-primary" />
            <span className="ml-2">Buscando...</span>
          </div>
        )}

        {error && (
          <div className="text-center py-20">
            <p className="text-destructive">Error al buscar. Intenta de nuevo.</p>
          </div>
        )}

        {data && (
          <div className="space-y-6">
            {/* AI Overview */}
            {data.ai_overview?.text && (
              <Card className="bg-gradient-to-r from-blue-50 to-purple-50 border-blue-200">
                <CardContent className="p-6">
                  <h3 className="font-semibold mb-2 flex items-center gap-2">
                    <span className="text-lg">✨</span> Respuesta del Modelo
                  </h3>
                  <p className="text-muted-foreground">{data.ai_overview.text}</p>
                </CardContent>
              </Card>
            )}

            {/* Results Count */}
            <div className="flex items-center justify-between">
              <p className="text-muted-foreground">
                {data.cdn_results.length} resultado(s) para "{initialQuery}"
              </p>
            </div>

            {/* Result Cards */}
            {data.cdn_results.length > 0 ? (
              <div className="space-y-4">
                {data.cdn_results.map((result) => (
                  <ResultCard key={result.content_id} result={result} />
                ))}
              </div>
            ) : (
              <div className="text-center py-20">
                <p className="text-muted-foreground">No se encontraron resultados para esta búsqueda.</p>
                <p className="text-sm text-muted-foreground mt-2">
                  Prueba con otros términos como: SDN, Dijkstra, YOLO, TCP
                </p>
              </div>
            )}

            {/* Related Searches */}
            {data.related_searches && data.related_searches.length > 0 && (
              <div className="pt-6">
                <h3 className="font-medium mb-3">Búsquedas relacionadas</h3>
                <div className="flex flex-wrap gap-2">
                  {data.related_searches.map((term) => (
                    <Button
                      key={term}
                      variant="outline"
                      size="sm"
                      onClick={() => navigate(`/search?q=${encodeURIComponent(term)}`)}
                    >
                      {term}
                    </Button>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  )
}
