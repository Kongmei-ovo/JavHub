<template>
  <div class="library page-shell page-shell--standard">
    <h1>库检测</h1>

    <div class="check-form">
      <input v-model="code" placeholder="输入影片番号，如 ABC-123" @keyup.enter="check" />
      <button @click="check" :disabled="checking">{{ checking ? '检测中...' : '检测' }}</button>
    </div>

    <div v-if="result" class="result">
      <div v-if="result.exists" class="exists">
        <p class="found">影片存在于Emby库中</p>
        <div v-for="item in result.items" :key="item.id" class="item">
          <p><strong>名称:</strong> {{ item.name }}</p>
          <p><strong>路径:</strong> {{ item.path }}</p>
        </div>
      </div>
      <div v-else class="not-exists">
        <p class="not-found">影片不在Emby库中</p>
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
.library {
  --page-max: 880px;
}
.library h1 {
  margin: 0;
  font-size: 28px;
  line-height: 1.2;
}
.check-form {
  margin: 20px 0;
  display: flex;
  gap: 10px;
}
.check-form input {
  flex: 1;
  min-width: 0;
  min-height: 44px;
  padding: 0 14px;
  border: 1px solid var(--border);
  border-radius: 14px;
  background: var(--bg-card);
  color: var(--text-primary);
  font: inherit;
  outline: none;
  transition: border-color var(--motion-fast), background var(--motion-fast), box-shadow var(--motion-fast);
}
.check-form input:focus {
  border-color: var(--border-light);
  background: var(--bg-card-hover);
  box-shadow: 0 0 0 3px rgba(var(--accent-rgb), 0.08);
}
.check-form button {
  min-height: 44px;
  min-width: 96px;
  padding: 0 20px;
  background: var(--accent);
  color: var(--text-on-accent);
  border: 1px solid var(--accent);
  border-radius: 14px;
  cursor: pointer;
  font: inherit;
  font-weight: 700;
  transition: background var(--motion-fast), border-color var(--motion-fast), transform var(--motion-fast), opacity var(--motion-fast);
}
.check-form button:hover:not(:disabled) {
  background: var(--accent-light);
  transform: translateY(-1px);
}
.check-form button:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}
.result {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  padding: 20px;
  box-shadow: var(--shadow-card);
}
.exists { color: var(--badge-success-text); }
.not-exists { color: var(--text-secondary); }
.item {
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid var(--border);
  padding: 12px;
  margin-top: 10px;
  border-radius: var(--radius-sm);
}
.item p + p {
  margin-top: 6px;
}
.found,
.not-found {
  font-size: 15px;
  font-weight: 700;
}
.found { color: var(--badge-success-text); }
.not-found { color: var(--text-secondary); }

@media (max-width: 640px) {
  .library {
    padding: 20px 16px 40px;
  }
  .check-form {
    flex-direction: column;
  }
  .check-form button {
    width: 100%;
  }
}
</style>
