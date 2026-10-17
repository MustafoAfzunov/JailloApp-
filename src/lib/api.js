// Tiny API client: JWT in localStorage, one silent refresh on 401, ?lang= added to every GET.
const TOKENS_KEY = 'jailo.tokens'
let currentLang = 'ky'

export const setApiLang = (lang) => { currentLang = lang }

export function getTokens() {
  try { return JSON.parse(localStorage.getItem(TOKENS_KEY)) || null } catch { return null }
}
export function setTokens(tokens) {
  try {
    if (tokens) localStorage.setItem(TOKENS_KEY, JSON.stringify(tokens))
    else localStorage.removeItem(TOKENS_KEY)
  } catch { /* private mode: stay logged in for this tab only */ }
}

export class ApiError extends Error {
  constructor(status, data) {
    super(typeof data === 'string' ? data : data?.detail || `HTTP ${status}`)
    this.status = status
    this.data = data
  }
}

/** First readable message out of a DRF error body. */
export function errorText(err, fallback = '') {
  const d = err?.data
  if (!d) return fallback
  if (typeof d === 'string') return d
  if (d.detail) return String(d.detail)
  const first = Object.values(d)[0]
  return String(Array.isArray(first) ? first[0] : first || fallback)
}

let refreshing = null
async function refreshAccess() {
  const tokens = getTokens()
  if (!tokens?.refresh) return false
  refreshing ??= fetch('/api/auth/token/refresh/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ refresh: tokens.refresh }),
  })
    .then(async (r) => {
      if (!r.ok) return false
      const data = await r.json()
      setTokens({ ...tokens, access: data.access, refresh: data.refresh || tokens.refresh })
      return true
    })
    .catch(() => false)
    .finally(() => { refreshing = null })
  return refreshing
}

async function send(path, { method = 'GET', body, params, signal } = {}, retry = true) {
  const url = new URL(`/api${path}`, window.location.origin)
  if (method === 'GET') url.searchParams.set('lang', currentLang)
  Object.entries(params || {}).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== '') url.searchParams.set(k, v)
  })
  const headers = {}
  const tokens = getTokens()
  if (tokens?.access) headers.Authorization = `Bearer ${tokens.access}`
  let payload = body
  if (body && !(body instanceof FormData)) {
    headers['Content-Type'] = 'application/json'
    payload = JSON.stringify(body)
  }
  const res = await fetch(url, { method, headers, body: payload, signal })
  if (res.status === 401 && retry && tokens?.refresh && (await refreshAccess())) {
    return send(path, { method, body, params, signal }, false)
  }
  if (res.status === 204) return null
  const text = await res.text()
  let data = null
  try { data = text ? JSON.parse(text) : null } catch { data = text }
  if (!res.ok) throw new ApiError(res.status, data)
  return data
}

export const api = {
  get: (path, params, signal) => send(path, { params, signal }),
  post: (path, body) => send(path, { method: 'POST', body }),
  patch: (path, body) => send(path, { method: 'PATCH', body }),
  del: (path) => send(path, { method: 'DELETE' }),
}

/** DRF lists are paginated ({results}) on some endpoints and plain arrays on others. */
export const unwrap = (data) => (Array.isArray(data) ? data : data?.results || [])
