<template>
  <button data-chat-ui type="button" class="btn btn-outline-primary chat-share-button" :class="{ 'btn-sm': compact }" title="Отправить в чат" aria-label="Отправить в чат" @click.stop="share">
    <i class="bi bi-send" aria-hidden="true"></i><span v-if="!compact">В чат</span>
  </button>
</template>
<script setup>
import { accessState } from '../access'
const props = defineProps({ type: { type: String, required: true }, recordId: { type: Number, required: true }, title: String, compact: Boolean })
const emit = defineEmits(['shared'])
function share() {
  window.dispatchEvent(new CustomEvent('chat-share-record', { detail: {
    companyId: accessState.user?.company_id, type: props.type, id: props.recordId, title: props.title || 'Выбранный объект',
  } }))
  emit('shared')
}
</script>
<style scoped>
.chat-share-button { display: inline-flex; align-items: center; justify-content: center; gap: 6px; white-space: nowrap; }
.chat-share-button.btn-sm { width: calc(1.5em + .5rem + 2px); height: calc(1.5em + .5rem + 2px); padding: 0; vertical-align: middle; }
.chat-share-button > .bi { display: flex; line-height: 1; }.chat-share-button > .bi::before { display: block; vertical-align: 0; line-height: 1; }
</style>
