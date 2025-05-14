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
          <li class="nav-item mx-lg-3">
            <RouterLink to="/supplier-orders" class="nav-link text-center">
              <i class="bi bi-truck fs-4"></i>
              <div class="small mt-1 d-none d-lg-block">Supplier Orders</div>
            </RouterLink>
          </li>
          <li class="nav-item mx-lg-3">
            <RouterLink to="/customer-orders" class="nav-link text-center">
              <i class="bi bi-cart-check fs-4"></i>
              <div class="small mt-1 d-none d-lg-block">Customer Orders</div>
            </RouterLink>
          </li>
          <li class="nav-item mx-lg-3">
            <RouterLink to="/products" class="nav-link text-center">
              <i class="bi bi-box-seam fs-4"></i>
              <div class="small mt-1 d-none d-lg-block">Products</div>
            </RouterLink>
          </li>
          <li class="nav-item mx-lg-3">
            <RouterLink to="/counterparty" class="nav-link text-center">
              <i class="bi bi-people fs-4"></i>
              <div class="small mt-1 d-none d-lg-block">Counterparties</div>
            </RouterLink>
          </li>
          <li class="nav-item mx-lg-3">
            <RouterLink to="/profile" class="nav-link text-center">
              <i class="bi bi-person-circle fs-4"></i>
              <div class="small mt-1 d-none d-lg-block">Profile</div>
            </RouterLink>
          </li>
        </ul>
      </div>
    </div>
  </nav>
</template>

<script>
import logo from '../assets/logo.png'

export default {
  name: 'NavBar',
  data() {
    return {
      logo
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
.navbar-nav .nav-link.router-link-active {
  color: #0d6efd;
}

/* Адаптивная высота логотипа */
.logo-img {
  height: 100px;
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
