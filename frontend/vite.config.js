import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  build: {
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (!id.includes('node_modules')) return undefined
          if (id.includes('vue') || id.includes('vue-router')) return 'vue-vendor'
          if (id.includes('element-plus') || id.includes('@element-plus')) return 'element-plus'
          if (id.includes('hls.js') || id.includes('plyr') || id.includes('vue-video-player')) return 'media-player'
          if (id.includes('gsap')) return 'motion'
          if (id.includes('axios')) return 'network'
          return 'vendor'
        }
      }
    }
  },
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
