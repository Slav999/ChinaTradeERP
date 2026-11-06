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
import WarehousePage from '../views/WarehousePage.vue'
import CounterpartyPage from '../views/CounterpartyPage.vue'
import SupplierOrderDetail from '../views/SupplierOrderDetail.vue'
import CustomerOrderDetail from '../views/CustomerOrderDetail.vue'
import axios, { AUTH_SESSION_KEY, clearClientSession } from '../axios'
import { firstAllowedRoute, hasPermission, loadCurrentUser, PERMISSIONS } from '../access'

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
    {path: '/supplier-orders', component: SupplierOrdersPage, meta: {permission: PERMISSIONS.SUPPLIER_ORDERS_VIEW}},
    {path: '/supplier-orders/new', component: SupplierOrderDetail, meta: {permission: PERMISSIONS.SUPPLIER_ORDERS_MANAGE}},
    {path: '/supplier-orders/:id', component: SupplierOrderDetail, props: true, meta: {permission: PERMISSIONS.SUPPLIER_ORDERS_VIEW}},
    {path: '/samples-trips', component: SupplierOrdersPage, meta: {samples: true, permission: PERMISSIONS.SUPPLIER_ORDERS_VIEW}},
    {path: '/samples-trips/new', component: SupplierOrderDetail, meta: {samples: true, permission: PERMISSIONS.SUPPLIER_ORDERS_MANAGE}},
    {path: '/samples-trips/:id', component: SupplierOrderDetail, props: true, meta: {samples: true, permission: PERMISSIONS.SUPPLIER_ORDERS_VIEW}},
    {path: '/customer-orders', component: CustomerOrdersPage, meta: {permission: PERMISSIONS.CUSTOMER_ORDERS_VIEW}},
    {path: '/customer-orders/new', component: CustomerOrderDetail, meta: {permission: PERMISSIONS.CUSTOMER_ORDERS_MANAGE}},
    {path: '/customer-orders/:id', component: CustomerOrderDetail, props: true, meta: {permission: PERMISSIONS.CUSTOMER_ORDERS_VIEW}},
    {path: '/products', component: ProductsPage, meta: {permission: PERMISSIONS.PRODUCTS_VIEW}},
    {path: '/warehouse', component: WarehousePage, meta: {permission: PERMISSIONS.WAREHOUSE_VIEW}},
    {path: '/counterparty', component: CounterpartyPage, meta: {permission: PERMISSIONS.COUNTERPARTIES_VIEW}},
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
            const user = await loadCurrentUser({force: true})
            return firstAllowedRoute(user)
        }
    }

    if (!to.meta.public) {
        try {
            const user = await loadCurrentUser()
            if (to.meta.permission && !hasPermission(to.meta.permission, user)) {
                const fallback = firstAllowedRoute(user)
                return fallback === to.path ? '/profile' : fallback
            }
        } catch {
            clearClientSession()
            return {path: '/login', query: {next: to.fullPath}}
        }
    }

    return true
})

export default router
