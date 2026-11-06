<template>
  <div ref="root" class="attachment" :class="{ photo: attachment.is_image }">
    <a v-if="preview" data-i18n-skip :href="preview" target="_blank" rel="noopener" :aria-label="attachment.name"><img :src="preview" :alt="attachment.name" @load="$emit('loaded')"></a>
    <button class="attachment-file" type="button" :disabled="loading" @click="download">
      <i :class="`bi bi-${attachment.is_image ? 'image' : 'file-earmark-text'}`"></i>
      <span><strong data-i18n-skip>{{ attachment.name }}</strong><small>{{ (attachment.size / 1024).toFixed(0) }} КБ</small></span>
      <i class="bi bi-download"></i>
    </button>
    <small v-if="error" class="text-danger">{{ error }}</small>
  </div>
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue'
import axios from '../axios'
const props = defineProps({ attachment: { type: Object, required: true }, roomId: Number, companyId: Number })
defineEmits(['loaded'])
const root = ref(null), preview = ref(''), loading = ref(false), error = ref('')
let observer, disposed = false
async function fetchFile(isPreview) {
  const { data } = await axios.get(`/api/chat/conversations/${props.roomId}/attachments/${props.attachment.id}/`, {
    params: { company_id: props.companyId, ...(isPreview ? { preview: 1 } : {}) }, responseType: 'blob',
  })
  return data
}
async function loadPreview() {
  try {
    const data = await fetchFile(true)
    if (!disposed) preview.value = URL.createObjectURL(data)
  } catch { if (!disposed) error.value = 'Не удалось загрузить изображение.' }
}
async function download() {
  loading.value = true; error.value = ''
  try {
    const data = await fetchFile(false)
    if (disposed) return
    const url = URL.createObjectURL(data), link = document.createElement('a')
    link.href = url; link.download = props.attachment.name; link.click()
    window.setTimeout(() => URL.revokeObjectURL(url), 1000)
  } catch { error.value = 'Файл недоступен. Проверьте доступ к чату.' }
  finally { loading.value = false }
}
onMounted(() => {
  if (!props.attachment.is_image) return
  observer = new IntersectionObserver(entries => {
    if (entries.some(entry => entry.isIntersecting)) { observer.disconnect(); loadPreview() }
  })
  observer.observe(root.value)
})
onBeforeUnmount(() => { disposed = true; observer?.disconnect(); if (preview.value) URL.revokeObjectURL(preview.value) })
</script>

<style scoped>
.attachment { margin-top: 7px; border: 1px solid #dce5f0; border-radius: 12px; overflow: hidden; background: #ffffffb3; }
.attachment img { display: block; max-width: 100%; max-height: 230px; object-fit: contain; margin: auto; }
.attachment-file { display: flex; align-items: center; gap: 9px; width: 100%; border: 0; padding: 9px; background: transparent; color: #334d70; text-align: left; }
.attachment-file span { flex: 1; min-width: 0; }
.attachment-file strong { display: block; font-size: .78rem; overflow-wrap: anywhere; }
.attachment-file small { display: block; color: #738198; font-size: .68rem; }
</style>
