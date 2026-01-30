import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5175,
    proxy: {
      '/auth': 'http://localhost:8005',
      '/api': 'http://localhost:8005',
    }
  }
})
