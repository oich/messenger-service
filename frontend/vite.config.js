import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5175,
    proxy: {
      '/auth': 'http://localhost:8005',
      '/api/v1/events': {
        target: 'http://localhost:8005',
        // SSE: disable response buffering so events stream through
        configure: (proxy) => {
          proxy.on('proxyRes', (proxyRes) => {
            // Prevent proxy from buffering the streaming response
            proxyRes.headers['cache-control'] = 'no-cache'
            proxyRes.headers['x-accel-buffering'] = 'no'
          })
        },
        // Ensure no timeout kills the long-lived SSE connection
        timeout: 0,
      },
      '/api': 'http://localhost:8005',
    }
  }
})
