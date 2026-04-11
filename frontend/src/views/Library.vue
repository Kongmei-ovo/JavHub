<template>
  <div class="library">
    <h1>库检测</h1>

    <div class="check-form">
      <input v-model="code" placeholder="输入影片番号，如 ABC-123" @keyup.enter="check" />
      <button @click="check" :disabled="checking">{{ checking ? '检测中...' : '检测' }}</button>
    </div>

    <div v-if="result" class="result">
      <div v-if="result.exists" class="exists">
        <p class="found">✅ 影片存在于Emby库中</p>
        <div v-for="item in result.items" :key="item.id" class="item">
          <p><strong>名称:</strong> {{ item.name }}</p>
          <p><strong>路径:</strong> {{ item.path }}</p>
        </div>
      </div>
      <div v-else class="not-exists">
        <p class="not-found">❌ 影片不在Emby库中</p>
      </div>
    </div>
  </div>
</template>

<script>
import api from '../api'

export default {
  name: 'Library',
  data() {
    return {
      code: '',
      checking: false,
      result: null
    }
  },
  methods: {
    async check() {
      if (!this.code) return
      this.checking = true
      this.result = null
      try {
        const resp = await api.checkLibrary(this.code)
        this.result = resp.data
      } catch (e) {
        console.error('Check failed:', e)
      } finally {
        this.checking = false
      }
    }
  }
}
</script>

<style scoped>
.check-form { margin: 20px 0; display: flex; gap: 10px; }
.check-form input { flex: 1; padding: 12px; border: 1px solid #ddd; border-radius: 4px; font-size: 16px; }
.check-form button { padding: 12px 24px; background: #4CAF50; color: white; border: none; border-radius: 4px; cursor: pointer; }
.check-form button:disabled { background: #ccc; }
.result { background: white; border-radius: 8px; padding: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
.exists { color: #4CAF50; }
.not-exists { color: #666; }
.item { background: #f9f9f9; padding: 10px; margin-top: 10px; border-radius: 4px; }
.found { color: #4CAF50; font-size: 1.1em; }
.not-found { color: #666; font-size: 1.1em; }
</style>
