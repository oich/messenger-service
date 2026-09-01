import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_TARGET || '',
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Returns true if it actually navigated away (caller must not settle the
// pending request promise in that case), false if there was nowhere to
// redirect to (standalone mode, no VITE_HUB_URL) - the caller must then
// reject normally instead of hanging forever.
function redirectToLogin() {
  localStorage.removeItem('token')
  localStorage.removeItem('refresh_token')
  // Redirect to Hub if configured
  const hubUrl = import.meta.env.VITE_HUB_URL
  if (hubUrl) {
    window.location.href = hubUrl
    return true
  }
  return false
}

// Refresh queue to prevent multiple concurrent refresh calls
let isRefreshing = false
let refreshQueue = []

function processQueue(error, token = null) {
  refreshQueue.forEach(({ resolve, reject }) => {
    if (error) reject(error)
    else resolve(token)
  })
  refreshQueue = []
}

// Response interceptor: handle 401 with automatic token refresh, only
// hard-redirecting to the Hub if the refresh itself fails.
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config
    if (error.response?.status !== 401) {
      return Promise.reject(error)
    }
    if (originalRequest._retry) {
      return Promise.reject(error)
    }

    const refreshTokenStored = localStorage.getItem('refresh_token')
    if (!refreshTokenStored) {
      if (redirectToLogin()) return new Promise(() => {})
      return Promise.reject(error)
    }

    if (isRefreshing) {
      return new Promise((resolve, reject) => {
        refreshQueue.push({ resolve, reject })
      }).then((token) => {
        originalRequest.headers.Authorization = `Bearer ${token}`
        originalRequest._retry = true
        return api(originalRequest)
      })
    }

    isRefreshing = true
    originalRequest._retry = true

    try {
      const { refreshTokenNow } = await import('./utils/tokenRefresh')
      const newToken = await refreshTokenNow()

      if (!newToken) {
        processQueue(new Error('Refresh failed'))
        if (redirectToLogin()) return new Promise(() => {})
        return Promise.reject(error)
      }

      processQueue(null, newToken)
      originalRequest.headers.Authorization = `Bearer ${newToken}`
      return api(originalRequest)
    } catch (refreshError) {
      processQueue(refreshError)
      if (redirectToLogin()) return new Promise(() => {})
      return Promise.reject(error)
    } finally {
      isRefreshing = false
    }
  }
)

export async function configureApi() {
  // API is ready after token setup in main.js
}

export default api
