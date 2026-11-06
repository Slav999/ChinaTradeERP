import test from 'node:test'
import assert from 'node:assert/strict'
import { getNotificationSoundStatus, installNotificationSound, playNotificationSound, testNotificationSound } from './notificationSound.js'

test('sound unlocks on click, waits for async resume, recovers interruptions and deduplicates', async t => {
  const original = { window: globalThis.window, document: globalThis.document, localStorage: globalThis.localStorage }
  const storage = new Map(), oscillators = []
  let now = Date.now()
  t.mock.method(Date, 'now', () => now)
  let closed = false, activeContext
  class AudioContext {
    constructor() { activeContext = this }
    state = 'suspended'; currentTime = 0; destination = {}
    async resume() { await Promise.resolve(); this.state = 'running' }
    close() { closed = true; return Promise.resolve() }
    createOscillator() {
      const tone = { frequency: {}, connect() {}, disconnect() {}, start() {}, stop() {} }
      oscillators.push(tone); return tone
    }
    createGain() { return { gain: { setValueAtTime() {}, linearRampToValueAtTime() {}, exponentialRampToValueAtTime() {} }, connect() {}, disconnect() {} } }
  }
  globalThis.window = Object.assign(new EventTarget(), { AudioContext })
  globalThis.document = new EventTarget()
  globalThis.localStorage = { getItem: key => storage.get(key), setItem: (key, value) => storage.set(key, value) }
  let cleanup
  try {
    cleanup = installNotificationSound()
    assert.equal(await playNotificationSound('before-interaction'), false)
    assert.equal(getNotificationSoundStatus(), 'blocked')
    document.dispatchEvent(new Event('click'))
    await new Promise(resolve => setImmediate(resolve))
    assert.deepEqual(oscillators.map(tone => tone.frequency.value), [660, 880])
    assert.equal(getNotificationSoundStatus(), 'ready')
    now += 1000
    assert.equal(await playNotificationSound('incoming-message-1'), true)
    assert.equal(await playNotificationSound('incoming-message-1'), false)
    assert.equal(await playNotificationSound('same-burst'), false)
    now += 1000
    storage.set('erp_notification_sound_events', JSON.stringify([{ key: 'another-tab-message', at: now - 100 }]))
    assert.equal(await playNotificationSound('another-tab-message'), false)
    assert.equal(await playNotificationSound('another-tab-burst'), false)
    now += 1000
    activeContext.state = 'interrupted'
    assert.equal(await playNotificationSound('later-message'), true)
    assert.equal(activeContext.state, 'running')
    // Explicit testing works even inside the normal notification cooldown.
    assert.equal(await testNotificationSound(), true)
    activeContext.state = 'suspended'
    now += 1000
    assert.equal(await playNotificationSound('resumed-message'), true)
    cleanup(); cleanup = null
    assert.equal(closed, true)
    assert.equal(await playNotificationSound('after-cleanup'), false)
  } finally {
    cleanup?.()
    for (const [key, value] of Object.entries(original)) {
      if (value === undefined) delete globalThis[key]
      else globalThis[key] = value
    }
  }
})

test('unsupported audio APIs and browser rejection do not break notifications', async () => {
  const original = { window: globalThis.window, document: globalThis.document }
  globalThis.window = new EventTarget(); globalThis.document = new EventTarget()
  const cleanup = installNotificationSound()
  try {
    assert.equal(await testNotificationSound(), false)
    assert.equal(getNotificationSoundStatus(), 'unavailable')
    window.webkitAudioContext = class {
      state = 'suspended'
      resume() { return Promise.reject(new Error('Autoplay blocked')) }
      close() { return Promise.resolve() }
    }
    assert.equal(await testNotificationSound(), false)
    assert.equal(getNotificationSoundStatus(), 'blocked')
  } finally {
    cleanup()
    for (const [key, value] of Object.entries(original)) {
      if (value === undefined) delete globalThis[key]
      else globalThis[key] = value
    }
  }
})
