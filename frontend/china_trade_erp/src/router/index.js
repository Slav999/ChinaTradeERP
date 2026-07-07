// src/router/index.js
import {createRouter, createWebHistory} from 'vue-router'

// относительный путь от папки router → views
import RegisterPage from '../views/RegisterPage.vue'
import LoginPage from '../views/LoginPage.vue'
import ForgotPasswordPage from '../views/ForgotPasswordPage.vue'
import ResetPasswordPage from '../views/ResetPasswordPage.vue'
import VerifyEmailPage from '../views/VerifyEmailPage.vue'
import AcceptInvitePage from '../views/AcceptInvitePage.vue'
import ProfilePage from '../views/ProfilePage.vue'
import SupplierOrdersPage from '../views/SupplierOrdersPage.vue'
import CustomerOrdersPage from '../views/CustomerOrdersPage.vue'
import ProductsPage from '../views/ProductsPage.vue'
import CounterpartyPage from '../views/CounterpartyPage.vue'
import SupplierOrderDetail from '../views/SupplierOrderDetail.vue'
import CustomerOrderDetail from '../views/CustomerOrderDetail.vue'
import axios, { AUTH_SESSION_KEY, clearClientSession } from '../axios'

const routes = [
    {path: '/', redirect: '/login'},

    // — Auth (скрываем NavBar) —
    {path: '/register', component: RegisterPage, meta: {hideNav: true, public: true}},
    {path: '/login', component: LoginPage, meta: {hideNav: true, public: true}},
    {path: '/forgot-password', component: ForgotPasswordPage, meta: {hideNav: true, public: true}},
    {path: '/reset-password', component: ResetPasswordPage, meta: {hideNav: true, public: true}},
    {path: '/verify-email', component: VerifyEmailPage, meta: {hideNav: true, public: true}},
    {path: '/accept-invite', component: AcceptInvitePage, meta: {hideNav: true, public: true}},

    // — Основные страницы —
    {path: '/profile', component: ProfilePage},
    {path: '/supplier-orders', component: SupplierOrdersPage},
    {path: '/supplier-orders/new', component: SupplierOrderDetail},
    {path: '/supplier-orders/:id', component: SupplierOrderDetail, props: true},
    {path: '/customer-orders', component: CustomerOrdersPage},
    {path: '/customer-orders/new', component: CustomerOrderDetail},
    {path: '/customer-orders/:id', component: CustomerOrderDetail, props: true},
    {path: '/products', component: ProductsPage},
    {path: '/counterparty', component: CounterpartyPage},
]

const router = createRouter({
    history: createWebHistory(),
    routes
})

async function validateSession() {
    try {
        await axios.get('/api/auth/session/')
        localStorage.setItem(AUTH_SESSION_KEY, '1')
        return true
    } catch {
        clearClientSession()
        return false
    }
}

router.beforeEach(async (to) => {
    const hasSession = !!localStorage.getItem(AUTH_SESSION_KEY)

    if (!to.meta.public && !hasSession) {
        const sessionIsValid = await validateSession()
        if (!sessionIsValid) {
            return {path: '/login', query: {next: to.fullPath}}
        }
    }

    if (to.meta.public && hasSession && ['/login', '/register'].includes(to.path)) {
        const sessionIsValid = await validateSession()
        if (sessionIsValid) {
            return '/supplier-orders'
        }
    }

    return true
})

export default router
