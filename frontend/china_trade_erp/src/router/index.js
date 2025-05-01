import { createRouter, createWebHistory } from 'vue-router'
import RegisterPage from '../views/RegisterPage.vue'
import LoginPage from '../views/LoginPage.vue'
import ProfilePage from '../views/ProfilePage.vue'

const routes = [
  { path: '/register', component: RegisterPage },
  { path: '/login', component: LoginPage },
  { path: '/me', component: ProfilePage },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
