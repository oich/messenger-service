import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

const pkg = JSON.parse(readFileSync(new URL('./package.json', import.meta.url)))

// UI design system (shared/hub_ui_kit, docs/ui-designsystem-konzept.md): Docker build
// copies it to HUB_UI_PATH, local dev uses it straight from the Hub checkout.
const hubUiSrc = process.env.HUB_UI_PATH
  || fileURLToPath(new URL('../../../shared/hub_ui_kit/src', import.meta.url))

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: { '@hub/ui': hubUiSrc },
    // the lib lives outside node_modules: resolve its deps from here, otherwise
    // not found / a second PrimeVue instance (breaks theme + services)
    dedupe: ['vue', 'vue-router', 'primevue', '@primeuix/themes'],
  },
  define: {
    // Build stamp shown in the top bar: changes on every rebuild, so a stale
    // cached bundle is visible at a glance (Docker build context has no .git).
    __APP_VERSION__: JSON.stringify(pkg.version),
    __BUILD_TIME__: JSON.stringify(new Date().toISOString()),
  },
  server: {
    fs: { allow: ['..', hubUiSrc] },
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
