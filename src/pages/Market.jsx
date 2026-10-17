import { AnimatePresence, motion } from 'framer-motion'
import { useCallback, useEffect, useRef, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import Icon from '../components/Icon.jsx'
import { ErrorBox, Loading, Modal, Page, Toast, fadeUp, stagger } from '../components/ui.jsx'
import { api, errorText, unwrap } from '../lib/api.js'
import { useAuth } from '../lib/auth.jsx'
import { initial, isToday, money, num, telHref } from '../lib/format.js'
import { useI18n } from '../lib/i18n.jsx'
import { usePortal } from '../lib/portal.jsx'
import { listen } from '../lib/speech.js'

const CAT_STYLE = {
  dairy: { icon: 'water_drop', color: 'text-primary', badge: 'bg-primary-container text-on-primary' },
  meat: { icon: 'restaurant', color: 'text-secondary', badge: 'bg-secondary text-on-secondary' },
  honey: { icon: 'hive', color: 'text-tertiary', badge: 'bg-tertiary text-on-tertiary' },
  livestock: { icon: 'pets', color: 'text-on-surface', badge: 'bg-secondary text-on-secondary' },
}
const AVATARS = ['bg-primary-container text-on-primary', 'bg-secondary-container text-on-secondary', 'bg-tertiary-container text-on-tertiary', 'bg-primary-fixed-dim text-on-primary-fixed']

function Stars({ value }) {
  if (!value) return null
  return <span className="flex items-center gap-0.5 text-label-md text-warn"><Icon name="star" fill size={18} />{Number(value).toFixed(1)}</span>
}

export function OrderModal({ listing, onClose, onDone }) {
  const { t } = useI18n()
  const [qty, setQty] = useState(1)
  const [delivery, setDelivery] = useState('pickup')
  const [note, setNote] = useState('')
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState('')
  const max = Number(listing?.quantity || 1)
  useEffect(() => { setQty(1); setNote(''); setErr('') }, [listing?.id])

  const submit = async () => {
    setBusy(true); setErr('')
    try {
      await api.post('/market/orders/', { listing: listing.id, quantity: qty, delivery, note })
      onDone(t('market.orderSent'))
    } catch (e) { setErr(errorText(e, t('common.error'))) } finally { setBusy(false) }
  }

  return (
    <Modal open={!!listing} onClose={onClose} label={t('market.order')}>
      {listing && (
        <div className="flex flex-col gap-space-md">
          <h3 className="pr-12 text-headline-md">{listing.title}</h3>
          <div className="flex items-center justify-between rounded-xl bg-surface-container-low p-space-sm">
            <button type="button" aria-label="-" onClick={() => setQty((q) => Math.max(1, q - 1))} className="flex h-16 w-16 items-center justify-center rounded-xl bg-surface-container-highest"><Icon name="remove" size={34} /></button>
            <div className="text-center"><div className="text-headline-xl text-primary">{num(qty)}</div><div className="text-body-md text-on-surface-variant">{t(`unit.${listing.unit}`)} · {t('market.left', { n: num(max) })}</div></div>
            <button type="button" aria-label="+" onClick={() => setQty((q) => Math.min(max, q + 1))} className="flex h-16 w-16 items-center justify-center rounded-xl bg-primary-container text-on-primary"><Icon name="add" size={34} /></button>
          </div>
          <div className="grid grid-cols-2 gap-3">
            {['pickup', 'delivery'].map((d) => (
              <button key={d} type="button" onClick={() => setDelivery(d)}
                className={`flex h-16 items-center justify-center gap-2 rounded-xl text-label-lg ${delivery === d ? 'bg-primary text-on-primary' : 'bg-surface-container'}`}>
                <Icon name={d === 'pickup' ? 'directions_walk' : 'local_shipping'} size={28} />{t(`market.${d}`)}
              </button>
            ))}
          </div>
          <input value={note} onChange={(e) => setNote(e.target.value)} maxLength={200} placeholder={t('market.notePlaceholder')}
            className="h-16 rounded-xl bg-surface-container-low px-4 text-body-lg outline-none focus:bg-surface-container" />
          <div className="flex items-center justify-between rounded-xl bg-primary-fixed/30 p-space-sm text-label-lg">
            <span>{t('market.total')}</span><span className="text-headline-md text-primary">{money(qty * Number(listing.price_kgs))} {t('common.som')}</span>
          </div>
          <p className="flex items-start gap-2 text-body-md text-on-surface-variant"><Icon name="info" size={22} className="mt-0.5 text-primary" />{t('market.phoneNote')}</p>
          {err && <p className="rounded-lg bg-error-container p-3 text-on-error-container">{err}</p>}
          <motion.button whileTap={{ scale: 0.97 }} type="button" disabled={busy} onClick={submit}
            className="flex h-[68px] items-center justify-center gap-3 rounded-xl bg-primary text-headline-md text-on-primary shadow-lg disabled:opacity-50">
            <Icon name="shopping_basket" size={34} />{t('market.sendOrder')}
          </motion.button>
        </div>
      )}
    </Modal>
  )
}

function ListingCard({ l, me, onOrder, onChat, index }) {
  const { t } = useI18n()
  const style = CAT_STYLE[l.category] || CAT_STYLE.dairy
  const img = l.images?.[0]?.image
  const mine = me && l.seller.id === me.id
  const unitLabel = l.unit === 'head' ? '' : ` / ${t(`unit.${l.unit}`)}`
  return (
    <motion.article variants={fadeUp} whileHover={{ y: -4 }} className="flex flex-col justify-between overflow-hidden rounded-xl bg-surface-container-lowest shadow-md hover:shadow-lg">
      <div className="flex flex-col">
        <div className="relative h-72 w-full overflow-hidden bg-surface-container-high">
          {img ? <motion.img src={img} alt={l.title} loading="lazy" className="h-full w-full object-cover" whileHover={{ scale: 1.05 }} transition={{ duration: 0.3 }} />
            : <div className="flex h-full items-center justify-center"><Icon name={style.icon} size={96} className="text-outline-variant" /></div>}
          {l.tag && <div className={`absolute left-4 top-4 flex items-center gap-1 rounded-lg px-3 py-1.5 text-label-md shadow-sm ${style.badge}`}><Icon name="eco" size={18} />{l.tag}</div>}
          <div className="absolute bottom-4 right-4 rounded-lg bg-surface-container-lowest/95 px-3 py-1 text-label-md shadow-sm backdrop-blur">
            {isToday(l.created_at) ? t('market.today') : t('market.available', { n: num(l.quantity), unit: t(`unit.${l.unit}`) })}
          </div>
        </div>
        <div className="flex flex-col gap-space-sm p-space-md">
          <div>
            <h3 className="text-headline-lg leading-tight">{l.title}</h3>
            {l.description && <p className="mt-1 line-clamp-3 text-body-md text-on-surface-variant">{l.description}</p>}
          </div>
          <div className="flex items-center justify-between rounded-xl bg-surface-container-low p-space-sm">
            <span className="text-label-lg text-on-surface-variant">{t('market.price')}:</span>
            <span className="text-headline-lg font-extrabold text-primary">{money(l.price_kgs)} {t('common.som')}<span className="text-body-md font-normal text-on-surface-variant">{unitLabel}</span></span>
          </div>
          <div className="flex items-center gap-space-xs rounded-lg bg-surface-container p-3">
            <div className={`flex h-12 w-12 shrink-0 items-center justify-center rounded-full text-headline-md ${AVATARS[index % AVATARS.length]}`}>{initial(l.seller.name)}</div>
            <div className="flex min-w-0 flex-col">
              <div className="flex items-center gap-1">
                <span className="truncate text-[20px] font-bold">{l.seller.name}</span>
                {l.seller.is_verified && <Icon name="verified" size={20} className="text-primary" />}
                <Stars value={l.seller.rating} />
              </div>
              <span className="truncate text-body-md text-on-surface-variant">{l.place_note || l.village_name}</span>
            </div>
          </div>
          {l.village_alert && l.village_alert !== 'low' && (
            <p className="flex items-center gap-2 rounded-lg bg-warn-container p-3 text-label-md text-warn"><Icon name="warning" size={22} />{t('market.villageAlert')}</p>
          )}
        </div>
      </div>
      <div className="flex flex-col gap-2 p-space-md pt-0">
        {mine ? (
          <div className="flex h-16 items-center justify-center gap-2 rounded-xl bg-surface-container text-label-lg text-on-surface-variant"><Icon name="person" />{t('market.yours')}</div>
        ) : l.seller.phone ? (
          <motion.a whileTap={{ scale: 0.96 }} href={telHref(l.seller.phone)} className="flex h-[72px] items-center justify-center gap-space-xs rounded-xl bg-primary text-label-xl text-on-primary shadow-md hover:bg-tertiary">
            <Icon name="call" size={34} /><span>{t('market.call')} · {l.seller.phone}</span>
          </motion.a>
        ) : (
          <div className="grid grid-cols-[1fr_auto] gap-2">
            <motion.button whileTap={{ scale: 0.96 }} type="button" onClick={() => onOrder(l)} className="flex h-[72px] items-center justify-center gap-space-xs rounded-xl bg-primary text-label-xl text-on-primary shadow-md hover:bg-tertiary">
              <Icon name="shopping_basket" size={32} /><span>{t('market.order')}</span>
            </motion.button>
            <motion.button whileTap={{ scale: 0.96 }} type="button" onClick={() => onChat(l)} aria-label={t('market.chat')} className="flex h-[72px] w-[72px] items-center justify-center rounded-xl bg-surface-container text-primary hover:bg-surface-container-high">
              <Icon name="chat" size={32} />
            </motion.button>
          </div>
        )}
      </div>
    </motion.article>
  )
}

export default function Market() {
  const { t, lang } = useI18n()
  const { user } = useAuth()
  const { home } = usePortal()
  const navigate = useNavigate()
  const [cats, setCats] = useState([])
  const [cat, setCat] = useState('')
  const [q, setQ] = useState('')
  const [debounced, setDebounced] = useState('')
  const [items, setItems] = useState(null)
  const [count, setCount] = useState(0)
  const [page, setPage] = useState(1)
  const [more, setMore] = useState(false)
  const [error, setError] = useState(false)
  const [order, setOrder] = useState(null)
  const [toast, setToast] = useState('')
  const [listening, setListening] = useState(false)
  const rec = useRef(null)

  useEffect(() => { api.get('/market/categories/').then(setCats).catch(() => {}) }, [lang])
  useEffect(() => { const id = setTimeout(() => setDebounced(q.trim()), 350); return () => clearTimeout(id) }, [q])
  useEffect(() => { if (!toast) return undefined; const id = setTimeout(() => setToast(''), 4000); return () => clearTimeout(id) }, [toast])

  const load = useCallback(async (p = 1, append = false) => {
    try {
      const data = await api.get('/market/listings/', { category: cat, search: debounced, ordering: '-created_at', page: p })
      const rows = unwrap(data)
      setItems((prev) => (append ? [...(prev || []), ...rows] : rows))
      setCount(data.count ?? rows.length); setMore(!!data.next); setPage(p); setError(false)
    } catch { setError(true) }
  }, [cat, debounced])
  useEffect(() => { setItems(null); load(1) }, [load, lang, user?.id])

  const guard = (fn) => (l) => (user ? fn(l) : navigate('/login?next=/market'))
  const startChat = guard(async (l) => {
    try { const th = await api.post(`/market/listings/${l.id}/chat/`); navigate(`/chats/${th.id}`) } catch (e) { setToast(errorText(e, t('common.error'))) }
  })
  const openOrder = guard((l) => setOrder(l))

  const voice = () => {
    if (listening) { rec.current?.stop(); return }
    rec.current = listen(lang, (text) => setQ(text), () => setListening(false))
    if (rec.current) setListening(true); else setToast(t('market.noVoice'))
  }

  return (
    <Page>
      <div className="w-full bg-surface-container-high px-4 py-space-sm lg:px-12">
        <div className="mx-auto flex max-w-7xl flex-col justify-between gap-space-xs text-on-surface md:flex-row md:items-center">
          <div className="flex items-center gap-space-xs">
            <span className="h-4 w-4 shrink-0 animate-pulse rounded-full bg-primary" />
            <span className="text-label-lg text-primary">{home?.village?.valley}:</span>
            <span className="text-body-md font-bold text-on-surface-variant">{t('market.topNote')}</span>
          </div>
          <div className="flex items-center gap-4 text-label-md text-on-surface-variant">
            <span className="flex items-center gap-1"><Icon name="verified_user" size={20} className="text-primary" />{t('market.noMiddle')}</span>
            {home?.contacts?.support && <span className="hidden items-center gap-1 sm:flex"><Icon name="support_agent" size={20} className="text-tertiary" />{t('market.support')}: {home.contacts.support.phone_display}</span>}
          </div>
        </div>
      </div>

      <section className="w-full px-4 pb-space-md pt-space-lg lg:px-12">
        <div className="mx-auto flex max-w-7xl flex-col gap-space-lg">
          <div className="flex flex-col justify-between gap-space-md rounded-xl bg-surface-container-lowest p-space-md shadow-sm lg:flex-row lg:items-end lg:p-space-lg">
            <div className="flex max-w-2xl flex-col gap-space-xs">
              <div className="inline-flex w-fit items-center gap-2 rounded-lg bg-surface-container-low px-3 py-1"><Icon name="storefront" size={22} className="text-primary" /><span className="text-label-md uppercase tracking-wide text-primary">{t('market.badge')}</span></div>
              <h1 className="text-headline-xl tracking-tight">{t('market.title')}</h1>
              <p className="text-body-lg text-on-surface-variant">{t('market.sub')}</p>
            </div>
            <Link to="/sell">
              <motion.span whileTap={{ scale: 0.95 }} whileHover={{ scale: 1.02 }} className="group flex h-20 shrink-0 items-center justify-center gap-space-sm rounded-xl bg-primary px-8 text-on-primary shadow-md hover:bg-tertiary">
                <span className="flex h-12 w-12 items-center justify-center rounded-lg bg-white/20 transition-transform group-hover:rotate-90"><Icon name="add" size={32} /></span>
                <span className="flex flex-col text-left"><span className="text-headline-md leading-none">{t('nav.sell')}</span><span className="mt-1 text-label-md leading-tight opacity-90">{t('market.addNew')}</span></span>
              </motion.span>
            </Link>
          </div>

          <form className="flex w-full flex-col items-center gap-space-sm rounded-xl bg-surface-container-lowest p-space-sm shadow-sm sm:flex-row" onSubmit={(e) => e.preventDefault()}>
            <div className="relative flex w-full flex-1 items-center">
              <Icon name="search" size={32} className="absolute left-6 text-on-surface-variant" />
              <input value={q} onChange={(e) => setQ(e.target.value)} placeholder={t('market.searchPlaceholder')} aria-label={t('market.search')}
                className="h-20 w-full rounded-lg bg-surface-container-low pl-16 pr-6 text-headline-md outline-none placeholder:text-body-lg placeholder:text-on-surface-variant focus:bg-surface-container" />
            </div>
            <motion.button whileTap={{ scale: 0.96 }} type="button" onClick={voice}
              className={`flex h-20 w-full shrink-0 items-center justify-center gap-space-xs rounded-lg px-8 text-label-xl sm:w-auto ${listening ? 'bg-secondary text-on-secondary' : 'bg-surface-container hover:bg-surface-container-high'}`}>
              <motion.span animate={listening ? { scale: [1, 1.25, 1] } : {}} transition={{ repeat: Infinity, duration: 0.9 }} className="inline-flex"><Icon name="mic" size={34} className={listening ? '' : 'text-secondary'} /></motion.span>
              <span>{listening ? t('market.listening') : t('market.voice')}</span>
            </motion.button>
          </form>

          <div className="flex flex-col gap-space-xs">
            <span className="text-label-lg font-bold text-on-surface-variant">{t('market.pickSection')}</span>
            <div className="grid grid-cols-2 gap-space-sm lg:grid-cols-4">
              {cats.map((c) => {
                const st = CAT_STYLE[c.slug] || CAT_STYLE.dairy
                const active = cat === c.slug
                return (
                  <motion.button key={c.slug} whileTap={{ scale: 0.97 }} type="button" onClick={() => setCat(active ? '' : c.slug)} aria-pressed={active}
                    className={`flex h-24 items-center justify-center gap-space-sm rounded-xl p-space-sm shadow-sm transition-colors sm:justify-start ${active ? 'bg-primary text-on-primary' : 'bg-surface-container-lowest hover:bg-surface-container-low'}`}>
                    <div className={`flex h-14 w-14 shrink-0 items-center justify-center rounded-lg ${active ? 'bg-white/20' : 'bg-surface-container'}`}><Icon name={st.icon} fill={active} size={36} className={active ? '' : st.color} /></div>
                    <div className="flex flex-col text-left"><span className="text-headline-md leading-none">{c.name}</span><span className={`mt-1 hidden text-label-md sm:block ${active ? 'opacity-90' : 'text-on-surface-variant'}`}>{c.hint}</span></div>
                  </motion.button>
                )
              })}
            </div>
          </div>
        </div>
      </section>

      <section className="w-full px-4 py-space-md lg:px-12">
        <div className="mx-auto flex max-w-7xl flex-col gap-space-md">
          <div className="flex items-center justify-between">
            <h2 className="text-headline-lg">{t('market.listings')} <span className="text-body-md font-normal text-on-surface-variant">({t('market.count', { n: count })})</span></h2>
            <div className="flex items-center gap-2"><span className="text-label-md text-on-surface-variant">{t('market.sort')}:</span><span className="rounded-lg bg-surface-container-lowest px-3 py-1.5 text-label-md text-primary shadow-sm">{t('market.newest')}</span></div>
          </div>

          {error ? <ErrorBox onRetry={() => load(1)} /> : items === null ? <Loading /> : (
            <motion.div variants={stagger} initial="hidden" animate="show" key={`${cat}|${debounced}`} className="grid grid-cols-1 gap-space-lg md:grid-cols-2 lg:grid-cols-3">
              {items.map((l, i) => <ListingCard key={l.id} l={l} index={i} me={user} onOrder={openOrder} onChat={startChat} />)}
              {items.length === 0 && <p className="col-span-full rounded-xl bg-surface-container-low p-space-lg text-center text-body-lg text-on-surface-variant">{t('market.empty')}</p>}

              {home?.contacts?.transport && (
                <motion.article variants={fadeUp} className="flex flex-col justify-between rounded-xl bg-surface-container-high p-space-md shadow-sm">
                  <div className="flex flex-col gap-space-sm">
                    <div className="flex h-16 w-16 items-center justify-center rounded-xl bg-surface-container-lowest text-primary"><Icon name="local_shipping" size={38} /></div>
                    <h3 className="text-headline-md">{t('market.transportTitle')}</h3>
                    <p className="text-body-md text-on-surface-variant">{t('market.transportText')}</p>
                  </div>
                  <a href={telHref(home.contacts.transport.phone)} className="mt-space-md flex h-[72px] items-center justify-center gap-space-xs rounded-xl bg-surface-container-lowest text-label-lg text-primary shadow-sm hover:bg-surface"><Icon name="phone_in_talk" size={28} />{t('market.callTransport')}</a>
                </motion.article>
              )}
              <motion.article variants={fadeUp} className="flex flex-col items-center justify-center gap-space-sm rounded-xl bg-surface-container-low p-space-md text-center shadow-sm">
                <div className="flex h-20 w-20 items-center justify-center rounded-full bg-primary-container text-on-primary shadow-sm"><Icon name="add_business" size={44} /></div>
                <h3 className="text-headline-md">{t('market.haveGoods')}</h3>
                <p className="max-w-sm text-body-md text-on-surface-variant">{t('market.haveGoodsText')}</p>
                <Link to="/sell" className="flex h-[72px] w-full items-center justify-center gap-2 rounded-xl bg-primary text-label-xl text-on-primary shadow-md hover:bg-tertiary"><Icon name="campaign" size={30} />{t('market.newListing')}</Link>
              </motion.article>
            </motion.div>
          )}
          {more && <button type="button" onClick={() => load(page + 1, true)} className="mx-auto h-16 rounded-xl bg-surface-container-lowest px-8 text-label-lg text-primary shadow-sm">{t('market.more')}</button>}
        </div>
      </section>

      <section className="w-full px-4 py-space-xl lg:px-12">
        <div className="mx-auto flex max-w-7xl flex-col items-center gap-space-md rounded-xl bg-surface-container-lowest p-space-md text-center shadow-sm md:flex-row md:text-left lg:p-space-lg">
          <div className="flex h-20 w-20 shrink-0 items-center justify-center rounded-xl bg-tertiary-container text-on-tertiary shadow-sm"><Icon name="handshake" size={48} /></div>
          <div className="flex flex-1 flex-col gap-1">
            <span className="text-label-xl text-primary">{t('market.adviceLabel')}</span>
            <p className="text-headline-md leading-snug">{t('market.adviceTitle')}</p>
            <span className="text-body-md text-on-surface-variant">{t('market.adviceText')}</span>
          </div>
          <a href="tel:112" className="flex h-16 shrink-0 items-center gap-2 rounded-xl bg-surface-container px-6 text-label-lg hover:bg-surface-container-high"><Icon name="help" size={28} className="text-secondary" />{t('market.needHelp')}</a>
        </div>
      </section>

      <OrderModal listing={order} onClose={() => setOrder(null)} onDone={(m) => { setOrder(null); setToast(m); setTimeout(() => navigate('/orders'), 1200) }} />
      <Toast message={toast} />
    </Page>
  )
}
