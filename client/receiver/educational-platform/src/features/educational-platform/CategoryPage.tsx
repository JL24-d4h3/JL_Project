import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ArrowLeft, Loader2, Download, Play, FileText } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardTitle } from '@/components/ui/card'
import { getCategoryById, getContent } from '@/lib/api'
import type { Category, Content } from '@/lib/api'

export function CategoryPage() {
  const { slug } = useParams<{ slug: string }>()
  const navigate = useNavigate()

  const [category, setCategory] = useState<Category | null>(null)
  const [content, setContent] = useState<Content[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const loadCategoryContent = async () => {
      try {
        setLoading(true)

        // Obtener todas las categorías para encontrar la que coincida con el slug
        const { data: allContent } = await getContent(100)

        // TODO: Filtrar contenido por categoría slug
        // Por ahora mostramos todo el contenido
        setContent(allContent)

        // En una versión futura, buscaremos la categoría específica
        setCategory({
          id: '',
          name: slug?.split('-').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ') || '',
          slug: slug || '',
          description: 'Contenido educativo de esta categoría',
          parent_id: null,
          icon: '📚',
          color: '#3B82F6',
          display_order: 0,
          is_active: true,
          created_at: new Date().toISOString(),
        })
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Error loading content')
        console.error('Error:', err)
      } finally {
        setLoading(false)
      }
    }

    if (slug) {
      loadCategoryContent()
    }
  }, [slug])

  const getFileIcon = (type: string) => {
    switch (type) {
      case 'video':
        return <Play className="h-4 w-4" />
      case 'pdf':
      case 'document':
        return <FileText className="h-4 w-4" />
      default:
        return <Download className="h-4 w-4" />
    }
  }

  const getFileColor = (type: string) => {
    switch (type) {
      case 'video':
        return 'bg-red-100 text-red-700'
      case 'pdf':
        return 'bg-orange-100 text-orange-700'
      case 'document':
        return 'bg-blue-100 text-blue-700'
      case 'code':
        return 'bg-purple-100 text-purple-700'
      default:
        return 'bg-gray-100 text-gray-700'
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-50 to-white">
      {/* Header */}
      <header className="border-b bg-white/80 backdrop-blur-sm sticky top-0 z-50">
        <div className="container mx-auto px-4 py-4">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => navigate('/')}
            className="mb-2"
          >
            <ArrowLeft className="h-4 w-4 mr-2" />
            Volver
          </Button>
          <h1 className="text-2xl font-bold">{category?.name}</h1>
          <p className="text-muted-foreground">{category?.description}</p>
        </div>
      </header>

      {/* Content */}
      <section className="container mx-auto px-4 py-12">
        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded mb-6">
            Error: {error}
          </div>
        )}

        {loading ? (
          <div className="flex justify-center items-center py-12">
            <Loader2 className="h-8 w-8 animate-spin text-primary" />
          </div>
        ) : content.length === 0 ? (
          <div className="text-center text-muted-foreground py-12">
            No hay contenido disponible en esta categoría
          </div>
        ) : (
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
            {content.map((item) => (
              <Card key={item.id} className="hover:shadow-lg transition-shadow overflow-hidden">
                {item.thumbnail_path && (
                  <img
                    src={item.thumbnail_path}
                    alt={item.title}
                    className="w-full h-40 object-cover"
                  />
                )}
                <CardContent className="p-4">
                  <div className="flex items-start justify-between mb-2">
                    <CardTitle className="line-clamp-2 flex-1">{item.title}</CardTitle>
                    <span className={`text-xs font-medium px-2 py-1 rounded ml-2 ${getFileColor(item.type)}`}>
                      {item.type.toUpperCase()}
                    </span>
                  </div>
                  <CardDescription className="line-clamp-2 mb-4">
                    {item.description}
                  </CardDescription>

                  {/* Meta info */}
                  <div className="text-xs text-muted-foreground mb-4 space-y-1">
                    {item.file_size && (
                      <p>Tamaño: {(parseInt(item.file_size) / 1024 / 1024).toFixed(2)} MB</p>
                    )}
                    {item.duration_seconds && (
                      <p>Duración: {Math.floor(item.duration_seconds / 60)} min</p>
                    )}
                    <p>Vistas: {item.access_count}</p>
                  </div>

                  <Button className="w-full" size="sm">
                    {getFileIcon(item.type)}
                    <span className="ml-2">Abrir</span>
                  </Button>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </section>
    </div>
  )
}
