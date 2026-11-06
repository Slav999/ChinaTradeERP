import { computed, onScopeDispose, ref } from 'vue'

export function useChatDelivery({ api, drafts, selected, companyId, loadingMessages, error, getEpoch, onFailure, onAccepted }) {
  const deliveries = ref({})
  const activeDelivery = computed(() => deliveries.value[drafts.activeDraftKey.value])
  const sending = computed(() => activeDelivery.value?.status === 'sending')
  let generation = 0

  async function send() {
    const text = drafts.draft.value.trim()
    if ((!text && !drafts.files.value.length && !drafts.pendingReference.value) || !selected.value || sending.value || loadingMessages.value || drafts.missingDraftFiles.value) return
    const signature = JSON.stringify([text, drafts.files.value.map(file => [file.name, file.size, file.lastModified]),
      drafts.pendingReference.value?.type, drafts.pendingReference.value?.id, drafts.replyTarget.value?.id])
    if (!drafts.pendingSend.value || drafts.pendingSend.value.signature !== signature) {
      drafts.pendingSend.value = { text, client_id: crypto.randomUUID(), signature }
    }
    const entry = { key: drafts.activeDraftKey.value, roomId: selected.value.id, companyId: companyId.value, text,
      files: [...drafts.files.value], reference: drafts.pendingReference.value, replyId: drafts.replyTarget.value?.id,
      clientId: drafts.pendingSend.value.client_id, status: 'queued', progress: 0 }
    deliveries.value[entry.key] = entry
    drafts.save()
    await deliver(entry)
  }
  async function deliver(entry) {
    const token = getEpoch(), current = generation, state = deliveries.value[entry.key]
    if (!state || state.status === 'sending') return
    let accepted = false
    state.status = 'sending'; state.progress = 0; error.value = ''
    try {
      const body = new FormData()
      body.append('text', entry.text); body.append('client_id', entry.clientId)
      if (entry.reference) { body.append('reference_type', entry.reference.type); body.append('reference_id', entry.reference.id) }
      if (entry.replyId) body.append('reply_to_id', entry.replyId)
      entry.files.forEach(file => body.append('files', file))
      const { data } = await api.post(`/api/chat/conversations/${entry.roomId}/messages/`, body, {
        params: { company_id: entry.companyId }, headers: { 'Content-Type': 'multipart/form-data' },
        onUploadProgress: progress => { state.progress = progress.total ? Math.min(99, Math.round(progress.loaded / progress.total * 100)) : 0 },
      })
      if (current !== generation) return
      accepted = true; state.status = 'sent'; state.progress = 100; state.messageId = data.id; state.files = []
      const result = drafts.acknowledge(entry)
      if (result.active) await onAccepted(data, entry, result.cleared)
    } catch (err) {
      if (current !== generation) return
      if (!accepted) state.status = 'failed'
      await onFailure(err, token)
    }
  }
  function retry() {
    if (drafts.missingDraftFiles.value) { error.value = 'Прикрепите файлы черновика повторно.'; return }
    if (activeDelivery.value?.status === 'failed') return deliver(activeDelivery.value)
  }
  function clear() { generation++; deliveries.value = {} }
  onScopeDispose(clear)
  return { activeDelivery, sending, send, retry, clear }
}
