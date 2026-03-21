import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ArrowLeft, Loader2, Users, Eye } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { getCourseBySlug } from '@/lib/api'
import { Navbar } from '@/components/Navbar'
import type { Course } from '@/lib/api'

export function CoursePage() {
  const { slug } = useParams<{ slug: string }>()
  const navigate = useNavigate()
  const [course, setCourse] = useState<Course | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const loadCourse = async () => {
      if (!slug) return

      try {
        setLoading(true)
        const courseData = await getCourseBySlug(slug)
        setCourse(courseData)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Error loading course')
        console.error('Error:', err)
      } finally {
        setLoading(false)
      }
    }

    loadCourse()
  }, [slug])

  if (loading) {
    return (
      <div className="min-h-screen bg-white flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-slate-900" />
      </div>
    )
  }

  if (error || !course) {
    return (
      <div className="min-h-screen bg-white">
        <div className="container mx-auto px-6 py-10">
          <Button
            variant="ghost"
            onClick={() => navigate('/')}
            className="mb-6"
          >
            <ArrowLeft className="h-4 w-4 mr-2" />
            Volver
          </Button>
          <div className="text-center py-20">
            <p className="text-red-600">Error: {error || 'Curso no encontrado'}</p>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-50 to-white">
      <Navbar />

      {/* Back Button */}
      <div className="container mx-auto px-6 py-6">
        <Button
          variant="ghost"
          onClick={() => navigate('/')}
          className="text-slate-600 hover:text-slate-900"
        >
          <ArrowLeft className="h-4 w-4 mr-2" />
          Volver al Catálogo
        </Button>
      </div>

      {/* Course Hero */}
      <section className="bg-gradient-to-r from-slate-900 to-slate-800 text-white py-16">
        <div className="container mx-auto px-6">
          <div className="max-w-3xl">
            {/* Category Badge */}
            <div className="inline-block bg-slate-800 text-white text-xs font-semibold px-3 py-1 rounded-full mb-4">
              {course.category}
            </div>

            {/* Title */}
            <h1 className="text-5xl font-bold mb-4">{course.title}</h1>

            {/* Description */}
            <p className="text-xl text-slate-300 mb-8 max-w-2xl">
              {course.description}
            </p>

            {/* Stats */}
            <div className="flex flex-wrap gap-8">
              <div className="flex items-center gap-2">
                <Eye className="h-5 w-5" />
                <span>{course.view_count.toLocaleString()} vistas</span>
              </div>
              <div className="flex items-center gap-2">
                <Users className="h-5 w-5" />
                <span>{course.like_count.toLocaleString()} estudiantes</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-slate-900">★</span>
                <span>4.8 de 5</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Course Content */}
      <section className="container mx-auto px-6 py-16">
        <div className="grid md:grid-cols-3 gap-8">
          {/* Main Content */}
          <div className="md:col-span-2">
            {/* Course Content Sections */}
            <div className="space-y-6">
              <div>
                <h2 className="text-2xl font-bold text-slate-900 mb-4">Contenido del Curso</h2>
                <p className="text-slate-600 mb-6">
                  Este curso contiene módulos interactivos, videos, documentos y ejercicios prácticos que te ayudarán a dominar {course.title.toLowerCase()}.
                </p>
              </div>

              {/* Module Sections */}
              <div className="space-y-4">
                {[
                  { title: 'Módulo 1: Fundamentos', items: 5 },
                  { title: 'Módulo 2: Conceptos Intermedios', items: 7 },
                  { title: 'Módulo 3: Aplicaciones Avanzadas', items: 6 },
                ].map((module, idx) => (
                  <Card key={idx} className="border-slate-200 hover:shadow-md transition">
                    <CardContent className="p-6">
                      <h3 className="font-bold text-lg text-slate-900 mb-2">{module.title}</h3>
                      <p className="text-sm text-slate-600 mb-4">
                        {module.items} lecciones disponibles
                      </p>
                      <Button className="bg-slate-900 hover:bg-slate-800 text-white">
                        Empezar
                      </Button>
                    </CardContent>
                  </Card>
                ))}
              </div>
            </div>
          </div>

          {/* Sidebar */}
          <div>
            <div className="sticky top-24 space-y-6">
              {/* Información del Curso */}
              <Card className="border-slate-200">
                <CardContent className="p-6">
                  <h3 className="font-bold text-lg text-slate-900 mb-4">Información</h3>
                  <div className="space-y-4 text-sm">
                    <div>
                      <p className="text-slate-600 font-medium">Creado</p>
                      <p className="text-slate-900">
                        {new Date(course.created_at).toLocaleDateString('es-ES')}
                      </p>
                    </div>
                    <div>
                      <p className="text-slate-600 font-medium">Estado</p>
                      <p className="text-slate-900 font-semibold">
                        {course.is_published ? 'Disponible' : 'No disponible'}
                      </p>
                    </div>
                    <div>
                      <p className="text-slate-600 font-medium">Categoría</p>
                      <p className="text-slate-900">{course.category}</p>
                    </div>
                  </div>
                </CardContent>
              </Card>

              {/* Progress */}
              <Card className="border-slate-200 bg-slate-50">
                <CardContent className="p-6">
                  <h3 className="font-bold text-lg text-slate-900 mb-4">Tu Progreso</h3>
                  <div className="space-y-2">
                    <p className="text-sm text-slate-700">0%</p>
                    <div className="w-full bg-slate-300 rounded-full h-2">
                      <div className="bg-slate-800 h-2 rounded-full" style={{ width: '0%' }}></div>
                    </div>
                    <p className="text-xs text-slate-600 mt-2">Sin comenzar</p>
                  </div>
                </CardContent>
              </Card>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-slate-200 bg-slate-50 py-12 mt-20">
        <div className="container mx-auto px-6 text-center text-slate-600">
          <p>CDN Educativa PUCP — Plataforma offline para zonas sin conectividad</p>
        </div>
      </footer>
    </div>
  )
}
