import { useState } from 'react'
import { Search, BookOpen, Video, FileText, Code } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardDescription, CardTitle } from '@/components/ui/card'
import AIOverview    from '../components/search/AIOverview'
import SearchResults from '../components/search/SearchResults'
import { useSSESearch } from '../hooks/useSSESearch'

const categories = [
  { icon: BookOpen, title: 'Plataforma Educativa', description: 'Cursos, materiales y recursos', color: 'bg-blue-500' },
  { icon: FileText, title: 'Biblioteca Digital', description: 'PDFs, documentos académicos', color: 'bg-green-500' },
  { icon: Code, title: 'Proyectos Académicos', description: 'Tesis, investigaciones', color: 'bg-purple-500' },
  { icon: Video, title: 'Noticias', description: 'Actualizaciones del GTR', color: 'bg-orange-500' },
]

export default function SearchPage() {
  const { cards, overview, suggestions, spellSuggestion, level, isStreaming, error, search, cancel } = useSSESearch()
  const [query, setQuery] = useState('')
  const [lastQuery, setLastQuery] = useState('')

  const searched   = !!lastQuery
  const emptyState = searched && !isStreaming && cards.length === 0 && !overview && !error

  function handleSearch(e?: React.FormEvent) {
    e?.preventDefault()
    const q = query.trim()
    if (q) {
      setLastQuery(q)
      search(q)
    }
  }

  function quickSearch(term: string) {
    setQuery(term)
    setLastQuery(term)
    search(term)
  }

  function goHome() {
    setLastQuery('')
    setQuery('')
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-50 to-white">
      {/* Header */}
      <header className="border-b bg-white/80 backdrop-blur-sm sticky top-0 z-50">
        <div className="container mx-auto px-12 py-4 flex items-center justify-between">
          <a href="/" onClick={e => { if (searched) { e.preventDefault(); goHome() }}} className="flex items-center gap-2">
            <BookOpen className="h-8 w-8 text-primary" />
            <span className="font-bold text-xl">GTR-PUCP</span>
          </a>
          {!searched && (
            <nav className="hidden md:flex gap-6">
              <a href="/" className="text-muted-foreground hover:text-foreground">Inicio</a>
              <a href="/library" className="text-muted-foreground hover:text-foreground">Biblioteca</a>
              <a href="/projects" className="text-muted-foreground hover:text-foreground">Proyectos</a>
            </nav>
          )}
          {searched && (
            <form onSubmit={handleSearch} className="flex-1 max-w-2xl mx-4">
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
          )}
          {isStreaming && (
            <Button variant="ghost" size="sm" onClick={cancel}>
              Detener
            </Button>
          )}
        </div>
      </header>

      {/* Hero */}
      {!searched && (
        <>
          <section className="container mx-auto px-12 py-20 text-center">
            <h1 className="text-4xl md:text-5xl font-bold mb-6">
              Motor de Búsqueda con <span className="text-primary">IA</span>
            </h1>
            <p className="text-xl text-muted-foreground mb-8 max-w-2xl mx-auto">
              Accede a contenido educativo de calidad sin conexión a internet.
              Busca, explora y aprende con recursos de la GTR-PUCP.
            </p>

            {/* Search Bar */}
            <form onSubmit={handleSearch} className="max-w-2xl mx-auto mb-12">
              <div className="relative">
                <Search className="absolute left-4 top-1/2 -translate-y-1/2 h-5 w-5 text-muted-foreground" />
                <Input
                  type="text"
                  placeholder="Buscar contenido educativo..."
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  className="w-full h-14 pl-12 pr-4 text-lg rounded-full border-2 focus:border-primary"
                />
                <Button type="submit" size="lg" className="absolute right-2 top-1/2 -translate-y-1/2 rounded-full">
                  Buscar
                </Button>
              </div>
            </form>

            {/* Quick Searches */}
            <div className="flex flex-wrap justify-center gap-2 mb-6">
              {['SDN', 'Dijkstra', 'YOLO', 'TCP/IP', 'Machine Learning'].map((term) => (
                <Button
                  key={term}
                  variant="outline"
                  size="sm"
                  onClick={() => quickSearch(term)}
                >
                  {term}
                </Button>
              ))}
            </div>
          </section>

          {/* Categories */}
          <section className="container mx-auto px-12 pb-20">
            <h2 className="text-2xl font-bold mb-8 text-center">Explorar plataformas</h2>
            <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
              {categories.map((cat) => (
                <Card key={cat.title} className="hover:shadow-lg transition-shadow cursor-pointer group">
                  <CardContent className="p-6">
                    <div className={`w-12 h-12 rounded-lg ${cat.color} flex items-center justify-center mb-4 group-hover:scale-110 transition-transform`}>
                      <cat.icon className="h-6 w-6 text-white" />
                    </div>
                    <CardTitle className="mb-2">{cat.title}</CardTitle>
                    <CardDescription>{cat.description}</CardDescription>
                  </CardContent>
                </Card>
              ))}
            </div>
          </section>

          {/* Footer */}
          <footer className="border-t py-8">
            <div className="container mx-auto px-12 text-center text-muted-foreground">
              <p>GTR-PUCP — Plataforma offline para zonas sin conectividad</p>
            </div>
          </footer>
        </>
      )}

      {/* Results */}
      {searched && (
        <main className="container mx-auto px-12 py-6">
          {isStreaming && (
            <div className="flex items-center justify-center py-10">
              <svg className="h-8 w-8 animate-spin text-primary" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
                <circle cx="12" cy="12" r="10" strokeOpacity={0.2}/>
                <path d="M12 2a10 10 0 0 1 10 10"/>
              </svg>
              <span className="ml-2">Buscando...</span>
            </div>
          )}

          {error && (
            <div className="text-center py-10">
              <p className="text-destructive">Error al buscar. Intenta de nuevo.</p>
              <p className="text-sm text-muted-foreground mt-2">{error}</p>
            </div>
          )}

          {!isStreaming && !error && (
            <div className="space-y-6">
              {/* AI Overview */}
              {overview && (
                <Card className="bg-gradient-to-r from-blue-50 to-purple-50 border-blue-200">
                  <CardContent className="p-6">
                    <h3 className="font-semibold mb-2 flex items-center gap-2">
                      <span className="text-lg">✨</span> Respuesta del Modelo
                    </h3>
                    <AIOverview text={overview} isStreaming={isStreaming} hasError={!!error} level={level} />
                  </CardContent>
                </Card>
              )}

              {/* Results Count */}
              <div className="flex items-center justify-between">
                <p className="text-muted-foreground">
                  {cards.length} resultado(s) para "{lastQuery}"
                </p>
              </div>

              {/* ¿Quisiste decir...? */}
              {spellSuggestion && (
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <span>¿Quisiste decir:</span>
                  <Button variant="link" className="p-0 h-auto" onClick={() => quickSearch(spellSuggestion)}>
                    {spellSuggestion}
                  </Button>
                  <span>?</span>
                </div>
              )}

              {/* Result Cards */}
              {cards.length > 0 ? (
                <SearchResults cards={cards} isStreaming={isStreaming} />
              ) : emptyState ? (
                <div className="text-center py-20">
                  <p className="text-muted-foreground">No se encontraron resultados para esta búsqueda.</p>
                  <p className="text-sm text-muted-foreground mt-2">
                    Prueba con otros términos como: SDN, Dijkstra, YOLO, TCP
                  </p>
                </div>
              ) : null}

              {/* Related Searches */}
              {suggestions.length > 0 && (
                <div className="pt-6">
                  <h3 className="font-medium mb-3">Búsquedas relacionadas</h3>
                  <div className="flex flex-wrap gap-2">
                    {suggestions.map((term) => (
                      <Button
                        key={term}
                        variant="outline"
                        size="sm"
                        onClick={() => quickSearch(term)}
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
      )}
    </div>
  )
}
