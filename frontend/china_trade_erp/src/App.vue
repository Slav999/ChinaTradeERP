<template>
  <div id="app">
    <!-- Показываем NavBar только если текущий маршрут не прячет его -->
    <NavBar v-if="!$route.meta.hideNav" />
    <router-view/>
  </div>
</template>

<script>
import NavBar from './components/NavBar.vue'

export default {
  components: { NavBar }
}
</script>
