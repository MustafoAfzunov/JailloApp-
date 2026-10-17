import { motion } from 'framer-motion'

/** Flat illustrations in a mountain-and-yurt style (no external images needed). */
export function Valley({ className = '' }) {
  return (
    <svg viewBox="0 0 800 520" className={className} preserveAspectRatio="xMidYMid slice" role="img" aria-label="Жайлоо">
      <defs>
        <linearGradient id="vsky" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#bfe3ff" /><stop offset="1" stopColor="#f1f8e9" /></linearGradient>
      </defs>
      <rect width="800" height="520" fill="url(#vsky)" />
      <motion.circle cx="640" cy="90" r="42" fill="#fff6c8" animate={{ scale: [1, 1.08, 1] }} transition={{ repeat: Infinity, duration: 6 }} />
      <path d="M0 330 L130 190 L250 290 L390 120 L540 280 L660 170 L800 300 L800 520 L0 520Z" fill="#dce6ee" />
      <path d="M390 120 L445 185 L395 172 L350 195Z M130 190 L170 235 L130 228 L100 245Z M660 170 L700 215 L660 208 L630 225Z" fill="#fff" />
      <path d="M0 380 Q220 300 430 370 T800 340 L800 520 L0 520Z" fill="#7cb342" />
      <path d="M0 450 Q260 390 520 450 T800 430 L800 520 L0 520Z" fill="#558b2f" />
      {[[170, 400, 1], [330, 430, 0.8], [600, 410, 1.1]].map(([x, y, s], i) => (
        <g key={i} transform={`translate(${x} ${y}) scale(${s})`}>
          <path d="M-60 40 Q-60 -20 0 -34 Q60 -20 60 40Z" fill="#fff" stroke="#cfd8dc" strokeWidth="3" />
          <path d="M-18 40 Q-18 6 0 6 Q18 6 18 40Z" fill="#6d4c41" />
          <path d="M-60 40 H60" stroke="#8d6e63" strokeWidth="4" />
          <path d="M-48 12 H48 M-56 26 H56" stroke="#c0392b" strokeWidth="3" />
          <circle cx="0" cy="-38" r="6" fill="#c0392b" />
        </g>
      ))}
      {[[480, 480], [520, 492], [90, 486]].map(([x, y], i) => (
        <motion.g key={i} transform={`translate(${x} ${y})`} animate={{ x: [0, 6, 0] }} transition={{ repeat: Infinity, duration: 5 + i, ease: 'easeInOut' }}>
          <ellipse cx="0" cy="0" rx="22" ry="12" fill="#a1887f" />
          <rect x="-16" y="8" width="5" height="16" fill="#6d4c41" /><rect x="10" y="8" width="5" height="16" fill="#6d4c41" />
          <path d="M18 -4 q14 -16 22 -4 q-2 10 -12 8Z" fill="#8d6e63" />
        </motion.g>
      ))}
    </svg>
  )
}

export function MiniMap({ className = '' }) {
  return (
    <svg viewBox="0 0 400 180" className={className} preserveAspectRatio="xMidYMid slice" aria-hidden="true">
      <rect width="400" height="180" fill="#f6f3f2" />
      <path d="M0 0H400V40Q250 15 120 38T0 30Z" fill="#eae7e7" />
      <path d="M150 40C230 30 360 55 366 120C370 160 280 170 215 150C160 130 130 80 150 40Z" fill="#a3f69c" opacity=".7" />
      <path d="M60 0C70 50 45 100 20 150L28 180H80C60 140 85 90 100 60C110 40 120 20 118 0Z" fill="#ffb3ac" opacity=".85" />
      <motion.path d="M118 150L150 118L186 92L214 68" stroke="#0d631b" strokeWidth="6" strokeLinecap="round" strokeLinejoin="round" fill="none"
        initial={{ pathLength: 0 }} animate={{ pathLength: 1 }} transition={{ duration: 1.6, repeat: Infinity, repeatDelay: 1.2 }} />
      <circle cx="214" cy="66" r="9" fill="#0d631b" /><circle cx="118" cy="152" r="9" fill="#b6171e" />
      <rect x="150" y="130" width="22" height="16" rx="3" fill="#fff" stroke="#707a6c" /><rect x="260" y="95" width="22" height="16" rx="3" fill="#fff" stroke="#707a6c" />
    </svg>
  )
}

export function MarketArt({ className = '' }) {
  return (
    <svg viewBox="0 0 400 180" className={className} preserveAspectRatio="xMidYMid slice" aria-hidden="true">
      <rect width="400" height="180" fill="#f1f8e9" />
      <path d="M0 120Q100 80 200 112T400 100V180H0Z" fill="#7cb342" />
      <rect x="60" y="62" width="64" height="80" rx="14" fill="#f9a825" stroke="#e65100" strokeWidth="4" />
      <rect x="54" y="48" width="76" height="20" rx="7" fill="#8d6e63" />
      <path d="M170 100H270Q266 150 220 156Q174 150 170 100Z" fill="#fff8e1" stroke="#8d6e63" strokeWidth="5" />
      <ellipse cx="220" cy="100" rx="50" ry="12" fill="#fffde7" stroke="#8d6e63" strokeWidth="5" />
      <ellipse cx="325" cy="118" rx="40" ry="24" fill="#f5f1e6" stroke="#bdb59c" strokeWidth="3" />
      <ellipse cx="358" cy="96" rx="15" ry="13" fill="#6d4c41" />
    </svg>
  )
}
