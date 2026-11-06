<template>
  <div class="container profile-page py-4">
    <div class="profile-card">
      <div class="profile-header">
        <div class="avatar-wrap">
          <div class="profile-avatar-frame">
            <img v-if="avatarSrc" :src="avatarSrc" class="profile-avatar" alt="Profile avatar" />
            <div v-else class="profile-avatar avatar-placeholder">{{ initials }}</div>
          </div>
        </div>

        <div class="profile-title">
          <div class="profile-kicker">Employee profile</div>
          <h1>{{ displayName }}</h1>
          <div class="profile-subtitle">{{ profile.position || roleLabel }}</div>
          <div class="profile-badges">
            <span v-if="profile.company_name" class="badge text-bg-light">{{ profile.company_name }}</span>
            <span class="badge text-bg-primary">{{ roleLabel }}</span>
          </div>
          <div v-if="companyMemberships.length > 1" class="company-switch mt-3">
            <label class="form-label mb-1">Active company</label>
            <select
                class="form-select form-select-sm"
                :value="profile.company_id"
                :disabled="isSwitchingCompany"
                @change="switchCompany($event.target.value)"
            >
              <option v-for="membership in companyMemberships" :key="membership.id" :value="membership.company">
                {{ membership.company_name }}
              </option>
            </select>
          </div>
        </div>

        <div class="profile-actions">
          <button
              v-if="profile.is_company_admin"
              class="btn btn-outline-primary px-3"
              @click="openInviteModal"
          >
            Invite employee
          </button>
          <button
              v-if="profile.is_company_admin"
              class="btn btn-outline-primary px-3"
              @click="openSettingsModal"
          >
            Company settings
          </button>
          <button class="btn btn-primary px-3" @click="startEditing">
            Edit profile
          </button>
          <button class="btn btn-outline-danger px-3" :disabled="isLoggingOut" @click="logout">
            {{ isLoggingOut ? 'Logging out...' : 'Logout' }}
          </button>
        </div>
      </div>

      <div class="profile-section">
        <div class="section-title">
          <h2>Contact information</h2>
        </div>

        <div class="profile-fields">
          <div v-for="field in contactFields" :key="field.key" class="profile-field">
            <div class="field-label">{{ field.label }}</div>
            <div :class="['field-value', { empty: !field.value }]">
              {{ field.value || $t('not filled') }}
            </div>
          </div>
        </div>
      </div>
    </div>

    <div
        class="modal fade profile-modal"
        :class="{ show: isEditing }"
        :style="isEditing ? 'display: block;' : ''"
        tabindex="-1"
    >
      <div class="modal-dialog modal-dialog-centered modal-lg">
        <transition name="modal-fade">
          <div class="modal-content" v-if="isEditing">
            <div class="modal-header">
              <div>
                <h5 class="modal-title">Edit profile</h5>
                <div class="text-muted small">Update your contact information and photo</div>
              </div>
              <button type="button" class="btn-close" aria-label="Close" @click="cancelEditing"></button>
            </div>
            <form @submit.prevent="saveProfile">
              <div class="modal-body">
                <div class="profile-edit-layout">
                  <div class="profile-edit-photo">
                    <div class="profile-avatar-frame">
                      <div
                          v-if="avatarPreview"
                          class="avatar-crop-viewport"
                          @pointerdown="startAvatarDrag"
                          @pointermove="dragAvatar"
                          @pointerup="endAvatarDrag"
                          @pointercancel="endAvatarDrag"
                          @wheel.prevent="zoomAvatar"
                      >
                        <img :src="avatarPreview" :style="avatarPreviewStyle" alt="Avatar crop preview" />
                      </div>
                      <img v-else-if="avatarSrc" :src="avatarSrc" class="profile-avatar" alt="Profile avatar" />
                      <div v-else class="profile-avatar avatar-placeholder">{{ initials }}</div>
                    </div>
                    <label class="btn btn-sm btn-outline-primary avatar-action">
                      Change photo
                      <input type="file" accept="image/*" hidden @change="handleAvatarChange" />
                    </label>
                    <div v-if="avatarPreview" class="avatar-hint">
                      Drag photo, use mouse wheel to zoom
                    </div>
                  </div>

                  <div class="row gy-3 profile-form">
                    <div class="col-md-4">
                      <label class="form-label">First name</label>
                      <input v-model.trim="form.first_name" class="form-control" />
                    </div>
                    <div class="col-md-4">
                      <label class="form-label">Last name</label>
                      <input v-model.trim="form.last_name" class="form-control" />
                    </div>
                    <div class="col-md-4">
                      <label class="form-label">Middle name</label>
                      <input v-model.trim="form.middle_name" class="form-control" />
                    </div>
                    <div class="col-md-4">
                      <label class="form-label">Mobile phone</label>
                      <input v-model.trim="form.phone" class="form-control" />
                    </div>
                    <div class="col-md-4">
                      <label class="form-label">Work email</label>
                      <input v-model.trim="form.work_email" type="email" class="form-control" />
                    </div>
                    <div class="col-md-4">
                      <label class="form-label">Personal email</label>
                      <input v-model.trim="form.personal_email" type="email" class="form-control" />
                    </div>
                    <div class="col-md-4">
                      <label class="form-label">Department</label>
                      <input v-model.trim="form.department" class="form-control" />
                    </div>
                    <div class="col-md-4">
                      <label class="form-label">Position</label>
                      <input v-model.trim="form.position" class="form-control" />
                    </div>
                    <div class="col-md-4">
                      <label class="form-label">Interface language</label>
                      <select v-model="form.notification_language" class="form-select">
                        <option value="ru">Russian</option>
                        <option value="en">English</option>
                      </select>
                    </div>
                    <div class="col-md-4">
                      <label class="form-label">Birth date</label>
                      <input v-model="form.birth_date" type="date" class="form-control" />
                    </div>
                    <div class="col-md-4">
                      <label class="form-label">Hire date</label>
                      <input v-model="form.hire_date" type="date" class="form-control" />
                    </div>
                  </div>
                </div>
              </div>
              <div class="modal-footer">
                <button type="button" class="btn btn-outline-secondary" :disabled="isSaving" @click="cancelEditing">
                  Cancel
                </button>
                <button type="submit" class="btn btn-primary px-4" :disabled="isSaving">
                  {{ isSaving ? 'Saving...' : 'Save profile' }}
                </button>
              </div>
            </form>
          </div>
        </transition>
      </div>
    </div>

    <div
        class="modal fade invite-modal"
        :class="{ show: showInviteModal }"
        :style="showInviteModal ? 'display: block;' : ''"
        tabindex="-1"
    >
      <div class="modal-dialog modal-dialog-centered modal-lg">
        <transition name="modal-fade">
        <div class="modal-content" v-if="showInviteModal">
          <div class="modal-header">
            <div>
              <h5 class="modal-title">Invite employee</h5>
          <div class="text-muted small">{{ $t('Add an employee to') }} {{ profile.company_name || $t('your company') }}</div>
            </div>
            <button type="button" class="btn-close" aria-label="Close" @click="closeInviteModal"></button>
          </div>
          <form @submit.prevent="sendInvitation">
            <div class="modal-body">
              <div class="btn-group mb-3" role="group" aria-label="Employee modal tabs">
                <button
                    type="button"
                    :class="['btn btn-sm', inviteModalTab === 'invite' ? 'btn-primary' : 'btn-outline-primary']"
                    @click="inviteModalTab = 'invite'"
                >
                  Invite
                </button>
                <button
                    type="button"
                    :class="['btn btn-sm', inviteModalTab === 'employees' ? 'btn-primary' : 'btn-outline-primary']"
                    @click="openEmployeesTab"
                >
                  Employees
                </button>
              </div>

              <div v-if="inviteModalTab === 'invite'">
              <div class="row gy-3">
                <div class="col-md-3">
                  <label class="form-label">First name</label>
                  <input v-model.trim="invitationForm.first_name" class="form-control" />
                </div>
                <div class="col-md-3">
                  <label class="form-label">Last name</label>
                  <input v-model.trim="invitationForm.last_name" class="form-control" />
                </div>
                <div class="col-md-6">
                  <label class="form-label">Employee email</label>
                  <input v-model.trim="invitationForm.email" type="email" class="form-control" required />
                </div>
                <div class="col-md-6">
                  <label class="form-label">Access role</label>
                  <select v-model="invitationForm.access_role" class="form-select" required>
                    <option disabled value="">{{ $t('Select role...') }}</option>
                    <option v-for="role in accessRoles" :key="role.id" :value="role.id">
                      {{ systemRoleName(role.name) }}
                    </option>
                  </select>
                </div>
                <div class="col-md-6">
                  <label class="form-label">Department</label>
                  <select v-model="invitationForm.department" class="form-select" data-i18n-skip>
                    <option :value="null">{{ $t('No department') }}</option>
                    <option v-for="department in departments" :key="department.id" :value="department.id">
                      {{ departmentName(department) }}
                    </option>
                  </select>
                </div>
                <div class="col-12">
                  <label class="form-label">Position</label>
                  <input v-model.trim="invitationForm.position" class="form-control" />
                </div>
              </div>
              </div>

              <div v-if="inviteModalTab === 'invite' && invitationSuccess" class="alert alert-success mt-3 mb-0">
                {{ $t(invitationSuccess) }}
              </div>
              <div v-if="inviteModalTab === 'invite' && invitationError" class="alert alert-danger mt-3 mb-0">
                {{ invitationError }}
              </div>

              <div v-if="inviteModalTab === 'invite'" class="invitation-list mt-4">
                <div class="d-flex align-items-center justify-content-between mb-2">
                  <h6 class="mb-0">Pending invitations</h6>
                  <span class="text-muted small">{{ invitations.length }}</span>
                </div>
                <div v-if="!invitations.length" class="text-muted small">
                  No pending invitations.
                </div>
                <div v-for="invitation in invitations" :key="invitation.id" class="invitation-item">
                  <div>
                    <div class="fw-semibold">{{ invitation.email }}</div>
                    <div class="text-muted small">
                      {{ systemRoleName(invitation.access_role_display || invitation.role) }}
                      <span v-if="invitation.department_display"> / {{ departmentName({ name: invitation.department_display, translations: invitation.department_translations }) }}</span>
                      <span v-if="invitation.position"> / {{ invitation.position }}</span>
                    </div>
                  </div>
                  <div class="d-flex align-items-center flex-wrap gap-2">
                    <span class="text-muted small">{{ $t('Expires at') }}: {{ formatDateTime(invitation.expires_at) }}</span>
                    <IconButton icon="arrow-clockwise" size="sm" :title="$t('Resend invitation')"
                      :disabled="Boolean(invitationAction) || isSendingInvitation"
                      @click="manageInvitation(invitation, 'resend')" />
                    <IconButton icon="x-circle" size="sm" variant="outline-danger" :title="$t('Revoke invitation')"
                      :disabled="Boolean(invitationAction) || isSendingInvitation"
                      @click="manageInvitation(invitation, 'revoke')" />
                  </div>
                </div>
              </div>

              <div v-if="inviteModalTab === 'employees'" class="employee-list">
                <div class="d-flex flex-wrap align-items-center justify-content-between gap-2 mb-3">
                  <h6 class="mb-0">Employees</h6>
                  <div class="btn-group btn-group-sm">
                    <button
                        type="button"
                        :class="['btn', employeeStatusFilter === 'active' ? 'btn-primary' : 'btn-outline-primary']"
                        @click="setEmployeeStatusFilter('active')"
                    >
                      {{ $t('Active employees') }}
                    </button>
                    <button
                        type="button"
                        :class="['btn', employeeStatusFilter === 'disabled' ? 'btn-primary' : 'btn-outline-primary']"
                        @click="setEmployeeStatusFilter('disabled')"
                    >
                      {{ $t('Dismissed employees') }}
                    </button>
                  </div>
                </div>

                <div v-if="isLoadingEmployees" class="text-muted small">Loading employees...</div>
                <div v-else-if="!employees.length" class="text-muted small">No employees in this list.</div>
                <div v-for="employee in employees" :key="employee.id" class="employee-entry">
                  <div
                      :class="['employee-item', { selected: selectedEmployee?.id === employee.id }]"
                  >
                    <button
                        type="button"
                        class="employee-main employee-toggle"
                        :aria-expanded="selectedEmployee?.id === employee.id"
                        :aria-controls="`employee-detail-${employee.id}`"
                        @click="selectEmployee(employee)"
                    >
                      <div class="fw-semibold">{{ employeeName(employee) }}</div>
                      <div class="text-muted small">{{ employee.email }}</div>
                      <div class="text-muted small">
                        {{ systemRoleName(employee.access_role_name || employee.role_display || employee.role) }}
                        <span v-if="employee.department_name"> / {{ departmentName({ name: employee.department_name, translations: employee.department_translations }) }}</span>
                        <span v-if="employee.position"> / {{ employee.position }}</span>
                      </div>
                      <div v-if="employee.status === 'disabled'" class="text-muted small">
                        {{ $t('Dismissed on') }} {{ formatDate(employee.disabled_at) }}
                        <span v-if="employee.disabled_by_email"> {{ $t('by') }} {{ employee.disabled_by_email }}</span>
                      </div>
                    </button>
                    <div class="employee-actions">
                      <span :class="['badge', employee.status === 'active' ? 'text-bg-success' : 'text-bg-secondary']">
                        {{ $t(employee.status) }}
                      </span>
                      <button
                          v-if="employee.can_dismiss"
                          type="button"
                          class="btn btn-sm btn-outline-danger"
                          :disabled="isDismissingEmployee === employee.id"
                          @click.stop="dismissEmployee(employee)"
                      >
                        {{ isDismissingEmployee === employee.id ? $t('Dismissing...') : $t('Dismiss') }}
                      </button>
                      <IconButton :icon="selectedEmployee?.id === employee.id ? 'chevron-up' : 'chevron-down'"
                        size="sm" :title="selectedEmployee?.id === employee.id ? $t('Collapse employee details') : $t('Expand employee details')"
                        :aria-expanded="selectedEmployee?.id === employee.id" :aria-controls="`employee-detail-${employee.id}`"
                        @click="selectEmployee(employee)" />
                    </div>
                  </div>

                  <div v-if="selectedEmployee?.id === employee.id" :id="`employee-detail-${employee.id}`" class="employee-detail-panel">
                    <div class="d-flex align-items-start justify-content-between gap-3 mb-3">
                      <div>
                        <h6 class="mb-1">{{ employeeName(selectedEmployee) }}</h6>
                        <div class="text-muted small">{{ selectedEmployee.email }}</div>
                      </div>
                    </div>
                    <div class="employee-detail-grid">
                      <div>
                        <div class="field-label">Phone</div>
                        <div class="field-value">{{ selectedEmployee.phone || $t('not filled') }}</div>
                      </div>
                      <div>
                        <div class="field-label">Work email</div>
                        <div class="field-value">{{ selectedEmployee.work_email || $t('not filled') }}</div>
                      </div>
                      <div>
                        <div class="field-label">Personal email</div>
                        <div class="field-value">{{ selectedEmployee.personal_email || $t('not filled') }}</div>
                      </div>
                      <div class="employee-role-field">
                        <div class="field-label">Role</div>
                        <div v-if="selectedEmployee.status === 'active'" class="d-flex align-items-center gap-2">
                          <select v-model="selectedEmployeeRoleId" class="form-select form-select-sm">
                            <option v-for="role in accessRoles" :key="role.id" :value="role.id">
                              {{ systemRoleName(role.name) }}
                            </option>
                          </select>
                          <button
                              type="button"
                              class="btn btn-sm btn-outline-primary"
                              :disabled="isSavingEmployeeRole || !employeeRoleChanged"
                              @click="saveEmployeeRole"
                          >
                            {{ isSavingEmployeeRole ? $t('Saving...') : $t('Save') }}
                          </button>
                        </div>
                        <div v-else class="field-value">{{ systemRoleName(selectedEmployee.access_role_name || selectedEmployee.role_display || selectedEmployee.role) }}</div>
                      </div>
                      <div>
                        <div class="field-label">Department</div>
                        <div class="field-value">{{ departmentName({ name: selectedEmployee.department_name, translations: selectedEmployee.department_translations }) || $t('not filled') }}</div>
                      </div>
                      <div>
                        <div class="field-label">Position</div>
                        <div class="field-value">{{ selectedEmployee.position || $t('not filled') }}</div>
                      </div>
                      <div v-if="selectedEmployee.status === 'disabled'">
                        <div class="field-label">{{ $t('Dismissed at') }}</div>
                        <div class="field-value">{{ formatDate(selectedEmployee.disabled_at) || $t('not filled') }}</div>
                      </div>
                      <div v-if="selectedEmployee.status === 'disabled'">
                        <div class="field-label">Reason</div>
                        <div class="field-value">{{ selectedEmployee.disable_reason || $t('not filled') }}</div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
            <div class="modal-footer">
              <button type="button" class="btn btn-outline-secondary" @click="closeInviteModal">Cancel</button>
              <button
                  v-if="inviteModalTab === 'invite'"
                  class="btn btn-primary px-4"
                  :disabled="isSendingInvitation || Boolean(invitationAction)"
              >
                {{ isSendingInvitation ? 'Sending...' : 'Send invitation' }}
              </button>
            </div>
          </form>
        </div>
        </transition>
      </div>
    </div>

    <div
        class="modal fade profile-modal"
        :class="{ show: showSettingsModal }"
        :style="showSettingsModal ? 'display: block;' : ''"
        tabindex="-1"
    >
      <div class="modal-dialog modal-dialog-centered modal-lg">
        <transition name="modal-fade">
          <div class="modal-content" v-if="showSettingsModal">
            <div class="modal-header">
              <div>
                <h5 class="modal-title">Company settings</h5>
              <div class="text-muted small">{{ $t('Pricing settings for') }} {{ profile.company_name || $t('your company') }}</div>
              </div>
              <button type="button" class="btn-close" aria-label="Close" @click="closeSettingsModal"></button>
            </div>
            <form @submit.prevent="saveCompanySettings">
              <div class="modal-body">
                <div v-if="isLoadingSettings" class="text-muted">Loading settings...</div>
                <div v-else class="row gy-3">
                  <div class="col-md-6 country-picker">
                    <label class="form-label">Country of business</label>
                    <input
                      v-model="settingsCountrySearch"
                      type="text"
                      class="form-control"
                      required
                      placeholder="Start typing a country..."
                      autocomplete="off"
                      @focus="showSettingsCountrySuggestions = true"
                      @input="onSettingsCountrySearchInput"
                      @keydown.down.prevent="moveSettingsCountryHighlight(1)"
                      @keydown.up.prevent="moveSettingsCountryHighlight(-1)"
                      @keydown.enter.prevent="selectHighlightedSettingsCountry"
                      @keydown.esc="showSettingsCountrySuggestions = false"
                      @blur="hideSettingsCountrySuggestions"
                    />
                    <div
                      v-if="showSettingsCountrySuggestions && filteredSettingsCountries.length"
                      class="country-suggestions list-group shadow-sm"
                    >
                      <button
                        v-for="(country, index) in filteredSettingsCountries"
                        :key="country.code"
                        type="button"
                        class="list-group-item list-group-item-action"
                        :class="{ active: index === highlightedSettingsCountryIndex }"
                        @mousedown.prevent="selectSettingsCountry(country)"
                      >
                        <span>{{ country.name }}</span>
                        <span class="text-muted small ms-2">{{ country.code }}</span>
                      </button>
                    </div>
                    <div class="form-text">Changing country updates the company currency, exchange rates, and default tax rate.</div>
                  </div>
                  <div class="col-md-3">
                    <label class="form-label">Currency</label>
                    <input :value="settingsForm.company_currency_code || '-'" class="form-control" disabled />
                  </div>
                  <div class="col-md-3">
                    <label class="form-label">Symbol</label>
                    <input :value="settingsForm.company_currency_symbol || '-'" class="form-control" disabled />
                  </div>
                  <div class="col-12">
                    <hr class="my-2" />
                    <h6 class="mb-0">Company details for documents</h6>
                  </div>
                  <div class="col-md-4">
                    <label class="form-label">Company language</label>
                    <select v-model="settingsForm.company_language_code" class="form-select">
                      <option value="ru">Russian</option>
                      <option value="en">English</option>
                    </select>
                  </div>
                  <div class="col-md-4">
                    <label class="form-label">Company logo</label>
                    <input type="file" accept="image/*" class="form-control" @change="handleCompanyLogoChange" />
                    <div v-if="companyLogoPreview || settingsForm.company_logo_url" class="company-logo-preview mt-2">
                      <img :src="companyLogoPreview || settingsForm.company_logo_url" alt="Company logo" />
                    </div>
                  </div>
                  <div class="col-md-4">
                    <label class="form-label">Work email</label>
                    <input v-model.trim="settingsForm.company_work_email" type="email" class="form-control" />
                  </div>
                  <div class="col-md-4">
                    <label class="form-label">Company phone</label>
                    <input v-model.trim="settingsForm.company_phone" type="text" class="form-control" />
                  </div>
                  <div class="col-md-6">
                    <label class="form-label">Company address</label>
                    <textarea v-model.trim="settingsForm.company_address" class="form-control" rows="2"></textarea>
                  </div>
                  <div class="col-md-6">
                    <label class="form-label">China warehouse address</label>
                    <textarea v-model.trim="settingsForm.company_china_warehouse_address" class="form-control" rows="2"></textarea>
                  </div>
                  <div class="col-md-6">
                    <label class="form-label">Bank details</label>
                    <textarea v-model.trim="settingsForm.company_bank_details" class="form-control" rows="2"></textarea>
                  </div>
                  <div class="col-12">
                    <hr class="my-2" />
                    <h6 class="mb-0">Warehouse stock control</h6>
                    <div class="form-text">Each warehouse product can use a manual monthly value or an automatic value calculated from actual shipments.</div>
                  </div>
                  <div class="col-md-4">
                    <label class="form-label">Average delivery lead, calendar days</label>
                    <input v-model.number="settingsForm.stock_delivery_lead_days" type="number" min="1" max="365" class="form-control" required />
                  </div>
                  <div class="col-md-4">
                    <label class="form-label">Automatic consumption history</label>
                    <select v-model.number="settingsForm.stock_consumption_history_days" class="form-select" required>
                      <option :value="30">30 days — reacts faster</option>
                      <option :value="90">90 days — recommended</option>
                      <option :value="180">180 days — more stable</option>
                    </select>
                  </div>
                  <div class="col-md-4">
                    <label class="form-label">Company time zone</label>
                    <select v-model="settingsForm.stock_timezone" class="form-select" required>
                      <option v-for="zone in timezoneOptions" :key="zone" :value="zone">{{ zone }}</option>
                    </select>
                  </div>
                  <div class="col-12">
                    <div class="form-check form-switch">
                      <input
                          id="stock-weekly-control-enabled"
                          v-model="settingsForm.stock_weekly_control_enabled"
                          class="form-check-input"
                          type="checkbox"
                      />
                      <label class="form-check-label" for="stock-weekly-control-enabled">Weekly warehouse stock notification</label>
                    </div>
                  </div>
                  <div class="col-md-6">
                    <label class="form-label">Notification day</label>
                    <select v-model.number="settingsForm.stock_notification_weekday" class="form-select" :disabled="!settingsForm.stock_weekly_control_enabled">
                      <option :value="0">Monday</option>
                      <option :value="1">Tuesday</option>
                      <option :value="2">Wednesday</option>
                      <option :value="3">Thursday</option>
                      <option :value="4">Friday</option>
                      <option :value="5">Saturday</option>
                      <option :value="6">Sunday</option>
                    </select>
                  </div>
                  <div class="col-md-6">
                    <label class="form-label">Notification time</label>
                    <input v-model="settingsForm.stock_notification_time" type="time" class="form-control" :disabled="!settingsForm.stock_weekly_control_enabled" />
                    <div class="form-text">The notification is created on the first app activity after this time.</div>
                  </div>
                  <div class="col-12">
                    <hr class="my-2" />
                    <h6 class="mb-0">Pricing settings</h6>
                  </div>
                  <div class="col-md-4">
                    <label class="form-label">CNY to local rate</label>
                    <input v-model="settingsForm.cny_to_local_rate" type="number" step="0.01" min="0" class="form-control" required />
                  </div>
                  <div class="col-md-4">
                    <label class="form-label">USD to local rate</label>
                    <input v-model="settingsForm.usd_to_local_rate" type="number" step="0.01" min="0" class="form-control" required />
                  </div>
                  <div class="col-md-4">
                    <label class="form-label">Logistics USD/kg</label>
                    <input v-model="settingsForm.logistics_cost_per_kg_usd" type="number" step="0.01" min="0" class="form-control" required />
                  </div>
                  <div class="col-md-4">
                    <label class="form-label">Internal logistics, %</label>
                    <input v-model="settingsForm.internal_logistics_pct" type="number" step="0.01" min="0" class="form-control" required />
                  </div>
                  <div class="col-md-4">
                    <label class="form-label">Retail tax, %</label>
                    <input v-model="settingsForm.retail_tax_pct" type="number" step="0.01" min="0" class="form-control" required />
                  </div>
                  <div class="col-md-4">
                    <label class="form-label">Acquiring fee, %</label>
                    <input v-model="settingsForm.acquiring_pct" type="number" step="0.01" min="0" class="form-control" required />
                  </div>
                  <div class="col-md-4">
                    <label class="form-label">Packaging fee, %</label>
                    <input v-model="settingsForm.packaging_pct" type="number" step="0.01" min="0" class="form-control" required />
                  </div>
                  <div class="col-md-6">
                    <label class="form-label">{{ $t('Markup, %') }}</label>
                    <input v-model="settingsForm.margin_pct" type="number" step="0.01" min="0" class="form-control" required />
                  </div>
                  <div class="col-12">
                    <hr class="my-2" />
                    <h6 class="mb-0">Directories</h6>
                  </div>
                  <div
                    v-for="directory in settingsDirectories"
                    :key="directory.type"
                    class="col-md-6"
                  >
                    <div class="directory-box">
                      <label class="form-label">{{ $t(directory.label) }}</label>
                      <div class="input-group directory-input-group mb-2">
                        <select
                          :value="directory.selectedId"
                          class="form-select"
                          data-i18n-skip
                          @change="selectSettingsDirectory(directory.type, $event.target.value)"
                        >
                          <option disabled value="">{{ $t('Select...') }}</option>
                          <option v-for="item in directory.items" :key="item.id" :value="item.id">
                            {{ directoryItemName(directory.type, item) }}{{ item.is_archived ? ` (${$t('Archived')})` : '' }}
                          </option>
                        </select>
                        <IconButton
                          icon="plus-lg"
                          variant="outline-primary"
                          :title="$t('Create new item')"
                          @click="startNewSettingsDirectory(directory.type)"
                        />
                        <IconButton v-if="directory.type === 'department'"
                          :icon="selectedSettingsDirectoryItem('department')?.is_archived ? 'arrow-counterclockwise' : 'archive'"
                          :title="selectedSettingsDirectoryItem('department')?.is_archived ? $t('Restore department') : $t('Archive department')"
                          :disabled="!selectedSettingsDirectoryItem('department') || Boolean(isDeletingReference)"
                          @click="toggleDepartmentArchive" />
                        <IconButton v-else
                          icon="trash"
                          variant="outline-danger"
                          :disabled="!selectedSettingsDirectoryItem(directory.type) || isDeletingReference === `${directory.type}-${directory.selectedId}`"
                          @click="deleteSettingsReference(directory.type, selectedSettingsDirectoryItem(directory.type))"
                          :title="$t('Delete selected item')"
                        />
                      </div>
                      <div class="form-text mb-2">
                        {{ selectedSettingsDirectoryItem(directory.type) ? $t('Editing selected item') : $t('Creating new item') }}
                      </div>
                      <div class="directory-edit-grid" :class="{ 'directory-edit-grid-status': directory.isStatus || directory.isTranslated }">
                        <input
                          v-if="!directory.isStatus && !directory.isTranslated"
                          v-model.trim="settingsDirectoryForms[directory.type].name"
                          type="text"
                          class="form-control form-control-sm"
                          placeholder="Name"
                        />
                        <template v-else>
                          <div>
                            <label class="form-label small mb-1">{{ $t('Russian name') }}</label>
                            <input
                              v-model.trim="settingsDirectoryForms[directory.type].translations.ru"
                              type="text"
                              class="form-control form-control-sm"
                              :placeholder="$t('Russian name')"
                            />
                          </div>
                          <div>
                            <label class="form-label small mb-1">{{ $t('English name') }}</label>
                            <input
                              v-model.trim="settingsDirectoryForms[directory.type].translations.en"
                              type="text"
                              class="form-control form-control-sm"
                              :placeholder="$t('English name')"
                            />
                          </div>
                        </template>
                        <input
                          v-if="directory.hasColor"
                          v-model="settingsDirectoryForms[directory.type].color"
                          type="color"
                          class="form-control form-control-color form-control-sm"
                          title="Color"
                        />
                        <input
                          v-if="directory.hasMargin"
                          v-model="settingsDirectoryForms[directory.type].margin_pct"
                          type="number"
                          step="0.01"
                          min="0"
                          class="form-control form-control-sm"
                          :placeholder="$t('Markup, %')"
                        />
                      </div>
                      <div class="d-flex mt-2">
                        <button
                          v-if="!selectedSettingsDirectoryItem(directory.type)"
                          type="button"
                          class="btn btn-primary btn-sm flex-fill"
                          :disabled="!directoryFormHasName(directory.type)"
                          @click="createSettingsDirectory(directory.type)"
                        >
                          {{ $t('Add new item') }}
                        </button>
                        <button
                          v-else
                          type="button"
                          class="btn btn-outline-primary btn-sm flex-fill"
                          :disabled="!directoryFormHasName(directory.type)"
                          @click="updateSettingsDirectory(directory.type)"
                        >
                          {{ $t('Save changes') }}
                        </button>
                      </div>
                    </div>
                  </div>
                </div>

                <div v-if="settingsSuccess" class="alert alert-success mt-3 mb-0">
                  {{ $t(settingsSuccess) }}
                </div>
                <div v-if="settingsError" class="alert alert-danger mt-3 mb-0">
                  {{ settingsError }}
                </div>
              </div>
              <div class="modal-footer">
                <button type="button" class="btn btn-outline-secondary" :disabled="isSavingSettings" @click="closeSettingsModal">
                  Cancel
                </button>
                <button class="btn btn-primary px-4" :disabled="isSavingSettings || isLoadingSettings">
                  {{ isSavingSettings ? 'Saving...' : 'Save settings' }}
                </button>
              </div>
            </form>
          </div>
        </transition>
      </div>
    </div>
    <div
        class="modal-backdrop fade"
        :class="{ show: showInviteModal || showSettingsModal || isEditing }"
        v-if="showInviteModal || showSettingsModal || isEditing"
    ></div>
  </div>
</template>

<script>
import axios, { clearClientSession } from '../axios';
import { clearCacheByPrefix } from '../utils/pageCache';
import IconButton from '../components/IconButton.vue';
import { languageState } from '../i18n';
import { setCurrentUser } from '../access';

const API_ORIGIN = 'http://localhost:8000';
const SYSTEM_DIRECTORY_NAMES = {
  category: new Set(['General']),
  unit: new Set(['pcs', 'kg', 'g', 'm', 'm2', 'm3', 'box', 'set']),
  counterpartyStatus: new Set(['New', 'Active', 'Blocked']),
  customerOrderStatus: new Set(['New', 'In progress', 'Shipped', 'Completed', 'Cancelled']),
  supplierOrderStatus: new Set(['New', 'In production', 'In transit', 'Received', 'Cancelled']),
};
const SYSTEM_ROLE_NAMES = new Set(['Company admin', 'WED manager', 'Purchasing manager', 'Sales manager', 'Financial analyst', 'Warehouse manager', 'Viewer']);

export default {
  name: 'ProfilePage',
  components: { IconButton },
  data() {
    return {
      profile: {},
      form: {},
      avatarFile: null,
      avatarPreview: null,
      avatarCrop: { zoom: 1, x: 0, y: 0 },
      avatarImageSize: { width: 0, height: 0 },
      avatarDrag: { active: false, startX: 0, startY: 0, originX: 0, originY: 0 },
      invitationForm: {
        email: '',
        first_name: '',
        last_name: '',
        access_role: '',
        department: null,
        position: '',
      },
      invitations: [],
      employees: [],
      accessRoles: [],
      departments: [],
      countries: [],
      settingsCountrySearch: '',
      showSettingsCountrySuggestions: false,
      highlightedSettingsCountryIndex: 0,
      settingsForm: {
        business_country: '',
        company_language_code: 'ru',
        company_currency_code: '',
        company_currency_symbol: '',
        cny_to_local_rate: '',
        usd_to_local_rate: '',
        logistics_cost_per_kg_usd: '',
        internal_logistics_pct: '',
        retail_tax_pct: '',
        acquiring_pct: '',
        packaging_pct: '',
        margin_pct: '',
        settings_confirmed_at: '',
        company_logo_url: '',
        company_work_email: '',
        company_phone: '',
        company_address: '',
        company_china_warehouse_address: '',
        company_bank_details: '',
        stock_delivery_lead_days: 30,
        stock_consumption_history_days: 90,
        stock_timezone: 'Asia/Almaty',
        stock_weekly_control_enabled: true,
        stock_notification_weekday: 0,
        stock_notification_time: '10:00',
      },
      companyLogoFile: null,
      companyLogoPreview: null,
      invitationSuccess: '',
      invitationError: '',
      inviteModalTab: 'invite',
      employeeStatusFilter: 'active',
      selectedEmployee: null,
      settingsSuccess: '',
      settingsError: '',
      settingsCategories: [],
      settingsUnits: [],
      settingsDepartments: [],
      selectedSettingsDepartmentId: '',
      invitationAction: null,
      settingsCounterpartyStatuses: [],
      settingsCustomerOrderStatuses: [],
      settingsSupplierOrderStatuses: [],
      selectedSettingsCategoryId: '',
      selectedSettingsUnitId: '',
      selectedSettingsCounterpartyStatusId: '',
      selectedSettingsCustomerOrderStatusId: '',
      selectedSettingsSupplierOrderStatusId: '',
      settingsDirectoryForms: {
        department: { name: '', translations: { ru: '', en: '' }, sourceName: '', displayName: '' },
        category: { name: '', sourceName: '', displayName: '', margin_pct: '' },
        unit: { name: '', sourceName: '', displayName: '' },
        counterpartyStatus: { name: '', translations: { ru: '', en: '' }, sourceName: '', displayName: '', color: '#6c757d' },
        customerOrderStatus: { name: '', translations: { ru: '', en: '' }, sourceName: '', displayName: '', color: '#0d6efd' },
        supplierOrderStatus: { name: '', translations: { ru: '', en: '' }, sourceName: '', displayName: '', color: '#0d6efd' },
      },
      showInviteModal: false,
      showSettingsModal: false,
      isEditing: false,
      isLoading: false,
      isSaving: false,
      isLoggingOut: false,
      isSendingInvitation: false,
      isLoadingEmployees: false,
      isDismissingEmployee: null,
      isSavingEmployeeRole: false,
      selectedEmployeeRoleId: '',
      isLoadingSettings: false,
      isSavingSettings: false,
      isDeletingReference: null,
      isSwitchingCompany: false,
    };
  },
  computed: {
    displayName() {
      const fullName = [this.profile.first_name, this.profile.last_name].filter(Boolean).join(' ');
      return fullName || this.profile.username || 'Profile';
    },
    initials() {
      const first = this.profile.first_name || this.profile.username || '';
      const last = this.profile.last_name || '';
      return `${first.charAt(0)}${last.charAt(0)}`.toUpperCase() || 'U';
    },
    roleLabel() {
      return this.systemRoleName(this.profile.access_role_name || this.profile.role_display || this.profile.role || 'User');
    },
    avatarSrc() {
      return this.avatarPreview || this.mediaUrl(this.profile.avatar);
    },
    avatarPreviewStyle() {
      const size = this.avatarPreviewDisplaySize(112);
      return {
        width: `${size.width}px`,
        height: `${size.height}px`,
        transform: `translate(calc(-50% + ${this.avatarCrop.x}px), calc(-50% + ${this.avatarCrop.y}px))`,
      };
    },
    contactFields() {
      return [
        { key: 'first_name', label: this.$t('First name'), value: this.profile.first_name },
        { key: 'last_name', label: this.$t('Last name'), value: this.profile.last_name },
        { key: 'work_email', label: this.$t('Work email'), value: this.profile.work_email },
        { key: 'personal_email', label: this.$t('Personal email'), value: this.profile.personal_email },
        { key: 'phone', label: this.$t('Mobile phone'), value: this.profile.phone },
        { key: 'department', label: this.$t('Department'), value: this.profile.department },
        { key: 'position', label: this.$t('Position'), value: this.profile.position },
        { key: 'birth_date', label: this.$t('Birth date'), value: this.formatDate(this.profile.birth_date) },
        { key: 'hire_date', label: this.$t('Hire date'), value: this.formatDate(this.profile.hire_date) },
      ];
    },
    companyMemberships() {
      return this.profile.memberships || [];
    },
    employeeRoleChanged() {
      return Boolean(
        this.selectedEmployee
        && this.selectedEmployeeRoleId
        && Number(this.selectedEmployeeRoleId) !== Number(this.selectedEmployee.access_role)
      );
    },
    timezoneOptions() {
      const fallback = ['UTC', 'Asia/Almaty', 'Asia/Qyzylorda', 'Asia/Shanghai', 'Europe/Moscow', 'America/New_York'];
      try {
        const zones = Intl.supportedValuesOf('timeZone');
        if (this.settingsForm.stock_timezone && !zones.includes(this.settingsForm.stock_timezone)) {
          return [this.settingsForm.stock_timezone, ...zones];
        }
        return zones;
      } catch {
        return fallback;
      }
    },
    filteredSettingsCountries() {
      const query = this.settingsCountrySearch.trim().toLowerCase();
      return query
        ? this.countries.filter(country =>
          country.name.toLowerCase().includes(query) ||
          country.code.toLowerCase().includes(query)
        )
        : this.countries;
    },
    selectedSettingsCategory() {
      return this.settingsCategories.find(category => Number(category.id) === Number(this.selectedSettingsCategoryId)) || null;
    },
    selectedSettingsUnit() {
      return this.settingsUnits.find(unit => Number(unit.id) === Number(this.selectedSettingsUnitId)) || null;
    },
    settingsDirectories() {
      return [
        { type: 'department', label: 'Departments', items: this.settingsDepartments, selectedId: this.selectedSettingsDepartmentId, isTranslated: true },
        {
          type: 'category',
          label: 'Categories',
          items: this.settingsCategories,
          selectedId: this.selectedSettingsCategoryId,
          hasMargin: true,
        },
        {
          type: 'unit',
          label: 'Units',
          items: this.settingsUnits,
          selectedId: this.selectedSettingsUnitId,
        },
        {
          type: 'counterpartyStatus',
          label: 'Counterparty statuses',
          items: this.settingsCounterpartyStatuses,
          selectedId: this.selectedSettingsCounterpartyStatusId,
          hasColor: true,
          isStatus: true,
        },
        {
          type: 'customerOrderStatus',
          label: 'Customer order statuses',
          items: this.settingsCustomerOrderStatuses,
          selectedId: this.selectedSettingsCustomerOrderStatusId,
          hasColor: true,
          isStatus: true,
        },
        {
          type: 'supplierOrderStatus',
          label: 'Supplier order statuses',
          items: this.settingsSupplierOrderStatuses,
          selectedId: this.selectedSettingsSupplierOrderStatusId,
          hasColor: true,
          isStatus: true,
        },
      ];
    },
  },
  created() {
    this.fetchProfile();
  },
  watch: {
    '$route.query.settings': {
      immediate: true,
      async handler(value) {
        if (value === 'company') {
          await this.openSettingsModal();
        }
      },
    },
  },
  methods: {
    async fetchProfile() {
      this.isLoading = true;
      try {
        const { data } = await axios.get('/api/auth/me/');
        this.profile = data;
        this.form = { ...data };
        this.syncProfileForNav(data);
        if (data.is_company_admin) {
          await this.fetchCompanyAccess();
        }
      } finally {
        this.isLoading = false;
      }
    },
    async fetchCompanyAccess() {
      const [rolesRes, departmentsRes, invitationsRes] = await Promise.all([
        axios.get('/api/auth/access-roles/'),
        axios.get('/api/auth/departments/'),
        axios.get('/api/auth/invitations/'),
      ]);
      this.accessRoles = rolesRes.data;
      this.departments = departmentsRes.data;
      this.invitations = invitationsRes.data;
    },
    async openInviteModal() {
      this.invitationForm.access_role = '';
      this.showInviteModal = true;
      this.inviteModalTab = 'invite';
      this.invitationSuccess = '';
      this.invitationError = '';
      await this.fetchCompanyAccess();
    },
    closeInviteModal() {
      if (this.isSendingInvitation || this.invitationAction) return;
      this.showInviteModal = false;
    },
    async openEmployeesTab() {
      this.inviteModalTab = 'employees';
      this.invitationSuccess = '';
      this.invitationError = '';
      await this.fetchEmployees();
    },
    async setEmployeeStatusFilter(status) {
      this.employeeStatusFilter = status;
      await this.fetchEmployees();
    },
    async fetchEmployees() {
      this.isLoadingEmployees = true;
      try {
        const { data } = await axios.get('/api/auth/employees/', {
          params: { status: this.employeeStatusFilter },
        });
        this.employees = data;
        if (this.selectedEmployee) {
          this.selectedEmployee = this.employees.find(employee => employee.id === this.selectedEmployee.id) || null;
          this.selectedEmployeeRoleId = this.selectedEmployee?.access_role || '';
        }
      } catch (error) {
        alert(this.formatError(error.response?.data) || 'Unable to load employees.');
      } finally {
        this.isLoadingEmployees = false;
      }
    },
    selectEmployee(employee) {
      this.selectedEmployee = this.selectedEmployee?.id === employee.id ? null : employee;
      this.selectedEmployeeRoleId = employee.access_role || '';
    },
    async saveEmployeeRole() {
      if (!this.selectedEmployee || !this.employeeRoleChanged) return;
      this.isSavingEmployeeRole = true;
      try {
        const { data } = await axios.patch(
          `/api/auth/employees/${this.selectedEmployee.id}/access-role/`,
          { access_role: this.selectedEmployeeRoleId },
        );
        this.selectedEmployee = data;
        this.selectedEmployeeRoleId = data.access_role || '';
        const index = this.employees.findIndex(employee => employee.id === data.id);
        if (index >= 0) this.employees.splice(index, 1, data);
      } catch (error) {
        alert(this.formatError(error.response?.data) || this.$t('Unable to update employee role.'));
      } finally {
        this.isSavingEmployeeRole = false;
      }
    },
    async dismissEmployee(employee) {
      const employeeName = this.employeeName(employee);
      const companyName = this.profile.company_name || this.$t('this company');
      const reason = prompt(
        `${this.$t('Dismiss employee')} ${employeeName} ${this.$t('from company')} ${companyName}?\n\n${this.$t('Reason')}:`,
      );
      if (reason === null) {
        return;
      }
      this.isDismissingEmployee = employee.id;
      try {
        await axios.post(`/api/auth/employees/${employee.id}/dismiss/`, {
          reason: reason.trim(),
        });
        await this.fetchEmployees();
      } catch (error) {
        alert(this.formatError(error.response?.data) || this.$t('Unable to dismiss employee.'));
      } finally {
        this.isDismissingEmployee = null;
      }
    },
    async openSettingsModal() {
      this.showSettingsModal = true;
      this.settingsSuccess = '';
      this.settingsError = '';
      await this.fetchCountries();
      await Promise.all([
        this.fetchCompanySettings(),
        this.fetchSettingsDirectories(),
      ]);
    },
    closeSettingsModal() {
      if (this.isSavingSettings) return;
      this.showSettingsModal = false;
      this.companyLogoFile = null;
      if (this.companyLogoPreview) {
        URL.revokeObjectURL(this.companyLogoPreview);
        this.companyLogoPreview = null;
      }
    },
    async fetchCompanySettings() {
      this.isLoadingSettings = true;
      this.settingsError = '';
      try {
        const { data } = await axios.get('/api/settings/');
        const settings = data[0] || {};
        this.settingsForm = {
          ...this.settingsForm,
          ...this.settingsToForm(settings),
          business_country: settings.company_business_country || settings.business_country || '',
        };
        this.settingsCountrySearch = this.countryNameByCode(this.settingsForm.business_country) || settings.company_business_country_name;
      } catch (error) {
        this.settingsError = this.formatError(error.response?.data) || 'Unable to load company settings.';
      } finally {
        this.isLoadingSettings = false;
      }
    },
    async fetchSettingsCategories() {
      await this.fetchSettingsDirectory('category');
    },
    async fetchSettingsUnits() {
      await this.fetchSettingsDirectory('unit');
    },
    async fetchSettingsDirectories() {
      await Promise.all([
        this.fetchSettingsDirectory('category'),
        this.fetchSettingsDirectory('unit'),
        this.fetchSettingsDirectory('department'),
        this.fetchSettingsDirectory('counterpartyStatus'),
        this.fetchSettingsDirectory('customerOrderStatus'),
        this.fetchSettingsDirectory('supplierOrderStatus'),
      ]);
    },
    directoryConfig(type) {
      const configs = {
        department: { url: '/api/auth/departments/', listKey: 'settingsDepartments', selectedKey: 'selectedSettingsDepartmentId', label: 'Department' },
        category: {
          url: '/api/product-category/',
          listKey: 'settingsCategories',
          selectedKey: 'selectedSettingsCategoryId',
          cachePrefix: 'product-categories',
          label: 'Category',
        },
        unit: {
          url: '/api/units/',
          listKey: 'settingsUnits',
          selectedKey: 'selectedSettingsUnitId',
          cachePrefix: 'product-units',
          label: 'Unit',
        },
        counterpartyStatus: {
          url: '/api/counterparty-statuses/',
          listKey: 'settingsCounterpartyStatuses',
          selectedKey: 'selectedSettingsCounterpartyStatusId',
          label: 'Counterparty status',
        },
        customerOrderStatus: {
          url: '/api/customer-order-statuses/',
          listKey: 'settingsCustomerOrderStatuses',
          selectedKey: 'selectedSettingsCustomerOrderStatusId',
          label: 'Customer order status',
        },
        supplierOrderStatus: {
          url: '/api/supplier-order-statuses/',
          listKey: 'settingsSupplierOrderStatuses',
          selectedKey: 'selectedSettingsSupplierOrderStatusId',
          label: 'Supplier order status',
        },
      };
      return configs[type];
    },
    async fetchSettingsDirectory(type) {
      const config = this.directoryConfig(type);
      try {
        const { data } = await axios.get(config.url, type === 'department' ? { params: { include_archived: true } } : {});
        this[config.listKey] = data;
        this[config.selectedKey] = data[0]?.id || '';
        this.fillSettingsDirectoryForm(type, data[0] || null);
      } catch (error) {
        this.settingsError = this.formatError(error.response?.data) || `Unable to load ${config.label.toLowerCase()} list.`;
      }
    },
    selectedSettingsDirectoryItem(type) {
      const config = this.directoryConfig(type);
      const selectedId = this[config.selectedKey];
      return this[config.listKey].find(item => Number(item.id) === Number(selectedId)) || null;
    },
    selectSettingsDirectory(type, id) {
      const config = this.directoryConfig(type);
      this[config.selectedKey] = id;
      this.fillSettingsDirectoryForm(type, this.selectedSettingsDirectoryItem(type));
    },
    startNewSettingsDirectory(type) {
      const config = this.directoryConfig(type);
      this[config.selectedKey] = '';
      this.fillSettingsDirectoryForm(type, null);
    },
    fillSettingsDirectoryForm(type, item) {
      if (!item) {
        this.settingsDirectoryForms[type] = {
          ...this.settingsDirectoryForms[type],
          name: '',
          translations: { ru: '', en: '' },
          sourceName: '',
          displayName: '',
          margin_pct: type === 'category' ? '' : this.settingsDirectoryForms[type].margin_pct,
        };
        return;
      }
      const sourceName = item.name || '';
      const displayName = this.directoryItemName(type, item);
      if (type === 'category') {
        this.settingsDirectoryForms.category = {
          name: displayName,
          sourceName,
          displayName,
          margin_pct: item.margin_pct == null ? '' : this.rateToPercent(item.margin_pct),
        };
      } else if (type === 'unit') {
        this.settingsDirectoryForms.unit = { name: displayName, sourceName, displayName };
      } else {
        this.settingsDirectoryForms[type] = {
          name: displayName,
          translations: {
            ru: item.translations?.ru || '',
            en: item.translations?.en || '',
          },
          sourceName,
          displayName,
          color: item.color || '#0d6efd',
        };
      }
    },
    departmentName(item) {
      return item?.translations?.[languageState.locale] || item?.name || item?.translations?.ru || item?.translations?.en || '';
    },
    directoryItemName(type, item) {
      if (type === 'department') return this.departmentName(item);
      const name = typeof item === 'string' ? item : (item?.name || '');
      if (typeof item === 'object' && item?.display_name) return item.display_name;
      if (!SYSTEM_DIRECTORY_NAMES[type]?.has(name)) return name;
      const key = `directory.${type}.${name}`;
      const translated = this.$t(key);
      return translated === key ? name : translated;
    },
    systemRoleName(name) {
      if (!SYSTEM_ROLE_NAMES.has(name)) return name;
      const key = `role.${name}`;
      const translated = this.$t(key);
      return translated === key ? name : translated;
    },
    directoryPayload(type) {
      const form = this.settingsDirectoryForms[type];
      const name = form.name === form.displayName ? form.sourceName : form.name;
      const payload = { name };
      if (type === 'category') {
        payload.margin_pct = form.margin_pct === '' ? null : this.percentToRate(form.margin_pct);
      }
      if (type.endsWith('Status') || type === 'department') {
        payload.translations = {
          ru: form.translations?.ru || '',
          en: form.translations?.en || '',
        };
        payload.name = form.sourceName || payload.translations.en || payload.translations.ru;
        if (type.endsWith('Status')) payload.color = form.color || '#0d6efd';
        if (type === 'department') payload.name = payload.translations.ru || payload.translations.en;
      }
      return payload;
    },
    directoryFormHasName(type) {
      const form = this.settingsDirectoryForms[type];
      return (type.endsWith('Status') || type === 'department')
        ? Boolean(form.translations?.ru || form.translations?.en)
        : Boolean(form.name);
    },
    async createSettingsDirectory(type) {
      const config = this.directoryConfig(type);
      this.settingsSuccess = '';
      this.settingsError = '';
      try {
        const { data } = await axios.post(config.url, this.directoryPayload(type));
        this[config.listKey].push(data);
        this[config.selectedKey] = data.id;
        this.fillSettingsDirectoryForm(type, data);
        if (config.cachePrefix) clearCacheByPrefix(config.cachePrefix);
        this.settingsSuccess = type === 'department' ? 'Department has been added.' : `${config.label} has been added.`;
      } catch (error) {
        this.settingsError = this.formatError(error.response?.data) || (type === 'department' ? this.$t('Unable to add department.') : `Unable to add ${config.label.toLowerCase()}.`);
      }
    },
    async updateSettingsDirectory(type) {
      const config = this.directoryConfig(type);
      const item = this.selectedSettingsDirectoryItem(type);
      if (!item) return;
      this.settingsSuccess = '';
      this.settingsError = '';
      try {
        const { data } = await axios.patch(`${config.url}${item.id}/`, this.directoryPayload(type));
        const idx = this[config.listKey].findIndex(entry => entry.id === data.id);
        if (idx !== -1) this[config.listKey].splice(idx, 1, data);
        this.fillSettingsDirectoryForm(type, data);
        if (config.cachePrefix) clearCacheByPrefix(config.cachePrefix);
        this.settingsSuccess = type === 'department' ? 'Department has been saved.' : `${config.label} has been saved.`;
      } catch (error) {
        this.settingsError = this.formatError(error.response?.data) || (type === 'department' ? this.$t('Unable to update department.') : `Unable to save ${config.label.toLowerCase()}.`);
      }
    },
    async deleteSettingsReference(type, item) {
      const config = this.directoryConfig(type);
      const label = config.label.toLowerCase();
      if (!confirm(`Delete ${label} "${item.name}"?`)) return;

      this.isDeletingReference = `${type}-${item.id}`;
      this.settingsSuccess = '';
      this.settingsError = '';
      try {
        await axios.delete(`${config.url}${item.id}/`);
        this[config.listKey] = this[config.listKey].filter(entry => entry.id !== item.id);
        this[config.selectedKey] = this[config.listKey][0]?.id || '';
        this.fillSettingsDirectoryForm(type, this[config.listKey][0] || null);
        if (config.cachePrefix) clearCacheByPrefix(config.cachePrefix);
        this.settingsSuccess = `${config.label} has been deleted.`;
      } catch (error) {
        this.settingsError = this.formatError(error.response?.data) || `Unable to delete ${label}.`;
      } finally {
        this.isDeletingReference = null;
      }
    },
    async saveCompanySettings() {
      this.isSavingSettings = true;
      this.settingsSuccess = '';
      this.settingsError = '';
      if (!this.settingsForm.business_country) {
        this.settingsError = 'Please select a country from the list.';
        this.isSavingSettings = false;
        return;
      }
      try {
        const payload = new FormData();
        payload.append('business_country', this.settingsForm.business_country);
        payload.append('company_language_code', this.settingsForm.company_language_code || 'ru');
        payload.append('cny_to_local_rate', this.settingsForm.cny_to_local_rate);
        payload.append('usd_to_local_rate', this.settingsForm.usd_to_local_rate);
        payload.append('logistics_cost_per_kg_usd', this.settingsForm.logistics_cost_per_kg_usd);
        payload.append('internal_logistics_pct', this.percentToRate(this.settingsForm.internal_logistics_pct));
        payload.append('retail_tax_pct', this.percentToRate(this.settingsForm.retail_tax_pct));
        payload.append('acquiring_pct', this.percentToRate(this.settingsForm.acquiring_pct));
        payload.append('packaging_pct', this.percentToRate(this.settingsForm.packaging_pct));
        payload.append('margin_pct', this.percentToRate(this.settingsForm.margin_pct));
        payload.append('stock_delivery_lead_days', this.settingsForm.stock_delivery_lead_days);
        payload.append('stock_consumption_history_days', this.settingsForm.stock_consumption_history_days);
        payload.append('stock_timezone', this.settingsForm.stock_timezone);
        payload.append('stock_weekly_control_enabled', this.settingsForm.stock_weekly_control_enabled);
        payload.append('stock_notification_weekday', this.settingsForm.stock_notification_weekday);
        payload.append('stock_notification_time', this.settingsForm.stock_notification_time);
        payload.append('company_work_email', this.settingsForm.company_work_email || '');
        payload.append('company_phone', this.settingsForm.company_phone || '');
        payload.append('company_address', this.settingsForm.company_address || '');
        payload.append('company_china_warehouse_address', this.settingsForm.company_china_warehouse_address || '');
        payload.append('company_bank_details', this.settingsForm.company_bank_details || '');
        if (this.companyLogoFile) {
          payload.append('company_logo', this.companyLogoFile);
        }
        const { data } = await axios.post('/api/settings/', payload, {
          headers: { 'Content-Type': 'multipart/form-data' },
        });
        this.settingsForm = {
          ...this.settingsForm,
          ...this.settingsToForm(data),
          business_country: data.company_business_country || this.settingsForm.business_country,
        };
        this.companyLogoFile = null;
        if (this.companyLogoPreview) {
          URL.revokeObjectURL(this.companyLogoPreview);
          this.companyLogoPreview = null;
        }
        this.settingsCountrySearch = this.countryNameByCode(this.settingsForm.business_country) || data.company_business_country_name;
        this.showSettingsCountrySuggestions = false;
        this.settingsSuccess = 'Company settings have been saved.';
        await this.fetchProfile();
      } catch (error) {
        this.settingsError = this.formatError(error.response?.data) || 'Unable to save company settings.';
      } finally {
        this.isSavingSettings = false;
      }
    },
    async fetchCountries() {
      if (this.countries.length) return;
      try {
        const { data } = await axios.get('/api/auth/business-countries/');
        this.countries = data;
      } catch {
        this.countries = [];
      }
    },
    countryNameByCode(code) {
      return this.countries.find(country => country.code === code)?.name || '';
    },
    percentToRate(value) {
      const numberValue = Number(String(value || '0').replace(',', '.'));
      return (numberValue / 100).toFixed(4);
    },
    rateToPercent(value) {
      const numberValue = Number(String(value || '0').replace(',', '.'));
      return Number((numberValue * 100).toFixed(2));
    },
    settingsToForm(settings) {
      return {
        ...settings,
        stock_consumption_history_days: Number(settings.stock_consumption_history_days || 90),
        stock_notification_time: settings.stock_notification_time?.slice(0, 5) || '10:00',
        internal_logistics_pct: this.rateToPercent(settings.internal_logistics_pct),
        retail_tax_pct: this.rateToPercent(settings.retail_tax_pct),
        acquiring_pct: this.rateToPercent(settings.acquiring_pct),
        packaging_pct: this.rateToPercent(settings.packaging_pct),
        margin_pct: this.rateToPercent(settings.margin_pct),
      };
    },
    handleCompanyLogoChange(event) {
      const file = event.target.files?.[0];
      if (!file) return;
      this.companyLogoFile = file;
      if (this.companyLogoPreview) URL.revokeObjectURL(this.companyLogoPreview);
      this.companyLogoPreview = URL.createObjectURL(file);
    },
    onSettingsCountrySearchInput() {
      this.settingsForm.business_country = '';
      this.highlightedSettingsCountryIndex = 0;
      this.showSettingsCountrySuggestions = true;
    },
    selectSettingsCountry(country) {
      this.settingsForm.business_country = country.code;
      this.settingsCountrySearch = country.name;
      this.showSettingsCountrySuggestions = false;
    },
    moveSettingsCountryHighlight(direction) {
      if (!this.filteredSettingsCountries.length) return;
      const max = this.filteredSettingsCountries.length - 1;
      this.highlightedSettingsCountryIndex += direction;
      if (this.highlightedSettingsCountryIndex < 0) this.highlightedSettingsCountryIndex = max;
      if (this.highlightedSettingsCountryIndex > max) this.highlightedSettingsCountryIndex = 0;
    },
    selectHighlightedSettingsCountry() {
      const country = this.filteredSettingsCountries[this.highlightedSettingsCountryIndex];
      if (country) this.selectSettingsCountry(country);
    },
    hideSettingsCountrySuggestions() {
      setTimeout(() => {
        this.showSettingsCountrySuggestions = false;
      }, 120);
    },
    async toggleDepartmentArchive() {
      const item = this.selectedSettingsDirectoryItem('department');
      if (!item) return;
      this.isDeletingReference = `department-${item.id}`;
      this.settingsError = '';
      this.settingsSuccess = '';
      try {
        const { data } = await axios.patch(`/api/auth/departments/${item.id}/`, { is_archived: !item.is_archived });
        const index = this.settingsDepartments.findIndex(entry => entry.id === data.id);
        this.settingsDepartments.splice(index, 1, data);
        this.settingsSuccess = data.is_archived ? 'Department has been archived.' : 'Department has been restored.';
      } catch (error) {
        this.settingsError = this.formatError(error.response?.data) || this.$t('Unable to update department.');
      } finally {
        this.isDeletingReference = null;
      }
    },
    async manageInvitation(invitation, action) {
      if (this.invitationAction || this.isSendingInvitation) return;
      this.invitationAction = `${action}-${invitation.id}`;
      this.invitationError = '';
      this.invitationSuccess = '';
      try {
        const { data } = await axios.post(`/api/auth/invitations/${invitation.id}/${action}/`);
        this.invitations = this.invitations.filter(item => item.id !== invitation.id);
        if (action === 'resend') this.invitations.unshift(data);
        this.invitationSuccess = action === 'resend' ? 'Invitation has been resent.' : 'Invitation has been revoked.';
      } catch (error) {
        this.invitationError = this.formatError(error.response?.data) || this.$t('Unable to update invitation.');
      } finally {
        this.invitationAction = null;
      }
    },
    async sendInvitation() {
      this.isSendingInvitation = true;
      this.invitationSuccess = '';
      this.invitationError = '';
      try {
        const payload = {
          access_role: this.invitationForm.access_role || null,
          email: this.invitationForm.email,
          first_name: this.invitationForm.first_name,
          last_name: this.invitationForm.last_name,
          department: this.invitationForm.department,
          position: this.invitationForm.position,
        };
        const { data } = await axios.post('/api/auth/invitations/', payload);
        this.invitations = [data, ...this.invitations];
        this.invitationSuccess = 'Invitation has been sent.';
        this.invitationForm = {
          email: '',
          first_name: '',
          last_name: '',
          access_role: '',
          department: null,
          position: '',
        };
        await this.fetchCompanyAccess();
        if (this.inviteModalTab === 'employees') {
          await this.fetchEmployees();
        }
      } catch (error) {
        this.invitationError = this.formatError(error.response?.data) || 'Unable to send invitation.';
      } finally {
        this.isSendingInvitation = false;
      }
    },
    async switchCompany(companyId) {
      const nextCompanyId = Number(companyId);
      if (!nextCompanyId || nextCompanyId === Number(this.profile.company_id)) return;
      this.isSwitchingCompany = true;
      try {
        const { data } = await axios.post('/api/auth/switch-company/', { company_id: nextCompanyId });
        this.clearCompanyScopedCache();
        this.profile = data;
        this.form = { ...data };
        this.syncProfileForNav(data);
        await this.fetchCompanyAccess();
        if (this.showInviteModal && this.inviteModalTab === 'employees') {
          await this.fetchEmployees();
        }
        if (this.showSettingsModal) {
          await this.fetchCompanySettings();
        }
        await this.fetchProfile();
      } catch (error) {
        alert(this.formatError(error.response?.data) || 'Unable to switch company');
      } finally {
        this.isSwitchingCompany = false;
      }
    },
    clearCompanyScopedCache() {
      sessionStorage.clear();
      [
        'customer-order-statuses',
        'supplier-order-statuses',
        'counterparty-statuses',
        'counterparty-options',
        'customer-orders:',
        'supplier-orders:',
        'counterparties:',
        'products:',
        'product-categories',
        'product-units',
      ].forEach(prefix => clearCacheByPrefix(prefix));
    },
    startEditing() {
      this.form = { ...this.profile };
      this.avatarFile = null;
      this.avatarPreview = null;
      this.avatarCrop = { zoom: 1, x: 0, y: 0 };
      this.avatarImageSize = { width: 0, height: 0 };
      this.isEditing = true;
    },
    cancelEditing() {
      this.form = { ...this.profile };
      this.avatarFile = null;
      this.avatarPreview = null;
      this.avatarCrop = { zoom: 1, x: 0, y: 0 };
      this.avatarImageSize = { width: 0, height: 0 };
      this.isEditing = false;
    },
    async handleAvatarChange(event) {
      const file = event.target.files?.[0];
      if (!file) return;
      this.avatarFile = file;
      if (this.avatarPreview) URL.revokeObjectURL(this.avatarPreview);
      const previewUrl = URL.createObjectURL(file);
      const image = await this.loadImage(previewUrl);
      this.avatarPreview = previewUrl;
      this.avatarImageSize = { width: image.width, height: image.height };
      this.avatarCrop = { zoom: 1, x: 0, y: 0 };
    },
    startAvatarDrag(event) {
      this.avatarDrag = {
        active: true,
        startX: event.clientX,
        startY: event.clientY,
        originX: this.avatarCrop.x,
        originY: this.avatarCrop.y,
      };
      event.currentTarget.setPointerCapture?.(event.pointerId);
    },
    dragAvatar(event) {
      if (!this.avatarDrag.active) return;
      this.avatarCrop.x = this.clampAvatarOffset('x', this.avatarDrag.originX + event.clientX - this.avatarDrag.startX);
      this.avatarCrop.y = this.clampAvatarOffset('y', this.avatarDrag.originY + event.clientY - this.avatarDrag.startY);
    },
    endAvatarDrag() {
      this.avatarDrag.active = false;
    },
    zoomAvatar(event) {
      const direction = event.deltaY > 0 ? -1 : 1;
      const nextZoom = this.avatarCrop.zoom + direction * 0.08;
      this.avatarCrop.zoom = Math.min(3, Math.max(1, Number(nextZoom.toFixed(2))));
      this.avatarCrop.x = this.clampAvatarOffset('x', this.avatarCrop.x);
      this.avatarCrop.y = this.clampAvatarOffset('y', this.avatarCrop.y);
    },
    async saveProfile() {
      this.isSaving = true;
      try {
        const formData = new FormData();
        [
          'first_name', 'last_name', 'middle_name', 'phone',
          'work_email', 'personal_email', 'position', 'department',
          'birth_date', 'hire_date', 'notification_language',
        ].forEach(key => {
          formData.append(key, this.form[key] || '');
        });
        if (this.avatarFile) {
          formData.append('avatar', await this.buildCroppedAvatarFile());
        }

        const { data } = await axios.patch('/api/auth/me/', formData, {
          headers: { 'Content-Type': 'multipart/form-data' },
        });
        this.profile = data;
        this.form = { ...data };
        this.avatarFile = null;
        this.avatarPreview = null;
        this.avatarCrop = { zoom: 1, x: 0, y: 0 };
        this.avatarImageSize = { width: 0, height: 0 };
        this.isEditing = false;
        this.syncProfileForNav(data);
      } catch (error) {
        console.error(error.response?.data || error);
        alert('Unable to save profile');
      } finally {
        this.isSaving = false;
      }
    },
    async logout() {
      this.isLoggingOut = true;
      try {
        await axios.post('/api/auth/logout/', {});
      } catch (error) {
        console.warn('Logout request failed, clearing local session anyway.', error.response?.data || error);
      } finally {
        clearClientSession();
        window.dispatchEvent(new CustomEvent('profile-updated', { detail: {} }));
        this.isLoggingOut = false;
        this.$router.push('/login');
      }
    },
    syncProfileForNav(profile) {
      setCurrentUser(profile);
      window.dispatchEvent(new CustomEvent('profile-updated', { detail: profile }));
    },
    async buildCroppedAvatarFile() {
      const image = await this.loadImage(this.avatarPreview);
      const canvasSize = 512;
      const canvas = document.createElement('canvas');
      canvas.width = canvasSize;
      canvas.height = canvasSize;
      const ctx = canvas.getContext('2d');

      ctx.fillStyle = '#ffffff';
      ctx.fillRect(0, 0, canvasSize, canvasSize);

      const baseScale = Math.max(canvasSize / image.width, canvasSize / image.height);
      const scale = baseScale * this.avatarCrop.zoom;
      const drawWidth = image.width * scale;
      const drawHeight = image.height * scale;
      const drawX = (canvasSize - drawWidth) / 2 + this.avatarCrop.x * (canvasSize / 112);
      const drawY = (canvasSize - drawHeight) / 2 + this.avatarCrop.y * (canvasSize / 112);

      ctx.drawImage(image, drawX, drawY, drawWidth, drawHeight);

      const blob = await new Promise(resolve => canvas.toBlob(resolve, 'image/jpeg', 0.9));
      return new File([blob], 'avatar.jpg', { type: 'image/jpeg' });
    },
    avatarPreviewDisplaySize(viewportSize) {
      const width = this.avatarImageSize.width || viewportSize;
      const height = this.avatarImageSize.height || viewportSize;
      const baseScale = Math.max(viewportSize / width, viewportSize / height);
      const scale = baseScale * this.avatarCrop.zoom;

      return {
        width: width * scale,
        height: height * scale,
      };
    },
    clampAvatarOffset(axis, value) {
      const size = this.avatarPreviewDisplaySize(112);
      const imageSize = axis === 'x' ? size.width : size.height;
      const maxOffset = Math.max(0, (imageSize - 112) / 2);
      return Math.min(maxOffset, Math.max(-maxOffset, value));
    },
    loadImage(src) {
      return new Promise((resolve, reject) => {
        const image = new Image();
        image.onload = () => resolve(image);
        image.onerror = reject;
        image.src = src;
      });
    },
    mediaUrl(value) {
      if (!value) return '';
      if (value.startsWith('http')) return value;
      return new URL(value, API_ORIGIN).href;
    },
    formatDate(value) {
      return value ? new Date(value).toLocaleDateString() : '';
    },
    formatDateTime(value) {
      return value ? new Date(value).toLocaleString(languageState.locale === 'ru' ? 'ru-RU' : 'en-US') : 'not updated yet';
    },
    employeeName(employee) {
      const fullName = [employee.first_name, employee.last_name].filter(Boolean).join(' ');
      return fullName || employee.username || employee.email;
    },
    languageLabel(value) {
      if (value === 'en') return 'English';
      if (value === 'ru') return 'Russian';
      return value;
    },
    formatError(data) {
      if (!data) return '';
      if (typeof data === 'string') return data;
      if (data.detail || data.error) return data.detail || data.error;
      return Object.values(data).flat().join(' ');
    },
  },
};
</script>

<style scoped>
.profile-page {
  max-width: 1040px;
}

.profile-card {
  overflow: hidden;
  background: #fff;
  border: 1px solid #dee2e6;
  border-radius: 0.5rem;
  box-shadow: 0 0.5rem 1.4rem rgba(33, 37, 41, 0.08);
}

.profile-header {
  display: flex;
  align-items: center;
  gap: 1.5rem;
  padding: 1.5rem;
  background: linear-gradient(180deg, #f8fafc 0%, #fff 100%);
  border-bottom: 1px solid #e9ecef;
}

.avatar-wrap {
  display: flex;
  flex: 0 0 auto;
  flex-direction: column;
  align-items: center;
  gap: 0.75rem;
}

.profile-avatar-frame {
  width: 124px;
  height: 124px;
  padding: 5px;
  background: #fff;
  border: 1px solid #dee2e6;
  border-radius: 50%;
  box-shadow: 0 0.35rem 1rem rgba(33, 37, 41, 0.08);
}

.profile-avatar {
  width: 112px;
  height: 112px;
  object-fit: cover;
  border-radius: 50%;
}

.avatar-crop-viewport {
  position: relative;
  width: 112px;
  height: 112px;
  overflow: hidden;
  background: #e9ecef;
  border-radius: 50%;
  cursor: grab;
  touch-action: none;
}

.avatar-crop-viewport:active {
  cursor: grabbing;
}

.avatar-crop-viewport img {
  position: absolute;
  top: 50%;
  left: 50%;
  max-width: none;
  transform-origin: center;
  user-select: none;
  pointer-events: none;
}

.avatar-placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  color: #495057;
  font-size: 2rem;
  font-weight: 600;
  background: #f1f3f5;
}

.avatar-action {
  border-radius: 0.375rem;
}

.avatar-hint {
  max-width: 160px;
  color: #6c757d;
  font-size: 0.78rem;
  line-height: 1.25;
  text-align: center;
}

.profile-title {
  flex: 1 1 auto;
}

.profile-kicker {
  margin-bottom: 0.35rem;
  color: #6c757d;
  font-size: 0.82rem;
  font-weight: 600;
  text-transform: uppercase;
}

.profile-title h1 {
  margin: 0 0 0.25rem;
  color: #343a40;
  font-size: 2rem;
  font-weight: 600;
}

.profile-subtitle {
  color: #6c757d;
}

.profile-badges {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
  margin-top: 0.75rem;
}

.company-switch {
  max-width: 280px;
}

.profile-actions {
  display: grid;
  grid-template-columns: repeat(2, minmax(132px, 1fr));
  gap: 0.75rem;
  flex: 0 1 330px;
}

.profile-actions .btn {
  min-height: 40px;
  white-space: normal;
}

.profile-section {
  padding: 1.15rem 1.25rem 1.25rem;
}

.section-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 1rem;
}

.section-title h2 {
  margin: 0;
  color: #5c6773;
  font-size: 1.3rem;
  font-weight: 500;
}

.profile-fields {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 0.65rem;
}

.profile-field {
  min-width: 0;
  padding: 0.65rem 0.8rem;
  background: #f8f9fa;
  border: 1px solid #edf0f2;
  border-radius: 0.375rem;
}

.field-label {
  color: #adb5bd;
  font-size: 0.78rem;
}

.field-value {
  margin-top: 0.12rem;
  overflow-wrap: anywhere;
  color: #495057;
  font-size: 0.92rem;
  font-weight: 500;
}

.field-value.empty {
  font-weight: 400;
  color: #adb5bd;
}

.profile-form {
  margin: 0;
  padding: 0;
  background: transparent;
  border: 0;
  border-radius: 0;
}

.profile-edit-layout {
  display: grid;
  grid-template-columns: 160px minmax(0, 1fr);
  gap: 1.25rem;
  align-items: stretch;
  padding: 1rem;
  background: #f8f9fa;
  border: 1px solid #edf0f2;
  border-radius: 0.5rem;
}

.profile-edit-photo {
  display: grid;
  align-content: center;
  justify-items: center;
  gap: 0.65rem;
  min-height: 100%;
  padding: 0;
  background: transparent;
  border: 0;
  border-radius: 0;
}

.invitation-list {
  display: grid;
  gap: 0.65rem;
}

.invitation-item,
.employee-item {
  cursor: pointer;
  transition: border-color 0.15s ease, background-color 0.15s ease;
}

.employee-item.selected {
  background: #eef5ff;
  border-color: #b6d4fe;
}

.employee-item:hover {
  border-color: #ced4da;
}

.employee-toggle {
  flex: 1;
  padding: 0;
  border: 0;
  background: transparent;
  text-align: left;
  color: inherit;
}


.employee-detail-panel {
  padding: 1rem;
  background: #fff;
  border: 1px solid #dce6f3;
  border-radius: 0.375rem;
}

.employee-detail-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.85rem;
}

.employee-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding: 0.85rem 1rem;
  background: #fff;
  border: 1px solid #edf0f2;
  border-radius: 0.375rem;
}

.employee-list {
  display: grid;
  gap: 0.75rem;
}

.employee-main {
  min-width: 0;
}

.employee-actions {
  display: flex;
  flex: 0 0 auto;
  align-items: center;
  gap: 0.65rem;
}

.modal-backdrop {
  z-index: 1050;
}

.modal-backdrop.show {
  opacity: 0.45;
}

.invite-modal,
.profile-modal {
  z-index: 1055;
}

.invite-modal .modal-header,
.invite-modal .modal-footer,
.profile-modal .modal-header,
.profile-modal .modal-footer {
  padding: 1rem 1.25rem;
}

.invite-modal .modal-body,
.profile-modal .modal-body {
  padding: 1.25rem;
  background: #fff;
}

.profile-modal .modal-body {
  padding: 1rem 1.25rem;
}

.invite-modal .invitation-item,
.invite-modal .employee-item {
  background: #f8f9fa;
}

.country-picker {
  position: relative;
}

.country-suggestions {
  left: 0.75rem;
  max-height: 240px;
  overflow-y: auto;
  position: absolute;
  right: 0.75rem;
  top: 74px;
  z-index: 1060;
}

.country-suggestions .list-group-item {
  align-items: center;
  display: flex;
  justify-content: space-between;
}

.directory-box {
  padding: 0.85rem;
  background: #f8f9fa;
  border: 1px solid #edf0f2;
  border-radius: 0.375rem;
}

.directory-edit-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 0.5rem;
}

.directory-edit-grid-status {
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr) auto;
  align-items: end;
}

@media (max-width: 575.98px) {
  .directory-edit-grid-status {
    grid-template-columns: minmax(0, 1fr) auto;
  }

  .directory-edit-grid-status > div {
    grid-column: 1 / -1;
  }
}

.directory-edit-grid input[type="number"] {
  grid-column: 1 / -1;
}

.directory-edit-grid .form-control-color {
  width: 42px;
  min-width: 42px;
  padding: 0.2rem;
}

.company-logo-preview {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 140px;
  height: 70px;
  padding: 0.4rem;
  border: 1px solid #edf0f2;
  border-radius: 0.375rem;
  background: #f8f9fa;
}

.company-logo-preview img {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
}

@media (max-width: 576px) {
  .profile-edit-layout {
    grid-template-columns: 1fr;
  }

  .employee-item {
    align-items: flex-start;
    flex-direction: column;
  }

  .employee-actions {
    justify-content: space-between;
    width: 100%;
  }

  .employee-detail-grid {
    grid-template-columns: 1fr;
  }
}

.modal-fade-enter-active,
.modal-fade-leave-active {
  transition: opacity 0.18s ease, transform 0.18s ease;
}

.modal-fade-enter-from,
.modal-fade-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}

.modal-fade-enter-to,
.modal-fade-leave-from {
  opacity: 1;
  transform: translateY(0);
}

@media (max-width: 768px) {
  .profile-header {
    align-items: flex-start;
    flex-direction: column;
  }

  .profile-actions {
    width: 100%;
  }

  .profile-actions .btn {
    width: 100%;
    margin-bottom: 0.5rem;
  }

  .profile-fields {
    grid-template-columns: 1fr;
  }

  .invite-modal .modal-dialog {
    margin: 0.75rem;
  }
}
</style>
