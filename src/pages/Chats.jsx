import { AnimatePresence, motion } from 'framer-motion'
import { useCallback, useEffect, useRef, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import Icon from '../components/Icon.jsx'
import { Loading, Page } from '../components/ui.jsx'
import { api, unwrap } from '../lib/api.js'
import { clock, initial } from '../lib/format.js'
import { useI18n } from '../lib/i18n.jsx'

function Conversation({ id }) {
  const { t, lang } = useI18n()
  const [msgs, setMsgs] = useState([])
  const [thread, setThread] = useState(null)
  const [text, setText] = useState('')
  const [busy, setBusy] = useState(false)
  const last = useRef(0)
  const end = useRef(null)

  useEffect(() => { setMsgs([]); last.current = 0; api.get(`/market/threads/${id}/`).then(setThread).catch(() => {}) }, [id])
  const pull = useCallback(async () => {
    try {
      const rows = await api.get(`/market/threads/${id}/messages/`, { after: last.current || undefined })
      if (rows.length) { last.current = rows[rows.length - 1].id; setMsgs((m) => [...m, ...rows]) }
    } catch { /* keep polling */ }
  }, [id])
  useEffect(() => { pull(); const timer = setInterval(pull, 4000); return () => clearInterval(timer) }, [pull])
  useEffect(() => { end.current?.scrollIntoView({ behavior: 'smooth' }) }, [msgs.length])

  const send = async (e) => {
    e.preventDefault()
    const body = text.trim()
    if (!body) return
    setBusy(true)
    try { await api.post(`/market/threads/${id}/messages/`, { body }); setText(''); await pull() } finally { setBusy(false) }
  }

  return (
    <div className="flex h-[calc(100vh-14rem)] min-h-[420px] flex-col overflow-hidden rounded-xl bg-surface-container-lowest shadow-md lg:h-[70vh]">
      <div className="flex items-center gap-3 bg-primary p-4 text-on-primary">
        <Link to="/chats" className="lg:hidden" aria-label={t('common.back')}><Icon name="arrow_back" size={30} /></Link>
        <span className="flex h-11 w-11 items-center justify-center rounded-full bg-white/20 text-label-lg">{initial(thread?.other_user?.name)}</span>
        <div className="flex min-w-0 flex-col"><span className="truncate text-label-lg">{thread?.other_user?.name}</span><span className="truncate text-body-md opacity-90">{thread?.listing_title}</span></div>
      </div>
      <div className="flex flex-1 flex-col gap-2 overflow-y-auto bg-surface-container-low p-4">
        {msgs.length === 0 && <p className="m-auto text-center text-body-lg text-on-surface-variant">{t('chats.startHint')}</p>}
        <AnimatePresence initial={false}>
          {msgs.map((m) => (
            <motion.div key={m.id} initial={{ opacity: 0, y: 12, scale: 0.96 }} animate={{ opacity: 1, y: 0, scale: 1 }}
              className={`max-w-[82%] rounded-2xl px-4 py-3 text-body-lg shadow-sm ${m.mine ? 'self-end rounded-br-sm bg-primary text-on-primary' : 'self-start rounded-bl-sm bg-surface-container-lowest'}`}>
              <p className="whitespace-pre-wrap break-words">{m.body}</p>
              <span className={`mt-1 block text-right text-[13px] ${m.mine ? 'opacity-80' : 'text-on-surface-variant'}`}>{clock(m.created_at, lang)}</span>
            </motion.div>
          ))}
        </AnimatePresence>
        <div ref={end} />
      </div>
      <form onSubmit={send} className="flex items-center gap-2 border-t border-outline-variant bg-surface-container-lowest p-3">
        <input value={text} onChange={(e) => setText(e.target.value)} maxLength={2000} placeholder={t('chats.placeholder')} aria-label={t('chats.placeholder')}
          className="h-16 flex-1 rounded-xl bg-surface-container-low px-5 text-body-lg outline-none focus:bg-surface-container" />
        <motion.button whileTap={{ scale: 0.9 }} disabled={busy || !text.trim()} type="submit" aria-label={t('chats.send')} className="flex h-16 w-16 items-center justify-center rounded-xl bg-primary text-on-primary disabled:opacity-50"><Icon name="send" size={30} /></motion.button>
      </form>
    </div>
  )
}

export default function Chats() {
  const { t, lang } = useI18n()
  const { id } = useParams()
  const navigate = useNavigate()
  const [threads, setThreads] = useState(null)
  useEffect(() => {
    const load = () => api.get('/market/threads/').then((d) => setThreads(unwrap(d))).catch(() => setThreads([]))
    load(); const timer = setInterval(load, 10000); return () => clearInterval(timer)
  }, [lang])

  return (
    <Page className="mx-auto w-full max-w-5xl px-4 py-space-lg">
      <h1 className="mb-space-md text-headline-lg">{t('chats.title')}</h1>
      <div className="grid gap-space-md lg:grid-cols-[320px_1fr]">
        <div className={`${id ? 'hidden lg:flex' : 'flex'} flex-col gap-2`}>
          {threads === null ? <Loading /> : threads.length === 0 ? (
            <div className="flex flex-col items-center gap-3 rounded-xl bg-surface-container-low p-space-lg text-center"><Icon name="forum" size={56} className="text-outline" /><p className="text-body-lg">{t('chats.empty')}</p><Link to="/market" className="text-label-lg text-primary underline">{t('nav.market')}</Link></div>
          ) : threads.map((th) => (
            <motion.button key={th.id} layout whileTap={{ scale: 0.98 }} type="button" onClick={() => navigate(`/chats/${th.id}`)}
              className={`flex items-center gap-3 rounded-xl p-4 text-left shadow-sm ${String(th.id) === id ? 'bg-primary-fixed/50' : 'bg-surface-container-lowest hover:bg-surface-container'}`}>
              <span className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-primary-container text-label-lg text-on-primary">{initial(th.other_user.name)}</span>
              <span className="flex min-w-0 flex-col"><span className="truncate text-label-lg">{th.other_user.name}</span><span className="truncate text-body-md text-on-surface-variant">{th.listing_title}</span>{th.last_message && <span className="truncate text-body-md">{th.last_message.body}</span>}</span>
            </motion.button>
          ))}
        </div>
        <div className={id ? 'block' : 'hidden lg:block'}>
          {id ? <Conversation key={id} id={id} /> : (
            <div className="hidden h-[70vh] flex-col items-center justify-center gap-3 rounded-xl bg-surface-container-low text-on-surface-variant lg:flex"><Icon name="chat" size={64} /><p className="text-body-lg">{t('chats.pick')}</p></div>
          )}
        </div>
      </div>
    </Page>
  )
}
