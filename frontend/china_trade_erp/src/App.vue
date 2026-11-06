<template>
  <div id="app">
    <NavBar v-if="!$route.meta.hideNav" />
    <router-view :key="$route.meta.samples ? 'samples' : 'standard'" />
    <CompanyChat v-if="!$route.meta.hideNav" />

    <div class="modal fade" :class="{ show: showSettingsReminder }" :style="showSettingsReminder ? 'display: block;' : ''" tabindex="-1">
      <div class="modal-dialog modal-dialog-centered">
        <div class="modal-content" v-if="showSettingsReminder">
          <div class="modal-header">
            <h5 class="modal-title">Check company settings</h5>
            <button type="button" class="btn-close" @click="dismissSettingsReminder"></button>
          </div>
          <div class="modal-body">
            <p class="mb-2">Thanks for using ChinaTradeERP. We filled the basic company settings from your business country.</p>
            <p class="text-muted mb-0">Please check exchange rates, tax rate, and pricing settings so orders and product prices are calculated correctly.</p>
          </div>
          <div class="modal-footer">
            <button class="btn btn-outline-secondary" @click="dismissSettingsReminder">Later</button>
            <button class="btn btn-primary" @click="openCompanySettings">Open settings</button>
          </div>
        </div>
      </div>
    </div>
    <div v-if="showSettingsReminder" class="modal-backdrop fade show"></div>
  </div>
</template>

<script>
import axios, { AUTH_SESSION_KEY } from './axios'
import NavBar from './components/NavBar.vue'
import CompanyChat from './components/CompanyChat.vue'
import { hasPermission, PERMISSIONS, setCurrentUser } from './access'
import { installNotificationSound } from './utils/notificationSound'

export default {
  components: { NavBar, CompanyChat },
  data() {
    return { showSettingsReminder: false, releaseNotificationSound: null }
  },
  mounted() { this.releaseNotificationSound = installNotificationSound() },
  beforeUnmount() { this.releaseNotificationSound?.() },
  watch: {
    '$route.fullPath': {
      immediate: true,
      handler() { this.maybeShowSettingsReminder() },
    },
  },
  methods: {
    async maybeShowSettingsReminder() {
      if (this.$route.meta.hideNav || !localStorage.getItem(AUTH_SESSION_KEY)) {
        this.showSettingsReminder = false
        return
      }
      try {
        const { data } = await axios.get('/api/auth/me/')
        setCurrentUser(data)
        if (!hasPermission(PERMISSIONS.COMPANY_SETTINGS_MANAGE, data)) return
        if (!data.company_settings_needs_review || !this.canShowReminder()) return
        this.showSettingsReminder = true
      } catch {
        this.showSettingsReminder = false
      }
    },
    canShowReminder() {
      const today = new Date().toISOString().slice(0, 10)
      const raw = localStorage.getItem('company_settings_reminder')
      const state = raw ? JSON.parse(raw) : { totalShows: 0, lastShownDate: '' }
      if (state.totalShows >= 3 || state.lastShownDate === today) return false
      state.totalShows += 1
      state.lastShownDate = today
      localStorage.setItem('company_settings_reminder', JSON.stringify(state))
      return true
    },
    dismissSettingsReminder() { this.showSettingsReminder = false },
    openCompanySettings() {
      this.showSettingsReminder = false
      this.$router.push({ path: '/profile', query: { settings: 'company' } })
    },
  },
}
</script>
