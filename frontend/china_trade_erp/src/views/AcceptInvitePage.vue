<template>
  <div class="d-flex justify-content-center align-items-center min-vh-100 bg-light">
    <div class="card invite-card p-4 shadow-sm">
      <h2 class="text-center mb-2">Accept invitation</h2>
      <p v-if="invitation" class="text-center text-muted mb-4">
        {{ invitation.company_name }} invited {{ invitation.email }}
      </p>

      <div v-if="isLoading" class="text-center text-muted py-4">
        Loading invitation...
      </div>

      <div v-else-if="loadError" class="alert alert-danger">
        {{ loadError }}
      </div>

      <form v-else @submit.prevent="acceptInvitation">
        <div class="invite-summary mb-3">
          <div>
            <span class="text-muted">Role</span>
            <strong>{{ invitation.access_role_display || invitation.role }}</strong>
          </div>
          <div v-if="invitation.department_display">
            <span class="text-muted">Department</span>
            <strong>{{ invitation.department_display }}</strong>
          </div>
          <div v-if="invitation.position">
            <span class="text-muted">Position</span>
            <strong>{{ invitation.position }}</strong>
          </div>
        </div>

        <div v-if="invitation.account_exists && !hasToken" class="alert alert-info">
          This email already has an account. Sign in first, then open this invitation again.
          <router-link :to="{ path: '/login', query: { next: $route.fullPath } }">Go to login</router-link>
        </div>

        <div v-if="invitation.account_exists && hasToken" class="alert alert-success">
          You can accept this invitation with your existing account.
        </div>

        <div v-if="!invitation.account_exists" class="row gy-3">
          <div class="col-md-6">
            <label class="form-label">First name</label>
            <input v-model.trim="form.first_name" class="form-control" />
          </div>
          <div class="col-md-6">
            <label class="form-label">Last name</label>
            <input v-model.trim="form.last_name" class="form-control" />
          </div>
          <div class="col-12">
            <label class="form-label">Username</label>
            <input v-model.trim="form.username" class="form-control" />
          </div>
          <div class="col-12">
            <label class="form-label">Password</label>
            <input v-model="form.password" type="password" class="form-control" required />
            <div class="form-text">At least 8 characters, one uppercase letter and one number.</div>
          </div>
          <div class="col-12">
            <label class="form-label">Confirm password</label>
            <input v-model="form.password2" type="password" class="form-control" required />
          </div>
        </div>

        <button class="btn btn-primary w-100 mt-4" :disabled="isSaving || (invitation.account_exists && !hasToken)">
          {{ submitLabel }}
        </button>

        <div v-if="serverError" class="alert alert-danger mt-3 mb-0">
          {{ serverError }}
        </div>
      </form>
    </div>
  </div>
</template>

<script>
import axios, { AUTH_SESSION_KEY } from '../axios';

export default {
  name: 'AcceptInvitePage',
  data() {
    return {
      invitation: null,
      form: {
        username: '',
        first_name: '',
        last_name: '',
        password: '',
        password2: '',
      },
      isLoading: false,
      isSaving: false,
      loadError: '',
      serverError: '',
    };
  },
  computed: {
    token() {
      return this.$route.query.token || '';
    },
    hasToken() {
      return !!localStorage.getItem(AUTH_SESSION_KEY);
    },
    submitLabel() {
      if (this.isSaving) return this.invitation?.account_exists ? 'Accepting...' : 'Creating account...';
      return this.invitation?.account_exists ? 'Accept invitation' : 'Create account';
    },
  },
  created() {
    this.fetchInvitation();
  },
  methods: {
    async fetchInvitation() {
      if (!this.token) {
        this.loadError = 'Invitation token is missing.';
        return;
      }
      this.isLoading = true;
      try {
        const { data } = await axios.get(`/api/auth/invitations/${encodeURIComponent(this.token)}/`);
        this.invitation = data;
        this.form.first_name = data.first_name || '';
        this.form.last_name = data.last_name || '';
        this.form.username = data.email?.split('@')[0] || '';
      } catch (error) {
        this.loadError = error.response?.data?.detail || 'Invitation is invalid or expired.';
      } finally {
        this.isLoading = false;
      }
    },
    async acceptInvitation() {
      this.serverError = '';
      if (!this.invitation.account_exists && this.form.password !== this.form.password2) {
        this.serverError = 'Passwords do not match.';
        return;
      }
      this.isSaving = true;
      try {
        await axios.post('/api/auth/invitations/accept/', {
          token: this.token,
          ...(this.invitation.account_exists ? {} : this.form),
        });
        this.$router.push(this.invitation.account_exists ? '/profile' : '/login');
      } catch (error) {
        this.serverError = this.formatError(error.response?.data) || 'Unable to accept invitation.';
      } finally {
        this.isSaving = false;
      }
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
.invite-card {
  width: min(560px, calc(100% - 2rem));
  border: 1px solid #dee2e6;
  border-radius: 0.5rem;
}

.invite-summary {
  display: grid;
  gap: 0.5rem;
  padding: 1rem;
  background: #f8f9fa;
  border: 1px solid #edf0f2;
  border-radius: 0.5rem;
}

.invite-summary div {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
}
</style>
