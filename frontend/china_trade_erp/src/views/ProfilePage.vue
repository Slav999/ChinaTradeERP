<template>
  <div class="container profile-page py-4">
    <div class="profile-card">
      <div class="profile-header">
        <div class="avatar-wrap">
          <div class="profile-avatar-frame">
            <div
                v-if="isEditing && avatarPreview"
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
          <label v-if="isEditing" class="btn btn-sm btn-outline-primary avatar-action">
            Change photo
            <input type="file" accept="image/*" hidden @change="handleAvatarChange" />
          </label>
          <div v-if="isEditing && avatarPreview" class="avatar-hint">
            Drag photo, use mouse wheel to zoom
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
          <template v-if="!isEditing">
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
          </template>
          <template v-else>
            <button class="btn btn-outline-secondary me-2" :disabled="isSaving" @click="cancelEditing">
              Cancel
            </button>
            <button class="btn btn-primary px-4" :disabled="isSaving" @click="saveProfile">
              {{ isSaving ? 'Saving...' : 'Save' }}
            </button>
          </template>
        </div>
      </div>

      <div class="profile-section">
        <div class="section-title">
          <h2>Contact information</h2>
        </div>

        <div v-if="!isEditing" class="profile-fields">
          <div v-for="field in contactFields" :key="field.key" class="profile-field">
            <div class="field-label">{{ field.label }}</div>
            <div :class="['field-value', { empty: !field.value }]">
              {{ field.value || 'not filled' }}
            </div>
          </div>
        </div>

        <form v-else class="row gy-3 profile-form" @submit.prevent="saveProfile">
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
            <label class="form-label">Notification language</label>
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
        </form>
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
              <div class="text-muted small">Add an employee to {{ profile.company_name || 'your company' }}</div>
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
                <div class="col-md-6">
                  <label class="form-label">Employee email</label>
                  <input v-model.trim="invitationForm.email" type="email" class="form-control" required />
                  <div class="form-text">An existing account can be invited to another company.</div>
                </div>
                <div class="col-md-3">
                  <label class="form-label">First name</label>
                  <input v-model.trim="invitationForm.first_name" class="form-control" />
                </div>
                <div class="col-md-3">
                  <label class="form-label">Last name</label>
                  <input v-model.trim="invitationForm.last_name" class="form-control" />
                </div>
                <div class="col-md-4">
                  <label class="form-label">System role</label>
                  <select v-model="invitationForm.role" class="form-select">
                    <option value="viewer">Viewer</option>
                    <option value="manager">Manager</option>
                    <option value="admin">Admin</option>
                  </select>
                </div>
                <div class="col-md-4">
                  <label class="form-label">Access role</label>
                  <select v-model="invitationForm.access_role" class="form-select">
                    <option value="">Select role...</option>
                    <option v-for="role in accessRoles" :key="role.id" :value="role.id">
                      {{ role.name }}
                    </option>
                  </select>
                </div>
                <div class="col-md-4">
                  <label class="form-label">Department</label>
                  <input
                      v-model.trim="invitationForm.department_name"
                      class="form-control"
                      list="department-options"
                      placeholder="Type or select"
                  />
                  <datalist id="department-options">
                    <option v-for="department in departments" :key="department.id" :value="department.name" />
                  </datalist>
                </div>
                <div class="col-12">
                  <label class="form-label">Position</label>
                  <input v-model.trim="invitationForm.position" class="form-control" />
                </div>
              </div>
              </div>

              <div v-if="inviteModalTab === 'invite' && invitationSuccess" class="alert alert-success mt-3 mb-0">
                {{ invitationSuccess }}
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
                      {{ invitation.access_role_display || invitation.role }}
                      <span v-if="invitation.department_display"> / {{ invitation.department_display }}</span>
                      <span v-if="invitation.position"> / {{ invitation.position }}</span>
                    </div>
                  </div>
                  <span :class="['badge', invitation.status === 'pending' ? 'text-bg-warning' : 'text-bg-light']">
                    {{ invitation.status }}
                  </span>
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
                      Active
                    </button>
                    <button
                        type="button"
                        :class="['btn', employeeStatusFilter === 'disabled' ? 'btn-primary' : 'btn-outline-primary']"
                        @click="setEmployeeStatusFilter('disabled')"
                    >
                      Dismissed
                    </button>
                  </div>
                </div>

                <div v-if="isLoadingEmployees" class="text-muted small">Loading employees...</div>
                <div v-else-if="!employees.length" class="text-muted small">No employees in this list.</div>
                <div
                    v-for="employee in employees"
                    :key="employee.id"
                    :class="['employee-item', { selected: selectedEmployee?.id === employee.id }]"
                    @click="selectEmployee(employee)"
                >
                  <div class="employee-main">
                    <div class="fw-semibold">{{ employeeName(employee) }}</div>
                    <div class="text-muted small">{{ employee.email }}</div>
                    <div class="text-muted small">
                      {{ employee.access_role_name || employee.role_display || employee.role }}
                      <span v-if="employee.department_name"> / {{ employee.department_name }}</span>
                      <span v-if="employee.position"> / {{ employee.position }}</span>
                    </div>
                    <div v-if="employee.status === 'disabled'" class="text-muted small">
                      Dismissed {{ formatDate(employee.disabled_at) }}
                      <span v-if="employee.disabled_by_email"> by {{ employee.disabled_by_email }}</span>
                    </div>
                  </div>
                  <div class="employee-actions">
                    <span :class="['badge', employee.status === 'active' ? 'text-bg-success' : 'text-bg-secondary']">
                      {{ employee.status }}
                    </span>
                    <button
                        v-if="employee.can_dismiss"
                        type="button"
                        class="btn btn-sm btn-outline-danger"
                        :disabled="isDismissingEmployee === employee.id"
                        @click.stop="dismissEmployee(employee)"
                    >
                      {{ isDismissingEmployee === employee.id ? 'Dismissing...' : 'Dismiss' }}
                    </button>
                  </div>
                </div>

                <div v-if="selectedEmployee" class="employee-detail-panel">
                  <div class="d-flex align-items-start justify-content-between gap-3 mb-3">
                    <div>
                      <h6 class="mb-1">{{ employeeName(selectedEmployee) }}</h6>
                      <div class="text-muted small">{{ selectedEmployee.email }}</div>
                    </div>
                    <button type="button" class="btn-close" aria-label="Close" @click="selectedEmployee = null"></button>
                  </div>
                  <div class="employee-detail-grid">
                    <div>
                      <div class="field-label">Phone</div>
                      <div class="field-value">{{ selectedEmployee.phone || 'not filled' }}</div>
                    </div>
                    <div>
                      <div class="field-label">Work email</div>
                      <div class="field-value">{{ selectedEmployee.work_email || 'not filled' }}</div>
                    </div>
                    <div>
                      <div class="field-label">Personal email</div>
                      <div class="field-value">{{ selectedEmployee.personal_email || 'not filled' }}</div>
                    </div>
                    <div>
                      <div class="field-label">Role</div>
                      <div class="field-value">{{ selectedEmployee.access_role_name || selectedEmployee.role_display || selectedEmployee.role }}</div>
                    </div>
                    <div>
                      <div class="field-label">Department</div>
                      <div class="field-value">{{ selectedEmployee.department_name || 'not filled' }}</div>
                    </div>
                    <div>
                      <div class="field-label">Position</div>
                      <div class="field-value">{{ selectedEmployee.position || 'not filled' }}</div>
                    </div>
                    <div v-if="selectedEmployee.status === 'disabled'">
                      <div class="field-label">Dismissed at</div>
                      <div class="field-value">{{ formatDate(selectedEmployee.disabled_at) || 'not filled' }}</div>
                    </div>
                    <div v-if="selectedEmployee.status === 'disabled'">
                      <div class="field-label">Reason</div>
                      <div class="field-value">{{ selectedEmployee.disable_reason || 'not filled' }}</div>
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
                  :disabled="isSendingInvitation"
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
                <div class="text-muted small">Pricing settings for {{ profile.company_name || 'your company' }}</div>
              </div>
              <button type="button" class="btn-close" aria-label="Close" @click="closeSettingsModal"></button>
            </div>
            <form @submit.prevent="saveCompanySettings">
              <div class="modal-body">
                <div v-if="isLoadingSettings" class="text-muted">Loading settings...</div>
                <div v-else class="row gy-3">
                  <div class="col-md-4">
                    <label class="form-label">CNY to local rate</label>
                    <input v-model="settingsForm.cny_to_local_rate" type="number" step="0.000001" min="0" class="form-control" required />
                  </div>
                  <div class="col-md-4">
                    <label class="form-label">USD to local rate</label>
                    <input v-model="settingsForm.usd_to_local_rate" type="number" step="0.000001" min="0" class="form-control" required />
                  </div>
                  <div class="col-md-4">
                    <label class="form-label">Logistics USD/kg</label>
                    <input v-model="settingsForm.logistics_cost_per_kg_usd" type="number" step="0.01" min="0" class="form-control" required />
                  </div>
                  <div class="col-md-4">
                    <label class="form-label">Retail tax</label>
                    <input v-model="settingsForm.retail_tax_pct" type="number" step="0.0001" min="0" class="form-control" required />
                    <div class="form-text">Example: 0.08 = 8%</div>
                  </div>
                  <div class="col-md-4">
                    <label class="form-label">Acquiring fee</label>
                    <input v-model="settingsForm.acquiring_pct" type="number" step="0.0001" min="0" class="form-control" required />
                  </div>
                  <div class="col-md-4">
                    <label class="form-label">Packaging fee</label>
                    <input v-model="settingsForm.packaging_pct" type="number" step="0.0001" min="0" class="form-control" required />
                  </div>
                  <div class="col-md-6">
                    <label class="form-label">Margin</label>
                    <input v-model="settingsForm.margin_pct" type="number" step="0.0001" min="0" class="form-control" required />
                  </div>
                  <div class="col-md-6">
                    <label class="form-label">Discount</label>
                    <input v-model="settingsForm.discount_pct" type="number" step="0.0001" min="0" class="form-control" required />
                  </div>
                </div>

                <div v-if="settingsSuccess" class="alert alert-success mt-3 mb-0">
                  {{ settingsSuccess }}
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
        :class="{ show: showInviteModal || showSettingsModal }"
        v-if="showInviteModal || showSettingsModal"
    ></div>
  </div>
</template>

<script>
import axios, { clearClientSession } from '../axios';

const API_ORIGIN = 'http://localhost:8000';

export default {
  name: 'ProfilePage',
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
        role: 'viewer',
        access_role: '',
        department_name: '',
        position: '',
      },
      invitations: [],
      employees: [],
      accessRoles: [],
      departments: [],
      settingsForm: {
        cny_to_local_rate: '',
        usd_to_local_rate: '',
        logistics_cost_per_kg_usd: '',
        retail_tax_pct: '',
        acquiring_pct: '',
        packaging_pct: '',
        margin_pct: '',
        discount_pct: '',
      },
      invitationSuccess: '',
      invitationError: '',
      inviteModalTab: 'invite',
      employeeStatusFilter: 'active',
      selectedEmployee: null,
      settingsSuccess: '',
      settingsError: '',
      showInviteModal: false,
      showSettingsModal: false,
      isEditing: false,
      isLoading: false,
      isSaving: false,
      isLoggingOut: false,
      isSendingInvitation: false,
      isLoadingEmployees: false,
      isDismissingEmployee: null,
      isLoadingSettings: false,
      isSavingSettings: false,
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
      return this.profile.role_display || this.profile.role || 'User';
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
        { key: 'first_name', label: 'First name', value: this.profile.first_name },
        { key: 'last_name', label: 'Last name', value: this.profile.last_name },
        { key: 'middle_name', label: 'Middle name', value: this.profile.middle_name },
        { key: 'email', label: 'Account email', value: this.profile.email },
        { key: 'work_email', label: 'Work email', value: this.profile.work_email },
        { key: 'personal_email', label: 'Personal email', value: this.profile.personal_email },
        { key: 'phone', label: 'Mobile phone', value: this.profile.phone },
        { key: 'department', label: 'Department', value: this.profile.department },
        { key: 'position', label: 'Position', value: this.profile.position },
        { key: 'birth_date', label: 'Birth date', value: this.formatDate(this.profile.birth_date) },
        { key: 'hire_date', label: 'Hire date', value: this.formatDate(this.profile.hire_date) },
        { key: 'notification_language', label: 'Notification language', value: this.languageLabel(this.profile.notification_language) },
        { key: 'role', label: 'System role', value: this.roleLabel },
      ];
    },
    companyMemberships() {
      return this.profile.memberships || [];
    },
  },
  created() {
    this.fetchProfile();
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
      if (!this.invitationForm.access_role && this.accessRoles.length) {
        const viewerRole = this.accessRoles.find(role => role.name === 'Viewer');
        this.invitationForm.access_role = (viewerRole || this.accessRoles[0]).id;
      }
    },
    async openInviteModal() {
      this.showInviteModal = true;
      this.inviteModalTab = 'invite';
      this.invitationSuccess = '';
      this.invitationError = '';
      if (!this.accessRoles.length || !this.invitations.length) {
        await this.fetchCompanyAccess();
      }
    },
    closeInviteModal() {
      if (this.isSendingInvitation) return;
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
        }
      } catch (error) {
        alert(this.formatError(error.response?.data) || 'Unable to load employees.');
      } finally {
        this.isLoadingEmployees = false;
      }
    },
    selectEmployee(employee) {
      this.selectedEmployee = employee;
    },
    async dismissEmployee(employee) {
      const reason = prompt(`Dismiss ${this.employeeName(employee)} from ${this.profile.company_name || 'this company'}?\n\nReason:`);
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
        alert(this.formatError(error.response?.data) || 'Unable to dismiss employee.');
      } finally {
        this.isDismissingEmployee = null;
      }
    },
    async openSettingsModal() {
      this.showSettingsModal = true;
      this.settingsSuccess = '';
      this.settingsError = '';
      await this.fetchCompanySettings();
    },
    closeSettingsModal() {
      if (this.isSavingSettings) return;
      this.showSettingsModal = false;
    },
    async fetchCompanySettings() {
      this.isLoadingSettings = true;
      this.settingsError = '';
      try {
        const { data } = await axios.get('/api/settings/');
        this.settingsForm = {
          ...this.settingsForm,
          ...(data[0] || {}),
        };
      } catch (error) {
        this.settingsError = this.formatError(error.response?.data) || 'Unable to load company settings.';
      } finally {
        this.isLoadingSettings = false;
      }
    },
    async saveCompanySettings() {
      this.isSavingSettings = true;
      this.settingsSuccess = '';
      this.settingsError = '';
      try {
        const payload = {
          cny_to_local_rate: this.settingsForm.cny_to_local_rate,
          usd_to_local_rate: this.settingsForm.usd_to_local_rate,
          logistics_cost_per_kg_usd: this.settingsForm.logistics_cost_per_kg_usd,
          retail_tax_pct: this.settingsForm.retail_tax_pct,
          acquiring_pct: this.settingsForm.acquiring_pct,
          packaging_pct: this.settingsForm.packaging_pct,
          margin_pct: this.settingsForm.margin_pct,
          discount_pct: this.settingsForm.discount_pct,
        };
        const { data } = await axios.post('/api/settings/', payload);
        this.settingsForm = { ...this.settingsForm, ...data };
        this.settingsSuccess = 'Company settings have been saved.';
      } catch (error) {
        this.settingsError = this.formatError(error.response?.data) || 'Unable to save company settings.';
      } finally {
        this.isSavingSettings = false;
      }
    },
    async sendInvitation() {
      this.isSendingInvitation = true;
      this.invitationSuccess = '';
      this.invitationError = '';
      try {
        const payload = {
          ...this.invitationForm,
          access_role: this.invitationForm.access_role || null,
        };
        const { data } = await axios.post('/api/auth/invitations/', payload);
        this.invitations = [data, ...this.invitations];
        this.invitationSuccess = 'Invitation has been sent.';
        this.invitationForm = {
          email: '',
          first_name: '',
          last_name: '',
          role: 'viewer',
          access_role: this.invitationForm.access_role,
          department_name: '',
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
      const navProfile = {
        username: profile.username,
        first_name: profile.first_name,
        last_name: profile.last_name,
        avatar: profile.avatar,
      };
      localStorage.setItem('current_user_profile', JSON.stringify(navProfile));
      window.dispatchEvent(new CustomEvent('profile-updated', { detail: navProfile }));
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
  padding: 1.5rem;
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
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.85rem;
}

.profile-field {
  min-width: 0;
  padding: 0.85rem 1rem;
  background: #f8f9fa;
  border: 1px solid #edf0f2;
  border-radius: 0.375rem;
}

.field-label {
  color: #adb5bd;
  font-size: 0.9rem;
}

.field-value {
  margin-top: 0.2rem;
  overflow-wrap: anywhere;
  color: #495057;
  font-size: 1rem;
  font-weight: 500;
}

.field-value.empty {
  font-weight: 400;
  color: #adb5bd;
}

.profile-form {
  padding: 1rem;
  background: #f8f9fa;
  border: 1px solid #edf0f2;
  border-radius: 0.5rem;
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

.invite-modal .invitation-item,
.invite-modal .employee-item {
  background: #f8f9fa;
}

@media (max-width: 576px) {
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
