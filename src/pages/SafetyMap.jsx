import { AnimatePresence, motion } from 'framer-motion'
import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import Icon from '../components/Icon.jsx'
import { ErrorBox, Loading, Modal, Page, Toast, fadeUp, stagger } from '../components/ui.jsx'
import { AudioButton, WEATHER_ICON } from './Home.jsx'
import { api, errorText } from '../lib/api.js'
import { useAuth } from '../lib/auth.jsx'
import { clock, telHref } from '../lib/format.js'
import { useI18n } from '../lib/i18n.jsx'

const W = 700
const H = 740

/** lat/lon -> picture coordinates, same scale on both axes so the village is not stretched. */
function makeProject(b) {
  const lat0 = (b.north + b.south) / 2
  const kx = Math.cos((lat0 * Math.PI) / 180) * 111320
  const ky = 111320
  const w = (b.east - b.west) * kx
  const h = (b.north - b.south) * ky
  const s = Math.min((W - 40) / w, (H - 40) / h)
  const ox = (W - w * s) / 2
  const oy = (H - h * s) / 2
  return (lat, lon) => [ox + (lon - b.west) * kx * s, oy + (b.north - lat) * ky * s]
}

const pts = (project, list) => list.map(([lat, lon]) => project(lat, lon).map((n) => n.toFixed(1)).join(',')).join(' ')
const dist = (m) => (m >= 1000 ? `${(m / 1000).toFixed(1)} км` : `${m} м`)

const REPORT_TYPES = [
  { type: 'mudflow', icon: 'tsunami', color: 'text-secondary', key: 'report.flood' },
  { type: 'rockfall', icon: 'landslide', color: 'text-on-surface-variant', key: 'report.rockfall' },
  { type: 'avalanche', icon: 'ac_unit', color: 'text-primary', key: 'report.avalanche' },
  { type: 'fire', icon: 'local_fire_department', color: 'text-secondary', key: 'report.fire' },
]

export function ReportModal({ open, onClose, origin, onDone }) {
  const { t } = useI18n()
  const { user } = useAuth()
  const navigate = useNavigate()
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState('')

  const send = async (type) => {
    setBusy(true); setErr('')
    try {
      let { lat, lon } = origin
      if (navigator.geolocation) {
        try {
          const pos = await new Promise((res, rej) => navigator.geolocation.getCurrentPosition(res, rej, { timeout: 4000 }))
          lat = pos.coords.latitude; lon = pos.coords.longitude
        } catch { /* use the saved home / village centre */ }
      }
      await api.post('/reports/', { type, lat, lon })
      onClose(); onDone(t('report.sent'))
    } catch (e) {
      setErr(errorText(e, t('common.error')))
    } finally { setBusy(false) }
  }

  return (
    <Modal open={open} onClose={onClose} label={t('report.title')}>
      <div className="flex flex-col gap-space-md">
        <div className="mx-auto flex h-20 w-20 items-center justify-center rounded-full bg-error-container text-error"><Icon name="warning" size={48} /></div>
        <div className="text-center">
          <h3 className="text-headline-lg">{t('report.title')}</h3>
          <p className="text-body-lg text-on-surface-variant">{t('report.question')}</p>
        </div>
        {!user ? (
          <div className="flex flex-col gap-3 text-center">
            <p className="text-body-lg">{t('report.needLogin')}</p>
            <button type="button" onClick={() => navigate('/login?next=/map')} className="h-16 rounded-lg bg-primary text-label-xl text-on-primary">{t('nav.login')}</button>
          </div>
        ) : (
          <div className="flex flex-col gap-space-xs">
            {REPORT_TYPES.map((r, i) => (
              <motion.button key={r.type} type="button" disabled={busy} onClick={() => send(r.type)}
                initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0, transition: { delay: 0.05 * i } }} whileTap={{ scale: 0.97 }}
                className="flex h-16 items-center gap-space-sm rounded-lg bg-surface-container px-space-md text-left text-label-xl hover:bg-surface-container-high disabled:opacity-50">
                <Icon name={r.icon} size={32} className={r.color} /><span>{t(r.key)}</span>
              </motion.button>
            ))}
          </div>
        )}
        {err && <p className="rounded-lg bg-error-container p-3 text-center text-on-error-container">{err}</p>}
        <button type="button" onClick={onClose} className="h-16 rounded-lg bg-surface-container-highest text-label-xl">{t('common.cancel')}</button>
      </div>
    </Modal>
  )
}

export default function SafetyMap() {
  const { t, lang } = useI18n()
  const [data, setData] = useState(null)
  const [error, setError] = useState(false)
  const [selected, setSelected] = useState(null)
  const [zoom, setZoom] = useState(1)
  const [showSteps, setShowSteps] = useState(false)
  const [pulse, setPulse] = useState(0)
  const [reportOpen, setReportOpen] = useState(false)
  const [toast, setToast] = useState('')

  const load = useCallback(async () => {
    try { setData(await api.get('/portal/map/')); setError(false) } catch { setError(true) }
  }, [])
  useEffect(() => {
    load()
    const id = setInterval(load, 15000)
    return () => clearInterval(id)
  }, [load, lang])
  useEffect(() => { if (!toast) return undefined; const id = setTimeout(() => setToast(''), 4000); return () => clearTimeout(id) }, [toast])

  const project = useMemo(() => (data ? makeProject(data.bounds) : null), [data])
  if (!data) return <Page className="mx-auto max-w-7xl px-4 py-space-lg lg:px-12">{error ? <ErrorBox onRetry={load} /> : <Loading />}</Page>

  const { status, weather, shelters, zones, routes, buildings, river, roads, home, village } = data
  const shelter = shelters.find((s) => s.id === selected) || shelters[0]
  const route = routes.find((r) => r.point === shelter?.id)
  const toneBox = { calm: 'bg-on-primary-container text-on-primary-fixed', watch: 'bg-warn-container text-warn', danger: 'bg-secondary-fixed text-on-secondary-fixed' }[status.tone]
  const toneIcon = { calm: ['check_circle', 'bg-primary'], watch: ['info', 'bg-warn'], danger: ['warning', 'bg-secondary'] }[status.tone]
  const xy = (lat, lon) => project(lat, lon)
  const pct = ([x, y]) => ({ left: `${(x / W) * 100}%`, top: `${(y / H) * 100}%` })
  const homeXY = home ? xy(home.lat, home.lon) : null
  const shelterXY = shelter ? xy(shelter.lat, shelter.lon) : null
  const routePath = route ? pts(project, route.path)
    : homeXY && shelterXY ? `${homeXY.join(',')} ${shelterXY.join(',')}` : ''
  const danger = zones.find((z) => z.kind === 'danger')
  const dangerXY = danger ? (() => { const [la, lo] = danger.polygon[Math.floor(danger.polygon.length * 0.3)]; return xy(la, lo) })() : null

  return (
    <Page className="mx-auto w-full max-w-7xl px-4 py-space-lg lg:px-12">
      <div className="mb-space-md flex flex-wrap items-center justify-between gap-space-sm">
        <div className="flex flex-wrap items-center gap-2">
          <span className={`h-3 w-3 animate-pulse rounded-full ${status.tone === 'calm' ? 'bg-primary' : 'bg-secondary'}`} />
          <span className="text-label-lg uppercase tracking-wide text-primary">{t('map.live')}: {village.valley}</span>
          <span className="font-bold text-on-surface-variant">•</span>
          <span className="text-body-md text-on-surface-variant">{t('map.service')}</span>
        </div>
        <AudioButton text={data.speech} labelStart={t('map.listen')} labelStop={t('home.audioStop')} />
      </div>

      <div className="grid grid-cols-1 items-start gap-space-lg lg:grid-cols-12">
        {/* LEFT */}
        <motion.div variants={stagger} initial="hidden" animate="show" className="flex flex-col gap-space-md lg:col-span-5">
          <motion.div variants={fadeUp} className={`rounded-xl p-space-md shadow-md ${toneBox}`}>
            <div className="flex items-start gap-space-sm">
              <div className={`flex h-16 w-16 shrink-0 items-center justify-center rounded-xl text-white shadow-sm ${toneIcon[1]}`}><Icon name={toneIcon[0]} fill size={36} /></div>
              <div className="flex flex-col">
                <span className="text-label-md uppercase tracking-wider opacity-80">{t('map.current')}</span>
                <h1 className="mt-1 text-headline-lg">{status.map_headline}</h1>
              </div>
            </div>
            <div className="mt-space-sm flex items-center justify-between pt-space-xs opacity-90">
              {weather ? <span className="flex items-center gap-1 text-body-md"><Icon name={WEATHER_ICON[weather.condition] || 'wb_sunny'} size={20} />{t('home.weather')}: {weather.temp_c > 0 ? '+' : ''}{weather.temp_c}°C, {weather.label}</span> : <span />}
              <span className="text-label-md">{t('map.updated')}: {clock(status.updated_at, lang)}</span>
            </div>
            {status.primary_alert && (
              <Link to="/alert" className="mt-3 flex h-14 items-center justify-center gap-2 rounded-lg bg-secondary text-label-xl text-on-secondary"><Icon name="arrow_forward" />{t('home.openAlert')}</Link>
            )}
          </motion.div>

          {shelter && (
            <motion.div variants={fadeUp} className="flex flex-col gap-space-sm rounded-xl bg-surface-container-lowest p-space-md shadow-md">
              <div className="flex items-center justify-between">
                <span className="rounded-full bg-surface-container px-3 py-1 text-label-md text-primary">{t('map.shelterTag')}</span>
                <span className="flex items-center gap-1 text-label-md text-on-surface-variant"><Icon name="navigation" size={18} className="text-primary" />{dist(shelter.distance_m)}</span>
              </div>
              <AnimatePresence mode="wait">
                <motion.div key={shelter.id} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}>
                  <h2 className="text-headline-md">{shelter.is_primary ? t('map.mainShelter') : t('map.shelter')}: {shelter.name}</h2>
                  <p className="mt-1 text-body-lg text-on-surface-variant">{t('map.walk')}: <strong className="text-primary">{shelter.walk_minutes} {t('common.min')}</strong>{shelter.notes ? ` (${shelter.notes})` : ''}</p>
                </motion.div>
              </AnimatePresence>
              {(shelter.has_clinic || shelter.has_water) && (
                <div className="grid grid-cols-2 gap-space-xs rounded-lg bg-surface-container-low p-space-xs">
                  {shelter.has_clinic && <div className="flex items-center gap-2 rounded bg-surface-container-lowest p-2"><Icon name="local_hospital" size={24} className="text-primary" /><div className="flex flex-col"><span className="text-label-md">{t('map.clinic')}</span><span className="text-body-md text-on-surface-variant">{t('map.doctor')}</span></div></div>}
                  {shelter.has_water && <div className="flex items-center gap-2 rounded bg-surface-container-lowest p-2"><Icon name="water_drop" size={24} className="text-primary" /><div className="flex flex-col"><span className="text-label-md">{t('map.water')}</span><span className="text-body-md text-on-surface-variant">{t('map.tank')}</span></div></div>}
                </div>
              )}
              {shelters.length > 1 && (
                <div className="flex flex-wrap gap-2">
                  {shelters.map((s) => (
                    <button key={s.id} type="button" onClick={() => setSelected(s.id)}
                      className={`rounded-full px-3 py-2 text-label-md ${s.id === shelter.id ? 'bg-primary text-on-primary' : 'bg-surface-container text-on-surface'}`}>{s.name} · {dist(s.distance_m)}</button>
                  ))}
                </div>
              )}
              <motion.button whileTap={{ scale: 0.97 }} type="button" onClick={() => { setPulse((p) => p + 1); setShowSteps(true) }}
                className="flex h-16 w-full items-center justify-center gap-space-xs rounded-xl bg-primary text-label-xl text-on-primary shadow-md hover:bg-on-primary-fixed-variant">
                <Icon name="directions_walk" size={30} /><span>{t('map.showRoute', { name: shelter.name })}</span>
              </motion.button>
              <AnimatePresence>
                {showSteps && (
                  <motion.p initial={{ height: 0, opacity: 0 }} animate={{ height: 'auto', opacity: 1 }} exit={{ height: 0, opacity: 0 }}
                    className="overflow-hidden rounded-lg bg-primary-fixed/30 p-3 text-body-lg">{t('map.routeText', { name: shelter.name, dist: dist(shelter.distance_m) })}</motion.p>
                )}
              </AnimatePresence>
            </motion.div>
          )}

          <motion.div variants={fadeUp} className="rounded-xl bg-surface-container-low p-space-md shadow-sm">
            <h3 className="mb-space-sm flex items-center gap-2 text-headline-md"><Icon name="info" size={26} className="text-primary" />{t('map.legend')}</h3>
            <div className="flex flex-col gap-space-xs">
              {[
                ['bg-primary text-on-primary', 'check', t('map.legendSafe'), t('map.legendSafeText'), ''],
                ['bg-error text-on-error', 'warning', t('map.legendDanger'), t('map.legendDangerText'), 'text-error'],
                ['bg-surface-container-highest text-primary', 'person_pin_circle', t('map.legendYou'), t('map.legendYouText'), ''],
              ].map(([bg, icon, title, text, tc]) => (
                <div key={title} className="flex items-center gap-space-sm rounded-lg bg-surface-container-lowest p-3 shadow-sm">
                  <div className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-full ${bg}`}><Icon name={icon} fill size={24} /></div>
                  <div className="flex flex-col"><span className={`text-label-lg ${tc}`}>{title}</span><span className="text-body-md text-on-surface-variant">{text}</span></div>
                </div>
              ))}
            </div>
          </motion.div>

          <motion.button variants={fadeUp} whileTap={{ scale: 0.98 }} type="button" onClick={() => setReportOpen(true)}
            className="flex h-20 w-full items-center justify-center gap-space-sm rounded-xl bg-secondary text-headline-md text-on-secondary shadow-lg hover:bg-secondary-container">
            <motion.span animate={{ y: [0, -5, 0] }} transition={{ repeat: Infinity, duration: 1.1 }} className="inline-flex"><Icon name="campaign" size={36} /></motion.span>
            <span>{t('map.report')}</span>
          </motion.button>
        </motion.div>

        {/* RIGHT: the map */}
        <div className="flex flex-col lg:col-span-7">
          <div className="relative flex w-full flex-col justify-between overflow-hidden rounded-xl bg-surface-container-low p-space-md shadow-lg">
            <div className="relative mx-auto w-full" style={{ aspectRatio: `${W} / ${H}` }}>
              <motion.div className="absolute inset-0 origin-center" animate={{ scale: zoom }} transition={{ type: 'spring', stiffness: 160, damping: 22 }}>
                <svg className="h-full w-full" viewBox={`0 0 ${W} ${H}`} fill="none" role="img" aria-label={t('nav.map')}>
                  <defs>
                    <linearGradient id="safeG" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stopColor="#cbffc2" stopOpacity=".85" /><stop offset="1" stopColor="#88d982" stopOpacity=".45" /></linearGradient>
                    <linearGradient id="dangerG" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stopColor="#ffdad6" stopOpacity=".95" /><stop offset="1" stopColor="#ffb3ac" stopOpacity=".75" /></linearGradient>
                    <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse"><path d="M40 0H0V40" fill="none" stroke="#e5e2e1" strokeWidth="1" /></pattern>
                  </defs>
                  <rect width={W} height={H} fill="url(#grid)" />
                  <path d="M-20 120Q140 40 320 110T720 60V0H-20Z" fill="#eae7e7" />
                  {[[120, 60, 150, 110, 90, 110], [380, 40, 420, 110, 340, 110], [540, 50, 580, 100, 500, 100]].map((p, i) => <polygon key={i} points={`${p[0]},${p[1]} ${p[2]},${p[3]} ${p[4]},${p[5]}`} fill="#dcd9d9" opacity=".6" />)}
                  {zones.filter((z) => z.kind === 'safe').map((z) => <motion.polygon key={z.id} points={pts(project, z.polygon)} fill="url(#safeG)" initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.8 }} />)}
                  {zones.filter((z) => z.kind === 'danger').map((z) => (
                    <g key={z.id}>
                      <motion.polygon points={pts(project, z.polygon)} fill="url(#dangerG)" initial={{ opacity: 0 }} animate={{ opacity: [0.75, 1, 0.75] }} transition={{ repeat: Infinity, duration: 3.2 }} />
                      <polyline points={pts(project, z.polygon.slice(0, Math.ceil(z.polygon.length / 2)))} stroke="#ba1a1a" strokeWidth="4" strokeDasharray="10 8" fill="none" />
                    </g>
                  ))}
                  <path d="M40 320Q240 340 370 410T680 450" stroke="#fff" strokeWidth="20" strokeLinecap="round" />
                  <path d="M40 320Q240 340 370 410T680 450" stroke="#bfcaba" strokeWidth="6" strokeDasharray="12 12" strokeLinecap="round" />
                  {routePath && (
                    <g>
                      <motion.polyline key={`r${pulse}`} points={routePath} stroke="#0d631b" strokeLinecap="round" strokeLinejoin="round" fill="none"
                        initial={{ pathLength: 0, strokeWidth: 10 }} animate={{ pathLength: 1, strokeWidth: pulse ? [10, 18, 10] : 10 }} transition={{ duration: 1.4 }} />
                      <polyline points={routePath} stroke="#cbffc2" strokeWidth="4" strokeDasharray="8 8" strokeLinecap="round" fill="none" className="animate-pulse" />
                    </g>
                  )}
                  {buildings.map((b) => {
                    const [x, y] = xy(b.lat, b.lon)
                    const mine = home?.label && b.label === home.label
                    return <rect key={b.id} x={x - 20} y={y - 17} width="40" height="34" rx="4" fill={mine ? '#fff' : '#f0eded'} stroke={mine ? '#0d631b' : '#707a6c'} strokeWidth={mine ? 4 : 2} />
                  })}
                </svg>
              </motion.div>

              {/* markers sit above the zooming picture */}
              <motion.div className="pointer-events-none absolute inset-0 origin-center" animate={{ scale: zoom }} transition={{ type: 'spring', stiffness: 160, damping: 22 }}>
                {shelters.map((s) => {
                  const [x, y] = xy(s.lat, s.lon)
                  const isMain = s.id === shelter.id
                  return (
                    <button key={s.id} type="button" onClick={() => setSelected(s.id)} aria-label={s.name}
                      className="pointer-events-auto absolute flex -translate-x-1/2 -translate-y-full flex-col items-center" style={pct([x, y])}>
                      {isMain ? (
                        <motion.div animate={{ y: [0, -6, 0] }} transition={{ repeat: Infinity, duration: 1.4 }} className="flex flex-col items-center">
                          <span className="flex items-center gap-2 whitespace-nowrap rounded-xl bg-primary px-3 py-1.5 text-label-md text-white shadow-lg sm:text-label-xl sm:px-4 sm:py-2">
                            <Icon name="domain" fill size={24} />{s.name}
                          </span>
                          <span className="-mt-2 h-4 w-4 rotate-45 bg-primary" />
                        </motion.div>
                      ) : (
                        <span className="flex h-9 w-9 items-center justify-center rounded-full bg-primary-container text-white shadow-md"><Icon name={s.has_clinic ? 'local_hospital' : 'check'} fill size={20} /></span>
                      )}
                    </button>
                  )
                })}
                {homeXY && (
                  <div className="absolute flex -translate-x-1/2 -translate-y-1/2 flex-col items-center" style={pct(homeXY)}>
                    <span className="relative flex items-center justify-center">
                      <span className="absolute h-12 w-12 animate-ping rounded-full bg-secondary opacity-30" />
                      <span className="h-10 w-10 rounded-full bg-white p-1 shadow-lg"><span className="flex h-full w-full items-center justify-center rounded-full bg-secondary text-white"><Icon name="person" fill size={20} /></span></span>
                    </span>
                    <span className="mt-2 whitespace-nowrap rounded-xl bg-white px-3 py-1.5 text-label-md shadow-md">{t('map.you')}{home.label ? `: ${home.label}` : ''}</span>
                  </div>
                )}
                {dangerXY && (
                  <div className="absolute -translate-y-1/2" style={{ ...pct(dangerXY), transform: 'translate(-10%, -50%)' }}>
                    <span className="flex items-center gap-2 whitespace-nowrap rounded-lg bg-error-container px-3 py-2 text-label-md text-on-error-container shadow-sm"><Icon name="crisis_alert" size={22} className="text-error" />{t('map.dangerLabel')}</span>
                  </div>
                )}
              </motion.div>
            </div>

            {/* compass + zoom */}
            <div className="pointer-events-none absolute left-space-md top-space-md flex items-start justify-between right-space-md">
              <div className="pointer-events-auto flex items-center gap-3 rounded-xl bg-surface-container-lowest p-2 shadow-md sm:p-3">
                <div className="relative flex h-12 w-12 items-center justify-center rounded-full bg-surface-container sm:h-14 sm:w-14">
                  <Icon name="explore" size={30} className="text-primary" />
                  <span className="absolute top-0 text-[11px] font-black text-secondary">{t('map.n')}</span>
                  <span className="absolute bottom-0 text-[11px] font-bold">{t('map.s')}</span>
                  <span className="absolute right-0.5 text-[11px] font-bold">{t('map.e')}</span>
                  <span className="absolute left-0.5 text-[11px] font-bold">{t('map.w')}</span>
                </div>
                <div className="hidden flex-col sm:flex"><span className="text-label-lg leading-tight">{t('map.direction')}</span><span className="text-body-md text-on-surface-variant">{t('map.northUp')}</span></div>
              </div>
              <div className="pointer-events-auto flex flex-col gap-2 rounded-xl bg-surface-container-lowest p-1.5 shadow-md">
                {[['add', 0.2, t('map.zoomIn')], ['remove', -0.2, t('map.zoomOut')]].map(([icon, d, label]) => (
                  <motion.button key={icon} whileTap={{ scale: 0.9 }} type="button" aria-label={label} onClick={() => setZoom((z) => Math.min(1.6, Math.max(0.8, +(z + d).toFixed(2))))}
                    className="flex h-14 w-14 items-center justify-center rounded-lg bg-surface-container text-on-surface hover:bg-surface-container-high"><Icon name={icon} size={32} /></motion.button>
                ))}
              </div>
            </div>

            <div className="relative z-10 mt-space-md flex w-full flex-wrap items-center justify-between gap-space-sm rounded-xl bg-surface-container-lowest p-space-sm shadow-md">
              {river.level_m != null ? (
                <div className="flex items-center gap-3">
                  <span className={`h-4 w-4 rounded-full ${river.status === 'normal' ? 'bg-primary' : river.status === 'watch' ? 'bg-warn' : 'bg-secondary'}`} />
                  <span className="text-label-lg">{river.name}: <strong>{river.label} ({river.level_m} {t('common.m')})</strong></span>
                </div>
              ) : <span />}
              <div className="flex items-center gap-2 text-body-md text-on-surface-variant">
                <Icon name={roads.summary_status === 'open' ? 'check_circle' : 'report'} size={20} className={roads.summary_status === 'open' ? 'text-primary' : 'text-secondary'} />
                <span>{roads.summary}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="mt-space-lg grid grid-cols-1 gap-space-md pt-space-md md:grid-cols-3">
        {data.contacts.strip.map((c) => (
          <a key={c.role} href={telHref(c.phone)}
            className={`flex h-20 items-center gap-space-sm rounded-xl px-space-md shadow-md transition-colors ${c.role === 'emergency' ? 'bg-secondary text-on-secondary hover:bg-secondary-container' : 'bg-surface-container-lowest hover:bg-surface-container'}`}>
            <div className={`flex h-14 w-14 shrink-0 items-center justify-center rounded-xl ${c.role === 'emergency' ? 'bg-white/20' : 'bg-surface-container text-primary'}`}>
              <Icon name={c.role === 'head' ? 'call' : c.role === 'ambulance' ? 'medical_services' : 'e911_emergency'} size={32} className={c.role === 'ambulance' ? 'text-secondary' : ''} />
            </div>
            <div className="flex flex-col"><span className="text-body-md opacity-90">{c.name}</span><span className="text-label-xl">{c.phone_display}</span></div>
          </a>
        ))}
      </div>

      <ReportModal open={reportOpen} onClose={() => setReportOpen(false)} origin={{ lat: home?.lat ?? village.lat, lon: home?.lon ?? village.lon }} onDone={setToast} />
      <Toast message={toast} />
    </Page>
  )
}
