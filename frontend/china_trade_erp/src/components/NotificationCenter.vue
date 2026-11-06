<template>
  <div class="notification-center" ref="root">
    <button
      type="button"
      class="notification-button"
      :title="$t('Notifications')"
      @click="togglePanel"
    >
      <i class="bi bi-bell fs-4"></i>
      <span v-if="unreadCount" class="notification-badge">{{ unreadCount > 99 ? '99+' : unreadCount }}</span>
      <span class="small mt-1 d-none d-lg-block">{{ $t('Notifications') }}</span>
    </button>

    <div v-if="isOpen" class="notification-panel shadow" :style="{ top: toastTop }">
      <div class="notification-header">
        <span><strong>{{ $t('Notifications') }}</strong><small>{{ $t('Stored for 30 days') }}</small></span>
        <button v-if="unreadCount" class="btn btn-link btn-sm p-0" @click="markAllRead">
          {{ $t('Mark all as read') }}
        </button>
      </div>
      <div v-if="isLoading" class="text-muted text-center py-4">{{ $t('Loading...') }}</div>
      <div v-else-if="!items.length" class="text-muted text-center py-4">{{ $t('No notifications') }}</div>
      <template v-else>
        <div
          v-for="item in items"
          :key="item.key"
          class="notification-item"
          :class="{ unread: !item.is_read }"
        >
          <button type="button" class="notification-open" @click="openNotification(item)">
            <span class="notification-icon" :class="`severity-${item.severity}`">
              <i :class="item.kind === 'stock_weekly' ? 'bi bi-calendar-check' : 'bi bi-exclamation-triangle'"></i>
            </span>
            <span class="notification-copy">
              <span class="notification-title">{{ item.title }}</span>
              <span class="notification-message">{{ item.message }}</span>
              <span class="notification-time">{{ formatDate(item.created_at) }}</span>
            </span>
            <span v-if="!item.is_read" class="unread-dot"></span>
          </button>
          <button type="button" class="notification-dismiss btn-close" :title="$t('Hide notification')" @click.stop="hideNotification(item)"></button>
        </div>
      </template>
    </div>

    <TransitionGroup name="toast" tag="div" class="toast-stack" :style="{ top: toastTop }" aria-live="polite">
      <div v-for="toast in toasts" :key="toast.key" class="notification-toast shadow" :class="`toast-${toast.severity}`">
        <button type="button" class="toast-body" @click="openNotification(toast)">
          <strong>{{ toast.title }}</strong>
          <span>{{ toast.message }}</span>
        </button>
        <button type="button" class="btn-close btn-close-sm" @click="removeToast(toast.key)"></button>
      </div>
    </TransitionGroup>
  </div>
</template>

<script>
import axios, { AUTH_SESSION_KEY } from '../axios'
import { playNotificationSound } from '../utils/notificationSound'
import { accessState } from '../access'

export default {
  name: 'NotificationCenter',
  data() {
    return {
      items: [],
      unreadCount: 0,
      isOpen: false,
      isLoading: false,
      toasts: [],
      timer: null,
      initialized: false,
      toastTop: '120px',
      navResizeObserver: null,
      soundScope: '',
      knownSoundKeys: new Set(),
    }
  },
  mounted() {
    document.addEventListener('click', this.handleOutsideClick)
    window.addEventListener('warehouse-stock-changed', this.fetchNotifications)
    window.addEventListener('notifications-updated', this.fetchNotifications)
    this.fetchNotifications()
    this.timer = window.setInterval(this.fetchNotifications, 30000)
    this.updateToastTop()
    const nav = this.$refs.root?.closest('nav')
    if (nav && window.ResizeObserver) {
      this.navResizeObserver = new ResizeObserver(this.updateToastTop)
      this.navResizeObserver.observe(nav)
    }
    window.addEventListener('resize', this.updateToastTop)
  },
  beforeUnmount() {
    document.removeEventListener('click', this.handleOutsideClick)
    window.removeEventListener('warehouse-stock-changed', this.fetchNotifications)
    window.removeEventListener('notifications-updated', this.fetchNotifications)
    if (this.timer) window.clearInterval(this.timer)
    if (this.navResizeObserver) this.navResizeObserver.disconnect()
    window.removeEventListener('resize', this.updateToastTop)
  },
  methods: {
    async fetchNotifications() {
      if (!localStorage.getItem(AUTH_SESSION_KEY)) return
      const scope = `${accessState.user?.id}:${accessState.user?.company_id}`
      try {
        const { data } = await axios.get('/api/notifications/')
        if (scope !== `${accessState.user?.id}:${accessState.user?.company_id}`) return
        const nextItems = data.results || []
        const keys = new Set(nextItems.map(item => item.key))
        const freshSound = scope === this.soundScope
          ? nextItems.find(item => !item.is_read && !this.knownSoundKeys.has(item.key))
          : null
        if (scope === this.soundScope) this.knownSoundKeys.forEach(key => keys.add(key))
        this.soundScope = scope
        this.knownSoundKeys = new Set([...keys].slice(0, 1000))
        if (freshSound) playNotificationSound(`notification:${scope}:${freshSound.key}`)
        this.showNewToasts(nextItems)
        this.items = nextItems
        this.unreadCount = data.unread_count || 0
        this.initialized = true
      } catch {
        // Notification polling must never interrupt normal application work.
      }
    },
    showNewToasts(nextItems) {
      const seen = new Set(JSON.parse(sessionStorage.getItem('seen_notifications') || '[]'))
      const fresh = nextItems.filter(item => !item.is_read && !seen.has(item.key)).slice(0, 3)
      if (!fresh.length) return
      this.toasts.push(...fresh)
      fresh.forEach(item => {
        seen.add(item.key)
        window.setTimeout(() => this.removeToast(item.key), 8000)
      })
      sessionStorage.setItem('seen_notifications', JSON.stringify([...seen].slice(-100)))
    },
    togglePanel() {
      this.isOpen = !this.isOpen
      if (this.isOpen) this.fetchNotifications()
    },
    handleOutsideClick(event) {
      if (this.isOpen && this.$refs.root && !this.$refs.root.contains(event.target)) this.isOpen = false
    },
    async markRead(item) {
      if (item.is_read) return
      item.is_read = true
      this.unreadCount = Math.max(0, this.unreadCount - 1)
      try {
        await axios.post('/api/notifications/read/', { kind: item.kind, source_id: item.source_id })
      } catch {
        await this.fetchNotifications()
      }
    },
    async markAllRead() {
      this.items.forEach(item => { item.is_read = true })
      this.unreadCount = 0
      try {
        await axios.post('/api/notifications/read-all/', {})
      } finally {
        await this.fetchNotifications()
      }
    },
    async hideNotification(item) {
      this.items = this.items.filter(current => current.key !== item.key)
      this.removeToast(item.key)
      if (!item.is_read) this.unreadCount = Math.max(0, this.unreadCount - 1)
      try {
        await axios.post('/api/notifications/hide/', { kind: item.kind, source_id: item.source_id })
      } catch {
        await this.fetchNotifications()
      }
    },
    async openNotification(item) {
      await this.markRead(item)
      this.removeToast(item.key)
      this.isOpen = false
      if (this.$route.path === '/warehouse') {
        window.dispatchEvent(new CustomEvent('open-stock-control'))
      } else {
        await this.$router.push(item.action || { path: '/warehouse', query: { stockControl: '1' } })
      }
    },
    removeToast(key) {
      this.toasts = this.toasts.filter(item => item.key !== key)
    },
    updateToastTop() {
      this.$nextTick(() => {
        const bottom = this.$refs.root?.closest('nav')?.getBoundingClientRect().bottom || 0
        this.toastTop = `${Math.max(12, Math.round(bottom) + 12)}px`
      })
    },
    formatDate(value) {
      if (!value) return ''
      return new Date(value).toLocaleString(undefined, { dateStyle: 'short', timeStyle: 'short' })
    },
  },
}
</script>

<style scoped>
.notification-center { position: relative; }
.notification-button { align-items: center; background: transparent; border: 0; color: #444; display: flex; flex-direction: column; padding: .5rem .75rem; position: relative; }
.notification-button:hover { color: #0d6efd; }
.notification-badge { background: #dc3545; border: 2px solid #fff; border-radius: 999px; color: #fff; font-size: .65rem; font-weight: 700; line-height: 1; min-width: 20px; padding: 3px 5px; position: absolute; right: 5px; top: 2px; }
.notification-panel { background: #fff; border: 1px solid #dee2e6; border-radius: .75rem; max-height: min(70vh, 560px); overflow-y: auto; position: fixed; right: 1rem; width: min(420px, calc(100vw - 24px)); z-index: 1080; }
.notification-header { align-items: center; border-bottom: 1px solid #e9ecef; display: flex; justify-content: space-between; padding: .9rem 1rem; position: sticky; top: 0; background: #fff; z-index: 1; }
.notification-header span { display: flex; flex-direction: column; }
.notification-header small { color: #868e96; font-size: .7rem; font-weight: 400; margin-top: .1rem; }
.notification-item { align-items: flex-start; background: #fff; border-bottom: 1px solid #f0f1f2; display: flex; position: relative; width: 100%; }
.notification-item:hover { background: #f8f9fa; }
.notification-item.unread { background: #f3f7ff; }
.notification-open { align-items: flex-start; background: transparent; border: 0; display: flex; flex: 1; gap: .75rem; min-width: 0; padding: .85rem 2.6rem .85rem 1rem; text-align: left; }
.notification-dismiss { margin: .95rem .85rem 0 0; opacity: .45; position: absolute; right: 0; top: 0; }
.notification-dismiss:hover { opacity: .8; }
.notification-icon { align-items: center; border-radius: 50%; display: inline-flex; flex: 0 0 34px; height: 34px; justify-content: center; }
.severity-danger { background: #f8d7da; color: #842029; }
.severity-warning { background: #fff3cd; color: #664d03; }
.notification-copy { display: flex; flex: 1; flex-direction: column; min-width: 0; }
.notification-title { color: #212529; font-size: .9rem; font-weight: 700; }
.notification-message { color: #495057; font-size: .82rem; line-height: 1.35; margin-top: .15rem; }
.notification-time { color: #868e96; font-size: .72rem; margin-top: .35rem; }
.unread-dot { background: #0d6efd; border-radius: 50%; flex: 0 0 8px; height: 8px; margin-top: .4rem; }
.toast-stack { display: flex; flex-direction: column; gap: .65rem; position: fixed; right: 1.25rem; transition: top .2s ease; width: min(390px, calc(100vw - 2rem)); z-index: 1070; }
.notification-toast { align-items: flex-start; animation: toast-in .25s ease-out; background: #fff; border-left: 4px solid #0d6efd; border-radius: .6rem; display: flex; overflow: hidden; }
.notification-toast.toast-danger { border-left-color: #dc3545; }
.notification-toast.toast-warning { border-left-color: #ffc107; }
.toast-body { background: transparent; border: 0; display: flex; flex: 1; flex-direction: column; padding: .85rem 1rem; text-align: left; }
.toast-body strong { font-size: .9rem; }
.toast-body span { color: #495057; font-size: .82rem; margin-top: .2rem; }
.notification-toast .btn-close { margin: .75rem .75rem 0 0; }
@keyframes toast-in { from { opacity: 0; transform: translateX(24px); } to { opacity: 1; transform: translateX(0); } }
.toast-enter-active, .toast-leave-active { transition: opacity .3s ease, transform .3s ease; }
.toast-enter-from { opacity: 0; transform: translateX(24px); }
.toast-leave-to { opacity: 0; transform: translateY(-24px); }
@media (max-width: 991.98px) { .notification-panel { right: 12px; } .toast-stack { right: 1rem; } }
</style>
