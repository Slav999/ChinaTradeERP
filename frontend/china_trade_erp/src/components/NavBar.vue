<template>
  <nav class="navbar navbar-expand-lg navbar-light bg-white border-bottom sticky-top shadow-sm">
    <div class="container d-flex align-items-center justify-content-between">
      <!-- Logo -->
      <RouterLink to="/" class="navbar-brand">
        <img :src="logo" alt="Logo" class="logo-img" />
      </RouterLink>

      <!-- Бургер справа (виден только на <lg) -->
      <button
        class="navbar-toggler collapsed d-lg-none"
        type="button"
        data-bs-toggle="collapse"
        data-bs-target="#navbarNav"
        aria-controls="navbarNav"
        aria-expanded="false"
        aria-label="Toggle navigation"
      >
        <span class="navbar-toggler-icon"></span>
      </button>

      <!-- Меню с иконками -->
      <div class="collapse navbar-collapse w-100 justify-content-end" id="navbarNav">
        <ul class="navbar-nav d-flex w-100 flex-row justify-content-around justify-content-lg-end">
          <li v-if="canViewSupplierOrders" class="nav-item mx-lg-3">
            <RouterLink
                to="/supplier-orders"
                class="nav-link text-center"
                :class="{ 'section-active': isSectionActive('/supplier-orders') }"
            >
              <i class="bi bi-truck fs-4"></i>
              <div class="small mt-1 d-none d-lg-block">Supplier Orders</div>
            </RouterLink>
          </li>
          <li v-if="canViewCustomerOrders" class="nav-item mx-lg-3">
            <RouterLink
                to="/customer-orders"
                class="nav-link text-center"
                :class="{ 'section-active': isSectionActive('/customer-orders') }"
            >
              <i class="bi bi-cart-check fs-4"></i>
              <div class="small mt-1 d-none d-lg-block">Customer Orders</div>
            </RouterLink>
          </li>
          <li v-if="canViewSupplierOrders" class="nav-item mx-lg-3">
            <RouterLink to="/samples-trips" class="nav-link text-center"
                :class="{ 'section-active': isSectionActive('/samples-trips') }"
                :title="$t('Samples and trips')">
              <i class="bi bi-airplane fs-4 d-inline-block" style="transform: rotate(90deg)"></i>
              <div class="small mt-1 d-none d-lg-block">{{ $t('Samples and trips') }}</div>
            </RouterLink>
          </li>
          <li v-if="canViewProducts" class="nav-item mx-lg-3">
            <RouterLink
                to="/products"
                class="nav-link text-center"
                :class="{ 'section-active': isSectionActive('/products') }"
            >
              <i class="bi bi-box-seam fs-4"></i>
              <div class="small mt-1 d-none d-lg-block">Products</div>
            </RouterLink>
          </li>
          <li v-if="canViewWarehouse" class="nav-item mx-lg-3">
            <RouterLink
                to="/warehouse"
                class="nav-link text-center"
                :class="{ 'section-active': isSectionActive('/warehouse') }"
            >
              <i class="bi bi-boxes fs-4"></i>
              <div class="small mt-1 d-none d-lg-block">Warehouse</div>
            </RouterLink>
          </li>
          <li v-if="canViewCounterparties" class="nav-item mx-lg-3">
            <RouterLink
                to="/counterparty"
                class="nav-link text-center"
                :class="{ 'section-active': isSectionActive('/counterparty') }"
            >
              <i class="bi bi-people fs-4"></i>
              <div class="small mt-1 d-none d-lg-block">Counterparties</div>
            </RouterLink>
          </li>
          <li class="nav-item mx-lg-3">
            <NotificationCenter />
          </li>
          <li class="nav-item mx-lg-3">
            <RouterLink
                to="/profile"
                class="nav-link text-center"
                :class="{ 'section-active': isSectionActive('/profile') }"
            >
              <span class="profile-icon-slot">
                <img v-if="avatarSrc" :src="avatarSrc" class="nav-avatar" alt="Profile" />
                <span v-else class="nav-avatar avatar-placeholder">{{ initials }}</span>
              </span>
              <div class="small mt-1 d-none d-lg-block">Profile</div>
            </RouterLink>
          </li>
        </ul>
      </div>
    </div>
  </nav>
</template>

<script>
import axios, { AUTH_SESSION_KEY } from '../axios'
import logo from '../assets/logo.png'
import NotificationCenter from './NotificationCenter.vue'
import { setLanguage } from '../i18n'
import { accessState, hasPermission, PERMISSIONS, setCurrentUser } from '../access'

const API_ORIGIN = 'http://localhost:8000'

export default {
  name: 'NavBar',
  components: { NotificationCenter },
  data() {
    return {
      logo,
      profile: this.readCachedProfile()
    }
  },
  computed: {
    canViewSupplierOrders() {
      return hasPermission(PERMISSIONS.SUPPLIER_ORDERS_VIEW, accessState.user);
    },
    canViewCustomerOrders() {
      return hasPermission(PERMISSIONS.CUSTOMER_ORDERS_VIEW, accessState.user);
    },
    canViewProducts() {
      return hasPermission(PERMISSIONS.PRODUCTS_VIEW, accessState.user);
    },
    canViewWarehouse() {
      return hasPermission(PERMISSIONS.WAREHOUSE_VIEW, accessState.user);
    },
    canViewCounterparties() {
      return hasPermission(PERMISSIONS.COUNTERPARTIES_VIEW, accessState.user);
    },
    avatarSrc() {
      return this.mediaUrl(this.profile?.avatar);
    },
    initials() {
      const first = this.profile?.first_name || this.profile?.username || '';
      const last = this.profile?.last_name || '';
      return `${first.charAt(0)}${last.charAt(0)}`.toUpperCase() || 'U';
    }
  },
  mounted() {
    this.fetchProfile();
    window.addEventListener('profile-updated', this.handleProfileUpdated);
  },
  beforeUnmount() {
    window.removeEventListener('profile-updated', this.handleProfileUpdated);
  },
  methods: {
    readCachedProfile() {
      try {
        return JSON.parse(localStorage.getItem('current_user_profile')) || {};
      } catch {
        return {};
      }
    },
    async fetchProfile() {
      if (!localStorage.getItem(AUTH_SESSION_KEY)) return;
      try {
        const { data } = await axios.get('/api/auth/me/');
        this.handleProfileUpdated({ detail: data });
      } catch {
        this.profile = this.readCachedProfile();
      }
    },
    handleProfileUpdated(event) {
      this.profile = event.detail || {};
      setCurrentUser(this.profile);
      setLanguage(this.profile.notification_language || this.profile.company_language_code || 'ru');
    },
    mediaUrl(value) {
      if (!value) return '';
      if (value.startsWith('http')) return value;
      return new URL(value, API_ORIGIN).href;
    },
    isSectionActive(path) {
      return this.$route.path === path || this.$route.path.startsWith(`${path}/`);
    }
  }
}
</script>

<style scoped>
/* Цвет иконок и ховер остаются прежними */
.navbar-nav .nav-link {
  color: #444;
  transition: color .2s;
}
.navbar-nav .nav-link:hover,
.navbar-nav .nav-link.router-link-active,
.navbar-nav .nav-link.section-active {
  color: #0d6efd;
}

/* Адаптивная высота логотипа */
.logo-img {
  height: 100px;
}

.profile-icon-slot {
  display: inline-flex;
  height: 36px;
  align-items: center;
  justify-content: center;
  vertical-align: top;
}

.nav-avatar {
  display: inline-flex;
  width: 32px;
  height: 32px;
  align-items: center;
  justify-content: center;
  object-fit: cover;
  border: 1px solid #dee2e6;
  border-radius: 50%;
  font-size: 0.78rem;
  font-weight: 600;
  line-height: 1;
  vertical-align: middle;
}

.avatar-placeholder {
  color: #495057;
  background: #f1f3f5;
}

@media (max-width: 992px) {
  .logo-img {
    height: 80px;
  }
}

/* Анимация бургер-иконки */
.navbar-toggler-icon {
  transition: transform .3s ease;
}
.navbar-toggler.collapsed .navbar-toggler-icon {
  transform: rotate(0);
}
.navbar-toggler:not(.collapsed) .navbar-toggler-icon {
  transform: rotate(90deg);
}
</style>
