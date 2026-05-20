import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { readFileSync } from 'node:fs'

const packageJson = JSON.parse(readFileSync(new URL('./package.json', import.meta.url), 'utf8'))
const appVersion = process.env.VITE_APP_VERSION || packageJson.version

export default defineConfig({
  plugins: [vue()],
  define: {
    'import.meta.env.VITE_APP_VERSION': JSON.stringify(appVersion)
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (!id.includes('node_modules')) return undefined
          if (id.includes('vue') || id.includes('vue-router')) return 'vue-vendor'
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
    port: 5174,
    proxy: {
      '/health': {
        target: 'http://127.0.0.1:18090',
        changeOrigin: true
      },
      '/api': {
        // 端口与 config.yaml 中 server.port 保持一致
        target: 'http://127.0.0.1:18090',
        changeOrigin: true
      }
    }
  }
})
