import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5174,
    proxy: {
      // /api/ai/* → AI Engine (puerto 8000) — quita el prefijo /api/ai al reenviar
      // En producción/Jetson eliminar esta entrada y que el CDN server haga el proxy interno.
      '/api/ai': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        rewrite: (path: string) => path.replace(/^\/api\/ai/, '/api'),
      },
      // /files/* → archivos estáticos servidos por el AI Engine mock
      '/files': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      // /api/* → CDN server (puerto 3000)
      '/api': {
        target: 'http://localhost:3000',
        changeOrigin: true,
      },
    },
  },
})
