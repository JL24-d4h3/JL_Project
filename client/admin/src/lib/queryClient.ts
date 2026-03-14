import { QueryClient } from '@tanstack/react-query'

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60,        // 1 min
      gcTime: 1000 * 60 * 10,      // 10 min
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
})
