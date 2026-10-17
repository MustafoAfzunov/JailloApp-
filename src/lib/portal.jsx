import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react'
import { api } from './api.js'
import { useI18n } from './i18n.jsx'

const PortalCtx = createContext(null)
export const usePortal = () => useContext(PortalCtx)

/** Polls the Home endpoint so every page (header, alert bar) knows the village and its current status. */
export function PortalProvider({ children }) {
  const { lang } = useI18n()
  const [home, setHome] = useState(null)
  const [error, setError] = useState(false)
  const timer = useRef(null)

  const refresh = useCallback(async () => {
    try {
      setHome(await api.get('/portal/home/'))
      setError(false)
    } catch {
      setError(true)
    }
  }, [])

  useEffect(() => {
    refresh()
    timer.current = setInterval(refresh, 15000)
    return () => clearInterval(timer.current)
  }, [refresh, lang])

  const value = useMemo(() => ({ home, error, refresh }), [home, error, refresh])
  return <PortalCtx.Provider value={value}>{children}</PortalCtx.Provider>
}
