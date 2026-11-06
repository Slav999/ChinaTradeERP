<template>
  <article class="chat-message" :class="{ own: message.sender_id === userId, deleted: message.deleted_at, mentioned: message.mentions?.some(person => person.id === userId), focused }" :data-message-id="message.id">
    <div class="message-heading"><small v-if="group" class="fw-semibold" data-i18n-skip>{{ message.sender_name }}</small><i v-if="message.is_pinned" class="bi bi-pin-angle-fill ms-1 text-primary" title="Закреплено"></i>
      <details v-if="!message.deleted_at" ref="menu" class="message-menu"><summary aria-label="Действия с сообщением" title="Действия"><i class="bi bi-three-dots"></i></summary><div class="message-menu-body shadow">
        <button @click="action('reply')"><i class="bi bi-reply"></i>Ответить</button>
        <button v-if="message.sender_id === userId" @click="action('edit')"><i class="bi bi-pencil"></i>Редактировать</button>
        <button v-if="canPin" @click="action('pin')"><i class="bi bi-pin-angle"></i>{{ message.is_pinned ? 'Открепить' : 'Закрепить' }}</button>
        <button v-if="message.sender_id === userId" class="text-danger" @click="action('delete')"><i class="bi bi-trash3"></i>Удалить у всех</button>
        <div class="reaction-options"><button v-for="emoji in reactionOptions" :key="emoji" :aria-label="`Реакция ${emoji}`" @click="react(emoji)">{{ emoji }}</button></div>
      </div></details>
    </div>
    <button v-if="message.reply" class="reply-quote" :disabled="!message.reply.id" @click="$emit('jump', message.reply.id)"><strong data-i18n-skip>{{ message.reply.sender_name }}</strong><span v-if="!message.reply.id">Сообщение недоступно</span><span v-else-if="message.reply.deleted">Сообщение удалено</span><span v-else-if="message.reply.is_placeholder">Вложение или объект</span><span v-else data-i18n-skip>{{ message.reply.text }}</span></button>
    <div v-if="message.deleted_at" class="chat-text text-muted fst-italic"><i class="bi bi-slash-circle me-1"></i>Сообщение удалено</div>
    <template v-else>
      <div v-if="message.text" class="chat-text" data-i18n-skip><template v-for="(part, index) in mentionSegments(message)" :key="index"><mark v-if="part.person" class="chat-mention" :title="part.person.name">{{ part.text }}</mark><template v-else>{{ part.text }}</template></template></div>
      <button v-if="message.reference" class="record-card" :disabled="message.reference.unavailable" @click="$emit('reference', message.reference)"><i class="bi" :class="referenceIcon(message.reference.type)"></i><span><small>{{ message.reference.label || 'Нет доступа' }}</small><strong data-i18n-skip>{{ chatReferenceTitle(message.reference, languageState.locale) }}</strong></span><i v-if="!message.reference.unavailable" class="bi bi-box-arrow-up-right"></i></button>
      <ChatAttachment v-for="attachment in message.attachments" :key="attachment.id" :attachment="attachment" :room-id="roomId" :company-id="companyId" @loaded="$emit('loaded')" />
      <div v-if="message.reactions?.length" class="message-reactions"><button v-for="reaction in message.reactions" :key="reaction.emoji" :class="{ mine: reaction.mine }" :aria-label="`${reaction.emoji}: ${reaction.count}`" @click="react(reaction.emoji)">{{ reaction.emoji }} {{ reaction.count }}</button></div>
    </template>
    <small class="message-time"><span v-if="message.edited_at && !message.deleted_at">изменено · </span>{{ formatTime(message.created_at) }}</small>
    <template v-if="message.sender_id === userId && !message.deleted_at && readStatus?.total">
      <details v-if="group" class="message-read-status"><summary>Прочитали {{ readStatus.count }} из {{ readStatus.total }}</summary><div class="read-people"><span v-for="person in readStatus.readers" :key="person.id"><i class="bi bi-check2-all"></i> <span data-i18n-skip>{{ person.name }}</span><small>{{ person.read_at ? formatTime(person.read_at) : 'Время неизвестно' }}</small></span><span v-for="person in readStatus.unread" :key="person.id" class="text-muted"><span data-i18n-skip>{{ person.name }}</span><small>Ещё не прочитано</small></span></div></details>
      <small v-else class="message-read-status d-block" :title="readStatus.count ? (readStatus.readers[0].read_at ? `Прочитано ${formatTime(readStatus.readers[0].read_at)}` : 'Время прочтения неизвестно') : 'Сообщение отправлено'"><i class="bi" :class="readStatus.count ? 'bi-check2-all' : 'bi-check2'"></i> {{ readStatus.count ? 'Прочитано' : 'Отправлено' }}</small>
    </template>
  </article>
</template>
<script setup>
import { ref } from 'vue'
import { languageState } from '../i18n'
import { chatReferenceTitle } from '../utils/chatTranslations'
import ChatAttachment from './ChatAttachment.vue'
import { mentionSegments } from '../utils/chatUpdates'
const props = defineProps({ message: { type: Object, required: true }, userId: Number, roomId: Number, companyId: Number, group: Boolean, canPin: Boolean, focused: Boolean, readStatus: Object })
const emit = defineEmits(['reply', 'edit', 'delete', 'pin', 'react', 'jump', 'reference', 'loaded'])
const menu = ref(null), reactionOptions = ['👍', '✅', '👀', '❤️', '🙏']
function action(kind) { if (menu.value) menu.value.open = false; emit(kind, props.message) }
function react(emoji) { if (menu.value) menu.value.open = false; emit('react', props.message, emoji) }
function formatTime(value) { return new Date(value).toLocaleString(languageState.locale === 'en' ? 'en-GB' : 'ru-RU', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' }) }
function referenceIcon(kind) { return ({ product: 'bi-box-seam', counterparty: 'bi-building', supplier_order: 'bi-truck', customer_order: 'bi-receipt' })[kind] || 'bi-link-45deg' }
</script>
<style scoped>
.chat-message { position: relative; flex-shrink: 0; background: #fff; border: 1px solid #e7edf5; border-radius: 15px 15px 15px 4px; padding: 7px 12px 9px; margin-bottom: 9px; max-width: 90%; min-width: 115px; align-self: flex-start; overflow-wrap: anywhere; font-size: .88rem; }
.chat-message.own { background: #e6efff; border-color: #d9e7fd; border-radius: 15px 15px 4px 15px; align-self: flex-end; }
.chat-message.mentioned { border-color: #a5c6f1; }
.chat-message.focused { outline: 2px solid #8bb9f1; }
.message-heading { display: flex; align-items: center; min-height: 15px; gap: 4px; }
.message-heading small { font-size: .72rem; }
.message-menu { margin-left: auto; }
.message-menu summary { cursor: pointer; color: #8a9ab0; list-style: none; line-height: 1; padding: 0 2px 4px; }
.message-menu summary::-webkit-details-marker { display: none; }
.message-menu-body { position: absolute; right: 8px; top: 24px; z-index: 4; width: 188px; padding: 5px; border: 1px solid #dce5f1; border-radius: 10px; background: white; }
.chat-message:not(.own) .message-menu-body { left: 8px; right: auto; }
.message-menu-body > button { display: flex; gap: 8px; border: 0; background: none; padding: 8px; width: 100%; text-align: left; font-size: .78rem; color: #486589; border-radius: 6px; }
.message-menu-body > button:hover { background: #f0f5fc; }
.reaction-options { display: flex; border-top: 1px solid #edf1f6; padding-top: 5px; }
.reaction-options button { border: 0; background: transparent; padding: 5px; font-size: 1.05rem; }
.message-reactions { display: flex; flex-wrap: wrap; gap: 4px; margin-top: 7px; }
.message-reactions button { border: 1px solid #dce5f1; border-radius: 12px; padding: 2px 7px; background: #fff; font-size: .74rem; }
.message-reactions button.mine { background: #dbeaff; border-color: #9abfea; }
.reply-quote { display: block; width: 100%; padding: 6px 8px; border: 0; border-left: 3px solid #8bb3e7; border-radius: 5px; background: #dbe7f580; text-align: left; margin: 3px 0 7px; color: #547196; }
.reply-quote strong, .reply-quote span { display: block; font-size: .74rem; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.chat-text { white-space: pre-wrap; }
.chat-mention { color: #225ca6; background: #d5e6ff; border-radius: 4px; padding: 1px 3px; font-weight: 600; }
.message-time { display: block; text-align: right; color: #8a99ad; font-size: .67rem; margin-top: 4px; }
.message-read-status { text-align: right; color: #6884a8; font-size: .67rem; margin-top: 3px; }.message-read-status summary { cursor: pointer; }.read-people { text-align: left; border-top: 1px solid #cfddf1; margin-top: 5px; padding-top: 5px; }.read-people > span { display: block; padding: 3px 0; }.read-people small { display: block; font-size: inherit; opacity: .8; }
.record-card { display: flex; align-items: center; gap: 9px; border: 1px solid #cfddf1; background: #ffffffa8; border-radius: 12px; text-align: left; color: #2b629c; padding: 10px; width: 100%; margin-top: 6px; }
.record-card span { flex: 1; min-width: 0; }.record-card strong { display: block; font-size: .78rem; }.record-card small { display: block; font-size: .65rem; opacity: .7; }
</style>
