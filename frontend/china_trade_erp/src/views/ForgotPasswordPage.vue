<template>
  <div class="d-flex justify-content-center align-items-center min-vh-100 bg-light">
    <div class="card p-4 shadow-sm" style="width: 400px;">
      <h2 class="text-center mb-4">Forgot Password</h2>
      <form @submit.prevent="submitEmail">
        <div class="mb-3">
          <label for="email" class="form-label">Email</label>
          <input
            v-model="email"
            type="email"
            class="form-control"
            id="email"
            required
          >
        </div>
        <button type="submit" class="btn btn-primary w-100">Send Reset Code</button>
      </form>
      <p v-if="message" class="text-success text-center mt-3">{{ message }}</p>
      <p v-if="error" class="text-danger text-center mt-3">{{ error }}</p>
    </div>
  </div>
</template>

<script>
import axios from 'axios'

export default {
  name: 'ForgotPasswordPage',
  data() {
    return {
      email: '',
      message: '',
      error: ''
    }
  },
  methods: {
    async submitEmail() {
      this.message = ''
      this.error = ''
      try {
        await axios.post('http://localhost:8000/api/auth/forgot-password/', {
          email: this.email.toLowerCase()
        })
        this.message = 'Reset code sent to your email.'
        // redirect to /reset-password and pass email as query param
        this.$router.push({path: '/reset-password', query: {email: this.email}})
      } catch (err) {
        this.error = err.response?.data?.detail || 'Something went wrong.'
      }
    }
  }
}
</script>