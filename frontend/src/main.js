import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import './assets/main.css'
import { restoreTheme } from './assets/themes.js'

const app = createApp(App)

// 启动时恢复上次保存的主题
restoreTheme()

app.use(router)
app.mount('#app')
