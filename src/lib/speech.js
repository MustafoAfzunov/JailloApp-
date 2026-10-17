// Read text aloud. Few browsers ship a Kyrgyz voice, so fall back to Russian (same alphabet).
export const canSpeak = () => typeof window !== 'undefined' && 'speechSynthesis' in window

function pickVoice(lang) {
  const voices = window.speechSynthesis.getVoices()
  const want = lang === 'ky' ? ['ky', 'ru'] : ['ru']
  for (const prefix of want) {
    const v = voices.find((x) => x.lang.toLowerCase().startsWith(prefix))
    if (v) return v
  }
  return null
}

export function speak(text, lang, { onEnd } = {}) {
  if (!canSpeak()) return false
  window.speechSynthesis.cancel()
  const u = new SpeechSynthesisUtterance(text)
  const voice = pickVoice(lang)
  if (voice) { u.voice = voice; u.lang = voice.lang } else u.lang = lang === 'ky' ? 'ky-KG' : 'ru-RU'
  u.rate = 0.85
  u.onend = () => onEnd?.()
  u.onerror = () => onEnd?.()
  window.speechSynthesis.speak(u)
  return true
}

export const stopSpeaking = () => { if (canSpeak()) window.speechSynthesis.cancel() }

export function listen(lang, onText, onEnd) {
  const Rec = window.SpeechRecognition || window.webkitSpeechRecognition
  if (!Rec) return null
  const rec = new Rec()
  rec.lang = lang === 'ky' ? 'ru-RU' : 'ru-RU' // browsers have no Kyrgyz recogniser yet
  rec.interimResults = false
  rec.onresult = (e) => onText(e.results[0][0].transcript)
  rec.onend = onEnd
  rec.onerror = onEnd
  rec.start()
  return rec
}
