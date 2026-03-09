import { useQuery } from '@tanstack/react-query'
import { apiClient } from '../lib/apiClient'
import type { Submission, Category, ApiResponse } from '../types'

// ── My submissions ────────────────────────────────────────────
export function useMySubmissions() {
  return useQuery<Submission[]>({
    queryKey: ['submissions', 'mine'],
    queryFn: async () => {
      const res = await apiClient.get<ApiResponse<Submission[]>>('/api/upload/mine')
      return res.data.data
    },
  })
}

// ── Categories ────────────────────────────────────────────────
export function useCategories() {
  return useQuery<Category[]>({
    queryKey: ['categories'],
    queryFn: async () => {
      const res = await apiClient.get<ApiResponse<Category[]>>('/api/categories')
      return res.data.data
    },
    staleTime: 1000 * 60 * 10, // 10 min — categories rarely change
  })
}
