import { AnimatePresence, motion } from 'framer-motion'
import { useCallback, useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import Icon from '../components/Icon.jsx'
import { ErrorBox, Loading, Modal, Page, Toast, fadeUp, stagger } from '../components/ui.jsx'
import { api, errorText, unwrap } from '../lib/api.js'
import { num, telHref } from '../lib/format.js'
import { useI18n } from '../lib/i18n.jsx'

const STATUS_STYLE = {
  pending: 'bg-warn-container text-warn', accepted: 'bg-primary-fixed text-on-primary-fixed', declined: 'bg-error-container text-on-error-container',
  completed: 'bg-primary text-on-primary', cancelled: 'bg-surface-container-highest text-on-surface-variant',
}

function ReviewModal({ order, onClose, onDone }) {
  const { t } = useI18n()
  const [rating, setRating] = useState(5)
  const [comment, setComment] = useState('')
  const [err, setErr] = useState('')
  const send = async () => {
    try { await api.post(`/market/orders/${order.id}/review/`, { rating, comment }); onDone() } catch (e) { setErr(errorText(e, t('common.error'))) }
  }
  return (
    <Modal open={!!order} onClose={onClose} label={t('orders.review')}>
      <div className="flex flex-col gap-space-md">
        <h3 className="pr-12 text-headline-md">{t('orders.rateSeller')}</h3>
        <div className="flex justify-center gap-1" role="radiogroup">
          {[1, 2, 3, 4, 5].map((n) => (
            <motion.button key={n} type="button" whileTap={{ scale: 0.8 }} whileHover={{ scale: 1.15 }} onClick={() => setRating(n)} aria-label={`${n}`} aria-checked={rating === n} role="radio">
              <Icon name="star" fill={n <= rating} size={52} className={n <= rating ? 'text-warn' : 'text-outline-variant'} />
            </motion.button>
          ))}
        </div>
        <textarea value={comment} onChange={(e) => setComment(e.target.value)} maxLength={500} rows={3} placeholder={t('orders.commentPlaceholder')}
          className="rounded-xl bg-surface-container-low p-4 text-body-lg outline-none focus:bg-surface-container" />
        {err && <p className="rounded-lg bg-error-container p-3 text-on-error-container">{err}</p>}
        <button type="button" onClick={send} className="h-16 rounded-xl bg-primary text-label-xl text-on-primary">{t('orders.sendReview')}</button>
      </div>
    </Modal>
  )
}

function OrderCard({ o, role, act, openChat, onReview }) {
  const { t } = useI18n()
  const other = role === 'buyer' ? o.seller : o.buyer
  return (
    <motion.article variants={fadeUp} layout className="flex flex-col gap-space-sm rounded-xl bg-surface-container-lowest p-space-md shadow-md">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <h3 className="text-headline-md">{o.listing_title}</h3>
          <p className="text-body-lg text-on-surface-variant">{num(o.quantity)} {t(`unit.${o.listing_unit}`)} · {t(`market.${o.delivery}`)}</p>
        </div>
        <span className={`rounded-full px-4 py-1.5 text-label-md ${STATUS_STYLE[o.status]}`}>{t(`orders.status.${o.status}`)}</span>
      </div>
      {o.note && <p className="rounded-lg bg-surface-container-low p-3 text-body-md">“{o.note}”</p>}
      <div className="flex items-center gap-3 rounded-lg bg-surface-container p-3">
        <Icon name="person" size={28} className="text-primary" />
        <div className="flex flex-col"><span className="text-label-md text-on-surface-variant">{role === 'buyer' ? t('orders.seller') : t('orders.buyer')}</span><span className="text-label-lg">{other.name || '—'}</span></div>
      </div>
      <div className="flex flex-col gap-2">
        {other.phone && (
          <motion.a whileTap={{ scale: 0.97 }} href={telHref(other.phone)} className="flex h-[68px] items-center justify-center gap-3 rounded-xl bg-primary text-label-xl text-on-primary shadow-md">
            <Icon name="call" size={32} />{t('orders.call')} · {other.phone}
          </motion.a>
        )}
        {role === 'seller' && o.status === 'pending' && (
          <div className="grid grid-cols-2 gap-2">
            <button type="button" onClick={() => act(o, 'accept')} className="flex h-16 items-center justify-center gap-2 rounded-xl bg-primary text-label-xl text-on-primary"><Icon name="check" />{t('orders.accept')}</button>
            <button type="button" onClick={() => act(o, 'decline')} className="flex h-16 items-center justify-center gap-2 rounded-xl bg-error-container text-label-xl text-on-error-container"><Icon name="close" />{t('orders.decline')}</button>
          </div>
        )}
        {role === 'seller' && o.status === 'accepted' && (
          <button type="button" onClick={() => act(o, 'complete')} className="flex h-16 items-center justify-center gap-2 rounded-xl bg-primary-container text-label-xl text-on-primary"><Icon name="task_alt" />{t('orders.complete')}</button>
        )}
        {role === 'buyer' && ['pending', 'accepted'].includes(o.status) && (
          <button type="button" onClick={() => act(o, 'cancel')} className="h-14 rounded-xl bg-surface-container text-label-lg">{t('orders.cancel')}</button>
        )}
        {role === 'buyer' && o.status === 'completed' && !o.reviewed && (
          <button type="button" onClick={() => onReview(o)} className="flex h-16 items-center justify-center gap-2 rounded-xl bg-warn-container text-label-xl text-warn"><Icon name="star" fill />{t('orders.review')}</button>
        )}
        <button type="button" onClick={() => openChat(o)} className="flex h-14 items-center justify-center gap-2 rounded-xl bg-surface-container text-label-lg text-primary"><Icon name="chat" />{t('market.chat')}</button>
      </div>
    </motion.article>
  )
}

export default function Orders() {
  const { t, lang } = useI18n()
  const navigate = useNavigate()
  const [role, setRole] = useState('buyer')
  const [rows, setRows] = useState(null)
  const [error, setError] = useState(false)
  const [review, setReview] = useState(null)
  const [toast, setToast] = useState('')

  const load = useCallback(async () => {
    try { setRows(unwrap(await api.get('/market/orders/', { role }))); setError(false) } catch { setError(true) }
  }, [role])
  useEffect(() => { setRows(null); load(); const id = setInterval(load, 20000); return () => clearInterval(id) }, [load, lang])
  useEffect(() => { if (!toast) return undefined; const id = setTimeout(() => setToast(''), 3500); return () => clearTimeout(id) }, [toast])

  const act = async (o, action) => {
    try { await api.post(`/market/orders/${o.id}/${action}/`); setToast(t('orders.updated')); load() } catch (e) { setToast(errorText(e, t('common.error'))) }
  }
  const openChat = async (o) => {
    try { const th = await api.post(`/market/listings/${o.listing}/chat/`); navigate(`/chats/${th.id}`) } catch (e) { setToast(errorText(e, t('common.error'))) }
  }

  return (
    <Page className="mx-auto flex w-full max-w-3xl flex-col gap-space-md px-4 py-space-lg">
      <h1 className="text-headline-lg">{t('orders.title')}</h1>
      <div className="grid grid-cols-2 gap-2 rounded-xl bg-surface-container p-1.5" role="tablist">
        {['buyer', 'seller'].map((r) => (
          <button key={r} role="tab" aria-selected={role === r} type="button" onClick={() => setRole(r)}
            className={`relative h-16 rounded-lg text-label-xl ${role === r ? 'text-on-primary' : 'text-on-surface'}`}>
            {role === r && <motion.span layoutId="ordtab" className="absolute inset-0 rounded-lg bg-primary" />}
            <span className="relative">{t(`orders.tab.${r}`)}</span>
          </button>
        ))}
      </div>
      {error ? <ErrorBox onRetry={load} /> : rows === null ? <Loading /> : rows.length === 0 ? (
        <div className="flex flex-col items-center gap-3 rounded-xl bg-surface-container-low p-space-lg text-center"><Icon name="inventory_2" size={56} className="text-outline" /><p className="text-body-lg">{t('orders.empty')}</p><Link to="/market" className="text-label-lg text-primary underline">{t('nav.market')}</Link></div>
      ) : (
        <motion.div variants={stagger} initial="hidden" animate="show" key={role} className="flex flex-col gap-space-md">
          <AnimatePresence>{rows.map((o) => <OrderCard key={o.id} o={o} role={role} act={act} openChat={openChat} onReview={setReview} />)}</AnimatePresence>
        </motion.div>
      )}
      <ReviewModal order={review} onClose={() => setReview(null)} onDone={() => { setReview(null); setToast(t('orders.thanks')); load() }} />
      <Toast message={toast} />
    </Page>
  )
}
