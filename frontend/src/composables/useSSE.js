import { ref, onUnmounted } from 'vue'

const connected = ref(false)

export function useSSE(onMessage) {
  let eventSource = null
  let reconnectTimer = null
  let destroyed = false

  function connect() {
    if (destroyed) return

    // Close existing connection before creating a new one
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

    console.log('[SSE] Connecting...')
    const es = new EventSource(url)
    eventSource = es

    es.onopen = () => {
      console.log('[SSE] Connected')
      connected.value = true
    }

    es.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        if (data.type === 'keepalive') return
        console.log('[SSE] Event received:', data.type)
        if (onMessage) onMessage(data)
      } catch (err) {
        console.error('[SSE] Parse error:', err)
      }
    }

    es.onerror = (err) => {
      console.warn('[SSE] Connection error, will reconnect...', err)
      connected.value = false
      // Only handle if this is still the active connection
      if (eventSource === es) {
        es.close()
        eventSource = null
        scheduleReconnect()
      }
    }
  }

  function scheduleReconnect() {
    if (destroyed) return
    if (reconnectTimer) clearTimeout(reconnectTimer)
    reconnectTimer = setTimeout(() => {
      reconnectTimer = null
      connect()
    }, 3000)
  }

  function disconnect() {
    destroyed = true
    if (reconnectTimer) {
      clearTimeout(reconnectTimer)
      reconnectTimer = null
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
