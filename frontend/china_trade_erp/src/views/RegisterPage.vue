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

        <div class="mb-3 country-picker">
          <label for="business_country" class="form-label">Country of business</label>
          <input
            v-model="countrySearch"
            type="text"
            class="form-control"
            id="business_country"
            :class="{ 'is-invalid': errors.business_country }"
            placeholder="Start typing a country..."
            autocomplete="off"
            @focus="showCountrySuggestions = true"
            @input="onCountrySearchInput"
            @keydown.down.prevent="moveCountryHighlight(1)"
            @keydown.up.prevent="moveCountryHighlight(-1)"
            @keydown.enter.prevent="selectHighlightedCountry"
            @keydown.esc="showCountrySuggestions = false"
            @blur="hideCountrySuggestions"
          >
          <div
            v-if="showCountrySuggestions && filteredCountries.length"
            class="country-suggestions list-group shadow-sm"
          >
            <button
              v-for="(country, index) in filteredCountries"
              :key="country.code"
              type="button"
              class="list-group-item list-group-item-action"
              :class="{ active: index === highlightedCountryIndex }"
              @mousedown.prevent="selectCountry(country)"
            >
              <span>{{ country.name }}</span>
              <span class="text-muted small ms-2">{{ country.code }}</span>
            </button>
          </div>
          <div class="form-text">
            We use this to set the default currency, tax rate, and exchange rates.
          </div>
          <div class="invalid-feedback" v-if="errors.business_country">
            Country of business is required.
          </div>
        </div>

        <div class="mb-3">
          <label for="language_code" class="form-label">Company language</label>
          <select v-model="form.language_code" id="language_code" class="form-select">
            <option value="ru">Russian</option>
            <option value="en">English</option>
          </select>
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
import axios from '../axios'

export default {
  name: 'RegisterPage',
  data() {
    return {
      form: {
        company_name: '',
        username: '',
        email: '',
        business_country: '',
        language_code: 'ru',
        password: '',
        password2: ''
      },
      countries: [],
      countrySearch: '',
      showCountrySuggestions: false,
      highlightedCountryIndex: 0,
      errors: {},
      serverError: '',
      showPassword: false
    }
  },
  computed: {
    passwordTooltip() {
      return 'Password must be at least 8 characters,\ninclude uppercase letter and number.'
    },
    filteredCountries() {
      const query = this.countrySearch.trim().toLowerCase()
      return query
        ? this.countries.filter(country =>
            country.name.toLowerCase().includes(query) ||
            country.code.toLowerCase().includes(query)
          )
        : this.countries
    }
  },
  created() {
    this.fetchCountries()
  },
  watch: {
    'form.language_code'() {
      this.fetchCountries()
    },
  },
  methods: {
    async fetchCountries() {
      try {
        const selectedCode = this.form.business_country
        const { data } = await axios.get('/api/auth/business-countries/', {
          params: { language: this.form.language_code },
        })
        this.countries = data
        if (selectedCode) this.countrySearch = data.find(country => country.code === selectedCode)?.name || this.countrySearch
      } catch {
        this.countries = []
      }
    },
    onCountrySearchInput() {
      this.form.business_country = ''
      this.highlightedCountryIndex = 0
      this.showCountrySuggestions = true
    },
    selectCountry(country) {
      this.form.business_country = country.code
      this.countrySearch = country.name
      this.showCountrySuggestions = false
      this.errors.business_country = false
    },
    moveCountryHighlight(direction) {
      if (!this.filteredCountries.length) return
      const max = this.filteredCountries.length - 1
      this.highlightedCountryIndex += direction
      if (this.highlightedCountryIndex < 0) this.highlightedCountryIndex = max
      if (this.highlightedCountryIndex > max) this.highlightedCountryIndex = 0
    },
    selectHighlightedCountry() {
      const country = this.filteredCountries[this.highlightedCountryIndex]
      if (country) this.selectCountry(country)
    },
    hideCountrySuggestions() {
      setTimeout(() => {
        this.showCountrySuggestions = false
      }, 120)
    },
    async register() {
      this.errors = {}
      this.serverError = ''

      // Frontend validation
      if (!this.form.company_name) this.errors.company_name = true
      if (!this.form.business_country) this.errors.business_country = true
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
            '/api/auth/register/',
            {
              company_name: this.form.company_name,
              business_country: this.form.business_country,
              language_code: this.form.language_code,
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

<style scoped>
.country-picker {
  position: relative;
}

.country-suggestions {
  left: 0;
  max-height: 240px;
  overflow-y: auto;
  position: absolute;
  right: 0;
  top: 74px;
  z-index: 1050;
}

.country-suggestions .list-group-item {
  align-items: center;
  display: flex;
  justify-content: space-between;
}
</style>
