import axios from 'axios'

// Base URLs for different services
const CHATBOT_BASE_URL = process.env.NEXT_PUBLIC_CHATBOT_API_URL || 'http://localhost:8005'
const WEB_APP_BASE_URL = process.env.NEXT_PUBLIC_WEB_APP_API_URL || 'http://localhost:8000'
const ANALYZER_BASE_URL = process.env.NEXT_PUBLIC_ANALYZER_API_URL || 'http://localhost:8001'
const WAF_BASE_URL = process.env.NEXT_PUBLIC_WAF_API_URL || 'http://localhost:9090'

// Axios instance for chatbot API
export const chatbotApi = axios.create({
  baseURL: CHATBOT_BASE_URL,
})

// Axios instance for web app API
export const webAppApi = axios.create({
  baseURL: WEB_APP_BASE_URL,
})

// Axios instance for analyzer API
export const analyzerApi = axios.create({
  baseURL: ANALYZER_BASE_URL,
})

// Axios instance for WAF API
export const wafApi = axios.create({
  baseURL: WAF_BASE_URL,
})

// Add token to requests
chatbotApi.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

webAppApi.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

analyzerApi.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

wafApi.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Handle auth errors
chatbotApi.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

webAppApi.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

analyzerApi.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

wafApi.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)
