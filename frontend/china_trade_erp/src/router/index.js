// src/router/index.js
import { createRouter, createWebHistory } from 'vue-router'

// относительный путь от папки router → views
import RegisterPage       from '../views/RegisterPage.vue'
import LoginPage          from '../views/LoginPage.vue'
import ForgotPasswordPage from '../views/ForgotPasswordPage.vue'
import ResetPasswordPage  from '../views/ResetPasswordPage.vue'
import VerifyEmailPage    from '../views/VerifyEmailPage.vue'
import ProfilePage        from '../views/ProfilePage.vue'
import SupplierOrdersPage from '../views/SupplierOrdersPage.vue'
import CustomerOrdersPage from '../views/CustomerOrdersPage.vue'
import ProductsPage       from '../views/ProductsPage.vue'
import CounterpartyPage   from '../views/CounterpartyPage.vue'

const routes = [
  { path: '/', redirect: '/login' },

  // — Auth (скрываем NavBar) —
  { path: '/register',      component: RegisterPage,      meta: { hideNav: true } },
  { path: '/login',         component: LoginPage,         meta: { hideNav: true } },
  { path: '/forgot-password', component: ForgotPasswordPage, meta: { hideNav: true } },
  { path: '/reset-password',  component: ResetPasswordPage,  meta: { hideNav: true } },
  { path: '/verify-email',    component: VerifyEmailPage,    meta: { hideNav: true } },

  // — Основные страницы —
  { path: '/me',               component: ProfilePage          },
  { path: '/supplier-orders',  component: SupplierOrdersPage   },
  { path: '/customer-orders',  component: CustomerOrdersPage   },
  { path: '/products',         component: ProductsPage         },
  { path: '/counterparty',     component: CounterpartyPage     },
]

export default createRouter({
  history: createWebHistory(),
  routes
})
