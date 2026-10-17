import { AnimatePresence, motion } from 'framer-motion'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import Icon from '../components/Icon.jsx'
import { Page, fadeUp, stagger } from '../components/ui.jsx'
import { telHref } from '../lib/format.js'
import { useI18n } from '../lib/i18n.jsx'
import { usePortal } from '../lib/portal.jsx'

const HAZARDS = [['mudflow', 'tsunami'], ['flood', 'flood'], ['avalanche', 'ac_unit'], ['fire', 'local_fire_department']]

function Accordion({ icon, title, steps }) {
  const [open, setOpen] = useState(false)
  return (
    <motion.div variants={fadeUp} layout className="overflow-hidden rounded-xl bg-surface-container-lowest shadow-md">
      <button type="button" onClick={() => setOpen(!open)} aria-expanded={open} className="flex min-h-[80px] w-full items-center gap-4 p-space-md text-left">
        <span className="flex h-14 w-14 shrink-0 items-center justify-center rounded-xl bg-primary-fixed text-on-primary-fixed"><Icon name={icon} size={34} /></span>
        <span className="flex-1 text-headline-md">{title}</span>
        <motion.span animate={{ rotate: open ? 180 : 0 }} className="inline-flex"><Icon name="expand_more" size={36} /></motion.span>
      </button>
      <AnimatePresence initial={false}>
        {open && (
          <motion.ol initial={{ height: 0, opacity: 0 }} animate={{ height: 'auto', opacity: 1 }} exit={{ height: 0, opacity: 0 }} className="flex flex-col gap-3 overflow-hidden px-space-md pb-space-md">
            {steps.map((s, i) => (
              <li key={i} className="flex items-start gap-3 text-body-lg"><span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-primary text-label-lg text-on-primary">{i + 1}</span><span>{s}</span></li>
            ))}
          </motion.ol>
        )}
      </AnimatePresence>
    </motion.div>
  )
}

export default function Help() {
  const { t } = useI18n()
  const { home } = usePortal()
  const contacts = [...(home?.contacts?.strip || []), ...(home?.contacts?.community || [])]
  return (
    <Page className="mx-auto flex w-full max-w-4xl flex-col gap-space-lg px-4 py-space-lg">
      <div className="flex items-center gap-5 rounded-xl bg-surface-container-low p-6 shadow-sm">
        <div className="flex h-16 w-16 shrink-0 items-center justify-center rounded-xl bg-primary text-on-primary"><Icon name="help" size={36} /></div>
        <div className="flex flex-col"><h1 className="text-headline-lg">{t('help.title')}</h1><span className="text-body-lg text-on-surface-variant">{t('help.sub')}</span></div>
      </div>

      <motion.a whileTap={{ scale: 0.98 }} href="tel:112" className="flex h-24 items-center justify-center gap-4 rounded-xl bg-secondary text-headline-lg text-on-secondary shadow-lg">
        <motion.span animate={{ scale: [1, 1.15, 1] }} transition={{ repeat: Infinity, duration: 1.4 }} className="inline-flex"><Icon name="phone_in_talk" size={48} /></motion.span>{t('help.call112')}
      </motion.a>

      <section className="flex flex-col gap-space-sm">
        <h2 className="text-headline-md">{t('help.whatToDo')}</h2>
        <motion.div variants={stagger} initial="hidden" animate="show" className="flex flex-col gap-space-sm">
          {HAZARDS.map(([h, icon]) => <Accordion key={h} icon={icon} title={t(`hazard.${h}`)} steps={t(`alert.steps.${h}`)} />)}
        </motion.div>
      </section>

      <section className="flex flex-col gap-space-sm">
        <h2 className="text-headline-md">{t('help.howTo')}</h2>
        <div className="grid gap-space-sm sm:grid-cols-3">
          {[['shield', 'help.how1'], ['storefront', 'help.how2'], ['campaign', 'help.how3']].map(([icon, key], i) => (
            <motion.div key={key} initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ delay: i * 0.1 }}
              className="flex flex-col gap-3 rounded-xl bg-surface-container-lowest p-space-md shadow-md">
              <span className="flex h-14 w-14 items-center justify-center rounded-full bg-primary-container text-on-primary"><Icon name={icon} size={30} /></span>
              <p className="text-body-lg">{t(key)}</p>
            </motion.div>
          ))}
        </div>
      </section>

      {contacts.length > 0 && (
        <section className="flex flex-col gap-space-sm">
          <h2 className="text-headline-md">{t('help.contacts')}</h2>
          <div className="grid gap-space-sm sm:grid-cols-2">
            {contacts.map((c) => (
              <a key={c.role} href={telHref(c.phone)} className="flex min-h-20 items-center gap-4 rounded-xl bg-surface-container-lowest p-4 shadow-md hover:bg-surface-container">
                <span className="flex h-14 w-14 shrink-0 items-center justify-center rounded-xl bg-surface-container text-primary"><Icon name="call" size={30} /></span>
                <span className="flex flex-col"><span className="text-body-md text-on-surface-variant">{t(`role.${c.role}`)} · {c.name}</span><span className="text-label-xl">{c.phone_display}</span></span>
              </a>
            ))}
          </div>
        </section>
      )}
      <Link to="/login" className="mx-auto text-label-lg text-primary underline">{t('help.loginHint')}</Link>
    </Page>
  )
}
