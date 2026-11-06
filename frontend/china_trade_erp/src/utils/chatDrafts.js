const PREFIX = 'chat_draft:v1:'
const MAX_AGE = 7 * 24 * 60 * 60 * 1000

export function draftKey(userId, companyId, roomId) { return `${PREFIX}${userId}:${companyId}:${roomId}` }
export function readDraft(key) {
  try {
    const draft = JSON.parse(localStorage.getItem(key) || 'null')
    if (!draft || Date.now() - draft.savedAt > MAX_AGE) { localStorage.removeItem(key); return null }
    return draft
  } catch { return null }
}
export function writeDraft(key, value) {
  if (!key) return
  try {
    if (!value.text && !value.reference && !value.replyId && !value.fileCount) localStorage.removeItem(key)
    else localStorage.setItem(key, JSON.stringify({ ...value, savedAt: Date.now() }))
  } catch { /* Restricted or full browser storage must not prevent sending. */ }
}
export function removeDraft(key) { try { localStorage.removeItem(key) } catch { /* Optional storage. */ } }
export function clearChatDrafts() {
  try {
    for (let index = localStorage.length - 1; index >= 0; index--) {
      const key = localStorage.key(index)
      if (key?.startsWith(PREFIX)) localStorage.removeItem(key)
    }
  } catch { /* Logout must always complete. */ }
}
