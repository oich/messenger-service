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

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token')
      // Redirect to Hub if configured
      const hubUrl = import.meta.env.VITE_HUB_URL
      if (hubUrl) {
        window.location.href = hubUrl
      }
    }
    return Promise.reject(error)
  }
)

export async function configureApi() {
  // API is ready after token setup in main.js
}

export default api
