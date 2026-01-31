import { ref, onUnmounted } from 'vue'

const connected = ref(false)

export function useSSE(onMessage) {
  let eventSource = null
  let reconnectTimer = null
  let pollTimer = null
  let destroyed = false
  let usePolling = false

  function connect() {
    if (destroyed) return

    if (eventSource) {
      eventSource.onopen = null
      eventSource.onmessage = null
      eventSource.onerror = null
      eventSource.close()
      eventSource = null
    }

    const token = localStorage.getItem('token')
    if (!token) {
      console.warn('[SSE] No token found, skipping connection')
      return
    }

    const baseUrl = import.meta.env.VITE_API_TARGET || ''
    const url = `${baseUrl}/api/v1/events/stream?token=${encodeURIComponent(token)}`

    console.log('[SSE] Connecting to:', url.replace(/token=[^&]+/, 'token=***'))

    let opened = false

    try {
      const es = new EventSource(url)
      eventSource = es

      es.onopen = () => {
        opened = true
        console.log('[SSE] Connected successfully')
        connected.value = true
        usePolling = false
        if (pollTimer) {
          clearTimeout(pollTimer)
          pollTimer = null
        }
      }

      es.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          if (data.type === 'keepalive' || data.type === 'connected') return
          console.log('[SSE] Event received:', data.type)
          if (onMessage) onMessage(data)
        } catch (err) {
          console.error('[SSE] Parse error:', err)
        }
      }

      es.onerror = () => {
        connected.value = false
        if (eventSource === es) {
          es.close()
          eventSource = null
          if (!opened && !usePolling) {
            console.warn('[SSE] EventSource failed, falling back to polling')
            usePolling = true
            startPolling()
          } else if (!usePolling) {
            scheduleReconnect()
          }
        }
      }

      // Safety timeout
      setTimeout(() => {
        if (!opened && !destroyed && !usePolling) {
          console.warn('[SSE] Connection timeout, falling back to polling')
          if (eventSource === es) {
            es.close()
            eventSource = null
          }
          usePolling = true
          startPolling()
        }
      }, 5000)

    } catch (err) {
      console.error('[SSE] EventSource constructor failed:', err)
      usePolling = true
      startPolling()
    }
  }

  function startPolling() {
    if (destroyed || pollTimer) return
    console.log('[SSE] Starting polling fallback (every 2s)')
    connected.value = true

    async function poll() {
      if (destroyed) return
      try {
        const token = localStorage.getItem('token')
        if (!token) return
        const baseUrl = import.meta.env.VITE_API_TARGET || ''
        const resp = await fetch(`${baseUrl}/api/v1/events/poll?token=${encodeURIComponent(token)}`)
        if (resp.ok) {
          const events = await resp.json()
          for (const event of events) {
            if (event.type === 'keepalive' || event.type === 'connected') continue
            if (onMessage) onMessage(event)
          }
        }
      } catch {
        // Polling endpoint may not be available
      }
      if (!destroyed) {
        pollTimer = setTimeout(poll, 2000)
      }
    }

    poll()
  }

  function scheduleReconnect() {
    if (destroyed) return
    if (reconnectTimer) clearTimeout(reconnectTimer)
    reconnectTimer = setTimeout(() => {
      reconnectTimer = null
      connect()
    }, 5000)
  }

  function disconnect() {
    destroyed = true
    if (reconnectTimer) {
      clearTimeout(reconnectTimer)
      reconnectTimer = null
    }
    if (pollTimer) {
      clearTimeout(pollTimer)
      pollTimer = null
    }
    if (eventSource) {
      eventSource.onopen = null
      eventSource.onmessage = null
      eventSource.onerror = null
      eventSource.close()
      eventSource = null
      connected.value = false
    }
  }

  onUnmounted(disconnect)

  return {
    connected,
    connect,
    disconnect,
  }
}
