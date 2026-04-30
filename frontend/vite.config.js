import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    host: '0.0.0.0',
    proxy: {
      '/api': {
        // 端口与 config.yaml 中 server.port 保持一致
        target: 'http://localhost:18090',
        changeOrigin: true
      }
    }
  }
})
