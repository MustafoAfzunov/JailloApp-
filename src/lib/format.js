export const money = (n) => Number(n).toLocaleString('ru-RU', { maximumFractionDigits: 0 })
export const num = (n) => Number(n).toLocaleString('ru-RU', { maximumFractionDigits: 2 })
export const clock = (iso, lang) =>
  new Date(iso).toLocaleTimeString(lang === 'ky' ? 'ru-RU' : 'ru-RU', { hour: '2-digit', minute: '2-digit' })
export const isToday = (iso) => new Date(iso).toDateString() === new Date().toDateString()
export const telHref = (phone) => `tel:${String(phone).replace(/[^\d+]/g, '')}`
export const initial = (name) => (name || '?').trim().charAt(0).toUpperCase()
export const mmss = (secs) => {
  const s = Math.max(0, Math.floor(secs))
  return `${String(Math.floor(s / 60)).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}`
}
