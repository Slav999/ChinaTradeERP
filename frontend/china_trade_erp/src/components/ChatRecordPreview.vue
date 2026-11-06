<template>
  <div v-if="recordId" class="card border-primary-subtle mb-3" data-chat-ui>
    <div class="card-body">
      <button class="btn-close float-end" aria-label="Закрыть карточку" @click="close"></button>
      <small class="text-primary">Контрагент из переписки</small>
      <div v-if="record"><strong data-i18n-skip>{{ record.name }}</strong><div class="small text-muted mt-1" data-i18n-skip>{{ [record.phone, record.email, record.address].filter(Boolean).join(' · ') }}</div></div>
      <div v-if="record" class="d-flex flex-wrap gap-2 mt-2">
        <ChatShareButton type="counterparty" :record-id="record.id" :title="record.name" />
        <RelatedChatsButton type="counterparty" :record-id="record.id" :title="record.name" />
      </div>
      <div v-else class="small text-muted">{{ error || 'Загрузка…' }}</div>
    </div>
  </div>
</template>
<script setup>
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import axios from '../axios'
import ChatShareButton from './ChatShareButton.vue'
import RelatedChatsButton from './RelatedChatsButton.vue'
const route = useRoute(), router = useRouter(), record = ref(null), error = ref('')
const recordId = computed(() => route.query.chatRecord)
watch(recordId, async id => {
  record.value = null; error.value = ''
  if (!id || !/^\d+$/.test(String(id))) return
  try {
    const { data } = await axios.get(`/api/counterparties/${id}/`)
    if (recordId.value === id) record.value = data
  } catch { if (recordId.value === id) error.value = 'Контрагент недоступен.' }
}, { immediate: true })
function close() { const query = { ...route.query }; delete query.chatRecord; router.replace({ path: route.path, query }) }
</script>
