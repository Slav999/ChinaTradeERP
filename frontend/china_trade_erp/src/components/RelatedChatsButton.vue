<template><button v-if="hasDiscussions" data-chat-ui type="button" class="btn btn-outline-secondary" title="Доступные вам обсуждения" @click.stop="open"><i class="bi bi-chat-dots me-1"></i>Обсуждения</button></template>
<script setup>
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import axios from '../axios'
import { accessState } from '../access'
const props = defineProps({ type: String, recordId: Number, title: String })
const emit = defineEmits(['opened'])
const hasDiscussions = ref(false)
let sequence = 0, disposed = false, timer
async function refresh() {
  const current = ++sequence, companyId = accessState.user?.company_id
  if (!companyId || !props.recordId || document.hidden) return
  try {
    const { data } = await axios.get('/api/chat/related/', { params: {
      company_id: companyId, reference_type: props.type, reference_id: props.recordId, exists: 1,
    } })
    if (current === sequence && !disposed) hasDiscussions.value = data.has_discussions === true
  } catch { if (current === sequence && !disposed) hasDiscussions.value = false }
}
function scheduleRefresh() { clearTimeout(timer); timer = setTimeout(refresh, 150) }
function open() {
  window.dispatchEvent(new CustomEvent('chat-open-related', { detail: { ...props, id: props.recordId, companyId: accessState.user?.company_id } }))
  emit('opened')
}
watch(() => [props.type, props.recordId, accessState.user?.id, accessState.user?.company_id,
  accessState.user?.is_company_admin, JSON.stringify(accessState.user?.permissions || [])], () => {
  hasDiscussions.value = false; refresh()
}, { immediate: true })
onMounted(() => {
  window.addEventListener('chat-discussions-changed', scheduleRefresh)
  window.addEventListener('focus', scheduleRefresh)
  document.addEventListener('visibilitychange', scheduleRefresh)
})
onBeforeUnmount(() => {
  disposed = true; sequence++; clearTimeout(timer)
  window.removeEventListener('chat-discussions-changed', scheduleRefresh)
  window.removeEventListener('focus', scheduleRefresh)
  document.removeEventListener('visibilitychange', scheduleRefresh)
})
</script>
