export function mergeMessages(current, changes, { append = true, hiddenBefore = 0, includeOlder = true } = {}) {
  const rows = new Map(current.filter(message => message.id > hiddenBefore).map(message => [message.id, message]))
  const firstId = current[0]?.id || 0
  for (const message of changes) {
    const previous = rows.get(message.id)
    if (previous && (previous.revision || 0) > (message.revision || 0)) continue
    if (!includeOlder && !previous && message.id < firstId) continue
    if (message.id > hiddenBefore && (append || previous)) rows.set(message.id, message)
  }
  return [...rows.values()].sort((a, b) => a.id - b.id)
}

export function visibleMessageIds(elements, viewport) {
  return elements.filter(element => {
    const rect = element.getBoundingClientRect()
    return rect.top < viewport.bottom && rect.bottom > viewport.top && rect.bottom <= viewport.bottom + 2
  }).map(element => Number(element.dataset.messageId))
}

export function readStatusRows({ recipients = [], results = [] }) {
  const people = new Map(recipients.map(person => [person.id, person]))
  return Object.fromEntries(results.map(message => {
    const read = new Map(message.read_by.filter(receipt => people.has(receipt.user_id)).map(receipt => [receipt.user_id, receipt]))
    return [message.id, { total: people.size, count: read.size,
      readers: [...read.values()].map(receipt => ({ ...people.get(receipt.user_id), read_at: receipt.read_at })),
      unread: [...people.values()].filter(person => !read.has(person.id)),
    }]
  }))
}
