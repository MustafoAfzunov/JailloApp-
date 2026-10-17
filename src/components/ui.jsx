import { AnimatePresence, motion } from 'framer-motion'
import { useEffect } from 'react'
import Icon from './Icon.jsx'
import { useI18n } from '../lib/i18n.jsx'

export const fadeUp = {
  hidden: { opacity: 0, y: 18 },
  show: { opacity: 1, y: 0, transition: { type: 'spring', stiffness: 160, damping: 20 } },
}
export const stagger = { hidden: {}, show: { transition: { staggerChildren: 0.08, delayChildren: 0.05 } } }

/** Page wrapper: soft slide-in like a mountain mist lifting. */
export function Page({ children, className = '' }) {
  return (
    <motion.div
      className={className}
      initial={{ opacity: 0, y: 14 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
      transition={{ duration: 0.28, ease: 'easeOut' }}
    >
      {children}
    </motion.div>
  )
}

/** Big pressable button with a spring tap. */
export const Press = motion.create('button')

export function Modal({ open, onClose, children, label }) {
  const { t } = useI18n()
  useEffect(() => {
    if (!open) return undefined
    const onKey = (e) => e.key === 'Escape' && onClose()
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open, onClose])
  return (
    <AnimatePresence>
      {open && (
        <motion.div
          className="fixed inset-0 z-[60] flex items-center justify-center bg-on-surface/60 p-4 backdrop-blur-sm"
          initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
          onClick={onClose}
        >
          <motion.div
            role="dialog" aria-modal="true" aria-label={label}
            className="relative max-h-[92vh] w-full max-w-lg overflow-y-auto rounded-xl bg-surface-container-lowest p-space-lg shadow-2xl"
            initial={{ scale: 0.9, y: 30, opacity: 0 }} animate={{ scale: 1, y: 0, opacity: 1 }}
            exit={{ scale: 0.95, y: 20, opacity: 0 }}
            transition={{ type: 'spring', stiffness: 260, damping: 24 }}
            onClick={(e) => e.stopPropagation()}
          >
            <button type="button" onClick={onClose} aria-label={t('common.close')}
              className="absolute right-3 top-3 flex h-12 w-12 items-center justify-center rounded-full bg-surface-container text-on-surface">
              <Icon name="close" size={28} />
            </button>
            {children}
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}

export function Loading() {
  const { t } = useI18n()
  return (
    <div className="flex items-center justify-center gap-3 py-space-xl text-on-surface-variant">
      <motion.span animate={{ rotate: 360 }} transition={{ repeat: Infinity, duration: 1.2, ease: 'linear' }} className="inline-flex">
        <Icon name="progress_activity" size={36} className="text-primary" />
      </motion.span>
      <span className="text-body-lg">{t('common.loading')}</span>
    </div>
  )
}

export function ErrorBox({ message, onRetry }) {
  const { t } = useI18n()
  return (
    <div className="flex flex-col items-center gap-3 rounded-xl bg-error-container p-space-md text-center text-on-error-container">
      <Icon name="cloud_off" size={40} />
      <p className="text-body-lg">{message || t('common.error')}</p>
      {onRetry && (
        <button type="button" onClick={onRetry} className="h-14 rounded-lg bg-error px-6 text-label-lg text-on-error">
          {t('common.retry')}
        </button>
      )}
    </div>
  )
}

export function Toast({ message, tone = 'ok' }) {
  return (
    <AnimatePresence>
      {message && (
        <motion.div
          className={`fixed bottom-24 left-1/2 z-[70] flex max-w-[92vw] items-center gap-3 rounded-xl px-5 py-4 text-label-lg shadow-xl lg:bottom-8 ${
            tone === 'ok' ? 'bg-primary-container text-on-primary' : 'bg-error text-on-error'
          }`}
          initial={{ opacity: 0, y: 40, x: '-50%' }} animate={{ opacity: 1, y: 0, x: '-50%' }} exit={{ opacity: 0, y: 40, x: '-50%' }}
        >
          <Icon name={tone === 'ok' ? 'task_alt' : 'error'} size={28} />
          <span>{message}</span>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
