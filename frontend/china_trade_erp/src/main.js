import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import { installI18n, refreshTranslations } from './i18n'
import './styles/custom.scss'
import 'bootstrap/dist/js/bootstrap.bundle';

const app = createApp(App)
installI18n(app)
router.afterEach(refreshTranslations)
app.use(router).mount('#app')
