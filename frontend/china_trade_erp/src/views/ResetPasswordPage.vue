<template>
  <div class="d-flex justify-content-center align-items-center min-vh-100 bg-light">
    <div class="card p-4 shadow-sm" style="width: 400px;">
      <h2 class="text-center mb-4">Reset Password</h2>
      <form @submit.prevent="resetPassword">
        <div class="mb-3">
          <label for="code" class="form-label">Reset Code</label>
          <input
              v-model="form.code"
              type="text"
              class="form-control"
              id="code"
              required
          >
        </div>
        <div class="mb-3">
          <label for="new_password" class="form-label">New Password</label>
          <div class="input-group">
            <input
                v-model="form.new_password"
                :type="showPassword ? 'text' : 'password'"
                class="form-control"
                id="new_password"
                required
                :title="passwordTooltip"
            >
            <span class="input-group-text" @click="togglePassword" style="cursor: pointer;">
      <i :class="showPassword ? 'bi bi-eye-slash' : 'bi bi-eye'"></i>
    </span>
          </div>
        </div>
        <button type="submit" class="btn btn-primary w-100">Reset</button>
      </form>
      <p v-if="message" class="text-success text-center mt-3">{{ message }}</p>
      <p v-if="error" class="text-danger text-center mt-3">{{ error }}</p>
    </div>
  </div>
</template>

<script>
import axios from 'axios'

export default {
  name: 'ResetPasswordPage',
  data() {
    return {
      form: {
        email: '',
        code: '',
        new_password: ''
      },
      message: '',
      error: '',
      showPassword: false
    }
  },
  computed: {
    passwordTooltip() {
      return 'Password must be at least 8 characters,\ncontain an uppercase letter and a digit.'
    }
  },
  methods: {
    togglePassword() {
      this.showPassword = !this.showPassword
    },
    async resetPassword() {
      this.message = ''
      this.error = ''

      const strongPassword = /^(?=.*[A-Z])(?=.*\d).{8,}$/
      if (!strongPassword.test(this.form.new_password)) {
        this.error = 'Password is too weak.'
        return
      }

      this.form.email = this.form.email.toLowerCase()


      try {
        await axios.post('http://localhost:8000/api/auth/reset-password/', this.form)
        this.message = 'Password updated successfully.'
        setTimeout(() => {
          this.$router.push('/login')
        }, 2000)
      } catch (err) {
        this.error = err.response?.data?.detail || 'Failed to reset password.'
      }
    }
  },
  mounted() {
    const emailFromQuery = this.$route.query.email
    if (emailFromQuery) {
      this.form.email = emailFromQuery
    }
  }
}
</script>

<style scoped>
.cursor-pointer {
  cursor: pointer;
}
</style>