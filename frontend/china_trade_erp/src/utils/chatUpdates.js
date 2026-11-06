export function createIncomingTracker() {
  let initialized = false
  let seen = new Map()
  return {
    reset() { initialized = false; seen = new Map() },
    update(rooms) {
      let newest = null
      for (const room of rooms) {
        const mode = room.notification_mode || 'all'
        const id = Number((mode === 'mentions' ? room.last_mention_message_id : room.last_incoming_message_id) || 0)
        const unread = mode === 'mentions' ? room.unread_mention_count : room.unread_count
        const previous = seen.get(room.id)
        if (initialized && mode !== 'off' && (!previous || previous.mode === mode) && unread > 0 && id > (previous?.id || 0) && (!newest || id > newest.messageId)) {
          newest = { roomId: room.id, messageId: id }
        }
        seen.set(room.id, { mode, id: previous?.mode === mode ? Math.max(previous.id, id) : id })
      }
      initialized = true
      return newest
    },
  }
}

export function mentionSegments(message) {
  const parts = []
  let cursor = 0
  for (const mention of message.mentions || []) {
    if (mention.start < cursor || mention.end > message.text.length) continue
    if (mention.start > cursor) parts.push({ text: message.text.slice(cursor, mention.start) })
    parts.push({ text: message.text.slice(mention.start, mention.end), person: mention })
    cursor = mention.end
  }
  if (cursor < message.text.length) parts.push({ text: message.text.slice(cursor) })
  return parts
}
