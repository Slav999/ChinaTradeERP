import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import './styles/custom.scss'
import 'bootstrap/dist/js/bootstrap.bundle';

createApp(App).use(router).mount('#app')
