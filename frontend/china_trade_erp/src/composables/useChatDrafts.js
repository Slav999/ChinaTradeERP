import { computed, onScopeDispose, reactive, ref, watch } from 'vue'
import { draftKey, readDraft, removeDraft, writeDraft } from '../utils/chatDrafts.js'

export function useChatDrafts({ api, userId, companyId, rooms, selected, hasSession, isCurrent, reportError,
  formatText = value => value, formatReference = record => record.title }) {
  const draft = ref(''), files = ref([]), pendingReference = ref(null)
  const replyTarget = ref(null), editTarget = ref(null), pendingSend = ref(null)
  const activeDraftKey = ref(''), missingDraftFiles = ref(false)
  const memory = reactive(new Map())
  let editRestore = null, missingFileCount = 0, timer, restoring = false, ready = false, sequence = 0

  function cached(key) { return memory.get(key) || readDraft(key) }
  function forget(key = activeDraftKey.value) { memory.delete(key); removeDraft(key) }
  const draftPreviews = computed(() => Object.fromEntries(rooms.value.map(room => {
    const snapshot = cached(draftKey(userId.value, companyId.value, room.id))
    const text = snapshot?.text?.trim().replace(/\s+/g, ' ')
    return [room.id, text || (snapshot?.reference ? formatReference(snapshot.reference) : '') ||
      formatText(snapshot?.fileCount ? `Файлы (${snapshot.fileCount})` : snapshot?.replyId ? 'Ответ на сообщение' : '')]
  })))

  function snapshot() {
    return { text: draft.value, reference: pendingReference.value, reply: replyTarget.value, replyId: replyTarget.value?.id,
      files: [...files.value], fileCount: missingDraftFiles.value ? missingFileCount : files.value.length,
      editId: editTarget.value?.id, editRestore, pendingClientId: pendingSend.value?.client_id,
      pendingSignature: pendingSend.value?.signature, pendingText: pendingSend.value?.text }
  }
  function save() {
    clearTimeout(timer)
    if (!activeDraftKey.value || restoring || !ready || !hasSession()) return
    const value = snapshot()
    memory.set(activeDraftKey.value, value)
    const { files: ignoredFiles, reply: ignoredReply, ...stored } = value
    writeDraft(activeDraftKey.value, { ...stored, editRestore: editRestore ? {
      text: editRestore.text, reference: editRestore.reference, replyId: editRestore.replyId, fileCount: editRestore.fileCount,
      pendingClientId: editRestore.pendingClientId, pendingSignature: editRestore.pendingSignature, pendingText: editRestore.pendingText,
    } : null })
  }
  function clearComposer() {
    draft.value = ''; files.value = []; pendingReference.value = null; replyTarget.value = null
    pendingSend.value = null; missingDraftFiles.value = false; missingFileCount = 0
  }
  async function restore(token) {
    const current = ++sequence, key = activeDraftKey.value, roomId = selected.value.id
    const params = { company_id: companyId.value }
    const valid = () => current === sequence && key === activeDraftKey.value && isCurrent(token)
    restoring = true
    try {
      const value = cached(key)
      draft.value = value?.text || ''; files.value = value?.files || []; pendingReference.value = value?.reference || null
      missingFileCount = value?.fileCount || 0; missingDraftFiles.value = missingFileCount > files.value.length
      pendingSend.value = value?.pendingClientId ? { client_id: value.pendingClientId, signature: value.pendingSignature, text: value.pendingText } : null
      replyTarget.value = null; editTarget.value = null; editRestore = value?.editRestore || null
      if (value?.replyId || value?.editId) {
        try {
          const { data } = await api.get(`/api/chat/conversations/${roomId}/messages/${value.editId || value.replyId}/`, { params })
          if (!valid()) return
          if (value.editId && data.sender_id === userId.value && !data.deleted_at) editTarget.value = data
          else if (!value.editId) replyTarget.value = data
        } catch { if (valid()) reportError('Исходное сообщение недоступно. Текст черновика сохранён.') }
      }
      if (pendingSend.value && valid()) {
        try {
          const pending = pendingSend.value
          const { data } = await api.get(`/api/chat/conversations/${roomId}/messages/`, { params: { ...params, client_id: pending.client_id } })
          if (!valid()) return
          if (data.results.length && draft.value.trim() === pending.text) { clearComposer(); forget(key) }
        } catch { /* Retrying an uncertain send keeps the same client UUID. */ }
      }
    } finally { if (current === sequence) { restoring = false; ready = valid() } }
  }
  function resetContext() {
    clearTimeout(timer); ready = false; sequence++; restoring = false
    replyTarget.value = null; editTarget.value = null; editRestore = null; missingDraftFiles.value = false
  }
  function beginEdit(message) {
    if (editTarget.value) cancelContext()
    save(); editRestore = snapshot()
    editTarget.value = message; draft.value = message.text; files.value = []; pendingReference.value = null; replyTarget.value = null
    missingDraftFiles.value = false; pendingSend.value = null; save()
  }
  function cancelContext() {
    if (editTarget.value) {
      const previous = editRestore
      editTarget.value = null; editRestore = null
      draft.value = previous?.text || ''; files.value = previous?.files || []; pendingReference.value = previous?.reference || null
      replyTarget.value = previous?.reply || (previous?.replyId ? { id: previous.replyId, sender_name: '', text: 'Сообщение из черновика' } : null)
      missingFileCount = previous?.fileCount || 0; missingDraftFiles.value = missingFileCount > files.value.length
      pendingSend.value = previous?.pendingClientId ? { client_id: previous.pendingClientId, signature: previous.pendingSignature, text: previous.pendingText } : null
    } else replyTarget.value = null
    save()
  }
  function acknowledge(entry) {
    const value = cached(entry.key)
    if (value?.pendingClientId === entry.clientId && value.text?.trim() === entry.text) forget(entry.key)
    if (activeDraftKey.value !== entry.key) return { active: false, cleared: false }
    const cleared = pendingSend.value?.client_id === entry.clientId && draft.value.trim() === entry.text && !editTarget.value
    if (cleared) { clearComposer(); save() }
    if (editRestore?.pendingClientId === entry.clientId) editRestore = { text: '', files: [], fileCount: 0 }
    return { active: true, cleared }
  }
  function storageChanged(event) {
    if (event.key?.startsWith(draftKey(userId.value, companyId.value, ''))) memory.set(event.key, readDraft(event.key))
  }
  function filesAttached() { missingDraftFiles.value = false; missingFileCount = 0 }
  function clearMemory() { resetContext(); memory.clear() }

  watch([draft, () => files.value.length, () => pendingReference.value?.id, () => replyTarget.value?.id], () => {
    if (!restoring) { clearTimeout(timer); timer = setTimeout(save, 250) }
  })
  onScopeDispose(() => { clearTimeout(timer); sequence++ })
  return { draft, files, pendingReference, replyTarget, editTarget, pendingSend, activeDraftKey, missingDraftFiles, draftPreviews,
    save, restore, resetContext, beginEdit, cancelContext, acknowledge, forget, storageChanged, filesAttached, clearMemory }
}
