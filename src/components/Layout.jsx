import { AnimatePresence, LayoutGroup, motion } from 'framer-motion'
import { Link, NavLink, Outlet, useLocation } from 'react-router-dom'
import Icon from './Icon.jsx'
import Countdown, { useCountdown } from './Countdown.jsx'
import { useAuth } from '../lib/auth.jsx'
import { useI18n } from '../lib/i18n.jsx'
import { usePortal } from '../lib/portal.jsx'

const NAV = [
  { to: '/', key: 'nav.home', icon: 'home' },
  { to: '/map', key: 'nav.map', icon: 'shield' },
  { to: '/market', key: 'nav.market', icon: 'storefront' },
  { to: '/sell', key: 'nav.sell', icon: 'add_circle' },
  { to: '/help', key: 'nav.help', icon: 'help' },
]

function Header() {
  const { t, lang, setLang } = useI18n()
  const { home } = usePortal()
  const { user } = useAuth()
  const { pathname } = useLocation()
  const village = home?.village
  return (
    <header className="fixed top-0 z-50 w-full bg-surface-container-lowest shadow-[0_1px_8px_rgba(0,0,0,0.06)]">
      <div className="mx-auto flex h-20 max-w-7xl items-center justify-between gap-space-sm px-4 lg:px-12">
        <div className="flex items-center gap-space-md">
          <Link to="/" className="flex items-center gap-space-xs">
            <motion.div whileHover={{ rotate: -6, scale: 1.05 }} className="flex h-12 w-12 items-center justify-center rounded-xl bg-primary-container text-on-primary">
              <Icon name="landscape" size={28} />
            </motion.div>
            <div className="flex flex-col">
              <span className="text-headline-md leading-none text-primary">{t('brand.name')}</span>
              <span className="mt-1 hidden text-label-md leading-none text-on-surface-variant sm:block">{t('brand.tagline')}</span>
            </div>
          </Link>
          {village && (
            <div className="hidden items-center gap-2 pl-space-md xl:flex">
              <Icon name="location_on" size={24} className="text-primary" />
              <div className="flex flex-col">
                <span className="text-label-md leading-tight text-on-surface">{village.name}</span>
                <span className="text-body-md leading-tight text-on-surface-variant">{village.valley}</span>
              </div>
            </div>
          )}
        </div>

        <LayoutGroup id="nav">
          <nav className="hidden items-center gap-2 lg:flex" aria-label="main">
            {NAV.map((n) => {
              const active = n.to === '/' ? pathname === '/' : pathname.startsWith(n.to)
              return (
                <NavLink key={n.to} to={n.to} end={n.to === '/'}
                  className={`relative rounded-lg px-space-sm py-2 text-label-lg transition-colors ${active ? 'text-primary' : 'text-on-surface-variant hover:bg-surface-container hover:text-on-surface'}`}>
                  {active && <motion.span layoutId="navpill" className="absolute inset-0 -z-0 rounded-lg bg-surface-container-low" transition={{ type: 'spring', stiffness: 380, damping: 30 }} />}
                  <span className="relative">{t(n.key)}</span>
                </NavLink>
              )
            })}
          </nav>
        </LayoutGroup>

        <div className="flex items-center gap-space-xs sm:gap-space-sm">
          <div className="flex items-center rounded-lg bg-surface-container p-1" role="group" aria-label="language">
            {[['ky', 'КЫРГ'], ['ru', 'РУС']].map(([code, label]) => (
              <button key={code} type="button" onClick={() => setLang(code)}
                className={`rounded-lg px-2.5 py-1.5 text-label-md sm:px-3 ${lang === code ? 'bg-surface-container-lowest font-bold text-on-surface shadow-sm' : 'text-on-surface-variant'}`}>
                {label}
              </button>
            ))}
          </div>
          <motion.a whileTap={{ scale: 0.94 }} href="tel:112"
            className="flex h-14 items-center gap-2 rounded-lg bg-secondary px-4 text-label-xl text-on-secondary hover:bg-secondary-container sm:px-5">
            <Icon name="e911_emergency" size={26} /><span>112</span>
          </motion.a>
          <Link to={user ? '/me' : '/login'} aria-label={user ? t('nav.profile') : t('nav.login')}
            className="flex h-11 w-11 items-center justify-center rounded-full bg-primary text-on-primary">
            {user ? <span className="text-label-lg">{(user.name || user.phone).trim().charAt(0).toUpperCase()}</span> : <Icon name="person" size={24} />}
          </Link>
        </div>
      </div>
    </header>
  )
}

function AlertBar() {
  const { t } = useI18n()
  const { home } = usePortal()
  const alert = home?.status?.primary_alert
  const secs = useCountdown(alert?.eta_seconds_remaining ?? null)
  const tone = home?.status?.tone
  const show = tone && tone !== 'calm'
  return (
    <AnimatePresence>
      {show && (
        <motion.div
          initial={{ height: 0, opacity: 0 }} animate={{ height: 'auto', opacity: 1 }} exit={{ height: 0, opacity: 0 }}
          className={`overflow-hidden ${tone === 'danger' ? 'bg-secondary text-on-secondary' : 'bg-warn-container text-warn'}`}
        >
          <Link to="/alert" className="mx-auto flex max-w-7xl flex-wrap items-center gap-3 px-4 py-3 lg:px-12">
            <motion.span animate={{ scale: [1, 1.2, 1] }} transition={{ repeat: Infinity, duration: 1.1 }} className="inline-flex">
              <Icon name={tone === 'danger' ? 'warning' : 'info'} fill size={32} />
            </motion.span>
            <span className="min-w-0 flex-1 text-label-lg">{home.status.headline}</span>
            {secs != null && <span className="text-headline-md"><Countdown seconds={secs} /></span>}
            <span className="flex items-center gap-1 rounded-lg bg-white/25 px-3 py-2 text-label-md">{t('alertbar.open')}<Icon name="arrow_forward" size={20} /></span>
          </Link>
        </motion.div>
      )}
    </AnimatePresence>
  )
}

function BottomNav() {
  const { t } = useI18n()
  const { pathname } = useLocation()
  return (
    <nav className="fixed bottom-0 left-0 right-0 z-50 border-t border-outline-variant bg-surface-container-lowest lg:hidden" aria-label="main">
      <ul className="mx-auto grid max-w-xl grid-cols-5">
        {NAV.map((n) => {
          const active = n.to === '/' ? pathname === '/' : pathname.startsWith(n.to)
          return (
            <li key={n.to}>
              <Link to={n.to} className={`relative flex h-[68px] flex-col items-center justify-center gap-0.5 ${active ? 'text-primary' : 'text-on-surface-variant'}`}>
                {active && <motion.span layoutId="bnav" className="absolute top-0 h-1 w-10 rounded-b bg-primary" />}
                <Icon name={n.icon} fill={active} size={28} />
                <span className="text-[13px] font-bold leading-none">{t(n.key)}</span>
              </Link>
            </li>
          )
        })}
      </ul>
    </nav>
  )
}

function Footer() {
  const { t } = useI18n()
  const { home } = usePortal()
  const support = home?.contacts?.support
  return (
    <footer className="w-full bg-surface-container-lowest py-space-xl pb-28 shadow-[0_-1px_8px_rgba(0,0,0,0.04)] lg:pb-space-xl">
      <div className="mx-auto flex max-w-7xl flex-col items-center justify-between gap-space-md px-6 md:flex-row lg:px-12">
        <div className="flex flex-col gap-1 text-center md:text-left">
          <span className="text-headline-md text-primary">{t('footer.title')}</span>
          <span className="text-body-md text-on-surface-variant">{t('footer.sub')}</span>
        </div>
        <div className="flex flex-wrap items-center justify-center gap-space-md text-label-md text-on-surface-variant">
          <span className="flex items-center gap-1 text-on-surface"><Icon name="verified" size={20} className="text-primary" />{t('footer.code112')}</span>
          {support && <span>{t('footer.hub')}: {support.phone_display}</span>}
        </div>
      </div>
    </footer>
  )
}

export default function Layout() {
  const { pathname } = useLocation()
  return (
    <div className="min-h-screen bg-surface">
      <Header />
      <main className="w-full pt-20">
        <AlertBar />
        <AnimatePresence mode="wait">
          <Outlet key={pathname} />
        </AnimatePresence>
      </main>
      <Footer />
      <BottomNav />
    </div>
  )
}
