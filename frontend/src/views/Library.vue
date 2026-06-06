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
  font-size: var(--type-page-title);
  line-height: 1.2;
  letter-spacing: 0;
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
  border: 1px solid var(--glass-control-border);
  border-radius: 14px;
  background: var(--surface-specular-edge), var(--surface-noise), var(--material-glass-control);
  color: var(--text-primary);
  font: inherit;
  outline: none;
  box-shadow: var(--glass-control-shadow);
  backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
  -webkit-backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
  transition: transform var(--motion-standard), opacity var(--motion-fast);
}
.check-form input:focus {
  border-color: var(--glass-active-border);
  background: var(--surface-specular-edge-strong), var(--surface-noise), var(--glass-active-material);
  box-shadow: var(--glass-active-shadow);
}
.check-form button {
  min-height: 44px;
  min-width: 96px;
  padding: 0 20px;
  background: var(--surface-specular-edge), var(--surface-noise), var(--material-glass-control);
  color: var(--text-primary);
  border: 1px solid var(--glass-control-border);
  border-radius: 14px;
  cursor: pointer;
  font: inherit;
  font-weight: 700;
  box-shadow: var(--glass-control-shadow);
  backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
  -webkit-backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
  transition: transform var(--motion-standard), opacity var(--motion-fast);
}
.check-form button:hover:not(:disabled) {
  background: var(--surface-specular-edge-strong), var(--surface-noise), var(--material-glass-control-hover);
  border-color: var(--glass-control-border-hover);
  box-shadow: var(--glass-control-shadow-hover);
  transform: translateY(-1px);
}
.check-form button:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}
.result {
  background: var(--surface-specular-edge-strong), var(--surface-noise), var(--material-glass-sheet);
  border: 1px solid var(--glass-edge);
  border-radius: var(--radius-md);
  padding: 20px;
  box-shadow: var(--glass-surface-shadow);
  backdrop-filter: blur(var(--glass-blur-surface)) saturate(var(--glass-saturate-surface));
  -webkit-backdrop-filter: blur(var(--glass-blur-surface)) saturate(var(--glass-saturate-surface));
}
.exists { color: var(--badge-success-text); }
.not-exists { color: var(--text-secondary); }
.item {
  background: var(--surface-specular-edge), var(--surface-noise), var(--material-glass-control);
  border: 1px solid var(--glass-control-border);
  padding: 12px;
  margin-top: 10px;
  border-radius: var(--radius-sm);
  box-shadow: var(--glass-control-shadow);
  backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
  -webkit-backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
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
