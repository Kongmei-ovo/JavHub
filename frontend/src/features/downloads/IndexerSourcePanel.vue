<template>
  <section class="indexer-panel">
    <header class="indexer-panel-header">
      <div class="indexer-panel-copy">
        <h2>磁力索引源</h2>
        <p>连接 Prowlarr / Jackett / 通用 Torznab，为下载与候选生成提供磁链搜索。</p>
      </div>
      <label class="indexer-enable" :class="{ on: draft.enabled }">
        <input type="checkbox" v-model="draft.enabled" role="switch" />
        <span>{{ draft.enabled ? '已启用' : '未启用' }}</span>
      </label>
    </header>

    <div class="indexer-kind" role="group" aria-label="索引源类型">
      <button
        v-for="option in kindOptions"
        :key="option.value"
        type="button"
        class="indexer-kind-btn"
        :class="{ active: kind === option.value }"
        @click="kind = option.value"
      >
        <strong>{{ option.label }}</strong>
        <em>{{ option.tag }}</em>
      </button>
    </div>
    <p class="indexer-kind-hint">{{ activeKind.intro }}</p>

    <div class="indexer-fields">
      <label class="indexer-row">
        <span class="indexer-label">服务地址</span>
        <input class="input" v-model.trim="draft.base_url" :placeholder="activeKind.baseUrlPlaceholder" />
        <span class="indexer-note">{{ activeKind.baseUrlHint }}</span>
      </label>

      <label class="indexer-row">
        <span class="indexer-label">API Key</span>
        <span class="input-password-wrap">
          <input
            class="input"
            :type="showKey ? 'text' : 'password'"
            v-model="draft.api_key"
            autocomplete="off"
            placeholder="留空表示不修改已保存的密钥"
          />
          <button class="input-eye-btn" type="button" :title="showKey ? '隐藏' : '显示'" @click="showKey = !showKey">
            <svg v-if="!showKey" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="16" height="16"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
            <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="16" height="16"><path d="M17.94 17.94A10.07 10.07 0 0112 20c-7 0-11-8-11-8a18.45 18.45 0 015.06-5.94M9.9 4.24A9.12 9.12 0 0112 4c7 0 11 8 11 8a18.5 18.5 0 01-2.16 3.19m-6.72-1.07a3 3 0 11-4.24-4.24"/><line x1="1" y1="1" x2="23" y2="23"/></svg>
          </button>
        </span>
        <span class="indexer-note">从索引器后台复制；留空保存则保留现有密钥。</span>
      </label>

      <label class="indexer-row">
        <span class="indexer-label">Indexer</span>
        <input class="input" v-model.trim="draft.indexer" :placeholder="activeKind.indexerPlaceholder" />
        <span class="indexer-note">{{ activeKind.indexerHint }}</span>
      </label>

      <label class="indexer-row">
        <span class="indexer-label">分类 Categories</span>
        <input class="input" v-model.trim="draft.categories" placeholder="可留空，使用服务默认分类" />
        <span class="indexer-note">多个分类用逗号分隔，留空则用索引源默认值。</span>
      </label>

      <div class="indexer-row indexer-row--split">
        <label class="indexer-mini">
          <span class="indexer-label">返回上限</span>
          <span class="indexer-number">
            <input class="input" v-model.number="draft.limit" type="number" min="1" max="100" step="1" inputmode="numeric" />
            <span class="indexer-unit">条</span>
          </span>
          <span class="indexer-note">单次查询返回数量（1-100）。</span>
        </label>
        <label class="indexer-mini">
          <span class="indexer-label">超时</span>
          <span class="indexer-number">
            <input class="input" v-model.number="draft.timeout" type="number" min="1" max="60" step="1" inputmode="numeric" />
            <span class="indexer-unit">秒</span>
          </span>
          <span class="indexer-note">请求等待秒数（1-60）。</span>
        </label>
      </div>
    </div>

    <footer class="indexer-actions" aria-live="polite">
      <span class="indexer-status">{{ statusText }}</span>
      <button class="btn btn-primary" type="button" :disabled="saving" @click="emitSave">
        {{ saving ? '保存中...' : '保存索引源' }}
      </button>
    </footer>
  </section>
</template>

<script>
const KIND_STORAGE_KEY = 'javhub_indexer_kind'

const KIND_OPTIONS = [
  {
    value: 'prowlarr',
    label: 'Prowlarr',
    tag: '推荐',
    intro: 'Prowlarr 通过 Torznab 协议暴露索引器，按数字 ID 寻址。',
    baseUrlPlaceholder: 'http://localhost:9696',
    baseUrlHint: '填 Prowlarr 根地址即可，无需带 /api。',
    indexerPlaceholder: '例如 1',
    indexerHint: 'Indexer 填数字 ID（Prowlarr 里某索引器 Torznab Feed 末尾的数字），系统会自动拼成 /api/v1/indexer/<id>/newznab。',
  },
  {
    value: 'jackett',
    label: 'Jackett',
    tag: '兼容',
    intro: 'Jackett 同样走 Torznab 协议，按 tracker 名称寻址。',
    baseUrlPlaceholder: 'http://localhost:9117',
    baseUrlHint: '填 Jackett 根地址即可，无需带 /api。',
    indexerPlaceholder: '例如 nyaasi 或 all',
    indexerHint: 'Indexer 填 tracker 名（如 nyaasi），系统会自动拼成 /api/v2.0/indexers/<name>/results/torznab/api。',
  },
  {
    value: 'torznab',
    label: '通用 Torznab',
    tag: '自定义',
    intro: '任意兼容 Torznab/Newznab 的服务，可直接填完整 API 地址。',
    baseUrlPlaceholder: 'http://host:port/api',
    baseUrlHint: '可填完整 API 地址；也支持用 {indexer} 占位符替换 Indexer 值。',
    indexerPlaceholder: 'all',
    indexerHint: '如地址已是完整 API，可保持 all；含 {indexer} 占位时会替换为此值。',
  },
]

const DEFAULT_DRAFT = {
  enabled: false,
  name: 'torznab',
  base_url: '',
  api_key: '',
  indexer: 'all',
  categories: '',
  limit: 20,
  timeout: 15,
}

export default {
  name: 'IndexerSourcePanel',
  props: {
    modelValue: { type: Object, default: () => ({}) },
    saving: { type: Boolean, default: false },
    statusMessage: { type: String, default: '' },
  },
  emits: ['save'],
  data() {
    return {
      kind: 'prowlarr',
      showKey: false,
      draft: { ...DEFAULT_DRAFT },
      kindOptions: KIND_OPTIONS,
    }
  },
  computed: {
    activeKind() {
      return this.kindOptions.find(option => option.value === this.kind) || this.kindOptions[0]
    },
    statusText() {
      if (this.saving) return '正在保存索引源配置。'
      if (this.statusMessage) return this.statusMessage
      if (!this.draft.enabled) return '启用后才会参与磁链搜索。'
      if (!this.draft.base_url) return '填写服务地址后保存即可生效。'
      return '配置已就绪，保存后立即生效。'
    },
  },
  watch: {
    modelValue: {
      immediate: true,
      handler(value) {
        this.draft = { ...DEFAULT_DRAFT, ...(value || {}), api_key: '' }
      },
    },
  },
  created() {
    try {
      const saved = localStorage.getItem(KIND_STORAGE_KEY)
      if (saved && this.kindOptions.some(option => option.value === saved)) this.kind = saved
    } catch (e) { /* ignore */ }
  },
  methods: {
    emitSave() {
      try { localStorage.setItem(KIND_STORAGE_KEY, this.kind) } catch (e) { /* ignore */ }
      this.$emit('save', { ...this.draft })
    },
  },
}
</script>

<style scoped>
.indexer-panel {
  border: 1px solid var(--hairline);
  border-radius: var(--radius-card);
  background: var(--card);
  box-shadow: var(--shadow-card);
  padding: 22px;
  display: flex;
  flex-direction: column;
  gap: 18px;
}
.indexer-panel-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}
.indexer-panel-copy h2 {
  margin: 0 0 4px;
  font-size: var(--type-panel-title);
  color: var(--text-primary);
}
.indexer-panel-copy p {
  margin: 0;
  color: var(--text-secondary);
  font-size: var(--type-caption);
  line-height: 1.6;
}
.indexer-enable {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  flex: 0 0 auto;
  color: var(--text-secondary);
  font-size: var(--type-control);
  font-weight: 650;
}
.indexer-enable.on { color: var(--text-primary); }

.indexer-kind {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
}
.indexer-kind-btn {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 2px;
  padding: 10px 14px;
  border-radius: var(--radius-md);
  border: 1px solid var(--hairline);
  background: var(--card-2);
  color: var(--text-secondary);
  cursor: pointer;
  text-align: left;
  transition: transform var(--motion-standard), border-color var(--motion-fast);
}
.indexer-kind-btn:hover { border-color: var(--hairline-strong); transform: translateY(-1px); }
.indexer-kind-btn.active {
  border-color: var(--glass-active-border);
  background: var(--glass-active-material);
  color: var(--text-primary);
  box-shadow: var(--glass-active-shadow);
}
.indexer-kind-btn strong { font-size: var(--type-control); }
.indexer-kind-btn em { font-style: normal; font-size: var(--type-micro); color: var(--text-muted); }
.indexer-kind-hint {
  margin: -6px 0 0;
  color: var(--text-muted);
  font-size: var(--type-caption);
  line-height: 1.6;
}

.indexer-fields { display: flex; flex-direction: column; gap: 16px; }
.indexer-row { display: flex; flex-direction: column; gap: 6px; }
.indexer-row--split {
  flex-direction: row;
  gap: 16px;
  flex-wrap: wrap;
}
.indexer-mini { display: flex; flex-direction: column; gap: 6px; flex: 1 1 160px; }
.indexer-label { font-size: var(--type-control); font-weight: 650; color: var(--text-primary); }
.indexer-note { font-size: var(--type-caption); color: var(--text-muted); line-height: 1.55; }
.indexer-number { display: inline-flex; align-items: center; gap: 8px; }
.indexer-number .input { max-width: 120px; }
.indexer-unit { font-size: var(--type-caption); color: var(--text-muted); }

.input-password-wrap { position: relative; display: block; }
.input-password-wrap .input { width: 100%; padding-right: 40px; }
.input-eye-btn {
  position: absolute;
  top: 50%;
  right: 8px;
  transform: translateY(-50%);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border: none;
  background: transparent;
  color: var(--text-muted);
  cursor: pointer;
}
.input-eye-btn:hover { color: var(--text-primary); }

.indexer-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  border-top: 1px solid var(--hairline);
  padding-top: 16px;
}
.indexer-status { color: var(--text-secondary); font-size: var(--type-caption); }

@media (max-width: 640px) {
  .indexer-kind { grid-template-columns: 1fr; }
  .indexer-actions { flex-direction: column; align-items: stretch; }
}
</style>
