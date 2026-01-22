import axios from 'axios'

const BACKEND_BASE_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000/api/v1'

// Single unified API instance for all backend endpoints
export const api = axios.create({
  baseURL: BACKEND_BASE_URL,
})

// Add token to requests
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Handle auth errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

// Legacy exports for backward compatibility (deprecated)
export const chatbotApi = api
export const webAppApi = api
export const analyzerApi = api
export const wafApi = api
