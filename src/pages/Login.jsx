import { AnimatePresence, motion } from 'framer-motion'
import { useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import Icon from '../components/Icon.jsx'
import { Page } from '../components/ui.jsx'
import { api, errorText } from '../lib/api.js'
import { useAuth } from '../lib/auth.jsx'
import { useI18n } from '../lib/i18n.jsx'

const DEMO = [['+996700000003', 'login.demoVillager'], ['+996700000002', 'login.demoRescuer'], ['+996700000004', 'login.demoBuyer']]

export default function Login() {
  const { t } = useI18n()
  const { login } = useAuth()
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const next = params.get('next') || '/'
  const [cfg, setCfg] = useState(null)
  const [step, setStep] = useState(1)
  const [phone, setPhone] = useState('')
  const [code, setCode] = useState('')
  const [name, setName] = useState('')
  const [sent, setSent] = useState(null)
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState('')

  useEffect(() => { api.get('/portal/config/').then(setCfg).catch(() => {}) }, [])
  const bot = cfg?.bot_username || 'JailoAppBot'

  const requestCode = async (e) => {
    e?.preventDefault()
    setBusy(true); setErr('')
    try {
      const r = await api.post('/auth/otp/request/', { phone })
      setSent(r); setStep(2)
    } catch (ex) { setErr(errorText(ex, t('common.error'))) } finally { setBusy(false) }
  }

  const verify = async (e) => {
    e?.preventDefault()
    setBusy(true); setErr('')
    try {
      const data = await api.post('/auth/otp/verify/', { phone, code: code.trim(), name: name.trim() })
      await login(data)
      navigate(next, { replace: true })
    } catch (ex) { setErr(errorText(ex, t('common.error'))) } finally { setBusy(false) }
  }

  return (
    <Page className="mx-auto flex w-full max-w-xl flex-col gap-space-md px-4 py-space-lg sm:py-space-xl">
      <div className="flex items-center gap-5 rounded-xl bg-surface-container-low p-6 shadow-sm">
        <motion.div initial={{ rotate: -12, scale: 0.8 }} animate={{ rotate: 0, scale: 1 }} transition={{ type: 'spring', stiffness: 200 }}
          className="flex h-16 w-16 shrink-0 items-center justify-center rounded-xl bg-primary text-on-primary"><Icon name="lock_open" size={36} /></motion.div>
        <div className="flex flex-col"><span className="text-headline-lg">{t('login.title')}</span><span className="text-body-lg text-on-surface-variant">{t('login.sub')}</span></div>
      </div>

      <AnimatePresence mode="wait">
        {step === 1 ? (
          <motion.form key="s1" onSubmit={requestCode} initial={{ opacity: 0, x: 30 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -30 }}
            className="flex flex-col gap-space-md rounded-xl bg-surface-container-lowest p-6 shadow-md sm:p-8">
            <label className="flex flex-col gap-2">
              <span className="text-headline-md">{t('login.phone')}</span>
              <input value={phone} onChange={(e) => setPhone(e.target.value)} inputMode="tel" autoComplete="tel" placeholder="0700 12 34 56" required
                className="h-20 rounded-xl bg-surface-container-low px-6 text-headline-lg tracking-wide outline-none focus:bg-surface-container" />
            </label>
            {err && <p className="rounded-lg bg-error-container p-3 text-on-error-container">{err}</p>}
            <motion.button whileTap={{ scale: 0.97 }} disabled={busy || phone.trim().length < 7} type="submit"
              className="flex h-[68px] items-center justify-center gap-3 rounded-xl bg-primary text-headline-md text-on-primary shadow-lg disabled:opacity-50"><Icon name="sms" size={32} />{t('login.getCode')}</motion.button>

            <div className="flex flex-col gap-3 rounded-xl bg-primary-fixed/30 p-4">
              <div className="flex items-center gap-2 text-label-lg text-primary"><Icon name="send" size={24} />{t('login.howTitle')}</div>
              <ol className="list-decimal space-y-1 pl-6 text-body-md">
                <li>{t('login.how1', { bot: `@${bot}` })}</li><li>{t('login.how2')}</li><li>{t('login.how3')}</li>
              </ol>
              <a href={`https://t.me/${bot}`} target="_blank" rel="noreferrer" className="flex h-14 items-center justify-center gap-2 rounded-lg bg-surface-container-lowest text-label-lg text-primary shadow-sm"><Icon name="open_in_new" size={22} />{t('login.openBot')}</a>
            </div>

            {cfg?.debug_codes && (
              <div className="flex flex-col gap-2 rounded-xl border-2 border-dashed border-outline-variant p-4">
                <span className="text-label-md text-on-surface-variant">{t('login.demoTitle')}</span>
                <div className="flex flex-wrap gap-2">
                  {DEMO.map(([ph, key]) => <button key={ph} type="button" onClick={() => setPhone(ph)} className="rounded-full bg-surface-container px-4 py-2 text-label-md hover:bg-surface-container-high">{t(key)}</button>)}
                </div>
              </div>
            )}
          </motion.form>
        ) : (
          <motion.form key="s2" onSubmit={verify} initial={{ opacity: 0, x: 30 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -30 }}
            className="flex flex-col gap-space-md rounded-xl bg-surface-container-lowest p-6 shadow-md sm:p-8">
            <p className="text-body-lg">
              {sent?.channel === 'telegram' ? t('login.sentTelegram') : sent?.channel === 'dev' ? t('login.sentDev') : t('login.sentNone', { bot: `@${bot}` })}
            </p>
            {sent?.dev_code && (
              <button type="button" onClick={() => setCode(String(sent.dev_code))} className="flex items-center justify-between rounded-xl bg-warn-container p-4 text-warn">
                <span className="text-label-md">{t('login.devCode')}</span><span className="text-headline-lg tracking-[0.3em]">{sent.dev_code}</span>
              </button>
            )}
            <label className="flex flex-col gap-2">
              <span className="text-headline-md">{t('login.code')}</span>
              <input value={code} onChange={(e) => setCode(e.target.value.replace(/\D/g, ''))} inputMode="numeric" autoComplete="one-time-code" maxLength={8} required autoFocus
                className="h-24 rounded-xl bg-surface-container-low px-6 text-center text-[44px] font-extrabold tracking-[0.35em] outline-none focus:bg-surface-container" />
            </label>
            <label className="flex flex-col gap-2">
              <span className="text-label-lg text-on-surface-variant">{t('login.yourName')}</span>
              <input value={name} onChange={(e) => setName(e.target.value)} maxLength={80} className="h-16 rounded-xl bg-surface-container-low px-5 text-body-lg outline-none focus:bg-surface-container" />
            </label>
            {err && <p className="rounded-lg bg-error-container p-3 text-on-error-container">{err}</p>}
            <motion.button whileTap={{ scale: 0.97 }} disabled={busy || code.length < 4} type="submit"
              className="flex h-[68px] items-center justify-center gap-3 rounded-xl bg-primary text-headline-md text-on-primary shadow-lg disabled:opacity-50"><Icon name="login" size={32} />{t('login.enter')}</motion.button>
            <button type="button" onClick={() => { setStep(1); setCode(''); setErr('') }} className="h-14 rounded-lg bg-surface-container text-label-lg">{t('login.changeNumber')}</button>
          </motion.form>
        )}
      </AnimatePresence>
    </Page>
  )
}
