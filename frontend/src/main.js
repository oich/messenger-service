import { createApp } from 'vue'
import App from './App.vue'
// PrimeVue + HubPreset + locale + Toast/Confirm + tooltip/ripple + tokens
// (docs/ui-designsystem-konzept.md, shared/hub_ui_kit)
import HubUi from '@hub/ui'
import router from './router'
import { configureApi } from './api'

import 'primeicons/primeicons.css'
import './style.css'
import 'primeflex/primeflex.css'

/**
 * Exchange an authorization code for an access token via Hub backend.
 */
async function exchangeCodeForToken(code, redirectUri) {
  const { getHubUrl } = await import('./utils/tokenRefresh')
  const hubUrl = getHubUrl()
  try {
    const response = await fetch(`${hubUrl}/api/auth/sso/token`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ code, redirect_uri: redirectUri }),
    })
    if (response.ok) {
      const data = await response.json()
      return data // { access_token, refresh_token, token_type }
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
    const tokenData = await exchangeCodeForToken(hubCode, currentUrl)
    if (tokenData) {
      localStorage.setItem('token', tokenData.access_token)
      if (tokenData.refresh_token) {
        localStorage.setItem('refresh_token', tokenData.refresh_token)
      }
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

  // Start proactive token refresh if a refresh token exists
  if (localStorage.getItem('refresh_token')) {
    const { scheduleRefresh } = await import('./utils/tokenRefresh')
    scheduleRefresh()
  }

  await configureApi()

  const app = createApp(App)

  app.use(router)
  app.use(HubUi)

  await router.isReady()
  app.mount('#app')
}

initializeApp()
