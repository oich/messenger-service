// Refresh the token 2 minutes before expiry
const REFRESH_BUFFER_MS = 2 * 60 * 1000

let refreshTimerId = null

// Derive Hub URL from current location (Hub is on port 443, same host) -
// Derive the Hub's base URL. window.location only IS the Hub when this
// satellite shares the Hub's exact host (LAN/plain-domain deployment, only
// the port differs). If VITE_HUB_URL's host differs, this satellite has its
// own dedicated hostname (Cloudflare Tunnel, e.g. "messenger-service.aesystek.de"
// next to the Hub's "syshub.aesystek.de") - use the baked-in VITE_HUB_URL
// (build-time env var, see docker-compose.hub.yml) instead.
export function getHubUrl() {
  const envUrl = import.meta.env?.VITE_HUB_URL
  const currentHost = window.location.hostname
  if (envUrl) {
    try {
      if (new URL(envUrl).hostname === currentHost) {
        return `${window.location.protocol}//${currentHost}`
      }
    } catch { /* envUrl not a valid URL - fall through to window.location */ }
    return envUrl
  }
  return `${window.location.protocol}//${currentHost}`
}

/**
 * Decode a JWT payload without verifying signature (client-side only).
 * Returns null if the token is malformed.
 */
function decodeTokenPayload(token) {
  try {
    const parts = token.split('.')
    if (parts.length !== 3) return null
    return JSON.parse(atob(parts[1]))
  } catch {
    return null
  }
}

/**
 * Schedule a proactive token refresh based on the access token's exp claim.
 * Should be called after login / code exchange and after each successful refresh.
 */
export function scheduleRefresh() {
  clearRefreshTimer()

  const token = localStorage.getItem('token')
  if (!token) return

  const payload = decodeTokenPayload(token)
  if (!payload || !payload.exp) return

  const expiresAt = payload.exp * 1000
  const delay = expiresAt - Date.now() - REFRESH_BUFFER_MS

  if (delay <= 0) {
    refreshTokenNow()
    return
  }

  refreshTimerId = setTimeout(() => {
    refreshTokenNow()
  }, delay)
}

/**
 * Clear the scheduled refresh timer.
 */
export function clearRefreshTimer() {
  if (refreshTimerId !== null) {
    clearTimeout(refreshTimerId)
    refreshTimerId = null
  }
}

/**
 * Perform a token refresh against the Hub backend.
 * Uses plain fetch (not apiClient) to avoid the axios 401 interceptor loop.
 * Returns the new access token on success, null on failure.
 */
export async function refreshTokenNow() {
  const refreshToken = localStorage.getItem('refresh_token')
  if (!refreshToken) return null

  const hubUrl = getHubUrl()
  if (!hubUrl) return null

  try {
    const resp = await fetch(`${hubUrl}/api/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: refreshToken }),
    })

    if (!resp.ok) {
      console.warn('Token refresh failed:', resp.status)
      if (resp.status === 401) {
        localStorage.removeItem('refresh_token')
      }
      return null
    }

    const data = await resp.json()
    localStorage.setItem('token', data.access_token)
    if (data.refresh_token) {
      localStorage.setItem('refresh_token', data.refresh_token)
    }

    scheduleRefresh()
    return data.access_token
  } catch (e) {
    console.error('Token refresh error:', e)
    return null
  }
}
