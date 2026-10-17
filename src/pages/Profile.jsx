import { motion } from 'framer-motion'
import { useCallback, useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import Icon from '../components/Icon.jsx'
import { Page, Toast, fadeUp, stagger } from '../components/ui.jsx'
import { api, errorText, unwrap } from '../lib/api.js'
import { useAuth } from '../lib/auth.jsx'
import { money } from '../lib/format.js'
import { useI18n } from '../lib/i18n.jsx'
import { usePortal } from '../lib/portal.jsx'

function Card({ icon, title, children }) {
  return (
    <motion.section variants={fadeUp} className="flex flex-col gap-space-sm rounded-xl bg-surface-container-lowest p-space-md shadow-md">
      <h2 className="flex items-center gap-2 text-headline-md"><Icon name={icon} className="text-primary" />{title}</h2>
      {children}
    </motion.section>
  )
}

const input = 'h-16 w-full rounded-xl bg-surface-container-low px-5 text-body-lg outline-none focus:bg-surface-container'

function RescuerPanel({ onToast }) {
  const { t } = useI18n()
  const { refresh } = usePortal()
  const [villages, setVillages] = useState([])
  const [form, setForm] = useState({ village: '', hazard: 'mudflow', level: 'critical', eta_seconds: 600 })
  useEffect(() => { api.get('/portal/config/').then((c) => { setVillages(c.villages); setForm((f) => ({ ...f, village: c.villages.find((v) => v.slug === 'ak-tash')?.id || c.villages[0]?.id })) }) }, [])
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value })
  const fire = async () => {
    try { await api.post('/alerts/simulate/', { ...form, village: Number(form.village), eta_seconds: Number(form.eta_seconds) }); onToast(t('profile.alertSent')); refresh() } catch (e) { onToast(errorText(e, t('common.error'))) }
  }
  const clear = async () => {
    try {
      const active = await api.get('/alerts/active/')
      await Promise.all(unwrap(active).map((a) => api.post(`/alerts/${a.id}/resolve/`)))
      onToast(t('profile.alertCleared')); refresh()
    } catch (e) { onToast(errorText(e, t('common.error'))) }
  }
  return (
    <Card icon="emergency" title={t('profile.rescuer')}>
      <p className="text-body-md text-on-surface-variant">{t('profile.rescuerHint')}</p>
      <div className="grid gap-3 sm:grid-cols-2">
        <select value={form.village} onChange={set('village')} className={input}>{villages.map((v) => <option key={v.id} value={v.id}>{v.name}</option>)}</select>
        <select value={form.hazard} onChange={set('hazard')} className={input}>{['mudflow', 'flood', 'avalanche', 'fire'].map((h) => <option key={h} value={h}>{t(`hazard.${h}`)}</option>)}</select>
        <select value={form.level} onChange={set('level')} className={input}>{['medium', 'high', 'critical'].map((l) => <option key={l} value={l}>{t(`level.${l}`)}</option>)}</select>
        <input type="number" min="0" max="3600" value={form.eta_seconds} onChange={set('eta_seconds')} className={input} aria-label="ETA, s" />
      </div>
      <div className="grid gap-3 sm:grid-cols-2">
        <button type="button" onClick={fire} className="h-16 rounded-xl bg-secondary text-label-xl text-on-secondary">{t('profile.fireAlert')}</button>
        <button type="button" onClick={clear} className="h-16 rounded-xl bg-surface-container text-label-xl">{t('profile.clearAlerts')}</button>
      </div>
    </Card>
  )
}

export default function Profile() {
  const { t, lang, setLang } = useI18n()
  const { user, updateMe, logout } = useAuth()
  const navigate = useNavigate()
  const [name, setName] = useState(user.name || '')
  const [village, setVillage] = useState(user.village || '')
  const [label, setLabel] = useState(user.home_label || '')
  const [villages, setVillages] = useState([])
  const [mine, setMine] = useState([])
  const [toast, setToast] = useState('')
  const say = useCallback((m) => { setToast(m); setTimeout(() => setToast(''), 3500) }, [])

  useEffect(() => { api.get('/portal/config/').then((c) => setVillages(c.villages)).catch(() => {}) }, [lang])
  const loadMine = useCallback(() => api.get('/market/listings/', { mine: 1, status: 'active' }).then((d) => setMine(unwrap(d))).catch(() => {}), [])
  useEffect(() => { loadMine() }, [loadMine])

  const save = async (patch, ok = t('profile.saved')) => {
    try { await updateMe(patch); say(ok) } catch (e) { say(errorText(e, t('common.error'))) }
  }
  const locate = () => {
    if (!navigator.geolocation) { say(t('profile.noGeo')); return }
    navigator.geolocation.getCurrentPosition(
      (p) => save({ home_lat: +p.coords.latitude.toFixed(6), home_lon: +p.coords.longitude.toFixed(6), home_label: label }, t('profile.homeSaved')),
      () => say(t('profile.noGeo')), { timeout: 8000 })
  }
  const closeListing = async (l) => { await api.patch(`/market/listings/${l.id}/`, { status: 'closed' }); loadMine(); say(t('profile.listingClosed')) }

  return (
    <Page className="mx-auto w-full max-w-3xl px-4 py-space-lg">
      <motion.div variants={stagger} initial="hidden" animate="show" className="flex flex-col gap-space-md">
        <motion.div variants={fadeUp} className="flex items-center gap-5 rounded-xl bg-surface-container-low p-6 shadow-sm">
          <span className="flex h-16 w-16 items-center justify-center rounded-full bg-primary text-headline-lg text-on-primary">{(user.name || user.phone).trim().charAt(0).toUpperCase()}</span>
          <div className="flex flex-col"><span className="flex items-center gap-2 text-headline-lg">{user.name || user.phone}{user.is_verified && <Icon name="verified" className="text-primary" />}</span><span className="text-body-lg text-on-surface-variant">{user.phone} · {t(`role.user.${user.role}`)}</span></div>
        </motion.div>

        <div className="grid grid-cols-2 gap-space-sm">
          <Link to="/orders" className="flex h-20 items-center justify-center gap-3 rounded-xl bg-surface-container-lowest text-label-xl shadow-md"><Icon name="receipt_long" size={32} className="text-primary" />{t('orders.title')}</Link>
          <Link to="/chats" className="flex h-20 items-center justify-center gap-3 rounded-xl bg-surface-container-lowest text-label-xl shadow-md"><Icon name="chat" size={32} className="text-primary" />{t('chats.title')}</Link>
        </div>

        <Card icon="badge" title={t('profile.about')}>
          <input value={name} onChange={(e) => setName(e.target.value)} placeholder={t('login.yourName')} className={input} />
          <select value={village} onChange={(e) => setVillage(e.target.value)} className={input} aria-label={t('profile.village')}>
            <option value="">{t('profile.village')}</option>
            {villages.map((v) => <option key={v.id} value={v.id}>{v.name} — {v.valley}</option>)}
          </select>
          <button type="button" onClick={() => save({ name, village: village ? Number(village) : null })} className="h-16 rounded-xl bg-primary text-label-xl text-on-primary">{t('profile.save')}</button>
        </Card>

        <Card icon="home_pin" title={t('profile.home')}>
          <p className="text-body-md text-on-surface-variant">{t('profile.homeHint')}</p>
          <input value={label} onChange={(e) => setLabel(e.target.value)} placeholder={t('profile.houseNo')} maxLength={60} className={input} />
          <div className="grid gap-3 sm:grid-cols-2">
            <button type="button" onClick={locate} className="flex h-16 items-center justify-center gap-2 rounded-xl bg-primary-container text-label-xl text-on-primary"><Icon name="my_location" />{t('profile.useGps')}</button>
            <button type="button" onClick={() => save({ home_label: label })} className="h-16 rounded-xl bg-surface-container text-label-xl">{t('profile.save')}</button>
          </div>
          {user.home_lat != null && <p className="flex items-center gap-2 text-body-md text-primary"><Icon name="check_circle" size={22} />{t('profile.homeSet')}</p>}
        </Card>

        <Card icon="language" title={t('profile.language')}>
          <div className="grid grid-cols-2 gap-3">
            {[['ky', 'Кыргызча'], ['ru', 'Русский']].map(([c, label2]) => (
              <button key={c} type="button" onClick={() => setLang(c)} className={`h-16 rounded-xl text-label-xl ${lang === c ? 'bg-primary text-on-primary' : 'bg-surface-container'}`}>{label2}</button>
            ))}
          </div>
          <p className="flex items-center gap-2 text-body-md text-on-surface-variant"><Icon name={user.telegram_linked ? 'check_circle' : 'info'} size={22} className={user.telegram_linked ? 'text-primary' : ''} />{user.telegram_linked ? t('profile.tgLinked') : t('profile.tgNot')}</p>
        </Card>

        <Card icon="sell" title={t('profile.myListings')}>
          {mine.length === 0 ? <p className="text-body-lg text-on-surface-variant">{t('profile.noListings')}</p> : mine.map((l) => (
            <div key={l.id} className="flex items-center justify-between gap-3 rounded-xl bg-surface-container-low p-3">
              <div className="flex min-w-0 flex-col"><span className="truncate text-label-lg">{l.title}</span><span className="text-body-md text-on-surface-variant">{money(l.price_kgs)} {t('common.som')}</span></div>
              <button type="button" onClick={() => closeListing(l)} className="h-12 shrink-0 rounded-lg bg-surface-container px-4 text-label-md">{t('profile.closeListing')}</button>
            </div>
          ))}
          <Link to="/sell" className="flex h-16 items-center justify-center gap-2 rounded-xl bg-primary text-label-xl text-on-primary"><Icon name="add" />{t('market.newListing')}</Link>
        </Card>

        {['rescuer', 'admin'].includes(user.role) && <RescuerPanel onToast={say} />}

        <button type="button" onClick={() => { logout(); navigate('/') }} className="flex h-16 items-center justify-center gap-2 rounded-xl bg-error-container text-label-xl text-on-error-container"><Icon name="logout" />{t('profile.logout')}</button>
      </motion.div>
      <Toast message={toast} />
    </Page>
  )
}
