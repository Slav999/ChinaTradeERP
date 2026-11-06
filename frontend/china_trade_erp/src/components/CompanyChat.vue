<template>
  <div v-if="companyId" ref="chatRoot" class="company-chat" data-chat-ui>
    <button class="chat-launcher btn btn-light shadow-sm" type="button" :aria-expanded="isOpen" aria-controls="company-chat-panel" @click="toggle">
      <span class="launcher-icon"><i class="bi" :class="isOpen ? 'bi-x-lg' : 'bi-chat-dots-fill'" aria-hidden="true"></i></span><span>Чат</span>
      <span v-if="unread" class="badge rounded-pill bg-primary">{{ unread > 99 ? '99+' : unread }}</span>
    </button>

    <section v-if="isOpen" id="company-chat-panel" class="chat-panel shadow" aria-label="Чат компании" @keydown.esc="isOpen = false">
      <header class="d-flex align-items-center gap-2 border-bottom p-3">
        <button v-if="selected || creating" class="chat-icon" type="button" title="Назад к диалогам" aria-label="Назад к диалогам" @click="back"><i class="bi bi-chevron-left"></i></button>
        <span v-else class="chat-avatar company-avatar"><img v-if="companyLogo && !logoFailed" :src="companyLogo" :alt="companyName" @error="logoFailed = true"><i v-else class="bi bi-building"></i></span>
        <div class="flex-grow-1 overflow-hidden">
          <strong class="d-block text-truncate"><span v-if="selected && !creating" data-i18n-skip>{{ selected.title }}</span><template v-else>{{ creating ? 'Новый чат' : 'Команда на связи' }}</template></strong>
          <button v-if="selected?.is_group" class="participant-count" data-i18n-attributes-skip :title="participantTooltip" @click="openSettings">{{ selected.participants.length }} участников</button>
          <small v-else class="text-muted" data-i18n-skip>{{ companyName }}</small>
        </div>
        <button v-if="!selected && !creating" class="chat-icon accent" type="button" title="Новый чат" aria-label="Новый чат" @click="startCreate"><i class="bi bi-pencil-square"></i></button>
        <button v-if="selected" class="chat-icon" type="button" title="Поиск и материалы" aria-label="Поиск и материалы" @click="openResources('search')"><i class="bi bi-search"></i></button>
        <button v-if="selected" class="chat-icon" type="button" title="Настройки чата" aria-label="Настройки чата" @click="openSettings"><i class="bi bi-three-dots"></i></button>
        <button class="chat-icon" type="button" aria-label="Закрыть чат" @click="isOpen = false"><i class="bi bi-x-lg"></i></button>
      </header>
      <div v-if="error" class="alert alert-warning m-2 py-2 small" role="alert">{{ error }} <button class="btn btn-sm btn-link p-0" @click="retry">Повторить</button></div>

      <div v-if="shareChoosing" class="share-banner"><i class="bi bi-send"></i><span>Кому отправить: <strong data-i18n-skip>{{ referenceTitle(pendingReference) }}</strong></span><button class="chat-icon" title="Отменить" @click="cancelShare"><i class="bi bi-x"></i></button></div>
      <div v-if="confirmAction" class="chat-confirm p-3 border-bottom">
        <strong>{{ confirmAction === 'transfer' ? 'Передать управление выбранному участнику?' : confirmAction === 'leave' ? 'Выйти из группы?' : confirmAction === 'clear' ? 'Очистить историю у вас?' : selected?.is_group ? 'Удалить группу для всех участников?' : 'Удалить переписку у вас?' }}</strong>
        <p class="small text-muted mt-1 mb-2">{{ confirmAction === 'delete' && selected?.is_group ? 'Участники потеряют доступ к сообщениям и вложениям этой группы.' : 'История у других участников сохранится.' }}</p>
        <div class="d-flex gap-2"><button class="btn btn-sm btn-danger" :disabled="busy" @click="performAction">Подтвердить</button><button class="btn btn-sm btn-light" @click="confirmAction = ''">Отмена</button></div>
      </div>
      <ChatResources v-if="resourcesOpen && selected" :key="`${companyId}-${selected.id}-${resourceTab}`" :room-id="selected.id" :company-id="companyId" :revision="selected.revision" :initial-tab="resourceTab" @close="resourcesOpen = false" @jump="jumpToMessage" @reference="openReference" />
      <form v-else-if="managing" class="chat-content p-3" @submit.prevent="saveGroup">
        <div class="d-flex align-items-center justify-content-between mb-3"><strong>{{ selected.is_group ? 'Настройки группы' : 'Настройки переписки' }}</strong><button type="button" class="chat-icon" aria-label="Закрыть настройки" @click="managing = false"><i class="bi bi-x-lg"></i></button></div>
        <template v-if="selected.is_group && isGroupAdmin">
          <label class="d-block mb-3 small">Название группы<input v-model="editTitle" class="form-control mt-1" maxlength="120" required></label>
          <strong class="small">Участники · {{ editMembers.length }}</strong>
          <div class="group-member-list"><div v-for="person in groupMembers" :key="person.id" class="member-row"><span class="chat-avatar small-avatar" data-i18n-skip :style="avatarStyle(person.id)">{{ initials(person.name) }}</span><span class="flex-grow-1"><span data-i18n-skip>{{ person.name }}</span><small v-if="person.id === userId" class="d-block text-muted">Администратор группы</small></span><button v-if="person.id !== userId" type="button" class="chat-icon remove-member" :title="`Убрать ${person.name} из группы`" :aria-label="`Убрать ${person.name} из группы`" @click="removeMember(person.id)"><i class="bi bi-trash3"></i></button></div></div>
          <label class="d-block small mt-3">Добавить сотрудника<input v-model="memberSearch" class="form-control my-2" placeholder="Введите имя или ник"></label>
          <small v-if="memberSearch.trim() && !memberCandidates.length" class="text-muted">Подходящих сотрудников вне группы не найдено.</small>
          <button v-for="person in memberCandidates" :key="person.id" type="button" class="member-result" :disabled="editMembers.length >= 100" @click="addMember(person)"><span class="chat-avatar small-avatar" data-i18n-skip :style="avatarStyle(person.id)">{{ initials(person.name) }}</span><span class="flex-grow-1 text-start"><span data-i18n-skip>{{ person.name }}</span></span><i class="bi bi-plus-lg"></i></button>
          <small class="text-muted d-block my-2">Изменения применятся после сохранения. Добавленные участники видят всю историю группы.</small>
          <button class="btn btn-primary w-100" :disabled="busy || !editTitle.trim() || editMembers.length > 100">Сохранить изменения</button>
        </template>
        <div v-else-if="selected.is_group" class="mb-3"><p class="small text-muted">Составом группы управляет её администратор.</p><div v-for="person in selected.participants" :key="person.id" class="member-row"><span class="chat-avatar small-avatar" data-i18n-skip :style="avatarStyle(person.id)">{{ initials(person.name) }}</span><span data-i18n-skip>{{ person.name }}</span><small v-if="person.id === (selected.owner_id || selected.created_by_id)" class="text-muted">Администратор</small></div></div>
        <label class="d-block small mt-3">Звук в этой переписке<select :value="selected.notification_mode || 'all'" class="form-select form-select-sm mt-1" :disabled="busy" @change="updatePreferences({ notification_mode: $event.target.value })"><option value="all">Все новые сообщения</option><option value="mentions">Только упоминания</option><option value="off">Без звука</option></select></label>
        <button type="button" class="btn btn-sm btn-outline-primary mt-3" :disabled="busy || loadingMessages" @click="markUnread"><i class="bi bi-envelope me-2"></i>Пометить непрочитанным</button>
        <div v-if="selected.is_group && isGroupAdmin" class="mt-3">
          <label for="chat-transfer-user" class="small d-block mb-1">Передать управление</label>
          <div class="d-flex align-items-center gap-2">
            <select id="chat-transfer-user" v-model.number="transferUser" class="form-select form-select-sm flex-grow-1 w-auto" style="min-width: 0"><option :value="null">Выберите участника</option><option v-for="person in selected.participants.filter(p => p.id !== userId)" :key="person.id" :value="person.id" data-i18n-skip>{{ person.name }}</option></select>
            <button type="button" class="btn btn-sm btn-outline-primary flex-shrink-0 text-nowrap" :disabled="busy || !transferUser" @click="confirmAction = 'transfer'">Передать управление</button>
          </div>
        </div>
        <button v-if="selected.can_take_over" type="button" class="btn btn-sm btn-outline-primary mt-3" :disabled="busy" @click="transferUser = userId; confirmAction = 'transfer'">Восстановить управление группой</button>
        <div v-if="selected.is_group" class="mt-3"><button type="button" class="btn btn-sm btn-outline-secondary" @click="confirmAction = 'leave'">Выйти из группы</button></div>
        <div class="d-grid gap-2 mt-4"><button type="button" class="btn btn-sm btn-outline-secondary" @click="confirmAction = 'clear'"><i class="bi bi-eraser me-2"></i>Очистить историю у меня</button><button v-if="!selected.is_group || isGroupAdmin" type="button" class="btn btn-sm btn-outline-danger" @click="confirmAction = 'delete'"><i class="bi bi-trash3 me-2"></i>{{ selected.is_group ? 'Удалить группу для всех' : 'Удалить переписку у меня' }}</button></div>
      </form>
      <form v-else-if="creating" class="chat-content p-3" @submit.prevent="createRoom">
        <div class="d-flex gap-3 mb-3">
          <label><input v-model="group" type="radio" :value="false" @change="chosen = []"> Личный</label>
          <label><input v-model="group" type="radio" :value="true" @change="chosen = []"> Группа</label>
        </div>
        <label v-if="group" class="d-block mb-3">Название группы
          <input v-model="title" class="form-control mt-1" maxlength="120" required placeholder="Например, продажи">
        </label>
        <label class="d-block">Поиск сотрудника<input v-model="search" class="form-control mt-1 mb-2" placeholder="Имя сотрудника"></label>
        <p v-if="loadingEmployees" class="text-muted">Загрузка сотрудников…</p>
        <p v-else-if="!filteredEmployees.length" class="text-muted">Сотрудники не найдены.</p>
        <label v-for="person in filteredEmployees" :key="person.id" class="member-row">
          <input v-if="group" v-model="chosen" type="checkbox" :value="person.id">
          <input v-else v-model="directPerson" type="radio" :value="person.id" name="chat-employee">
          <span class="chat-avatar small-avatar" data-i18n-skip :style="avatarStyle(person.id)">{{ initials(person.name) }}</span><span data-i18n-skip>{{ person.name }}</span>
        </label>
        <small v-if="group" class="d-block text-muted my-2">Вы — администратор группы. Выбрано коллег: {{ chosen.length }}.</small>
        <button class="btn btn-primary w-100 mt-3" :disabled="busy || loadingEmployees || (group ? !title.trim() || !chosen.length || chosen.length > 99 : !directPerson)">Открыть чат</button>
      </form>

      <template v-else-if="selected">
        <button v-if="pinnedMessages.length" class="pinned-strip" @click="openResources('pins')"><i class="bi bi-pin-angle-fill"></i><span>Закреплено · {{ pinnedMessages.length }} — <span v-if="pinnedMessages[0].text" data-i18n-skip>{{ pinnedMessages[0].text }}</span><span v-else>Вложение или объект</span></span></button>
        <button v-if="!canReadPage && firstUnreadId" class="btn btn-sm btn-light rounded-0" @click="jumpToUnread">Перейти к непрочитанным</button>
        <div ref="messageList" class="chat-content chat-messages p-3" @scroll="onScroll">
          <button v-if="hasOlder" class="btn btn-sm btn-outline-secondary d-block mx-auto mb-3" :disabled="loadingOlder" @click="loadOlder">{{ loadingOlder ? 'Загрузка…' : 'Предыдущие сообщения' }}</button>
          <p v-if="loadingMessages" class="text-muted text-center">Загрузка…</p>
          <p v-else-if="!messages.length" class="text-muted text-center small">Напишите первое сообщение.</p>
          <template v-for="item in timeline" :key="item.key"><div v-if="item.type === 'event'" class="system-event">{{ item.value.text }}</div><template v-else><div v-if="item.value.id === unreadBoundary" class="unread-divider">Новые сообщения</div><ChatMessageItem :message="item.value" :user-id="userId" :room-id="selected.id" :company-id="companyId" :group="selected.is_group" :can-pin="!selected.is_group || isGroupAdmin" :focused="focusedMessageId === item.value.id" :read-status="readStatuses[item.value.id]" @reply="startReply" @edit="startEdit" @delete="deleteMessage" @pin="pinMessage" @react="reactMessage" @jump="jumpToMessage" @reference="openReference" @loaded="onImageLoaded" /></template></template>
          <div v-if="activeDelivery && (activeDelivery.status !== 'sent' || !messages.some(message => message.id === activeDelivery.messageId))" class="pending-message"><div v-if="activeDelivery.text" data-i18n-skip>{{ activeDelivery.text }}</div><div v-else>Вложение или объект</div><small v-if="activeDelivery.status === 'sending'">{{ activeDelivery.files.length ? `Загрузка ${activeDelivery.progress}%` : 'Отправляется…' }}</small><small v-else-if="activeDelivery.status === 'sent'">Отправлено</small><div v-else><small class="text-danger">Не отправлено</small><button class="btn btn-sm btn-link" @click="retryDelivery">Повторить</button></div><div v-if="activeDelivery.status === 'sending' && activeDelivery.files.length" class="progress mt-1" style="height: 3px"><div class="progress-bar" :style="{ width: `${activeDelivery.progress}%` }"></div></div></div>
          <button v-if="hasNewer" class="btn btn-sm btn-outline-secondary mx-auto my-2" :disabled="loadingMessages" @click="loadNewer">Следующие сообщения</button>
        </div>
        <button v-if="!atBottom || hasNewer" class="btn btn-sm btn-light border-top rounded-0" @click="jumpToLatest">К последним сообщениям <i class="bi bi-arrow-down-short"></i></button>
        <div v-if="referencePicker" class="reference-picker border-top p-3">
          <div class="d-flex gap-2"><select v-model="referenceKind" class="form-select form-select-sm" @change="scheduleReferenceSearch"><option v-for="kind in referenceKinds" :key="kind.type" :value="kind.type">{{ kind.label }}</option></select><button class="chat-icon" aria-label="Закрыть поиск" @click="closeReferencePicker"><i class="bi bi-x"></i></button></div>
          <div class="input-group input-group-sm my-2"><span class="input-group-text"><i class="bi bi-search"></i></span><input v-model="referenceSearch" class="form-control" placeholder="Номер, артикул или контрагент" @input="scheduleReferenceSearch"></div>
          <small v-if="searchingReferences" class="text-muted">Поиск…</small><small v-else-if="!referenceSearch.trim()" class="text-muted">Начните вводить номер, название, артикул или контрагента.</small><small v-else-if="!referenceResults.length" class="text-muted">Ничего не найдено</small>
          <button v-for="record in referenceResults" :key="`${record.type}-${record.id}`" class="reference-result" @click="attachReference(record)"><i class="bi" :class="referenceIcon(record.type)"></i><span data-i18n-skip>{{ referenceTitle(record) }}</span></button>
        </div>
        <form class="chat-composer border-top p-3" @submit.prevent="send">
          <div v-if="editTarget || replyTarget" class="compose-context"><i class="bi" :class="editTarget ? 'bi-pencil' : 'bi-reply'"></i><span><strong>{{ editTarget ? 'Редактирование сообщения' : `Ответ: ${replyTarget.sender_name}` }}</strong><small v-if="(editTarget || replyTarget).text" data-i18n-skip>{{ (editTarget || replyTarget).text }}</small><small v-else>Вложение или объект</small></span><button type="button" class="chat-icon" aria-label="Отменить" @click="cancelComposeContext"><i class="bi bi-x"></i></button></div>
          <small v-if="missingDraftFiles" class="text-warning d-block mb-2">Черновик восстановлен. Прикрепите файлы повторно.</small>
          <div v-if="emojiOpen" ref="emojiPicker" class="emoji-picker" role="group" aria-label="Смайлики"><button v-for="emoji in emojis" :key="emoji.value" type="button" :title="emoji.label" :aria-label="emoji.label" @pointerdown.prevent @click="insertEmoji(emoji.value)">{{ emoji.value }}</button></div>
          <div v-if="pendingReference && !shareChoosing" class="share-banner mb-2"><i class="bi" :class="referenceIcon(pendingReference.type)"></i><span data-i18n-skip>{{ referenceTitle(pendingReference) }}</span><button type="button" class="chat-icon" title="Убрать объект" :disabled="sending" @click="pendingReference = null"><i class="bi bi-x"></i></button></div>
          <div v-if="files.length" class="pending-files mb-2"><span v-for="(file, index) in files" :key="index"><i class="bi bi-paperclip"></i><span data-i18n-skip>{{ file.name }}</span><button type="button" :disabled="sending" :aria-label="`Убрать ${file.name}`" @click="files.splice(index, 1)"><i class="bi bi-x"></i></button></span></div>
          <label for="chat-message-text" class="visually-hidden">Сообщение</label>
          <div v-if="mentionCandidates.length" class="mention-picker" role="listbox" aria-label="Упомянуть сотрудника"><button v-for="(person, index) in mentionCandidates" :key="person.id" type="button" role="option" :aria-selected="index === mentionIndex" :class="{ active: index === mentionIndex }" @pointerdown.prevent @click="insertMention(person)"><strong data-i18n-skip>@{{ person.username }}</strong><small><span data-i18n-skip>{{ person.name }}</span></small></button></div>
          <textarea id="chat-message-text" ref="composerText" v-model="draft" class="form-control" rows="2" maxlength="5000" placeholder="Напишите сообщение… @ — упомянуть" :disabled="sending" @paste="pasteFiles" @input="updateMentionQuery" @click="updateMentionQuery" @keyup.left="updateMentionQuery" @keyup.right="updateMentionQuery" @keydown="composerKeydown"></textarea>
          <div class="d-flex align-items-center justify-content-between mt-2">
            <div class="d-flex align-items-center gap-1"><button type="button" class="chat-icon" title="Прикрепить фото или документ" aria-label="Прикрепить файл" :disabled="sending || Boolean(editTarget)" @click="fileInput.click()"><i class="bi bi-paperclip"></i></button><button type="button" class="chat-icon" title="Прикрепить заказ, товар или контрагента" aria-label="Прикрепить объект" :disabled="sending || Boolean(editTarget)" @click="openReferencePicker"><i class="bi bi-box-seam"></i></button><button ref="emojiToggle" type="button" class="chat-icon" title="Смайлики" aria-label="Смайлики" :disabled="sending" :aria-expanded="emojiOpen" @click="emojiOpen = !emojiOpen"><i class="bi bi-emoji-smile"></i></button><small class="composer-hint">Shift+Enter — перенос строки</small></div>
            <input ref="fileInput" type="file" class="d-none" multiple accept=".jpg,.jpeg,.png,.webp,.gif,.pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.txt,.csv" @change="chooseFiles">
            <button class="chat-send" :title="editTarget ? 'Сохранить изменения' : 'Отправить'" :aria-label="editTarget ? 'Сохранить изменения' : 'Отправить сообщение'" :disabled="sending || loadingMessages || missingDraftFiles || (!draft.trim() && !files.length && !pendingReference)"><span v-if="sending" class="spinner-border spinner-border-sm"></span><i v-else class="bi" :class="editTarget ? 'bi-check-lg' : 'bi-send-fill'"></i></button>
          </div>
        </form>
      </template>

      <div v-else class="chat-content">
        <div class="chat-list-tools p-3 border-bottom"><div class="d-flex gap-2"><div class="chat-search-field position-relative flex-grow-1"><input ref="roomSearchInput" v-model="roomSearch" class="form-control form-control-sm" :class="{ 'pe-5': roomSearch }" placeholder="Чат, сотрудник, артикул…" aria-label="Поиск чатов" @input="scheduleRoomSearch"><button v-if="roomSearch" type="button" class="chat-icon search-clear" title="Очистить поиск" aria-label="Очистить поиск" @click="clearRoomSearch"><i class="bi bi-x-lg"></i></button></div><button class="chat-icon" :class="{ accent: archivedView }" title="Архив" aria-label="Архив" @click="toggleArchive"><i class="bi bi-archive"></i></button></div><div v-if="relatedFilter" class="small text-primary mt-2">Обсуждения: <span data-i18n-skip>{{ referenceTitle(relatedFilter) }}</span> <button class="btn btn-sm btn-link p-0" @click="clearRelated">Сбросить</button></div></div>
        <p v-if="!rooms.length" class="text-muted text-center p-4">{{ relatedFilter ? 'Доступных вам обсуждений этого объекта пока нет.' : roomSearch || archivedView ? 'Переписки не найдены.' : 'Пока нет переписок. Нажмите кнопку с карандашом, чтобы написать коллеге или создать группу.' }}</p>
        <div v-for="room in rooms" :key="room.id" class="chat-room-row position-relative">
        <button class="chat-room w-100 text-start border-0 border-bottom p-3" type="button" @click="selectRoom(room, { mention: Boolean(room.unread_mention_count) })">
          <span class="chat-avatar" data-i18n-skip :style="avatarStyle(room.id)"><i v-if="room.is_group" class="bi bi-people-fill"></i><template v-else>{{ initials(room.title) }}</template></span>
          <span class="room-copy"><span class="d-flex justify-content-between gap-2"><strong class="text-truncate" data-i18n-skip>{{ room.title }}</strong><span v-if="room.unread_count" class="badge rounded-pill bg-primary">{{ room.unread_count }}</span></span><small v-if="room.unread_mention_count" class="mention-label">@ Вас упомянули<span v-if="room.unread_mention_count > 1"> · {{ room.unread_mention_count }}</span></small><small v-if="draftPreviews[room.id]" class="d-block text-truncate draft-preview"><strong>Черновик:</strong> <span data-i18n-skip>{{ draftPreviews[room.id] }}</span></small><small v-else class="d-block text-muted text-truncate"><span v-if="room.last_text && !room.last_message_deleted" data-i18n-skip>{{ room.last_text }}</span><template v-else>{{ room.last_text || (room.last_time ? 'Вложение или объект' : 'Начните переписку') }}</template></small></span><i class="bi bi-chevron-right text-muted small"></i>
        </button>
        <button type="button" class="chat-icon room-archive" :disabled="archivingRoom !== null" :title="room.is_archived ? 'Вернуть из архива' : 'В архив'" :aria-label="`${room.is_archived ? 'Вернуть из архива' : 'В архив'}: ${room.title}`" @click.stop="archiveRoom(room)"><span v-if="archivingRoom === room.id" class="spinner-border spinner-border-sm"></span><i v-else class="bi" :class="room.is_archived ? 'bi-arrow-up-square' : 'bi-archive'"></i></button>
        </div>
        <button v-if="hasMoreRooms" class="btn btn-sm btn-outline-secondary d-block mx-auto my-3" :disabled="roomsLoading" @click="loadMoreRooms">Показать ещё</button>
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import axios, { AUTH_SESSION_KEY } from '../axios'
import { accessState, loadCurrentUser, setCurrentUser } from '../access'
import { useRouter } from 'vue-router'
import { languageState } from '../i18n'
import { chatReferenceTitle, translateChatText } from '../utils/chatTranslations'
import ChatMessageItem from './ChatMessageItem.vue'
import ChatResources from './ChatResources.vue'
import { playNotificationSound } from '../utils/notificationSound'
import { createIncomingTracker } from '../utils/chatUpdates'
import { draftKey } from '../utils/chatDrafts'
import { useChatDrafts } from '../composables/useChatDrafts'
import { useChatDelivery } from '../composables/useChatDelivery'
import { mergeMessages, readStatusRows, visibleMessageIds } from '../utils/chatThread'

const router = useRouter()

const companyId = computed(() => accessState.user?.company_id)
const companyName = computed(() => accessState.user?.company_name || translateChatText('Текущая компания', languageState.locale))
const companyLogo = computed(() => accessState.user?.company_logo_url || '')
const logoFailed = ref(false)
watch(companyLogo, () => { logoFailed.value = false })
const userId = computed(() => accessState.user?.id)
const isOpen = ref(false), rooms = ref([]), unread = ref(0), selected = ref(null)
const roomSearch = ref(''), archivedView = ref(false), relatedFilter = ref(null), hasMoreRooms = ref(false), roomsLoading = ref(false)
const roomOffset = ref(0), resourcesOpen = ref(false), resourceTab = ref('search')
const events = ref([]), pinnedMessages = ref([]), hasNewer = ref(false), syncRevision = ref(0), readCursor = ref(0)
const readStatuses = ref({})
let readStatusSequence = 0
const firstUnreadId = ref(null), unreadBoundary = ref(null), canReadPage = ref(true), focusedMessageId = ref(null)
const transferUser = ref(null), archivingRoom = ref(null), roomSearchInput = ref(null)
let locallyRead = new Set()
let roomSearchTimer, employeeSearchTimer, readTimer
const emojiOpen = ref(false)
const emojiPicker = ref(null), emojiToggle = ref(null)
const emojis = [
  { value: '🙂', label: 'Улыбка' }, { value: '😊', label: 'Радость' },
  { value: '😀', label: 'Широкая улыбка' }, { value: '😁', label: 'Очень рад' },
  { value: '😂', label: 'Смех' }, { value: '😅', label: 'Облегчение' },
  { value: '😉', label: 'Подмигивание' }, { value: '😎', label: 'Круто' },
  { value: '🤔', label: 'Думаю' }, { value: '😮', label: 'Удивление' },
  { value: '😢', label: 'Грусть' }, { value: '😡', label: 'Недовольство' },
  { value: '😴', label: 'Сон' }, { value: '👍', label: 'Одобряю' },
  { value: '👎', label: 'Не согласен' }, { value: '👌', label: 'Хорошо' },
  { value: '👏', label: 'Отлично' }, { value: '🤝', label: 'Договорились' },
  { value: '🙏', label: 'Спасибо' }, { value: '💪', label: 'Справимся' },
  { value: '👀', label: 'Смотрю' }, { value: '❤️', label: 'Сердце' },
  { value: '🔥', label: 'Огонь' }, { value: '💡', label: 'Идея' },
  { value: '📌', label: 'Важно' }, { value: '✅', label: 'Готово' },
  { value: '📦', label: 'Товар' }, { value: '🚚', label: 'Доставка' },
  { value: '🎉', label: 'Поздравляю' }, { value: '🚀', label: 'Поехали' },
]
const messages = ref([]), error = ref(''), creating = ref(false)
const employees = ref([]), search = ref(''), chosen = ref([]), directPerson = ref(null)
const group = ref(false), title = ref(''), busy = ref(false)
const loadingEmployees = ref(false), loadingMessages = ref(false), loadingOlder = ref(false)
const hasOlder = ref(false), atBottom = ref(true), messageList = ref(null)
const chatRoot = ref(null), composerText = ref(null), mentionQuery = ref(null), mentionIndex = ref(0)
const incomingTracker = createIncomingTracker()
const participantTooltip = computed(() => {
  const people = selected.value?.participants || []
  return people.slice(0, 7).map(person => person.name).join('\n') + (people.length > 7 ? '\n' + translateChatText('… Полный список — в меню ⋯', languageState.locale) : '')
})
const mentionCandidates = computed(() => {
  if (mentionQuery.value === null || !selected.value) return []
  const query = mentionQuery.value.query.toLocaleLowerCase()
  return selected.value.participants.filter(person => person.id !== userId.value && person.username &&
    (person.username.toLocaleLowerCase().startsWith(query) || person.name.toLocaleLowerCase().includes(query))).slice(0, 6)
})
const managing = ref(false), editTitle = ref(''), editMembers = ref([]), memberSearch = ref(''), confirmAction = ref('')
const fileInput = ref(null), shareChoosing = ref(false)
const referencePicker = ref(false), referenceSearch = ref(''), referenceKind = ref('customer_order'), referenceResults = ref([]), searchingReferences = ref(false)
const referenceKinds = [{ type: 'customer_order', label: 'Заказы покупателей' }, { type: 'supplier_order', label: 'Заказы поставщикам' }, { type: 'product', label: 'Товары' }, { type: 'counterparty', label: 'Контрагенты' }]
const isGroupAdmin = computed(() => selected.value?.is_group && (selected.value.owner_id || selected.value.created_by_id) === userId.value)
const timeline = computed(() => {
  const first = messages.value[0]?.id || 0, last = messages.value.at(-1)?.id || 0
  const system = events.value.filter(event => (!hasOlder.value || event.after_message_id >= first) && event.after_message_id <= last)
  return [...messages.value.map(value => ({ type: 'message', value, key: `m${value.id}` })),
    ...system.map(value => ({ type: 'event', value, key: `e${value.id}` }))]
    .sort((a, b) => new Date(a.value.created_at) - new Date(b.value.created_at) || a.value.id - b.value.id)
})
const allMemberPeople = computed(() => {
  const people = new Map((selected.value?.participants || []).map(person => [person.id, person]))
  stagedPeople.value.forEach(person => people.set(person.id, person))
  employees.value.forEach(person => people.set(person.id, person))
  return [...people.values()]
})
const stagedPeople = ref([])
const groupMembers = computed(() => allMemberPeople.value.filter(person => editMembers.value.includes(person.id)))
const memberCandidates = computed(() => {
  const query = memberSearch.value.trim().toLocaleLowerCase()
  if (!query) return []
  return allMemberPeople.value.filter(person => !editMembers.value.includes(person.id) &&
    `${person.name} ${person.username || ''}`.toLocaleLowerCase().includes(query)).slice(0, 5)
})
const filteredEmployees = computed(() => employees.value.filter(p => `${p.name} ${p.username || ''}`.toLocaleLowerCase().includes(search.value.trim().toLocaleLowerCase())))
let epoch = 0, timer, polling = false, disposed = false, marking = false, readRequest
let discussionSignature = ''
function notifyDiscussionsChanged() { window.dispatchEvent(new Event('chat-discussions-changed')) }
const drafts = useChatDrafts({
  api: axios, userId, companyId, rooms, selected,
  formatText: value => translateChatText(value, languageState.locale), formatReference: referenceTitle,
  hasSession: () => Boolean(localStorage.getItem(AUTH_SESSION_KEY)),
  isCurrent: token => token === epoch && !disposed,
  reportError: message => { error.value = message },
})
const { draft, files, pendingReference, replyTarget, editTarget, pendingSend, activeDraftKey, missingDraftFiles, draftPreviews,
  save: saveCurrentDraft, restore: restoreCurrentDraft, cancelContext: cancelComposeContext } = drafts
const delivery = useChatDelivery({
  api: axios, drafts, selected, companyId, loadingMessages, error, getEpoch: () => epoch, onFailure: failure,
  onAccepted: async (message, entry, cleared) => {
    if (cleared) mentionQuery.value = null
    if (selected.value?.is_archived) {
      archivedView.value = false; rooms.value = []; roomOffset.value = 0
    }
    applyChangedMessage(message)
    const token = epoch
    await fetchRooms(token)
    if (token !== epoch || disposed || activeDraftKey.value !== entry.key) return
    await fetchNew(token)
    if (token === epoch && atBottom.value && !hasNewer.value) await scrollBottom()
    await fetchReadStatuses(token)
  },
})
const { activeDelivery, sending, retry: retryDelivery } = delivery

function config() { return { params: { company_id: companyId.value } } }
function clearThreadState() {
  readStatuses.value = {}; readStatusSequence++
  drafts.resetContext()
  locallyRead = new Set()
  events.value = []; pinnedMessages.value = []; hasNewer.value = false; resourcesOpen.value = false
  firstUnreadId.value = null; unreadBoundary.value = null; readCursor.value = 0; focusedMessageId.value = null
  syncRevision.value = 0; canReadPage.value = true; missingDraftFiles.value = false; transferUser.value = null
}
function reset() {
  saveCurrentDraft(); activeDraftKey.value = ''; clearThreadState()
  epoch++
  rooms.value = []; unread.value = 0; selected.value = null; messages.value = []
  employees.value = []; draft.value = ''; error.value = ''; creating.value = false
  chosen.value = []; directPerson.value = null; search.value = ''; title.value = ''
  pendingSend.value = null; marking = false
  incomingTracker.reset(); mentionQuery.value = null
  roomSearch.value = ''; relatedFilter.value = null; roomOffset.value = 0; hasMoreRooms.value = false
  emojiOpen.value = false; cancelReferenceSearch()
  managing.value = false; confirmAction.value = ''; files.value = []; pendingReference.value = null; shareChoosing.value = false
  referencePicker.value = false; referenceResults.value = []
  loadingMessages.value = false; loadingEmployees.value = false; busy.value = false
}
async function failure(err, token) {
  if (token !== epoch || disposed) return
  if ([401, 403, 409].includes(err.response?.status)) {
    reset()
    error.value = 'Доступ или компания изменились. Обновляем чат…'
    try { await loadCurrentUser({ force: true }) } catch { /* Existing auth flow handles expired sessions. */ }
  } else {
    const detail = err.response?.data
    error.value = err.response?.status === 429 ? 'Слишком много запросов. Подождите немного.' : (typeof detail === 'string' ? detail : detail?.detail || (Array.isArray(detail) ? detail.join(' ') : 'Не удалось выполнить действие. Проверьте данные и соединение.'))
  }
}
async function fetchRooms(token = epoch, { more = false, compact = false } = {}) {
  const filterSignature = () => JSON.stringify([roomSearch.value, archivedView.value, relatedFilter.value?.type, relatedFilter.value?.id])
  const signature = filterSignature()
  const query = { ...config().params, q: roomSearch.value, archived: archivedView.value ? 1 : undefined,
    offset: more ? roomOffset.value : 0, selected_id: selected.value?.id, compact: compact ? 1 : undefined }
  const endpoint = relatedFilter.value && !compact ? '/api/chat/related/' : '/api/chat/conversations/'
  if (relatedFilter.value && !compact) { query.reference_type = relatedFilter.value.type; query.reference_id = relatedFilter.value.id }
  const { data } = await axios.get(endpoint, { params: query })
  if (token !== epoch || disposed || (!compact && signature !== filterSignature())) return
  const incoming = incomingTracker.update(data.notifications || data.results)
  const nextDiscussionSignature = `${userId.value}:${companyId.value}:` + (data.notifications || data.results)
    .map(room => `${room.id}:${room.revision}`).sort().join(',')
  if (nextDiscussionSignature !== discussionSignature) {
    discussionSignature = nextDiscussionSignature; notifyDiscussionsChanged()
  }
  if (incoming) playNotificationSound(`chat:${userId.value}:${companyId.value}:${incoming.roomId}:${incoming.messageId}`)
  unread.value = data.unread_count
  if (compact) return
  const allowed = new Set((data.notifications || data.results).map(room => room.id))
  const merged = new Map((more ? rooms.value : rooms.value.slice(data.results.length)).filter(room => allowed.has(room.id)).map(room => [room.id, room]))
  data.results.forEach(room => merged.set(room.id, room))
  rooms.value = more ? [...merged.values()] : [...data.results, ...[...merged.values()].filter(room => !data.results.some(row => row.id === room.id))]
  roomOffset.value = more ? data.next_offset : Math.max(roomOffset.value, data.next_offset || 0)
  hasMoreRooms.value = data.total_count === undefined ? data.has_more : rooms.value.length < data.total_count
  if (selected.value) {
    const room = data.selected || rooms.value.find(r => r.id === selected.value.id)
    if (room) {
      if (room.history_after_id !== selected.value.history_after_id) {
        messages.value = messages.value.filter(message => message.id > room.history_after_id)
        events.value = []; hasOlder.value = false; unreadBoundary.value = null
        firstUnreadId.value = null; canReadPage.value = true
      }
      readCursor.value = Math.max(readCursor.value, room.last_read_id || 0)
      if (!room.unread_count) { firstUnreadId.value = null; canReadPage.value = true }
      selected.value = room
    }
    else { drafts.forget(); activeDraftKey.value = ''; back() }
  }
}
async function poll() {
  if (polling || !companyId.value || disposed) return
  polling = true
  const token = epoch
  try {
    await fetchRooms(token, { compact: !isOpen.value || document.hidden })
    if (token === epoch && isOpen.value && selected.value && !loadingMessages.value && !document.hidden) {
      await fetchNew(token)
      await fetchReadStatuses(token)
    }
  } catch (err) { await failure(err, token) }
  finally { polling = false }
}
function back() {
  saveCurrentDraft(); activeDraftKey.value = ''; clearThreadState()
  epoch++; selected.value = null; creating.value = false; messages.value = []; draft.value = ''; error.value = ''; pendingSend.value = null
  loadingMessages.value = false; busy.value = false; managing.value = false; confirmAction.value = ''; files.value = []; referencePicker.value = false
  mentionQuery.value = null
  emojiOpen.value = false; cancelReferenceSearch()
  if (!shareChoosing.value) pendingReference.value = null
}
async function toggle() {
  isOpen.value = !isOpen.value
  if (!isOpen.value) { saveCurrentDraft(); return }
  await poll()
  if (selected.value) await openThread(relatedFilter.value
    ? { reference_type: relatedFilter.value.type, reference_id: relatedFilter.value.id } : { initial: 1 })
}
async function selectRoom(room, { mention = false } = {}) {
  saveCurrentDraft()
  const shared = shareChoosing.value ? pendingReference.value : null
  epoch++; const token = epoch
  clearThreadState()
  selected.value = room; creating.value = false; messages.value = []; draft.value = ''; error.value = ''
  emojiOpen.value = false; cancelReferenceSearch()
  mentionQuery.value = null
  managing.value = false; confirmAction.value = ''; files.value = []; referencePicker.value = false
  if (!shareChoosing.value) pendingReference.value = null
  shareChoosing.value = false
  activeDraftKey.value = draftKey(userId.value, companyId.value, room.id)
  pendingSend.value = null; loadingMessages.value = true; atBottom.value = true
  try {
    const context = relatedFilter.value
      ? { reference_type: relatedFilter.value.type, reference_id: relatedFilter.value.id }
      : { initial: 1, unread_mention: mention ? 1 : undefined }
    const { data } = await axios.get(`/api/chat/conversations/${room.id}/messages/`, { params: { ...config().params, ...context } })
    if (token !== epoch || disposed) return
    applyHistory(data)
    await restoreCurrentDraft(token)
    if (token !== epoch || disposed) return
    if (shared) pendingReference.value = shared
    await focusHistory(data.focus_id)
    await fetchReadStatuses(token)
  } catch (err) { await failure(err, token) }
  finally { if (token === epoch) loadingMessages.value = false }
}
function mergeEvents(changes) {
  const rows = new Map(events.value.map(event => [event.id, event]))
  changes.forEach(event => rows.set(event.id, event)); events.value = [...rows.values()]
}
function updateReadWindow(data) {
  readCursor.value = Math.max(readCursor.value, data.last_read_id || 0)
  firstUnreadId.value = data.first_unread_id || null
  if (!unreadBoundary.value) unreadBoundary.value = firstUnreadId.value
  const first = messages.value[0]?.id || 0, last = messages.value.at(-1)?.id || 0
  canReadPage.value = !firstUnreadId.value || messages.value.some(message => message.id === firstUnreadId.value) ||
    (first <= readCursor.value && last >= readCursor.value)
}
function applyHistory(data) {
  messages.value = data.results.filter(message => message.id > (selected.value.history_after_id || 0))
  events.value = data.events || []; pinnedMessages.value = data.pinned_messages || []
  hasOlder.value = data.has_older ?? data.has_more; hasNewer.value = Boolean(data.has_newer)
  syncRevision.value = data.sync_revision || 0; updateReadWindow(data)
  ;(data.read_message_ids || []).forEach(id => locallyRead.add(id))
}
async function focusHistory(id) {
  await nextTick()
  const root = messageList.value, element = id ? root?.querySelector(`[data-message-id="${id}"]`) : null
  if (root && element) {
    root.scrollTop += element.getBoundingClientRect().top - root.getBoundingClientRect().top - 24
    focusedMessageId.value = id
    onScroll(); await markRead()
  } else await scrollBottom()
}
async function openThread(params) {
  if (!selected.value) return
  const token = epoch, roomId = selected.value.id
  resourcesOpen.value = false; managing.value = false; loadingMessages.value = true
  unreadBoundary.value = null
  try {
    const { data } = await axios.get(`/api/chat/conversations/${roomId}/messages/`, { params: { ...config().params, ...params } })
    if (token !== epoch || disposed) return
    applyHistory(data); await focusHistory(data.focus_id); await fetchReadStatuses(token)
  } catch (err) { await failure(err, token) }
  finally { if (token === epoch) loadingMessages.value = false }
}
function jumpToMessage(id) { return openThread({ around: id }) }
function jumpToUnread() { return openThread({ initial: 1 }) }
function jumpToLatest() { return openThread({}) }
async function fetchNew(token) {
  if (!selected.value || syncRevision.value >= selected.value.revision) return
  const roomId = selected.value.id, follow = atBottom.value && !hasNewer.value
  for (let page = 0; page < 3; page++) {
    const { data } = await axios.get(`/api/chat/conversations/${roomId}/messages/`, { params: { ...config().params, since_revision: syncRevision.value } })
    if (token !== epoch || disposed) return
    messages.value = mergeMessages(messages.value, data.results, { append: !hasNewer.value, includeOlder: false, hiddenBefore: selected.value.history_after_id || 0 })
    mergeEvents(data.events || [])
    const pins = new Map(pinnedMessages.value.map(message => [message.id, message]))
    data.results.forEach(message => {
      const current = messages.value.find(row => row.id === message.id) || pins.get(message.id)
      if ((current?.revision || 0) > (message.revision || 0)) return
      if (message.is_pinned && !message.deleted_at) pins.set(message.id, message); else pins.delete(message.id)
    })
    pinnedMessages.value = [...pins.values()].sort((a, b) => b.id - a.id)
    syncRevision.value = Math.max(syncRevision.value, data.sync_revision); updateReadWindow(data)
    if (!data.has_more) break
  }
  if (follow) await scrollBottom()
}
async function loadOlder() {
  if (loadingOlder.value || !messages.value.length) return
  const token = epoch, roomId = selected.value.id
  loadingOlder.value = true
  const oldHeight = messageList.value?.scrollHeight || 0
  const oldTop = messageList.value?.scrollTop || 0
  try {
    const { data } = await axios.get(`/api/chat/conversations/${roomId}/messages/`, { params: { ...config().params, before: messages.value[0].id } })
    if (token !== epoch || disposed) return
    messages.value = mergeMessages(messages.value, data.results, { hiddenBefore: selected.value.history_after_id || 0 })
    mergeEvents(data.events || []); hasOlder.value = data.has_older ?? data.has_more; updateReadWindow(data)
    await nextTick()
    if (messageList.value) messageList.value.scrollTop = oldTop + messageList.value.scrollHeight - oldHeight
  } catch (err) { await failure(err, token) }
  finally { loadingOlder.value = false }
}
async function loadNewer() {
  if (!selected.value || loadingMessages.value) return
  const token = epoch
  loadingMessages.value = true
  try {
    const { data } = await axios.get(`/api/chat/conversations/${selected.value.id}/messages/`, {
      params: { ...config().params, after: messages.value.at(-1)?.id || 0 },
    })
    if (token !== epoch || disposed) return
    messages.value = mergeMessages(messages.value, data.results, { hiddenBefore: selected.value.history_after_id || 0 })
    mergeEvents(data.events || []); hasNewer.value = data.has_newer; updateReadWindow(data)
  } catch (err) { await failure(err, token) }
  finally { if (token === epoch) loadingMessages.value = false }
}
async function markRead() {
  const root = messageList.value
  if (!root || marking || !isOpen.value || !selected.value || document.hidden) return
  const ids = visibleMessageIds([...root.querySelectorAll('[data-message-id]')], root.getBoundingClientRect())
    .filter(id => !locallyRead.has(id) && messages.value.some(message => message.id === id && message.sender_id !== userId.value && !message.deleted_at)).slice(0, 100)
  if (!ids.length && !selected.value.is_marked_unread) return
  const token = epoch, roomId = selected.value.id
  marking = true
  try {
    readRequest = axios.post(`/api/chat/conversations/${roomId}/read/`, { message_ids: ids }, config())
    const { data } = await readRequest
    if (token !== epoch || disposed) return
    ids.forEach(id => locallyRead.add(id))
    readCursor.value = Math.max(readCursor.value, data.last_read_id)
    await fetchRooms(token)
  } catch (err) { await failure(err, token) }
  finally { marking = false }
}
async function scrollBottom() {
  await nextTick()
  if (!messageList.value) return
  messageList.value.scrollTop = messageList.value.scrollHeight
  atBottom.value = true
  await markRead()
}
async function fetchReadStatuses(token = epoch) {
  const root = messageList.value
  if (token !== epoch || disposed || !root || !selected.value || document.hidden || !isOpen.value) return
  const ids = visibleMessageIds([...root.querySelectorAll('[data-message-id]')], root.getBoundingClientRect())
    .filter(id => messages.value.some(message => message.id === id && message.sender_id === userId.value && !message.deleted_at)).slice(0, 100)
  if (!ids.length) return
  const sequence = ++readStatusSequence
  try {
    const { data } = await axios.get(`/api/chat/conversations/${selected.value.id}/read-status/`, { params: { ...config().params, message_ids: ids.join(',') } })
    if (token === epoch && !disposed && sequence === readStatusSequence) readStatuses.value = { ...readStatuses.value, ...readStatusRows(data) }
  } catch (err) { if (err.response?.status !== 404) throw err }
}
function onScroll() {
  const el = messageList.value
  if (!el) return
  atBottom.value = el.scrollHeight - el.scrollTop - el.clientHeight < 40
  clearTimeout(readTimer); readTimer = setTimeout(markRead, 1000)
}
async function startCreate() {
  back(); creating.value = true; group.value = false; chosen.value = []; directPerson.value = null; title.value = ''; search.value = ''
  const token = epoch
  loadingEmployees.value = true
  try {
    const { data } = await axios.get('/api/chat/employees/', config())
    if (token === epoch && !disposed) employees.value = data
  } catch (err) { await failure(err, token) }
  finally { if (token === epoch) loadingEmployees.value = false }
}
async function createRoom() {
  if (busy.value) return
  const token = epoch
  busy.value = true; error.value = ''
  try {
    const { data } = await axios.post('/api/chat/conversations/', { is_group: group.value, title: title.value, user_ids: group.value ? chosen.value : [directPerson.value] }, config())
    if (token !== epoch || disposed) return
    await fetchRooms(token)
    if (token !== epoch || disposed) return
    let room = rooms.value.find(r => r.id === data.id)
    if (!room) {
      const response = await axios.get(`/api/chat/conversations/${data.id}/`, config())
      if (token !== epoch || disposed) return
      room = response.data
    }
    await selectRoom(room)
  } catch (err) { await failure(err, token) }
  finally { busy.value = false }
}
async function send() {
  if (editTarget.value) await saveEditedMessage()
  else await delivery.send()
}
function applyChangedMessage(message) {
  const current = messages.value.find(row => row.id === message.id) || pinnedMessages.value.find(row => row.id === message.id)
  if ((current?.revision || 0) > (message.revision || 0)) return
  messages.value = mergeMessages(messages.value, [message], { append: !hasNewer.value, includeOlder: false, hiddenBefore: selected.value?.history_after_id || 0 })
  messages.value = messages.value.map(row => row.reply?.id === message.id ? { ...row, reply: {
    id: message.id, sender_name: message.sender_name,
    text: message.deleted_at ? 'Сообщение удалено' : message.text.slice(0, 200) || 'Вложение или объект', deleted: Boolean(message.deleted_at), is_placeholder: !message.text,
  } } : row)
  const pins = new Map(pinnedMessages.value.map(item => [item.id, item]))
  if (message.is_pinned && !message.deleted_at) pins.set(message.id, message); else pins.delete(message.id)
  pinnedMessages.value = [...pins.values()].sort((a, b) => b.id - a.id)
  if (message.deleted_at && replyTarget.value?.id === message.id) replyTarget.value = null
}
async function mutateMessage(message, action, payload = {}) {
  const token = epoch, roomId = selected.value?.id
  if (!roomId) return null
  busy.value = true; error.value = ''
  try {
    const url = `/api/chat/conversations/${roomId}/messages/${message.id}/`
    const response = action === 'delete' ? await axios.delete(url, config()) : action === 'edit'
      ? await axios.patch(url, payload, config()) : await axios.post(`${url}${action}/`, payload, config())
    if (token !== epoch || disposed) return null
    applyChangedMessage(response.data)
    return response.data
  } catch (err) { await failure(err, token); return null }
  finally { if (token === epoch) busy.value = false }
}
function startReply(message) {
  if (editTarget.value) cancelComposeContext()
  replyTarget.value = message; composerText.value?.focus(); saveCurrentDraft()
}
function startEdit(message) {
  drafts.beginEdit(message); composerText.value?.focus()
}
async function saveEditedMessage() {
  if (sending.value || busy.value || !editTarget.value) return
  const changed = await mutateMessage(editTarget.value, 'edit', { text: draft.value, expected_revision: editTarget.value.revision })
  if (changed) cancelComposeContext()
}
async function deleteMessage(target) {
  if (!target || busy.value) return
  const changed = await mutateMessage(target, 'delete')
  if (changed && editTarget.value?.id === target.id) cancelComposeContext()
}
function reactMessage(message, emoji) {
  return mutateMessage(message, 'reaction', { emoji, active: !message.reactions?.some(reaction => reaction.emoji === emoji && reaction.mine) })
}
function pinMessage(message) { return mutateMessage(message, 'pin', { pinned: !message.is_pinned }) }
function openResources(tab) { resourceTab.value = tab; resourcesOpen.value = true; managing.value = false; confirmAction.value = '' }
function initials(name) { return name.split(/\s+/).slice(0, 2).map(word => word[0]).join('').toLocaleUpperCase() }
function avatarStyle(id) {
  const hues = [215, 165, 265, 28, 335]
  const hue = hues[id % hues.length]
  return { background: `hsl(${hue} 80% 94%)`, color: `hsl(${hue} 55% 40%)` }
}
function referenceTitle(record) { return chatReferenceTitle(record, languageState.locale) }
function referenceIcon(kind) { return ({ product: 'bi-box-seam', counterparty: 'bi-building', supplier_order: 'bi-truck', customer_order: 'bi-receipt' })[kind] || 'bi-link-45deg' }
function onImageLoaded() { if (atBottom.value) scrollBottom() }
function removeMember(id) { if (id !== userId.value) editMembers.value = editMembers.value.filter(value => value !== id) }
function addMember(person) {
  if (editMembers.value.length < 100) {
    if (!stagedPeople.value.some(item => item.id === person.id)) stagedPeople.value.push(person)
    editMembers.value.push(person.id); memberSearch.value = ''
  }
}
async function openSettings() {
  managing.value = !managing.value; confirmAction.value = ''
  if (!managing.value) return
  editTitle.value = selected.value.title; editMembers.value = selected.value.participants.map(person => person.id); memberSearch.value = ''
  employees.value = []; stagedPeople.value = []; transferUser.value = null
}
async function updatePreferences(values) {
  if (!selected.value || busy.value) return
  const token = epoch
  busy.value = true
  try {
    await axios.patch(`/api/chat/conversations/${selected.value.id}/preferences/`, values, config())
    if (token === epoch) await fetchRooms(token)
  } catch (err) { await failure(err, token) }
  finally { if (token === epoch) busy.value = false }
}
async function markUnread() {
  if (!selected.value || busy.value) return
  const roomId = selected.value.id, requestConfig = config(), pendingRead = readRequest, requester = userId.value
  back()
  const token = epoch
  busy.value = true
  try {
    // Finish any read already in flight before setting the personal reminder.
    try { await pendingRead } catch { /* The reminder can still be saved. */ }
    if (disposed || requester !== userId.value || requestConfig.params.company_id !== companyId.value) return
    await axios.patch(`/api/chat/conversations/${roomId}/preferences/`, { is_marked_unread: true }, requestConfig)
    if (token === epoch && !disposed) await fetchRooms(token)
  } catch (err) { await failure(err, token) }
  finally { if (token === epoch) busy.value = false }
}
async function transferOwnership(userId) {
  if (!selected.value) return
  const token = epoch
  await axios.post(`/api/chat/conversations/${selected.value.id}/transfer/`, { user_id: userId }, config())
  if (token === epoch) { confirmAction.value = ''; await fetchRooms(token) }
}
async function saveGroup() {
  if (busy.value || !selected.value) return
  const token = epoch
  busy.value = true; error.value = ''
  try {
    await axios.patch(`/api/chat/conversations/${selected.value.id}/`, { title: editTitle.value, user_ids: editMembers.value }, config())
    if (token !== epoch || disposed) return
    managing.value = false; await fetchRooms(token)
  } catch (err) { await failure(err, token) }
  finally { if (token === epoch) busy.value = false }
}
async function performAction() {
  if (busy.value || !selected.value) return
  const token = epoch, room = selected.value, action = confirmAction.value
  busy.value = true; error.value = ''
  try {
    if (action === 'transfer') { await transferOwnership(transferUser.value); return }
    if (action === 'leave') await axios.post(`/api/chat/conversations/${room.id}/leave/`, {}, config())
    else if (action === 'clear') await axios.post(`/api/chat/conversations/${room.id}/clear/`, {}, config())
    else await axios.delete(`/api/chat/conversations/${room.id}/`, config())
    if (token !== epoch || disposed) return
    confirmAction.value = ''; managing.value = false
    if (action === 'clear') notifyDiscussionsChanged()
    await fetchRooms(token)
    if (token !== epoch) return
    if (action === 'clear') { const updated = rooms.value.find(item => item.id === room.id); if (updated) await selectRoom(updated) }
    else { drafts.forget(); activeDraftKey.value = ''; back() }
  } catch (err) { await failure(err, token) }
  finally { busy.value = false }
}
function addFiles(incoming) {
  const next = [...files.value, ...incoming]
  if (next.length > 5 || next.some(file => !file.size || file.size > 20 * 1024 * 1024) || next.reduce((total, file) => total + file.size, 0) > 50 * 1024 * 1024) {
    error.value = 'До 5 файлов, каждый до 20 МБ, вместе до 50 МБ.'; return
  }
  files.value = next; drafts.filesAttached(); error.value = ''
}
function chooseFiles(event) { addFiles([...event.target.files]); event.target.value = '' }
function pasteFiles(event) {
  const pasted = [...(event.clipboardData?.files || [])]
  if (pasted.length) { event.preventDefault(); addFiles(pasted) }
}
function openReferencePicker() {
  referencePicker.value = !referencePicker.value
  referenceSearch.value = ''; referenceResults.value = []; cancelReferenceSearch()
}
let referenceSearchId = 0
let referenceTimer = null
function cancelReferenceSearch() { clearTimeout(referenceTimer); referenceSearchId++; searchingReferences.value = false }
function closeReferencePicker() { referencePicker.value = false; cancelReferenceSearch() }
function scheduleReferenceSearch() {
  cancelReferenceSearch(); referenceResults.value = []
  if (!referenceSearch.value.trim()) return
  searchingReferences.value = true
  referenceTimer = setTimeout(findReferences, 300)
}
async function findReferences() {
  const token = epoch, searchId = ++referenceSearchId
  searchingReferences.value = true; referenceResults.value = []
  if (!referenceSearch.value.trim()) { searchingReferences.value = false; return }
  try {
    const { data } = await axios.get('/api/chat/references/', { params: { ...config().params, type: referenceKind.value, search: referenceSearch.value } })
    if (token === epoch && searchId === referenceSearchId && !disposed) referenceResults.value = data
  } catch (err) {
    if (token === epoch && searchId === referenceSearchId) {
      if (err.response?.status === 403) error.value = 'У вас нет доступа к этому разделу.'
      else await failure(err, token)
    }
  } finally { if (searchId === referenceSearchId) searchingReferences.value = false }
}
function attachReference(record) { pendingReference.value = record; closeReferencePicker(); error.value = '' }
async function insertEmoji(emoji) {
  const input = composerText.value, start = input?.selectionStart ?? draft.value.length, end = input?.selectionEnd ?? start
  if (draft.value.length - (end - start) + emoji.length > 5000) return
  draft.value = draft.value.slice(0, start) + emoji + draft.value.slice(end)
  emojiOpen.value = false; mentionQuery.value = null
  await nextTick(); composerText.value?.focus(); composerText.value?.setSelectionRange(start + emoji.length, start + emoji.length)
}
function handleOutsideClick(event) {
  chatRoot.value?.querySelectorAll('details.message-menu[open]').forEach(menu => { if (!menu.contains(event.target)) menu.open = false })
  if (emojiOpen.value && !emojiPicker.value?.contains(event.target) && !emojiToggle.value?.contains(event.target)) {
    emojiOpen.value = false
  }
  if (isOpen.value && chatRoot.value && !chatRoot.value.contains(event.target)) isOpen.value = false
}
function updateMentionQuery() {
  const input = composerText.value
  if (!input || input.selectionStart !== input.selectionEnd) { mentionQuery.value = null; return }
  const prefix = draft.value.slice(0, input.selectionStart)
  const match = prefix.match(/(?:^|\s)@([^\s@]*)$/u)
  mentionQuery.value = match ? { query: match[1], start: input.selectionStart - match[1].length - 1, end: input.selectionStart } : null
  mentionIndex.value = 0
}
async function insertMention(person) {
  const range = mentionQuery.value
  if (!range) return
  const inserted = `@${person.username} `
  const next = draft.value.slice(0, range.start) + inserted + draft.value.slice(range.end)
  if (next.length > 5000) return
  draft.value = next; mentionQuery.value = null
  await nextTick()
  composerText.value?.focus()
  composerText.value?.setSelectionRange(range.start + inserted.length, range.start + inserted.length)
}
function composerKeydown(event) {
  if (event.isComposing) return
  if (mentionCandidates.value.length && ['ArrowDown', 'ArrowUp', 'Enter', 'Escape'].includes(event.key) && !event.shiftKey) {
    event.preventDefault(); event.stopPropagation()
    if (event.key === 'Escape') mentionQuery.value = null
    else if (event.key === 'Enter') insertMention(mentionCandidates.value[mentionIndex.value] || mentionCandidates.value[0])
    else mentionIndex.value = (mentionIndex.value + (event.key === 'ArrowDown' ? 1 : -1) + mentionCandidates.value.length) % mentionCandidates.value.length
    return
  }
  if (event.key === 'Enter' && !event.shiftKey && !event.ctrlKey && !event.altKey && !event.metaKey) { event.preventDefault(); send() }
}
function openReference(record) { if (record.route) { isOpen.value = false; router.push(record.route) } }
function cancelShare() { pendingReference.value = null; shareChoosing.value = false }
async function shareRecord(event) {
  if (Number(event.detail?.companyId) !== Number(companyId.value)) return
  back(); isOpen.value = true; pendingReference.value = event.detail; shareChoosing.value = true
  roomSearch.value = ''; relatedFilter.value = null; archivedView.value = false; rooms.value = []; roomOffset.value = 0
  const token = epoch
  try { await fetchRooms(token) } catch (err) { await failure(err, token) }
}
function scheduleRoomSearch() {
  clearTimeout(roomSearchTimer)
  roomSearchTimer = setTimeout(async () => { rooms.value = []; roomOffset.value = 0; await refreshRooms() }, 300)
}
function clearRoomSearch() {
  clearTimeout(roomSearchTimer)
  roomSearch.value = ''; rooms.value = []; roomOffset.value = 0
  refreshRooms(); roomSearchInput.value?.focus()
}
async function archiveRoom(room) {
  if (archivingRoom.value !== null) return
  const token = epoch
  archivingRoom.value = room.id
  try {
    await axios.patch(`/api/chat/conversations/${room.id}/preferences/`, { is_archived: !room.is_archived }, config())
    if (token !== epoch || disposed) return
    rooms.value = rooms.value.filter(item => item.id !== room.id)
    roomOffset.value = Math.max(0, roomOffset.value - 1)
    await fetchRooms(token)
  } catch (err) { await failure(err, token) }
  finally { archivingRoom.value = null }
}
async function refreshRooms() {
  const token = epoch
  try { await fetchRooms(token) } catch (err) { await failure(err, token) }
}
function toggleArchive() { archivedView.value = !archivedView.value; rooms.value = []; roomOffset.value = 0; refreshRooms() }
function clearRelated() { relatedFilter.value = null; rooms.value = []; roomOffset.value = 0; refreshRooms() }
async function loadMoreRooms() {
  if (roomsLoading.value) return
  roomsLoading.value = true; const token = epoch
  try { await fetchRooms(token, { more: true }) } catch (err) { await failure(err, token) }
  finally { roomsLoading.value = false }
}
async function openRelated(event) {
  if (Number(event.detail?.companyId) !== Number(companyId.value)) return
  back(); isOpen.value = true; shareChoosing.value = false; relatedFilter.value = event.detail
  roomSearch.value = ''; rooms.value = []; roomOffset.value = 0; archivedView.value = false
  await refreshRooms()
}
let employeeSequence = 0
async function searchEmployees(query, limit = 20) {
  const token = epoch, sequence = ++employeeSequence
  loadingEmployees.value = true
  try {
    const { data } = await axios.get('/api/chat/employees/', { params: { ...config().params, q: query, limit,
      exclude_conversation: managing.value ? selected.value?.id : undefined } })
    if (token === epoch && sequence === employeeSequence) employees.value = data
  } catch (err) { await failure(err, token) }
  finally { if (token === epoch && sequence === employeeSequence) loadingEmployees.value = false }
}
watch(search, value => {
  if (!creating.value) return
  clearTimeout(employeeSearchTimer); employeeSearchTimer = setTimeout(() => searchEmployees(value), 300)
})
watch(memberSearch, value => {
  if (!managing.value || !isGroupAdmin.value) return
  clearTimeout(employeeSearchTimer); employeeSequence++
  if (!value.trim()) { employees.value = []; return }
  employeeSearchTimer = setTimeout(() => searchEmployees(value, 5), 300)
})
function retry() { error.value = ''; if (activeDelivery.value?.status === 'failed') retryDelivery(); else if (creating.value) startCreate(); else if (selected.value && loadingMessages.value === false && !messages.value.length) selectRoom(selected.value); else poll() }
function profileChanged(event) { setCurrentUser(event.detail?.id ? event.detail : null) }
async function storageChanged(event) {
  if (event.key === AUTH_SESSION_KEY && !event.newValue) {
    reset(); drafts.clearMemory(); delivery.clear(); setCurrentUser(null); return
  }
  drafts.storageChanged(event)
  if (['current_user_profile', 'auth_session'].includes(event.key)) { reset(); await loadCurrentUser({ force: true }); poll() }
}
watch(() => [companyId.value, userId.value], (current, previous) => {
  reset()
  if (current[1] !== previous[1] || !localStorage.getItem(AUTH_SESSION_KEY)) {
    drafts.clearMemory(); delivery.clear()
  }
  poll()
})
onMounted(async () => {
  window.addEventListener('profile-updated', profileChanged)
  window.addEventListener('storage', storageChanged)
  window.addEventListener('chat-share-record', shareRecord)
  window.addEventListener('chat-open-related', openRelated)
  document.addEventListener('visibilitychange', poll)
  document.addEventListener('pointerdown', handleOutsideClick)
  await loadCurrentUser()
  poll(); timer = window.setInterval(poll, 5000)
})
onBeforeUnmount(() => {
  saveCurrentDraft()
  disposed = true; epoch++; window.clearInterval(timer)
  cancelReferenceSearch()
  clearTimeout(roomSearchTimer); clearTimeout(employeeSearchTimer); clearTimeout(readTimer)
  window.removeEventListener('profile-updated', profileChanged)
  window.removeEventListener('storage', storageChanged)
  window.removeEventListener('chat-share-record', shareRecord)
  window.removeEventListener('chat-open-related', openRelated)
  document.removeEventListener('visibilitychange', poll)
  document.removeEventListener('pointerdown', handleOutsideClick)
})
</script>

<style scoped>
.company-chat { position: fixed; right: 28px; bottom: 32px; z-index: 1040; }
.chat-search-field { min-width: 0; align-self: center; }.chat-icon.search-clear { position: absolute; right: 2px; top: 50%; transform: translateY(-50%); width: 28px; height: 28px; }
.chat-icon.search-clear { padding: 0; line-height: 1; }.search-clear > .bi { display: flex; line-height: 1; }.search-clear > .bi::before { display: block; vertical-align: 0; line-height: 1; }
.chat-icon.room-archive { position: absolute; right: 38px; top: 50%; transform: translateY(-50%); width: 30px; height: 30px; }.chat-room .room-copy { margin-right: 32px; }
.chat-launcher { display: flex; align-items: center; gap: 9px; border: 1px solid #dbe6f4; border-radius: 28px; color: #35547e; padding: 7px 16px 7px 7px; background: #fff; font-weight: 600; transition: transform .18s, box-shadow .18s; }
.chat-launcher:hover { transform: translateY(-2px); box-shadow: 0 6px 20px #2964b51c !important; }
.launcher-icon { display: grid; place-items: center; width: 34px; height: 34px; border-radius: 50%; color: white; background: linear-gradient(135deg, #4387e5, #2163bd); }
.chat-panel { position: absolute; right: 0; bottom: 62px; width: 450px; height: min(710px, calc(100dvh - 150px)); display: flex; flex-direction: column; background: white; border: 1px solid #dce5f1; border-radius: 20px; overflow: hidden; box-shadow: 0 18px 60px #1f40652b !important; animation: chat-appear .18s ease-out; }
.chat-panel header { background: linear-gradient(115deg, #f0f6ff, #fff); flex-shrink: 0; }
.chat-icon { border: 0; background: transparent; color: #657993; border-radius: 11px; display: inline-grid; place-items: center; width: 34px; height: 34px; flex: 0 0 auto; transition: background .15s, color .15s; }
.chat-icon:hover { background: #e6eef9; color: #2467c4; }
.chat-icon.accent { color: #236bcf; background: #e6effd; }
.chat-avatar { display: inline-grid; place-items: center; width: 42px; height: 42px; flex: 0 0 auto; border-radius: 14px; color: #3372c5; background: #e4efff; font-size: .9rem; font-weight: 700; }
.company-avatar { overflow: hidden; }.company-avatar:has(img) { background: #fff; border: 1px solid #e7edf5; padding: 4px; }.company-avatar img { width: 100%; height: 100%; object-fit: contain; }
.small-avatar { width: 32px; height: 32px; border-radius: 11px; font-size: .72rem; }
.member-row { display: flex; align-items: center; gap: 10px; padding: 9px 4px; border-bottom: 1px solid #f0f3f8; font-size: .88rem; }
.member-row input { accent-color: #3478d6; }
.chat-confirm { background: #fff7f3; flex-shrink: 0; }
.pinned-strip { display: flex; gap: 8px; align-items: center; padding: 8px 16px; border: 0; border-bottom: 1px solid #e3ebf5; background: #f1f6ff; color: #4771a6; font-size: .75rem; text-align: left; }
.pinned-strip span { overflow: hidden; white-space: nowrap; text-overflow: ellipsis; }
.system-event { text-align: center; font-size: .68rem; color: #94a2b5; padding: 7px 16px; overflow-wrap: anywhere; }
.unread-divider { text-align: center; color: #4778b8; background: #e5eefb; border-radius: 8px; font-size: .72rem; padding: 4px; margin: 8px 0 12px; }
.pending-message { align-self: flex-end; background: #e9f0fb; padding: 8px 12px; border-radius: 13px; max-width: 90%; font-size: .82rem; white-space: pre-wrap; overflow-wrap: anywhere; }.pending-message small { color: #8191a8; font-size: .68rem; }
.compose-context { display: flex; align-items: center; gap: 8px; background: #eff5fd; border-left: 3px solid #8db6e8; border-radius: 7px; padding: 4px 8px; margin-bottom: 7px; color: #5277a5; }.compose-context span { flex: 1; min-width: 0; }.compose-context strong, .compose-context small { display: block; font-size: .72rem; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.chat-content { flex: 1; min-height: 0; overflow-y: auto; overscroll-behavior: contain; }
.chat-room { background: white; display: flex; align-items: center; gap: 12px; transition: background .15s; border-color: #eef2f7 !important; }
.chat-room:hover { background: #f3f7fd; }
.room-copy { flex: 1; min-width: 0; }
.room-copy strong { font-size: .88rem; }
.room-copy small { margin-top: 4px; font-size: .77rem; }
.room-copy .draft-preview { color: #bf5c59; }.room-copy .draft-preview strong { font-size: inherit; }
.chat-messages { display: flex; flex-direction: column; align-items: stretch; background: #f5f8fc; background-image: radial-gradient(#d9e3ef 0.6px, transparent 0.6px); background-size: 18px 18px; }
.chat-composer { background: #fff; flex-shrink: 0; }
.chat-composer textarea { border-color: #e1e8f1; border-radius: 12px; background: #f8fafd; resize: none; font-size: .88rem; }
.composer-hint { font-size: .73rem; color: #78889d; }
.participant-count { display: block; padding: 0; border: 0; background: transparent; color: #78889d; font-size: .75rem; cursor: pointer; }
.participant-count:hover { color: #2467c4; }
.mention-label { display: block; color: #2568bd; font-weight: 600; font-size: .73rem; }
.group-member-list { max-height: 240px; overflow-y: auto; }
.remove-member:hover { background: #ffeded; color: #c44848; }
.member-result { display: flex; align-items: center; gap: 9px; padding: 7px 3px; background: transparent; border: 0; width: 100%; font-size: .82rem; color: #32649d; }
.member-result:hover { background: #eef5ff; }
.emoji-picker { display: flex; flex-wrap: wrap; gap: 5px; padding: 6px; border: 1px solid #e1e8f2; border-radius: 11px; margin-bottom: 8px; max-height: 156px; overflow-y: auto; }
.emoji-picker button { border: 0; background: transparent; border-radius: 7px; padding: 4px 6px; font-size: 1.25rem; }
.emoji-picker button:hover { background: #edf4ff; }
.mention-picker { margin-bottom: 7px; padding: 4px; border: 1px solid #dce6f3; background: #fff; border-radius: 10px; max-height: 180px; overflow-y: auto; }
.mention-picker button { display: flex; gap: 8px; align-items: center; width: 100%; border: 0; border-radius: 6px; background: transparent; padding: 6px 8px; text-align: left; font-size: .8rem; color: #335d8d; }
.mention-picker button.active, .mention-picker button:hover { background: #edf4ff; }
.mention-picker small { color: #7d8da1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.chat-send { border: 0; border-radius: 13px; background: linear-gradient(135deg, #4387e5, #2163bd); color: white; width: 40px; height: 38px; box-shadow: 0 3px 8px #2767bc22; }
.chat-send:hover { filter: brightness(1.08); }
.chat-send:disabled { opacity: .45; box-shadow: none; }
.share-banner { display: flex; align-items: center; gap: 8px; padding: 8px 12px; background: #edf4ff; color: #396393; font-size: .75rem; }
.share-banner span { flex: 1; min-width: 0; overflow-wrap: anywhere; }
.pending-files { display: flex; flex-wrap: wrap; gap: 5px; max-height: 95px; overflow: auto; }
.pending-files span { display: inline-flex; align-items: center; gap: 4px; background: #f0f4f9; padding: 3px 6px; border-radius: 8px; font-size: .7rem; max-width: 100%; overflow-wrap: anywhere; }
.pending-files button { border: 0; background: transparent; color: #66788e; }
.reference-picker { max-height: 240px; overflow-y: auto; flex-shrink: 0; background: #fbfcff; }
.reference-result { display: flex; gap: 8px; border: 0; background: transparent; padding: 7px 3px; font-size: .78rem; width: 100%; text-align: left; color: #3c5a7d; }
.reference-result:hover { background: #edf4ff; }
@keyframes chat-appear { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: translateY(0); } }
@media (prefers-reduced-motion: reduce) { .chat-panel { animation: none; } .chat-launcher { transition: none; } }
@media (max-width: 575px) {
  .company-chat { right: 16px; bottom: 24px; }
  .chat-panel { position: fixed; left: 8px; right: 8px; bottom: 84px; width: auto; height: calc(100dvh - 100px); }
}
</style>
