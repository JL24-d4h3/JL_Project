import axios from 'axios'

export const apiClient = axios.create({
  baseURL: '',          // usa el proxy de Vite (/api → localhost:3000)
  withCredentials: true,
})

// Adjuntar el token JWT si existe en localStorage
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Limpiar sesión y redirigir al login si el servidor devuelve 401
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  },
)
