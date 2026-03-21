import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Search, Loader2, TrendingUp, Users, Award } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent } from '@/components/ui/card'
import { getCategories, getCourses } from '@/lib/api'
import { useAuth } from '@/context/AuthContext'
import { Navbar } from '@/components/Navbar'
import type { Category, Course } from '@/lib/api'

export function HomePage() {
  const [query, setQuery] = useState('')
  const [categories, setCategories] = useState<Category[]>([])
  const [courses, setCourses] = useState<Course[]>([])
  const [selectedCategory, setSelectedCategory] = useState<string>('Todos')
  const [loading, setLoading] = useState(true)
  const navigate = useNavigate()
  const { isAuthenticated } = useAuth()

  useEffect(() => {
    const loadData = async () => {
      try {
        setLoading(true)
        const [categoriesData, coursesData] = await Promise.all([
          getCategories(),
          getCourses(100),
        ])

        const mainCategories = categoriesData.filter(cat => cat.parent_id === null)
        setCategories(mainCategories)
        setCourses(coursesData.data)
      } catch (err) {
        console.error('Error:', err)
      } finally {
        setLoading(false)
      }
    }

    loadData()
  }, [])

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    if (query.trim()) {
      navigate(`/search?q=${encodeURIComponent(query)}`)
    }
  }

  const handleCourseClick = (slug: string) => {
    if (!isAuthenticated) {
      localStorage.setItem('pendingCourseSlug', slug)
      navigate('/auth')
    } else {
      navigate(`/course/${slug}`)
    }
  }

  const filteredCourses = selectedCategory === 'Todos'
    ? courses
    : courses.filter(course => course.category === selectedCategory)

  const getCategoryColor = (category: string): string => {
    const colors: Record<string, string> = {
      'Tecnología e Informática': 'bg-slate-800',
      'Ciencias Naturales': 'bg-slate-700',
      'Matemáticas y Ciencias Exactas': 'bg-slate-800',
      'Humanidades y Ciencias Sociales': 'bg-slate-700',
      'Arte y Cultura': 'bg-slate-800',
      'Idiomas y Comunicación': 'bg-slate-700',
      'Educación Física y Salud': 'bg-slate-800',
    }
    return colors[category] || 'bg-slate-600'
  }

  const totalStudents = courses.reduce((sum, course) => sum + course.like_count, 0)

  return (
    <div className="min-h-screen bg-white">
      <Navbar />

      {/* Hero */}
      <section className="bg-linear-gradient from-slate-50 via-slate-50 to-white px-6 py-20">
        <div className="container mx-auto max-w-4xl text-center">
          <h1 className="text-5xl md:text-6xl font-bold text-slate-900 mb-6">
            Aprende sin limitaciones
          </h1>
          <p className="text-xl text-slate-600 mb-12 max-w-2xl mx-auto">
            Accede a cursos profesionales de primer nivel, diseñados para impulsarte tu carrera académica y profesional.
          </p>

          {/* Search Bar */}
          <form onSubmit={handleSearch} className="max-w-2xl mx-auto mb-16">
            <div className="relative">
              <Search className="absolute left-4 top-1/2 -translate-y-1/2 h-5 w-5 text-slate-400" />
              <Input
                type="text"
                placeholder="Busca cursos, temas, instructores..."
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                className="w-full h-14 pl-12 pr-16 text-base rounded-lg border-2 border-slate-200 focus:border-slate-900 focus:outline-none bg-white"
              />
              <Button
                type="submit"
                size="lg"
                className="absolute right-2 top-1/2 -translate-y-1/2 rounded-lg bg-slate-900 hover:bg-slate-800 text-white"
              >
                Buscar
              </Button>
            </div>
          </form>

          {/* Stats */}
          <div className="grid grid-cols-3 gap-6 max-w-3xl mx-auto bg-slate-50 rounded-xl p-8 border border-slate-200">
            <div className="text-center">
              <div className="text-3xl font-bold text-slate-900 mb-2 flex items-center justify-center gap-2">
                {courses.length}
                <TrendingUp className="h-6 w-6 text-slate-700" />
              </div>
              <div className="text-sm text-slate-600">Cursos Disponibles</div>
            </div>
            <div className="text-center">
              <div className="text-3xl font-bold text-slate-900 mb-2 flex items-center justify-center gap-2">
                {categories.length}
                <Award className="h-6 w-6 text-slate-700" />
              </div>
              <div className="text-sm text-slate-600">Disciplinas</div>
            </div>
            <div className="text-center">
              <div className="text-3xl font-bold text-slate-900 mb-2 flex items-center justify-center gap-2">
                {totalStudents.toLocaleString()}
                <Users className="h-6 w-6 text-slate-700" />
              </div>
              <div className="text-sm text-slate-600">Estudiantes</div>
            </div>
          </div>
        </div>
      </section>

      {/* Courses Section */}
      <section className="container mx-auto px-6 py-20">
        {/* Category Filter */}
        <div className="mb-12">
          <h2 className="text-2xl font-bold text-slate-900 mb-6">Explorar Cursos</h2>
          <div className="flex flex-wrap gap-2">
            <Button
              variant={selectedCategory === 'Todos' ? 'default' : 'outline'}
              size="sm"
              onClick={() => setSelectedCategory('Todos')}
              className={selectedCategory === 'Todos' ? 'bg-slate-900 hover:bg-slate-800 text-white' : 'border-slate-300 text-slate-700 hover:bg-slate-50'}
            >
              Todos
            </Button>
            {categories.slice(0, 6).map((cat) => (
              <Button
                key={cat.id}
                variant={selectedCategory === cat.name ? 'default' : 'outline'}
                size="sm"
                onClick={() => setSelectedCategory(cat.name)}
                className={selectedCategory === cat.name ? 'bg-slate-900 hover:bg-slate-800 text-white' : 'border-slate-300 text-slate-700 hover:bg-slate-50'}
              >
                {cat.name}
              </Button>
            ))}
          </div>
          <p className="text-sm text-slate-600 mt-4">
            {filteredCourses.length} cursos encontrados
          </p>
        </div>

        {/* Courses Grid */}
        {loading ? (
          <div className="flex justify-center items-center py-20">
            <Loader2 className="h-8 w-8 animate-spin text-slate-900" />
          </div>
        ) : filteredCourses.length === 0 ? (
          <div className="text-center text-slate-600 py-20">
            No hay cursos disponibles en esta categoría
          </div>
        ) : (
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
            {filteredCourses.map((course) => (
              <Card
                key={course.id}
                className="hover:shadow-lg transition-all duration-300 border-slate-200 cursor-pointer group overflow-hidden"
                onClick={() => handleCourseClick(course.slug)}
              >
                {/* Header with Category */}
                <div className={`h-2 ${getCategoryColor(course.category)}`} />

                <CardContent className="p-6">
                  {/* Category Badge */}
                  <div className="text-xs font-semibold text-slate-600 mb-3 uppercase tracking-wider">
                    {course.category}
                  </div>

                  {/* Title */}
                  <h3 className="font-bold text-lg text-slate-900 line-clamp-2 mb-3 group-hover:text-slate-900 transition">
                    {course.title}
                  </h3>

                  {/* Description */}
                  <p className="text-sm text-slate-600 line-clamp-2 mb-6">
                    {course.description}
                  </p>

                  {/* Stats */}
                  <div className="flex items-center gap-4 text-xs text-slate-600 mb-6 pb-6 border-t border-slate-100">
                    <div className="flex items-center gap-1 mt-4">
                      <span className="font-semibold">{course.view_count}</span>
                      <span>vistas</span>
                    </div>
                    <div className="flex items-center gap-1 mt-4">
                      <span className="font-semibold">{course.like_count}</span>
                      <span>estudiantes</span>
                    </div>
                  </div>

                  {/* Button */}
                  <Button
                    className="w-full bg-slate-900 hover:bg-slate-800 text-white"
                    size="sm"
                  >
                    Explorar
                  </Button>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
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
