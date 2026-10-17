import { motion } from 'framer-motion'
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import Icon from '../components/Icon.jsx'
import { MarketArt, MiniMap, Valley } from '../components/art.jsx'
import Countdown, { useCountdown } from '../components/Countdown.jsx'
import { ErrorBox, Loading, Page, fadeUp, stagger } from '../components/ui.jsx'
import { telHref } from '../lib/format.js'
import { useI18n } from '../lib/i18n.jsx'
import { usePortal } from '../lib/portal.jsx'
import { canSpeak, speak, stopSpeaking } from '../lib/speech.js'

export const WEATHER_ICON = {
  clear: 'wb_sunny', partly_cloudy: 'partly_cloudy_day', cloudy: 'cloud', fog: 'foggy',
  rain: 'rainy', snow: 'ac_unit', storm: 'thunderstorm',
}

const TONES = {
  calm: { box: 'bg-primary-fixed/30', icon: 'verified_user', iconBox: 'bg-primary text-on-primary', pill: 'bg-primary text-on-primary', title: 'text-primary' },
  watch: { box: 'bg-warn-container', icon: 'info', iconBox: 'bg-warn text-white', pill: 'bg-warn text-white', title: 'text-warn' },
  danger: { box: 'bg-secondary-fixed', icon: 'warning', iconBox: 'bg-secondary text-on-secondary', pill: 'bg-secondary text-on-secondary', title: 'text-secondary' },
}

export function AudioButton({ text, labelStart, labelStop }) {
  const { lang } = useI18n()
  const [on, setOn] = useState(false)
  useEffect(() => stopSpeaking, [])
  const toggle = () => {
    if (on) { stopSpeaking(); setOn(false); return }
    if (speak(text, lang, { onEnd: () => setOn(false) })) setOn(true)
  }
  return (
    <motion.button whileTap={{ scale: 0.95 }} type="button" onClick={toggle} disabled={!canSpeak() || !text}
      className="flex h-16 w-full shrink-0 items-center justify-center gap-3 rounded-xl bg-primary px-space-lg text-label-xl text-on-primary shadow-md hover:bg-primary-container disabled:opacity-50 md:w-auto">
      <Icon name={on ? 'stop_circle' : 'play_circle'} size={32} />
      <span>{on ? labelStop : labelStart}</span>
    </motion.button>
  )
}

export default function Home() {
  const { t } = useI18n()
  const { home, error, refresh } = usePortal()
  const alert = home?.status?.primary_alert
  const secs = useCountdown(alert?.eta_seconds_remaining ?? null)

  if (!home) return <Page className="mx-auto max-w-7xl px-4 py-space-lg lg:px-12">{error ? <ErrorBox onRetry={refresh} /> : <Loading />}</Page>

  const { village, status, weather, roads, shelters, market, announcement, contacts } = home
  const tone = TONES[status.tone]
  const road = roads.items[0]

  return (
    <Page className="mx-auto flex max-w-7xl flex-col gap-space-lg px-4 py-space-lg lg:px-12">
      {/* big status */}
      <motion.section variants={fadeUp} initial="hidden" animate="show"
        className={`flex flex-col items-stretch justify-between gap-space-md rounded-xl p-space-md shadow-sm sm:p-space-lg xl:flex-row xl:items-center ${tone.box}`}>
        <div className="flex min-w-0 items-center gap-space-md">
          <motion.div animate={status.tone === 'calm' ? {} : { scale: [1, 1.1, 1] }} transition={{ repeat: Infinity, duration: 1.2 }}
            className={`flex h-20 w-20 shrink-0 items-center justify-center rounded-xl shadow-sm ${tone.iconBox}`}>
            <Icon name={tone.icon} fill size={48} />
          </motion.div>
          <div className="flex min-w-0 flex-col gap-1">
            <div className="flex flex-wrap items-center gap-space-xs">
              <span className={`rounded-full px-3 py-1 text-label-md uppercase tracking-wider ${tone.pill}`}>{t(`home.pill.${status.tone}`)}</span>
              <span className="text-body-md font-bold text-on-surface-variant">• {village.valley}, {village.name}</span>
            </div>
            <h1 className={`text-headline-lg font-extrabold ${tone.title}`}>{status.headline}</h1>
            <p className="text-body-md text-on-surface-variant">{status.subline}</p>
            {alert && (
              <Link to="/alert" className="mt-2 flex w-fit items-center gap-3 rounded-lg bg-secondary px-4 py-3 text-on-secondary">
                {secs != null && <span className="text-headline-md"><Countdown seconds={secs} /></span>}
                <span className="text-label-lg">{t('home.openAlert')}</span><Icon name="arrow_forward" />
              </Link>
            )}
          </div>
        </div>
        <div className="flex shrink-0 flex-wrap items-center gap-space-sm rounded-xl bg-surface-container-lowest p-space-sm shadow-sm">
          {road && (
            <div className="flex items-center gap-space-xs rounded-lg bg-surface-container-low px-space-sm py-2">
              <Icon name="directions_car" size={32} className={road.status === 'open' ? 'text-primary' : 'text-secondary'} />
              <div className="flex flex-col">
                <span className="text-label-md text-on-surface-variant">{road.name}</span>
                <span className={`text-label-lg ${road.status === 'open' ? 'text-primary' : 'text-secondary'}`}>{road.label}</span>
              </div>
            </div>
          )}
          {weather && (
            <div className="flex items-center gap-space-xs rounded-lg bg-surface-container-low px-space-sm py-2">
              <Icon name={WEATHER_ICON[weather.condition] || 'wb_sunny'} size={32} className="text-tertiary" />
              <div className="flex flex-col">
                <span className="text-label-md text-on-surface-variant">{t('home.weather')}</span>
                <span className="text-label-lg">{weather.temp_c > 0 ? '+' : ''}{weather.temp_c}°C {weather.label}</span>
              </div>
            </div>
          )}
        </div>
      </motion.section>

      {/* audio assist */}
      <motion.section variants={fadeUp} initial="hidden" animate="show"
        className="flex flex-col items-center justify-between gap-space-md rounded-xl bg-surface-container-low p-space-md shadow-sm md:flex-row">
        <div className="flex items-center gap-space-md">
          <div className="flex h-16 w-16 shrink-0 items-center justify-center rounded-xl bg-tertiary-container text-on-tertiary"><Icon name="volume_up" size={36} /></div>
          <div className="flex flex-col">
            <span className="text-headline-md">{t('home.audioTitle')}</span>
            <span className="text-body-lg text-on-surface-variant">{t('home.audioSub')}</span>
          </div>
        </div>
        <AudioButton text={home.speech} labelStart={t('home.audioStart')} labelStop={t('home.audioStop')} />
      </motion.section>

      {/* two huge cards */}
      <motion.section variants={stagger} initial="hidden" animate="show" className="grid grid-cols-1 gap-space-lg lg:grid-cols-2">
        {[
          { to: '/map', icon: 'shield', badge: t('home.mapBadge'), title: t('home.mapTitle'), text: t('home.mapText'), art: <MiniMap className="h-full w-full" />,
            caption: t('home.shelters', { n: shelters.count }), capIcon: 'place', cta: t('home.mapCta'), ctaIcon: 'map' },
          { to: '/market', icon: 'storefront', badge: t('home.marketBadge', { n: market.new_count }), title: t('home.marketTitle'), text: t('home.marketText'), art: <MarketArt className="h-full w-full" />,
            caption: t('home.marketCaption'), capIcon: 'payments', cta: t('home.marketCta'), ctaIcon: 'shopping_basket' },
        ].map((c) => (
          <motion.article key={c.to} variants={fadeUp} whileHover={{ y: -4 }} className="flex flex-col justify-between gap-space-lg rounded-xl bg-surface-container-lowest p-space-lg shadow-sm">
            <div className="flex flex-col gap-space-sm">
              <div className="flex items-center justify-between">
                <div className="flex h-16 w-16 items-center justify-center rounded-xl bg-primary-fixed text-on-primary-fixed"><Icon name={c.icon} size={36} /></div>
                <span className="rounded-full bg-primary-fixed/40 px-4 py-1.5 text-label-md text-primary">{c.badge}</span>
              </div>
              <h2 className="mt-2 text-headline-xl font-extrabold">{c.title}</h2>
              <p className="text-body-lg leading-relaxed text-on-surface-variant">{c.text}</p>
              <div className="relative mt-2 h-44 w-full overflow-hidden rounded-xl shadow-inner">
                {c.art}
                <div className="absolute inset-0 flex items-end bg-gradient-to-t from-on-surface/70 via-transparent to-transparent p-4">
                  <span className="flex items-center gap-2 text-label-lg text-white"><Icon name={c.capIcon} size={24} className="text-primary-fixed" />{c.caption}</span>
                </div>
              </div>
            </div>
            <Link to={c.to}>
              <motion.span whileTap={{ scale: 0.98 }} className="flex h-20 w-full items-center justify-center gap-space-sm rounded-xl bg-primary text-label-xl text-on-primary shadow-md hover:bg-primary-container">
                <Icon name={c.ctaIcon} size={36} /><span>{c.cta}</span>
              </motion.span>
            </Link>
          </motion.article>
        ))}
      </motion.section>

      {/* valley + announcement */}
      <motion.section variants={fadeUp} initial="hidden" whileInView="show" viewport={{ once: true }}
        className="flex w-full flex-col overflow-hidden rounded-xl bg-surface-container-lowest shadow-sm xl:flex-row">
        <div className="relative h-64 w-full xl:h-auto xl:w-5/12">
          <Valley className="absolute inset-0 h-full w-full" />
          <div className="absolute left-4 top-4 rounded-lg bg-on-surface/80 px-4 py-2 text-label-lg text-white backdrop-blur-sm">
            {village.name} • {village.elevation_m?.toLocaleString('ru-RU')} {t('common.m')}
          </div>
        </div>
        <div className="flex w-full flex-col justify-between gap-space-md p-space-lg xl:w-7/12">
          {announcement && (
            <div className="flex flex-col gap-2">
              <div className="flex items-center gap-2 text-label-lg text-primary"><Icon name="notifications_active" size={28} /><span>{announcement.source}</span></div>
              <h3 className="text-headline-lg font-extrabold">{announcement.title}</h3>
              <p className="text-body-lg text-on-surface-variant">{announcement.body}</p>
            </div>
          )}
          <div className="grid grid-cols-1 gap-space-sm sm:grid-cols-3">
            {contacts.community.map((c) => (
              <a key={c.role} href={telHref(c.phone)} className="flex flex-col rounded-xl bg-surface-container-low p-4 hover:bg-surface-container">
                <span className="text-label-md text-on-surface-variant">{t(`role.${c.role}`)}</span>
                <span className="text-label-lg">{c.name}</span>
                <span className="text-body-md font-bold text-primary">{c.phone_display}</span>
              </a>
            ))}
          </div>
        </div>
      </motion.section>

      {/* emergency bar */}
      <motion.section variants={fadeUp} initial="hidden" whileInView="show" viewport={{ once: true }}
        className="flex w-full flex-col items-center justify-between gap-space-md rounded-xl bg-secondary-fixed p-space-md shadow-md sm:p-space-lg md:flex-row">
        <div className="flex items-center gap-space-md text-center md:text-left">
          <motion.div animate={{ scale: [1, 1.08, 1] }} transition={{ repeat: Infinity, duration: 1.6 }}
            className="flex h-20 w-20 shrink-0 items-center justify-center rounded-full bg-secondary text-on-secondary shadow-md"><Icon name="emergency" size={44} /></motion.div>
          <div className="flex flex-col">
            <span className="text-headline-md font-extrabold text-on-secondary-fixed">{t('home.emergencyTitle')}</span>
            <span className="text-body-lg font-medium text-on-secondary-fixed-variant">{t('home.emergencyText')}</span>
          </div>
        </div>
        <motion.a whileTap={{ scale: 0.95 }} href="tel:112" className="flex h-20 w-full shrink-0 items-center justify-center gap-4 rounded-xl bg-secondary px-8 text-label-xl text-on-secondary shadow-lg hover:bg-secondary-container md:w-auto">
          <Icon name="phone_in_talk" size={40} />
          <div className="flex flex-col text-left"><span className="text-headline-md leading-none">{t('home.call112')}</span><span className="text-label-md leading-tight opacity-90">{t('home.call112Sub')}</span></div>
        </motion.a>
      </motion.section>
    </Page>
  )
}
