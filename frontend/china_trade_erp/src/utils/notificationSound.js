let context = null, release = null, pending = null
let lastPlayed = 0, available = true
const recent = new Map()

export function getNotificationSoundStatus() {
  return !available ? 'unavailable' : context?.state === 'running' ? 'ready' : 'blocked'
}
function changed() { window.dispatchEvent(new Event('notification-sound-state')) }
function ensureContext() {
  const AudioContext = window.AudioContext || window.webkitAudioContext
  available = Boolean(AudioContext)
  if (!available) { changed(); return null }
  if (!context || context.state === 'closed') {
    context = new AudioContext()
    context.onstatechange = changed
  }
  return context
}
async function resumeContext(create = false) {
  try {
    const current = create ? ensureContext() : context
    if (!current) return false
    // Safari can report "interrupted"; Edge/Firefox can suspend background audio.
    if (current.state !== 'running' && current.state !== 'closed') {
      let timer
      try { await Promise.race([current.resume(), new Promise(resolve => { timer = setTimeout(resolve, 1200) })]) }
      finally { clearTimeout(timer) }
    }
    changed()
    return current === context && current.state === 'running'
  } catch { changed(); return false }
}

// Unlock on click/touch release as well as keyboard (pointerdown alone is not
// sufficient user activation on every browser/device).
export function installNotificationSound() {
  if (release) return release
  const unlock = async () => {
    if (await resumeContext(true)) {
      const waiting = pending
      pending = null
      if (waiting && Date.now() - waiting.at < 15000) await playNotificationSound(waiting.key)
    }
  }
  const events = ['pointerdown', 'click', 'touchend', 'keydown']
  events.forEach(event => document.addEventListener(event, unlock, true))
  release = () => {
    events.forEach(event => document.removeEventListener(event, unlock, true))
    if (context) { context.onstatechange = null; context.close().catch(() => {}) }
    context = null; release = null; pending = null
    recent.clear(); lastPlayed = 0
    changed()
  }
  return release
}

function chime() {
  try {
    const start = context.currentTime
    ;[660, 880].forEach((frequency, index) => {
      const tone = context.createOscillator(), volume = context.createGain()
      const at = start + index * 0.1
      tone.type = 'sine'; tone.frequency.value = frequency
      volume.gain.setValueAtTime(0, at)
      volume.gain.linearRampToValueAtTime(0.1, at + 0.015)
      volume.gain.exponentialRampToValueAtTime(0.001, at + 0.26)
      tone.connect(volume); volume.connect(context.destination)
      tone.onended = () => { tone.disconnect(); volume.disconnect() }
      tone.start(at); tone.stop(at + 0.28)
    })
    return true
  } catch { return false }
}

export async function testNotificationSound() {
  // Explicit user action: resume first, then play, without deduplication limits.
  pending = null
  return await resumeContext(true) && chime()
}

export async function playNotificationSound(key) {
  if (!await resumeContext()) { pending = { key, at: Date.now() }; return false }
  const now = Date.now()
  if (recent.has(key) || now - lastPlayed < 700) return false
  // Avoid replaying the same incoming event in another open tab.
  let previous = []
  try {
    const saved = JSON.parse(localStorage.getItem('erp_notification_sound_events') || '[]')
    previous = Array.isArray(saved) ? saved.filter(event => now - event.at < 60000) : []
    if (previous.some(event => event.key === key || now - event.at < 700)) return false
  } catch { /* Private browsing/storage restrictions should not break alerts. */ }
  if (!chime()) return false
  try { localStorage.setItem('erp_notification_sound_events', JSON.stringify([...previous, { key, at: now }].slice(-100))) } catch { /* Optional storage. */ }
  recent.set(key, now)
  if (recent.size > 100) recent.delete(recent.keys().next().value)
  lastPlayed = now
  return true
}
