<template>
  <div class="d-flex justify-content-center align-items-center min-vh-100 bg-light">
    <div class="card p-4 shadow-sm" style="width: 400px;">
      <h2 class="text-center mb-4">Login</h2>
      <form @submit.prevent="login">
        <div class="mb-3">
          <label for="email" class="form-label">Email</label>
          <input v-model="form.email" type="email" class="form-control" id="email"
                 :class="{ 'is-invalid': errors.email }">
          <div class="invalid-feedback" v-if="errors.email">Valid email is required.</div>
        </div>

        <div class="mb-3 position-relative">
          <label for="password" class="form-label">Password</label>
          <div class="input-group">
            <input
                :type="showPassword ? 'text' : 'password'"
                v-model="form.password"
                class="form-control"
                id="password"
                :class="{ 'is-invalid': errors.password }"
            >
            <button type="button" class="btn btn-outline-secondary" @click="showPassword = !showPassword">
              <i :class="showPassword ? 'bi bi-eye-slash' : 'bi bi-eye'"></i>
            </button>
          </div>
          <div class="invalid-feedback" v-if="errors.password">Password is required.</div>
        </div>

        <button type="submit" class="btn btn-primary w-100">Login</button>
        <p class="text-center mt-3">
          <router-link to="/forgot-password">Forgot password?</router-link>
        </p>
        <p class="text-center mt-3">
          <router-link to="/register">Register</router-link>
        </p>
      </form>

      <p v-if="serverError" class="text-danger text-center mt-3">{{ serverError }}</p>
    </div>
  </div>
</template>

<script>
import axios from 'axios'

export default {
  name: 'LoginPage',
  data() {
    return {
      form: {
        email: '',
        password: ''
      },
      errors: {},
      serverError: '',
      showPassword: false
    }
  },
  methods: {
    async login() {
      this.errors = {}
      this.serverError = ''

      if (!this.form.email || !this.form.email.includes('@')) this.errors.email = true
      if (!this.form.password) this.errors.password = true

      if (Object.keys(this.errors).length) return

      this.form.email = this.form.email.toLowerCase()

      try {
        const response = await axios.post('http://localhost:8000/api/auth/login/', this.form)
        const access = response.data.access;
        const refresh = response.data.refresh;
        localStorage.setItem('access_token', access);
        localStorage.setItem('refresh_token', refresh);

        this.$router.push('/me')
      } catch (err) {
        this.serverError = err.response?.data?.detail || 'Login failed.'
      }
    }
  }
}
</script>

<style scoped>
input[title]:hover::after {
  content: attr(title);
  position: absolute;
  top: 100%;
  left: 0;
  background: #000;
  color: white;
  padding: 4px 8px;
  font-size: 0.75rem;
  border-radius: 4px;
  white-space: pre-line;
  z-index: 10;
}
</style>