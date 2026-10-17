import { motion } from 'framer-motion'
import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import Icon from '../components/Icon.jsx'
import Countdown, { useCountdown } from '../components/Countdown.jsx'
import { Loading, Page, Toast } from '../components/ui.jsx'
import { AudioButton } from './Home.jsx'
import { api, errorText } from '../lib/api.js'
import { useAuth } from '../lib/auth.jsx'
import { useI18n } from '../lib/i18n.jsx'
import { usePortal } from '../lib/portal.jsx'

const HAZARD_ICON = { mudflow: 'tsunami', flood: 'flood', avalanche: 'ac_unit', fire: 'local_fire_department' }

export default function AlertPage() {
  const { t } = useI18n()
  const { home, refresh } = usePortal()
  const { user } = useAuth()
  const navigate = useNavigate()
  const alert = home?.status?.primary_alert
  const secs = useCountdown(alert?.eta_seconds_remaining ?? null)
  const [safe, setSafe] = useState(false)
  const [toast, setToast] = useState('')

  if (!home) return <Page><Loading /></Page>

  if (!alert) {
    return (
      <Page className="mx-auto flex max-w-xl flex-col items-center gap-space-md px-4 py-space-xl text-center">
        <motion.div initial={{ scale: 0 }} animate={{ scale: 1 }} transition={{ type: 'spring' }} className="flex h-28 w-28 items-center justify-center rounded-full bg-primary-fixed text-primary"><Icon name="verified_user" fill size={64} /></motion.div>
        <h1 className="text-headline-lg">{t('alert.none')}</h1>
        <p className="text-body-lg text-on-surface-variant">{t('alert.noneSub')}</p>
        <Link to="/map" className="flex h-16 items-center gap-2 rounded-xl bg-primary px-8 text-label-xl text-on-primary"><Icon name="map" />{t('home.mapCta')}</Link>
      </Page>
    )
  }

  const shelter = home.shelters.primary
  const steps = t(`alert.steps.${alert.hazard}`) || []
  const critical = alert.level === 'critical'

  const imSafe = async () => {
    if (!user) { navigate('/login?next=/alert'); return }
    try {
      await api.post(`/alerts/${alert.id}/safe/`, {})
      setSafe(true); setToast(t('alert.safeThanks')); refresh()
    } catch (e) { setToast(errorText(e, t('common.error'))) }
    setTimeout(() => setToast(''), 4000)
  }

  return (
    <Page className="mx-auto flex w-full max-w-4xl flex-col gap-space-md px-4 py-space-lg">
      <div className={`relative overflow-hidden rounded-xl p-space-lg text-on-secondary shadow-xl ${critical ? 'bg-secondary' : 'bg-secondary-container'}`}>
        <motion.span className="absolute -right-16 -top-16 h-64 w-64 rounded-full bg-white/10" animate={{ scale: [1, 1.35, 1], opacity: [0.5, 0.15, 0.5] }} transition={{ repeat: Infinity, duration: 2.2 }} />
        <motion.span className="absolute -bottom-20 -left-10 h-56 w-56 rounded-full bg-white/10" animate={{ scale: [1.2, 1, 1.2] }} transition={{ repeat: Infinity, duration: 2.8 }} />
        <div className="relative flex flex-col gap-space-md">
          <div className="flex flex-wrap items-center gap-3">
            <motion.span animate={{ rotate: [-8, 8, -8] }} transition={{ repeat: Infinity, duration: 0.7 }} className="inline-flex"><Icon name={HAZARD_ICON[alert.hazard] || 'warning'} fill size={64} /></motion.span>
            <span className="rounded-full bg-white/25 px-4 py-1.5 text-label-lg uppercase tracking-wider">{t(`level.${alert.level}`)}</span>
            {alert.is_simulated && <span className="rounded-full bg-white px-4 py-1.5 text-label-md text-secondary">{t('alert.demo')}</span>}
          </div>
          <h1 className="text-headline-xl">{alert.title}</h1>
          <p className="whitespace-pre-line text-body-xl">{alert.message}</p>
          {secs != null && (
            <div className="flex flex-col items-center gap-1 rounded-xl bg-black/20 py-space-md">
              <span className="text-label-lg uppercase tracking-wider opacity-90">{t('alert.arrives')}</span>
              <span className="text-[72px] font-extrabold leading-none sm:text-[96px]"><Countdown seconds={secs} /></span>
            </div>
          )}
        </div>
      </div>

      <div className="grid gap-space-md md:grid-cols-2">
        <div className="flex flex-col gap-space-sm rounded-xl bg-surface-container-lowest p-space-md shadow-md">
          <h2 className="flex items-center gap-2 text-headline-md"><Icon name="directions_run" className="text-secondary" />{t('alert.doNow')}</h2>
          <ol className="flex flex-col gap-3">
            {steps.map((s, i) => (
              <motion.li key={i} initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0, transition: { delay: 0.12 * i } }} className="flex items-start gap-3 text-body-lg">
                <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-secondary text-label-lg text-on-secondary">{i + 1}</span><span>{s}</span>
              </motion.li>
            ))}
          </ol>
        </div>
        {shelter && (
          <div className="flex flex-col gap-space-sm rounded-xl bg-primary-fixed/30 p-space-md shadow-md">
            <span className="text-label-md uppercase tracking-wider text-primary">{t('map.shelterTag')}</span>
            <h2 className="text-headline-md">{shelter.name}</h2>
            <p className="text-body-lg">{shelter.distance_m} {t('common.m')} · <strong className="text-primary">{shelter.walk_minutes} {t('common.min')}</strong></p>
            <div className="flex gap-2">{shelter.has_clinic && <Icon name="local_hospital" className="text-primary" size={30} />}{shelter.has_water && <Icon name="water_drop" className="text-primary" size={30} />}</div>
            <Link to="/map" className="mt-auto flex h-16 items-center justify-center gap-2 rounded-xl bg-primary text-label-xl text-on-primary shadow-md"><Icon name="directions_walk" size={30} />{t('alert.showRoute')}</Link>
          </div>
        )}
      </div>

      <div className="grid gap-space-sm sm:grid-cols-2">
        <motion.button whileTap={{ scale: 0.97 }} type="button" onClick={imSafe} disabled={safe}
          className={`flex h-20 items-center justify-center gap-3 rounded-xl text-headline-md shadow-lg ${safe ? 'bg-primary-fixed text-primary' : 'bg-primary text-on-primary'}`}>
          <Icon name={safe ? 'task_alt' : 'health_and_safety'} size={36} />{safe ? t('alert.safeDone') : t('alert.imSafe')}
        </motion.button>
        <motion.a whileTap={{ scale: 0.97 }} href="tel:112" className="flex h-20 items-center justify-center gap-3 rounded-xl bg-secondary text-headline-md text-on-secondary shadow-lg"><Icon name="phone_in_talk" size={36} />{t('home.call112')}</motion.a>
      </div>
      <p className="text-center text-body-md text-on-surface-variant">{t('alert.safeCount', { n: alert.safe_count })}</p>
      <div className="flex justify-center"><AudioButton text={home.speech} labelStart={t('home.audioStart')} labelStop={t('home.audioStop')} /></div>
      <Toast message={toast} />
    </Page>
  )
}
