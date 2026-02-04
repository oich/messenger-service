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

/**
 * Exchange an authorization code for an access token via Hub backend.
 */
async function exchangeCodeForToken(code, redirectUri) {
  // Derive Hub URL from current location (Hub is on port 443, same host)
  const hubUrl = `${window.location.protocol}//${window.location.hostname}`
  try {
    const response = await fetch(`${hubUrl}/api/auth/sso/token`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ code, redirect_uri: redirectUri }),
    })
    if (response.ok) {
      const data = await response.json()
      return data.access_token
    }
    console.warn('Code exchange failed:', response.status)
    return null
  } catch (e) {
    console.error('Code exchange error:', e)
    return null
  }
}

async function initializeApp() {
  // SSO: Handle authorization code flow (hub_code) or legacy token flow (hub_token)
  const urlParams = new URLSearchParams(window.location.search)
  const hubCode = urlParams.get('hub_code')
  const hubToken = urlParams.get('hub_token')
  const currentUrl = window.location.origin + window.location.pathname

  if (hubCode) {
    // New secure flow: exchange code for token
    const token = await exchangeCodeForToken(hubCode, currentUrl)
    if (token) {
      localStorage.setItem('token', token)
    }
    urlParams.delete('hub_code')
    const cleanUrl = urlParams.toString()
      ? `${window.location.pathname}?${urlParams.toString()}`
      : window.location.pathname
    window.history.replaceState({}, '', cleanUrl)
  } else if (hubToken) {
    // Legacy flow (backwards compatibility)
    console.warn('Using legacy hub_token flow - please update Hub to use hub_code')
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
