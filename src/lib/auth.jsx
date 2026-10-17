import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import { api, getTokens, setTokens } from './api.js'
import { useI18n } from './i18n.jsx'

const AuthCtx = createContext(null)
export const useAuth = () => useContext(AuthCtx)

export function AuthProvider({ children }) {
  const { lang, setLang } = useI18n()
  const [user, setUser] = useState(null)
  const [ready, setReady] = useState(!getTokens())

  const loadMe = useCallback(async () => {
    try {
      const me = await api.get('/auth/me/')
      setUser(me)
      return me
    } catch {
      setTokens(null)
      setUser(null)
      return null
    } finally {
      setReady(true)
    }
  }, [])

  useEffect(() => { if (getTokens()) loadMe() }, [loadMe])

  const login = useCallback(async (data) => {
    setTokens({ access: data.access, refresh: data.refresh })
    setUser(data.user)
    setReady(true)
  }, [])

  const logout = useCallback(() => { setTokens(null); setUser(null) }, [])

  const updateMe = useCallback(async (patch) => {
    const me = await api.patch('/auth/me/', patch)
    setUser(me)
    return me
  }, [])

  // keep the account language in step with the toggle once logged in
  useEffect(() => {
    if (user && user.language !== lang && ['ky', 'ru'].includes(lang)) {
      api.patch('/auth/me/', { language: lang }).then(setUser).catch(() => {})
    }
  }, [lang, user])

  const value = useMemo(
    () => ({ user, ready, login, logout, updateMe, loadMe, setLang }),
    [user, ready, login, logout, updateMe, loadMe, setLang],
  )
  return <AuthCtx.Provider value={value}>{children}</AuthCtx.Provider>
}
