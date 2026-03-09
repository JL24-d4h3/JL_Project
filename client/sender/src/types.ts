// Shared type definitions for the sender app

export type ContentStatus = 'pending' | 'active' | 'rejected' | 'archived' | 'processing' | 'failed'

export interface Submission {
  id: string
  title: string
  description: string | null
  content_type: 'video' | 'audio' | 'document' | 'image'
  status: ContentStatus
  rejected_reason: string | null
  duration: number | null
  file_size_bytes: number | null
  thumbnail_path: string | null
  created_at: string
  updated_at: string
}

export interface Category {
  id: string
  name: string
  slug: string
}

export interface ApiResponse<T> {
  success: boolean
  data: T
}
