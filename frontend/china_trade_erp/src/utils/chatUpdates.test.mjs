import test from 'node:test'
import assert from 'node:assert/strict'
import { createIncomingTracker, mentionSegments } from './chatUpdates.js'

test('initial unread history is silent, new incoming messages alert only once', () => {
  const tracker = createIncomingTracker()
  const room = { id: 2, last_incoming_message_id: 12, unread_count: 5 }
  assert.equal(tracker.update([room]), null)
  assert.equal(tracker.update([room]), null)
  assert.deepEqual(tracker.update([{ ...room, last_incoming_message_id: 13 }]), { roomId: 2, messageId: 13 })
  assert.equal(tracker.update([{ ...room, last_incoming_message_id: 13 }]), null)
})
test('own messages, read receipts, and joining existing history do not cause sounds', () => {
  const tracker = createIncomingTracker()
  tracker.update([{ id: 1, last_incoming_message_id: 10, unread_count: 0 }])
  assert.equal(tracker.update([{ id: 1, last_incoming_message_id: 10, last_message_id: 11, unread_count: 0 }]), null)
  assert.equal(tracker.update([{ id: 2, last_incoming_message_id: 14, unread_count: 0 }]), null)
  assert.deepEqual(tracker.update([{ id: 3, last_incoming_message_id: 15, unread_count: 1 }]), { roomId: 3, messageId: 15 })
})
test('company changes reset the sound baseline', () => {
  const tracker = createIncomingTracker()
  tracker.update([])
  tracker.reset()
  assert.equal(tracker.update([{ id: 5, last_incoming_message_id: 90, unread_count: 12 }]), null)
})
test('mention segments preserve emoji, punctuation and untrusted plain text', () => {
  const message = { text: '😀 @bob <script>', mentions: [{ id: 2, start: 3, end: 7, name: 'Bob' }] }
  const parts = mentionSegments(message)
  assert.equal(parts.map(part => part.text).join(''), message.text)
  assert.equal(parts[1].text, '@bob')
  assert.equal(parts[2].text, ' <script>')
})

test('muted and mentions-only conversations sound only for the chosen events', () => {
  const tracker = createIncomingTracker()
  const room = { id: 1, last_incoming_message_id: 1, last_mention_message_id: 0, unread_count: 1, unread_mention_count: 0 }
  tracker.update([room])
  assert.equal(tracker.update([{ ...room, notification_mode: 'off', last_incoming_message_id: 2 }]), null)
  tracker.update([{ ...room, notification_mode: 'mentions' }])
  assert.equal(tracker.update([{ ...room, notification_mode: 'mentions', last_incoming_message_id: 3 }]), null)
  assert.deepEqual(tracker.update([{ ...room, notification_mode: 'mentions', last_incoming_message_id: 4,
    last_mention_message_id: 4, unread_mention_count: 1 }]), { roomId: 1, messageId: 4 })
})
