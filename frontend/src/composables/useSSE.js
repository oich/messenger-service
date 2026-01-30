import { ref, onUnmounted } from 'vue'

const connected = ref(false)

export function useSSE(onMessage) {
  let eventSource = null

  function connect() {
    const token = localStorage.getItem('token')
    if (!token) return

    const baseUrl = import.meta.env.VITE_API_TARGET || ''
    const url = `${baseUrl}/api/v1/events/stream?token=${encodeURIComponent(token)}`

    eventSource = new EventSource(url)

    eventSource.onopen = () => {
      connected.value = true
    }

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        if (data.type === 'keepalive') return
        if (onMessage) onMessage(data)
      } catch (err) {
        console.error('SSE parse error:', err)
      }
    }

    eventSource.onerror = () => {
      connected.value = false
      eventSource.close()
      // Reconnect after delay
      setTimeout(connect, 5000)
    }
  }

  function disconnect() {
    if (eventSource) {
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
