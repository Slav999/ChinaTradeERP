<template>
  <div class="chat-resources">
    <div class="d-flex justify-content-between align-items-center mb-2"><strong>{{ tab === 'pins' ? 'Закреплённые сообщения' : 'Поиск и материалы' }}</strong><button class="btn-close" aria-label="Закрыть материалы" @click="$emit('close')"></button></div>
    <div class="resource-tabs"><button v-for="item in tabs" :key="item.id" :class="{ active: tab === item.id }" @click="tab = item.id">{{ item.label }}</button></div>
    <input v-model="query" class="form-control form-control-sm my-2" :placeholder="tab === 'files' ? 'Название файла' : 'Поиск по переписке'" @input="scheduleSearch">
    <p v-if="tab === 'references'" class="text-muted small">Отправленные в чат заказы, товары и контрагенты.</p>
    <p v-if="error" class="text-danger small" role="alert">{{ error }}</p>
    <p v-if="loading && !items.length" class="text-muted small">Загрузка…</p>
    <p v-else-if="tab === 'search' && !query.trim()" class="text-muted small">Введите текст, номер заказа или имя файла.</p>
    <p v-else-if="!items.length" class="text-muted small">Ничего не найдено.</p>
    <div class="resource-results">
      <article v-for="message in items" :key="message.id" class="resource-item">
        <button class="resource-open" @click="$emit('jump', message.id)"><small data-i18n-skip>{{ message.sender_name }} · {{ date(message.created_at) }}</small><span v-if="message.text" data-i18n-skip>{{ message.text }}</span><span v-else-if="message.reference" data-i18n-skip>{{ chatReferenceTitle(message.reference, languageState.locale) }}</span><span v-else>Вложение</span></button>
        <ChatAttachment v-for="attachment in tab === 'files' ? message.attachments : []" :key="attachment.id" :attachment="attachment" :room-id="roomId" :company-id="companyId" />
        <button v-if="message.reference && tab === 'references'" class="btn btn-sm btn-link px-0" :disabled="message.reference.unavailable" @click="$emit('reference', message.reference)"><span data-i18n-skip>{{ chatReferenceTitle(message.reference, languageState.locale) }}</span> <i class="bi bi-box-arrow-up-right"></i></button>
      </article>
      <button v-if="hasMore" class="btn btn-sm btn-outline-secondary my-2" :disabled="loading" @click="load(true)">Показать ещё</button>
    </div>
  </div>
</template>
<script setup>
import { onBeforeUnmount, ref, watch } from 'vue'
import axios from '../axios'
import { languageState } from '../i18n'
import { chatReferenceTitle } from '../utils/chatTranslations'
import ChatAttachment from './ChatAttachment.vue'
const props = defineProps({ roomId: Number, companyId: Number, revision: Number, initialTab: { type: String, default: 'search' } })
defineEmits(['close', 'jump', 'reference'])
const tab = ref(props.initialTab), query = ref(''), items = ref([]), loading = ref(false), error = ref(''), hasMore = ref(false)
const tabs = [{ id: 'search', label: 'Сообщения' }, { id: 'files', label: 'Файлы' }, { id: 'references', label: 'Заказы и объекты' }]
let timer, sequence = 0, disposed = false
function config() { return { params: { company_id: props.companyId } } }
async function load(more = false) {
  const current = ++sequence
  if (!more) items.value = []
  if (tab.value === 'search' && !query.value.trim()) { loading.value = false; hasMore.value = false; return }
  loading.value = true; error.value = ''
  const rows = items.value
  const before = more && rows.length ? Math.min(...rows.map(row => row.id)) : undefined
  try {
    const { data } = await axios.get(`/api/chat/conversations/${props.roomId}/messages/`, {
      params: { ...config().params, q: query.value, tab: tab.value === 'search' ? undefined : tab.value, before },
    })
    if (current !== sequence || disposed) return
    items.value = more ? [...items.value, ...data.results.slice().reverse()] : data.results.slice().reverse()
    hasMore.value = data.has_more
  } catch { if (current === sequence) error.value = 'Не удалось загрузить материалы. Проверьте доступ и соединение.' }
  finally { if (current === sequence) loading.value = false }
}
function scheduleSearch() { sequence++; clearTimeout(timer); timer = setTimeout(() => load(), 300) }
function date(value) { return new Date(value).toLocaleString(languageState.locale === 'en' ? 'en-GB' : 'ru-RU') }
watch(() => [props.roomId, tab.value, props.revision], () => { clearTimeout(timer); load() }, { immediate: true })
onBeforeUnmount(() => { disposed = true; sequence++; clearTimeout(timer) })
</script>
<style scoped>
.chat-resources { flex: 1; min-height: 0; overflow-y: auto; padding: 16px; }
.resource-tabs { display: flex; flex-wrap: wrap; gap: 4px; }.resource-tabs button { border: 0; background: #f2f5fa; color: #72849c; padding: 5px 8px; border-radius: 8px; font-size: .73rem; }.resource-tabs button.active { background: #e2edfc; color: #2768bf; }
.resource-item { border-bottom: 1px solid #edf1f7; padding: 10px 0; }.resource-open { border: 0; padding: 0; background: none; text-align: left; width: 100%; }.resource-open small { display: block; color: #8c9aae; font-size: .7rem; }.resource-open span { display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical; overflow: hidden; font-size: .82rem; color: #456387; margin-top: 3px; overflow-wrap: anywhere; }
</style>
