import axios from 'axios'

export const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
})

// Agregar token a las peticiones
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error)
)

export interface SearchResult {
  content_id: string
  content_type: string
  title: string
  snippet: string
  thumbnail_url: string
  viewer_url: string
  relevance_score: number
}

export interface SearchResponse {
  query: string
  cdn_results: SearchResult[]
  ai_overview?: {
    text: string
    citations: string[]
  }
  related_searches?: string[]
}

export interface Category {
  id: string
  name: string
  slug: string
  description: string
  parent_id: string | null
  icon: string | null
  color: string
  display_order: number
  is_active: boolean
  created_at: string
}

export interface Content {
  id: string
  title: string
  description: string
  type: 'pdf' | 'video' | 'document' | 'code' | 'image'
  thumbnail_path: string | null
  duration_seconds: number | null
  file_size: string
  access_count: number
  average_rating: number | null
  is_featured: boolean
  created_at: string
  category_name: string | null
}

export async function searchContent(query: string): Promise<SearchResponse> {
  const { data } = await api.post<SearchResponse>('/search', { query })
  return data
}

export async function getCategories(): Promise<Category[]> {
  const { data } = await api.get<{ success: boolean; data: Category[] }>('/categories')
  return data.data
}

export async function getCategoriesTree(): Promise<Category[]> {
  const { data } = await api.get<{ success: boolean; data: Category[] }>('/categories/tree')
  return data.data
}

export async function getCategoryById(id: string): Promise<Category> {
  const { data } = await api.get<{ success: boolean; data: Category }>(`/categories/${id}`)
  return data.data
}

export async function getContent(limit = 20, page = 1): Promise<{ data: Content[]; total: number }> {
  const { data } = await api.get<{ success: boolean; data: Content[]; pagination: { total: number } }>('/content', {
    params: { limit, page },
  })
  return { data: data.data, total: data.pagination.total }
}

export async function getFeaturedContent(): Promise<Content[]> {
  const { data } = await api.get<{ success: boolean; data: Content[] }>('/content/featured')
  return data.data
}

export async function getContentById(id: string): Promise<Content> {
  const { data } = await api.get<{ success: boolean; data: Content }>(`/content/${id}`)
  return data.data
}

export interface Course {
  id: string
  slug: string
  title: string
  description: string
  thumbnail_url: string | null
  category: string
  is_published: boolean
  view_count: number
  like_count: number
  created_at: string
  updated_at: string
}

export async function getCourses(limit = 50, page = 1, category?: string): Promise<{ data: Course[]; pagination: { page: number; limit: number; total: number; total_pages: number } }> {
  const params: Record<string, any> = { limit, page }
  if (category) params.category = category

  const { data } = await api.get<{ success: boolean; data: Course[]; pagination: { page: number; limit: number; total: number; total_pages: number } }>('/courses', { params })
  return { data: data.data, pagination: data.pagination }
}

export async function getCourseById(id: string): Promise<Course> {
  const { data } = await api.get<{ success: boolean; data: Course }>(`/courses/${id}`)
  return data.data
}

export async function getCourseBySlug(slug: string): Promise<Course> {
  const { data } = await api.get<{ success: boolean; data: Course }>(`/courses/slug/${slug}`)
  return data.data
}
