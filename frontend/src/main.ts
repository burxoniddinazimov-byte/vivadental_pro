import { createApp } from 'vue'
import { createPinia } from 'pinia'
import { createI18n } from 'vue-i18n'
import { VueQueryPlugin } from 'vue-query'
import PrimeVue from 'primevue/config'
import Toast from 'vue3-toastify'

import App from './App.vue'
import router from './router'
import './style.css'

// Импорт стилей PrimeVue
import 'primevue/resources/themes/lara-light-blue/theme.css'
import 'primevue/resources/primevue.min.css'
import 'primeicons/primeicons.css'
import 'vue3-toastify/dist/index.css'

// Локализация
const i18n = createI18n({
  locale: 'ru',
  messages: {
    ru: {
      dashboard: 'Панель управления',
      patients: 'Пациенты',
      appointments: 'Записи',
      finance: 'Финансы',
      reports: 'Отчеты',
      settings: 'Настройки'
    }
  }
})

const app = createApp(App)

app.use(createPinia())
app.use(router)
app.use(i18n)
app.use(PrimeVue)
app.use(VueQueryPlugin)
app.use(Toast, {
  autoClose: 3000,
  position: 'top-right'
})

app.mount('#app')