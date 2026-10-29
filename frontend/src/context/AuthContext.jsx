import { useCallback, useEffect, useMemo, useState } from 'react'
import client, { setAccessToken, setOnSessionExpired } from '../api/client'
import { AuthContext } from './auth-context'

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [isLoading, setIsLoading] = useState(true)

  const clearSession = useCallback(() => {
    setAccessToken(null)
    localStorage.removeItem('refreshToken')
    setUser(null)
  }, [])

  useEffect(() => {
    setOnSessionExpired(clearSession)
  }, [clearSession])

  const fetchCurrentUser = useCallback(async () => {
    const { data } = await client.get('/auth/me/')
    setUser(data)
    return data
  }, [])

  const updateUser = useCallback(async (payload) => {
    const { data } = await client.patch('/auth/me/', payload)
    setUser(data)
    return data
  }, [])

  useEffect(() => {
    async function restoreSession() {
      const refreshToken = localStorage.getItem('refreshToken')
      if (!refreshToken) {
        setIsLoading(false)
        return
      }
      try {
        const { data } = await client.post('/auth/token/refresh/', { refresh: refreshToken })
        setAccessToken(data.access)
        if (data.refresh) {
          localStorage.setItem('refreshToken', data.refresh)
        }
        await fetchCurrentUser()
      } catch {
        clearSession()
      } finally {
        setIsLoading(false)
      }
    }
    restoreSession()
  }, [clearSession, fetchCurrentUser])

  const login = useCallback(
    async (username, password) => {
      const { data } = await client.post('/auth/token/', { username, password })
      setAccessToken(data.access)
      localStorage.setItem('refreshToken', data.refresh)
      return fetchCurrentUser()
    },
    [fetchCurrentUser],
  )

  const register = useCallback(
    async (payload) => {
      await client.post('/auth/register/', payload)
      return login(payload.username, payload.password)
    },
    [login],
  )

  const logout = useCallback(async () => {
    const refreshToken = localStorage.getItem('refreshToken')
    clearSession()
    if (refreshToken) {
      try {
        await client.post('/auth/token/blacklist/', { refresh: refreshToken })
      } catch {
        // Best-effort: the client-side session is already cleared either way.
      }
    }
  }, [clearSession])

  const value = useMemo(
    () => ({ user, isAuthenticated: Boolean(user), isLoading, login, register, logout, updateUser }),
    [user, isLoading, login, register, logout, updateUser],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
