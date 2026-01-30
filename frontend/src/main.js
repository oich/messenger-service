import { createApp } from 'vue'
import App from './App.vue'
import PrimeVue from 'primevue/config'
import Aura from '@primeuix/themes/aura'
import Tooltip from 'primevue/tooltip'
import ToastService from 'primevue/toastservice'
import router from './router'
import { configureApi } from './api'

import 'primeicons/primeicons.css'
import './style.css'
import 'primeflex/primeflex.css'

async function initializeApp() {
  // SSO: capture hub_token from URL query parameter
  const urlParams = new URLSearchParams(window.location.search)
  const hubToken = urlParams.get('hub_token')
  if (hubToken) {
    localStorage.setItem('token', hubToken)
    urlParams.delete('hub_token')
    const cleanUrl = urlParams.toString()
      ? `${window.location.pathname}?${urlParams.toString()}`
      : window.location.pathname
    window.history.replaceState({}, '', cleanUrl)
  }

  await configureApi()

  const app = createApp(App)

  app.use(router)
  app.use(PrimeVue, {
    theme: {
      preset: Aura,
      options: {
        prefix: 'p',
        darkMode: true,
      }
    },
    locale: {
      firstDayOfWeek: 1,
      dayNames: ["Sonntag", "Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag"],
      dayNamesShort: ["So", "Mo", "Di", "Mi", "Do", "Fr", "Sa"],
      dayNamesMin: ["So", "Mo", "Di", "Mi", "Do", "Fr", "Sa"],
      monthNames: ["Januar", "Februar", "Maerz", "April", "Mai", "Juni", "Juli", "August", "September", "Oktober", "November", "Dezember"],
      monthNamesShort: ["Jan", "Feb", "Maer", "Apr", "Mai", "Jun", "Jul", "Aug", "Sep", "Okt", "Nov", "Dez"],
      today: 'Heute',
      clear: 'Loeschen',
    }
  })

  app.use(ToastService)
  app.directive('tooltip', Tooltip)

  await router.isReady()
  app.mount('#app')
}

initializeApp()
