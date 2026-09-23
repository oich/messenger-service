import { readFileSync } from 'node:fs'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

const pkg = JSON.parse(readFileSync(new URL('./package.json', import.meta.url)))

export default defineConfig({
  plugins: [vue()],
  define: {
    // Build stamp shown in the top bar: changes on every rebuild, so a stale
    // cached bundle is visible at a glance (Docker build context has no .git).
    __APP_VERSION__: JSON.stringify(pkg.version),
    __BUILD_TIME__: JSON.stringify(new Date().toISOString()),
  },
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
