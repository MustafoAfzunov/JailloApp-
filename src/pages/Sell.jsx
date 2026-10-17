import { AnimatePresence, motion } from 'framer-motion'
import { useEffect, useRef, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import Icon from '../components/Icon.jsx'
import { Page, fadeUp, stagger } from '../components/ui.jsx'
import { api, errorText } from '../lib/api.js'
import { useAuth } from '../lib/auth.jsx'
import { money, num } from '../lib/format.js'
import { useI18n } from '../lib/i18n.jsx'
import { usePortal } from '../lib/portal.jsx'

const UNITS = ['kg', 'l', 'piece', 'head', 'jar']
const DEFAULT_UNIT = { dairy: 'l', meat: 'kg', honey: 'jar', livestock: 'head' }
const ICONS = { dairy: 'local_drink', meat: 'restaurant', honey: 'hive', livestock: 'pets' }
const PRICES = [500, 1500, 3000, 10000]

function Step({ n, title, children }) {
  return (
    <motion.div variants={fadeUp} className="flex flex-col gap-6 rounded-xl bg-surface-container-lowest p-6 shadow-md sm:p-10">
      <div className="flex items-center gap-4">
        <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-primary text-headline-md text-on-primary">{n}</span>
        <h2 className="text-headline-md">{title}</h2>
      </div>
      {children}
    </motion.div>
  )
}

export default function Sell() {
  const { t } = useI18n()
  const { user } = useAuth()
  const { home } = usePortal()
  const navigate = useNavigate()
  const fileRef = useRef(null)
  const [photo, setPhoto] = useState(null)
  const [preview, setPreview] = useState('')
  const [title, setTitle] = useState('')
  const [qty, setQty] = useState(1)
  const [unit, setUnit] = useState('kg')
  const [unitTouched, setUnitTouched] = useState(false)
  const [price, setPrice] = useState(1500)
  const [cats, setCats] = useState([])
  const [cat, setCat] = useState('dairy')
  const [busy, setBusy] = useState(false)
  const [done, setDone] = useState(false)
  const [err, setErr] = useState('')

  useEffect(() => { api.get('/market/categories/').then(setCats).catch(() => {}) }, [])
  useEffect(() => { if (!unitTouched) setUnit(DEFAULT_UNIT[cat] || 'kg') }, [cat, unitTouched])
  useEffect(() => () => preview && URL.revokeObjectURL(preview), [preview])

  const pick = (e) => {
    const f = e.target.files?.[0]
    if (!f) return
    setPhoto(f); setPreview(URL.createObjectURL(f))
  }
  const resetPhoto = () => { setPhoto(null); setPreview(''); if (fileRef.current) fileRef.current.value = '' }
  const step = unit === 'kg' || unit === 'l' ? 1 : 1

  const submit = async () => {
    setErr('')
    if (title.trim().length < 2) { setErr(t('sell.needName')); return }
    setBusy(true)
    try {
      const listing = await api.post('/market/listings/', { title: title.trim(), category: cat, price_kgs: price, unit, quantity: qty })
      if (photo) {
        const fd = new FormData(); fd.append('image', photo)
        await api.post(`/market/listings/${listing.id}/images/`, fd)
      }
      setDone(true)
      setTimeout(() => navigate('/market'), 2200)
    } catch (e) { setErr(errorText(e, t('common.error'))) } finally { setBusy(false) }
  }

  return (
    <Page className="mx-auto flex w-full max-w-[920px] flex-col gap-8 px-4 py-8 sm:px-6 md:py-12">
      <div className="flex flex-col items-start justify-between gap-6 rounded-xl bg-surface-container-low p-6 shadow-sm sm:p-8 md:flex-row md:items-center">
        <div className="flex items-center gap-5">
          <div className="flex h-16 w-16 shrink-0 items-center justify-center rounded-xl bg-primary text-on-primary"><Icon name="storefront" size={36} /></div>
          <div className="flex flex-col"><span className="text-headline-lg">{t('sell.title')}</span><span className="mt-1 text-body-lg text-on-surface-variant">{t('sell.sub')}</span></div>
        </div>
        <div className="flex shrink-0 items-center gap-3 rounded-lg bg-surface-container px-4 py-2.5"><Icon name="verified_user" size={24} className="text-primary" /><span className="text-label-md">{home?.village?.valley}</span></div>
      </div>

      {!user?.village && (
        <p className="flex flex-wrap items-center gap-3 rounded-xl bg-warn-container p-4 text-label-lg text-warn"><Icon name="warning" />{t('sell.needVillage')}<Link to="/me" className="underline">{t('nav.profile')}</Link></p>
      )}

      <motion.div variants={stagger} initial="hidden" animate="show" className="flex flex-col gap-8">
        {/* 1 photo */}
        <Step n={1} title={t('sell.step1')}>
          <AnimatePresence mode="wait">
            {!preview ? (
              <motion.div key="drop" exit={{ opacity: 0 }} className="flex cursor-pointer flex-col items-center justify-center gap-4 rounded-xl bg-surface-container-low p-8 text-center transition-colors hover:bg-surface-container sm:p-12"
                onClick={() => fileRef.current?.click()}>
                <div className="flex h-20 w-20 items-center justify-center rounded-full bg-surface-container-high text-primary"><Icon name="photo_camera" size={44} /></div>
                <div className="flex flex-col gap-1"><span className="text-headline-md">{t('sell.photoTitle')}</span><span className="text-body-md text-on-surface-variant">{t('sell.photoSub')}</span></div>
                <span className="flex h-14 items-center gap-3 rounded-lg bg-primary-container px-8 text-label-xl text-on-primary"><Icon name="add_a_photo" size={28} />{t('sell.pickPhoto')}</span>
              </motion.div>
            ) : (
              <motion.div key="prev" initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} className="flex flex-col items-center gap-6 rounded-xl bg-surface-container-low p-4 sm:flex-row">
                <img src={preview} alt="" className="h-32 w-32 shrink-0 rounded-lg object-cover" />
                <div className="flex flex-grow flex-col gap-2"><div className="flex items-center gap-2 text-label-lg text-primary"><Icon name="check_circle" />{t('sell.photoReady')}</div><span className="text-body-md text-on-surface-variant">{t('sell.photoClear')}</span></div>
                <button type="button" onClick={resetPhoto} className="h-12 rounded-lg bg-surface-variant px-4 text-label-md hover:bg-surface-container-high">{t('sell.otherPhoto')}</button>
              </motion.div>
            )}
          </AnimatePresence>
          <input ref={fileRef} type="file" accept="image/*" capture="environment" className="hidden" onChange={pick} />
        </Step>

        {/* 2 name + amount + unit */}
        <Step n={2} title={t('sell.step2')}>
          <input value={title} onChange={(e) => setTitle(e.target.value)} maxLength={80} placeholder={t('sell.namePlaceholder')} aria-label={t('sell.step2')}
            className="h-20 rounded-xl bg-surface-container-low px-6 text-headline-md outline-none placeholder:text-body-lg placeholder:text-on-surface-variant focus:bg-surface-container" />
          <div className="flex flex-col gap-2">
            <span className="text-label-md text-on-surface-variant">{t('sell.amount')}:</span>
            <div className="flex items-center justify-between gap-4 rounded-xl bg-surface-container-low p-4">
              <motion.button whileTap={{ scale: 0.9 }} type="button" aria-label="-" onClick={() => setQty((q) => Math.max(1, q - step))} className="flex h-16 w-16 items-center justify-center rounded-xl bg-surface-container-highest"><Icon name="remove" size={34} /></motion.button>
              <div className="text-center"><span className="text-[44px] font-extrabold leading-none text-primary">{num(qty)}</span><span className="ml-2 text-headline-md text-on-surface-variant">{t(`unit.${unit}`)}</span></div>
              <motion.button whileTap={{ scale: 0.9 }} type="button" aria-label="+" onClick={() => setQty((q) => q + step)} className="flex h-16 w-16 items-center justify-center rounded-xl bg-primary-container text-on-primary"><Icon name="add" size={34} /></motion.button>
            </div>
            <div className="grid grid-cols-3 gap-3 sm:grid-cols-5">
              {UNITS.map((u) => (
                <button key={u} type="button" onClick={() => { setUnit(u); setUnitTouched(true) }} aria-pressed={unit === u}
                  className={`h-14 rounded-lg text-label-lg transition-colors ${unit === u ? 'bg-primary text-on-primary' : 'bg-surface-container hover:bg-surface-variant'}`}>{t(`unit.${u}`)}</button>
              ))}
            </div>
          </div>
        </Step>

        {/* 3 price */}
        <Step n={3} title={t('sell.step3')}>
          <div className="flex flex-col items-center gap-6 rounded-xl bg-surface-container-low p-6 sm:p-8">
            <div className="flex items-baseline gap-3">
              <motion.span key={price} initial={{ scale: 1.15, opacity: 0.4 }} animate={{ scale: 1, opacity: 1 }} className="text-[48px] font-extrabold leading-none tracking-tight text-primary sm:text-[60px]">{money(price)}</motion.span>
              <span className="text-headline-lg text-on-surface-variant">{t('sell.som')}</span>
            </div>
            <div className="grid w-full grid-cols-1 gap-4 sm:grid-cols-2">
              <motion.button whileTap={{ scale: 0.96 }} type="button" onClick={() => setPrice((p) => Math.max(100, p - 100))} className="flex h-16 items-center justify-center gap-3 rounded-xl bg-surface-container-highest text-label-xl hover:bg-surface-variant"><Icon name="remove_circle_outline" size={32} />- 100 {t('sell.somShort')}</motion.button>
              <motion.button whileTap={{ scale: 0.96 }} type="button" onClick={() => setPrice((p) => p + 100)} className="flex h-16 items-center justify-center gap-3 rounded-xl bg-primary-container text-label-xl text-on-primary hover:bg-primary"><Icon name="add_circle_outline" size={32} />+ 100 {t('sell.somShort')}</motion.button>
            </div>
            <div className="flex w-full flex-col gap-2">
              <span className="text-label-md text-on-surface-variant">{t('sell.quick')}:</span>
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                {PRICES.map((p) => (
                  <button key={p} type="button" onClick={() => setPrice(p)} className={`h-14 rounded-lg text-label-lg transition-colors ${price === p ? 'bg-primary text-on-primary' : 'bg-surface-container hover:bg-surface-variant'}`}>{money(p)} {t('sell.somShort')}</button>
                ))}
              </div>
            </div>
            <p className="text-body-md text-on-surface-variant">{t('sell.priceFor', { unit: t(`unit.${unit}`) })}</p>
          </div>
        </Step>

        {/* 4 category */}
        <Step n={4} title={t('sell.step4')}>
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4" role="radiogroup">
            {cats.map((c) => (
              <motion.div key={c.slug} role="radio" aria-checked={cat === c.slug} tabIndex={0} whileTap={{ scale: 0.97 }} onClick={() => setCat(c.slug)} onKeyDown={(e) => e.key === 'Enter' && setCat(c.slug)}
                className={`flex cursor-pointer flex-col items-center justify-center gap-3 rounded-xl p-6 text-center transition-colors ${cat === c.slug ? 'bg-primary-container text-on-primary' : 'bg-surface-container-low hover:bg-surface-container'}`}>
                <Icon name={ICONS[c.slug] || 'category'} size={44} />
                <span className="text-headline-md">{c.name}</span>
              </motion.div>
            ))}
          </div>
        </Step>
      </motion.div>

      <div className="flex flex-col items-center justify-between gap-6 rounded-xl bg-surface-container-low p-6 shadow-sm sm:flex-row sm:p-8">
        <div className="flex items-center gap-4">
          <div className="flex h-14 w-14 items-center justify-center rounded-full bg-primary-fixed text-on-primary-fixed"><Icon name="phone_in_talk" size={32} /></div>
          <div className="flex flex-col"><span className="text-label-lg">{t('sell.yourPhone')}</span><span className="text-headline-md text-primary">{user?.phone}</span><span className="text-body-md text-on-surface-variant">{t('sell.phoneHidden')}</span></div>
        </div>
        {user?.is_verified && <div className="flex items-center gap-2 rounded-lg bg-surface-container-lowest px-4 py-2.5 shadow-sm"><Icon name="verified" size={22} className="text-primary" /><span className="text-label-md">{t('sell.verified')}</span></div>}
      </div>

      {err && <p className="rounded-xl bg-error-container p-4 text-label-lg text-on-error-container">{err}</p>}

      <motion.button whileTap={{ scale: 0.98 }} type="button" disabled={busy || done} onClick={submit}
        className="flex h-[68px] w-full items-center justify-center gap-4 rounded-xl bg-primary text-headline-md text-on-primary shadow-xl hover:bg-on-primary-fixed-variant disabled:opacity-60">
        <Icon name="check_circle" size={36} /><span>{busy ? t('common.loading') : t('sell.publish')}</span>
      </motion.button>

      <AnimatePresence>
        {done && (
          <motion.div initial={{ opacity: 0, y: 30, scale: 0.9 }} animate={{ opacity: 1, y: 0, scale: 1 }} exit={{ opacity: 0 }}
            className="flex items-center gap-5 rounded-xl bg-primary-container p-6 text-on-primary shadow-lg">
            <motion.span initial={{ rotate: -90, scale: 0 }} animate={{ rotate: 0, scale: 1 }} transition={{ type: 'spring', stiffness: 220 }} className="inline-flex"><Icon name="task_alt" size={44} /></motion.span>
            <div className="flex flex-col"><span className="text-headline-md leading-tight">{t('sell.done')}</span><span className="text-body-md opacity-90">{t('sell.doneSub')}</span></div>
          </motion.div>
        )}
      </AnimatePresence>
    </Page>
  )
}
