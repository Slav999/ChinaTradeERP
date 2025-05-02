<template>
  <div class="d-flex justify-content-center align-items-center min-vh-100 bg-light">
    <div class="card p-4 shadow-sm" style="width: 400px;">
      <h2 class="text-center mb-4">Verify Your Email</h2>
      <p class="text-center">Enter the 6-digit code sent to your email</p>
      <form @submit.prevent="verifyCode">
        <div class="mb-3">
          <label for="code" class="form-label">Verification Code</label>
          <input v-model="code" type="text" class="form-control" id="code" required maxlength="6">
        </div>
        <button type="submit" class="btn btn-primary w-100">Verify</button>
      </form>
      <p v-if="error" class="text-danger text-center mt-3">{{ error }}</p>
      <p v-if="success" class="text-success text-center mt-3">{{ success }}</p>
    </div>
  </div>
</template>

<script>
import axios from 'axios'

export default {
  name: 'VerifyEmailPage',
  data() {
    return {
      code: '',
      error: '',
      success: ''
    }
  },
  methods: {
    async verifyCode() {
      this.error = ''
      this.success = ''
      const email = this.$route.query.email

      if (!email) {
        this.error = 'Email not provided.'
        return
      }

      try {
        const response = await axios.post('http://localhost:8000/api/auth/verify-email/', {
          email,
          code: this.code
        })
        this.success = 'Email successfully verified! Redirecting...'
        setTimeout(() => {
          this.$router.push('/login')
        }, 2000)
      } catch (err) {
        this.error = err.response?.data?.error || 'Verification failed.'
      }
    }
  }
}
</script>

<style scoped>
.card {
  border-radius: 12px;
}
</style>
