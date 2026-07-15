import axios from 'axios'

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api'

const client = axios.create({
  baseURL: API_BASE_URL,
})

let accessToken = null
let onSessionExpired = () => {}

export function setAccessToken(token) {
  accessToken = token
}

export function setOnSessionExpired(handler) {
  onSessionExpired = handler
}

client.interceptors.request.use((config) => {
  if (accessToken) {
    config.headers.Authorization = `Bearer ${accessToken}`
  }
  return config
})

// Concurrent 401s share one in-flight refresh instead of each firing their own.
let refreshPromise = null

async function refreshAccessToken() {
  const refreshToken = localStorage.getItem('refreshToken')
  if (!refreshToken) {
    throw new Error('No refresh token available')
  }
  const { data } = await axios.post(`${API_BASE_URL}/auth/token/refresh/`, {
    refresh: refreshToken,
  })
  setAccessToken(data.access)
  if (data.refresh) {
    localStorage.setItem('refreshToken', data.refresh)
  }
  return data.access
}

client.interceptors.response.use(
  (response) => response,
  async (error) => {
    const { config, response } = error
    const isAuthEndpoint = config?.url?.includes('/auth/token/')

    if (response?.status === 401 && config && !config._retried && !isAuthEndpoint) {
      config._retried = true
      try {
        if (!refreshPromise) {
          refreshPromise = refreshAccessToken().finally(() => {
            refreshPromise = null
          })
        }
        const newAccessToken = await refreshPromise
        config.headers.Authorization = `Bearer ${newAccessToken}`
        return client(config)
      } catch (refreshError) {
        setAccessToken(null)
        localStorage.removeItem('refreshToken')
        onSessionExpired()
        return Promise.reject(refreshError)
      }
    }

    return Promise.reject(error)
  },
)

export default client
