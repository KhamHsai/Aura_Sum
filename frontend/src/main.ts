import { createApp } from 'vue'
import { createPinia } from 'pinia'
import { createI18n } from 'vue-i18n'
import router from './router'
import { useAuthStore } from './stores/auth'
import App from './App.vue'
import './style.css'

import en from './locales/en.json'
import th from './locales/th.json'

// Restore saved language or default to English.
const savedLocale = localStorage.getItem('locale') || 'en'

const i18n = createI18n({
  legacy: false,
  locale: savedLocale,
  fallbackLocale: 'en',
  messages: { en, th },
})

const app = createApp(App)
const pinia = createPinia()

app.use(pinia)
app.use(i18n)
app.use(router)

// Restore authentication from localStorage before the router starts navigating.
const auth = useAuthStore()
auth.initializeAuth().finally(() => {
  app.mount('#app')
})
