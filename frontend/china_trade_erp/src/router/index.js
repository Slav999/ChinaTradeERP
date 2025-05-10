import { createRouter, createWebHistory } from 'vue-router'
import RegisterPage from '../views/RegisterPage.vue'
import LoginPage from '../views/LoginPage.vue'
import ProfilePage from '../views/ProfilePage.vue'
import ForgotPasswordPage from '../views/ForgotPasswordPage.vue'
import ResetPasswordPage from '../views/ResetPasswordPage.vue'
import VerifyEmailPage from '../views/VerifyEmailPage.vue'
import CounterpartyPage from '../views/CounterpartyPage.vue'

const routes = [
  { path: '/', redirect: '/login' },
  { path: '/register', component: RegisterPage },
  { path: '/login', component: LoginPage },
  { path: '/me', component: ProfilePage },
  { path: '/forgot-password', component: ForgotPasswordPage },
  { path: '/reset-password', component: ResetPasswordPage },
  { path: '/verify-email', component: VerifyEmailPage },
  { path: '/counterparty', component: CounterpartyPage },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
