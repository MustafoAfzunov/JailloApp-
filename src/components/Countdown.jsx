import { AnimatePresence, motion } from 'framer-motion'
import { useEffect, useState } from 'react'
import { mmss } from '../lib/format.js'

/** Ticks down locally from a server value (re-synced whenever the server value changes). */
export function useCountdown(serverSeconds) {
  const [left, setLeft] = useState(serverSeconds)
  useEffect(() => { setLeft(serverSeconds) }, [serverSeconds])
  useEffect(() => {
    if (left == null) return undefined
    const id = setInterval(() => setLeft((s) => (s == null ? s : Math.max(0, s - 1))), 1000)
    return () => clearInterval(id)
  }, [left == null]) // eslint-disable-line react-hooks/exhaustive-deps
  return left
}

/** Big MM:SS where each changing digit rolls in. */
export default function Countdown({ seconds, className = '' }) {
  const text = mmss(seconds ?? 0)
  return (
    <span className={`inline-flex tabular-nums ${className}`} aria-live="off">
      {text.split('').map((ch, i) => (
        <span key={i} className="relative inline-block overflow-hidden" style={{ width: ch === ':' ? '0.45em' : '0.65em', height: '1.1em' }}>
          <AnimatePresence mode="popLayout" initial={false}>
            <motion.span
              key={ch + i}
              className="absolute inset-0 flex items-center justify-center"
              initial={{ y: '-100%', opacity: 0 }} animate={{ y: 0, opacity: 1 }} exit={{ y: '100%', opacity: 0 }}
              transition={{ duration: 0.25 }}
            >
              {ch}
            </motion.span>
          </AnimatePresence>
        </span>
      ))}
    </span>
  )
}
