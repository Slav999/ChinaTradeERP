<template>
  <div class="d-flex justify-content-center align-items-center min-vh-100 bg-light">
    <div class="card p-4 shadow-sm" style="width: 400px;">
      <h2 class="text-center mb-4">Register</h2>
      <form @submit.prevent="register">
        <div class="mb-3">
          <label for="company_name" class="form-label">Company Name</label>
          <input
            v-model="form.company_name"
            type="text"
            class="form-control"
            id="company_name"
            :class="{ 'is-invalid': errors.company_name }"
          >
          <div class="invalid-feedback" v-if="errors.company_name">
            Company name is required and must be unique.
          </div>
        </div>

        <div class="mb-3">
          <label for="username" class="form-label">Username</label>
          <input
            v-model="form.username"
            type="text"
            class="form-control"
            id="username"
            :class="{ 'is-invalid': errors.username }"
          >
          <div class="invalid-feedback" v-if="errors.username">
            Username is required.
          </div>
        </div>

        <div class="mb-3">
          <label for="email" class="form-label">Email</label>
          <input
            v-model="form.email"
            type="email"
            class="form-control"
            id="email"
            :class="{ 'is-invalid': errors.email }"
          >
          <div class="invalid-feedback" v-if="errors.email">
            Valid email is required.
          </div>
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
              :title="passwordTooltip"
            >
            <button type="button" class="btn btn-outline-secondary" @click="showPassword = !showPassword">
              <i :class="showPassword ? 'bi bi-eye-slash' : 'bi bi-eye'"></i>
            </button>
          </div>
          <div class="invalid-feedback" v-if="errors.password">
            {{ errors.password }}
          </div>
        </div>

        <div class="mb-3">
          <label for="password2" class="form-label">Confirm Password</label>
          <input
            v-model="form.password2"
            type="password"
            class="form-control"
            id="password2"
            :class="{ 'is-invalid': errors.password2 }"
          >
          <div class="invalid-feedback" v-if="errors.password2">
            Passwords do not match.
          </div>
        </div>

        <button type="submit" class="btn btn-primary w-100">Register</button>
      </form>

      <p v-if="serverError" class="text-danger text-center mt-3">{{ serverError }}</p>
    </div>
  </div>
</template>

<script>
import axios from 'axios'

export default {
  name: 'RegisterPage',
  data() {
    return {
      form: {
        company_name: '',
        username: '',
        email: '',
        password: '',
        password2: ''
      },
      errors: {},
      serverError: '',
      showPassword: false
    }
  },
  computed: {
    passwordTooltip() {
      return 'Password must be at least 8 characters,\ninclude uppercase letter and number.'
    }
  },
  methods: {
    async register() {
      this.errors = {}
      this.serverError = ''

      // Frontend validation
      if (!this.form.company_name) this.errors.company_name = true
      if (!this.form.username) this.errors.username = true
      if (!this.form.email || !this.form.email.includes('@')) this.errors.email = true

      const strongPassword = /^(?=.*[A-Z])(?=.*\d).{8,}$/
      if (!strongPassword.test(this.form.password)) {
        this.errors.password = 'Password is too weak.'
      }

      if (this.form.password !== this.form.password2) {
        this.errors.password2 = true
      }

      if (Object.keys(this.errors).length) return

      this.form.email = this.form.email.toLowerCase()

      // Backend call
      try {
        await axios.post(
            'http://localhost:8000/api/auth/register/',
            {
              company_name: this.form.company_name,
              username: this.form.username,
              email: this.form.email,
              password: this.form.password,
              password2: this.form.password2
            }
        )
        // после регистрации перенаправляем на верификацию
        this.$router.push(`/verify-email?email=${encodeURIComponent(this.form.email)}`)
      } catch (err) {
        // если компания уже существует или другая ошибка
        if (err.response?.data) {
          const data = err.response.data
          // общий message
          this.serverError = data.detail || data.error || JSON.stringify(data)
        } else {
          this.serverError = 'Registration failed.'
        }
      }
    }
  }
}
</script>
