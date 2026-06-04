<template>
  <div class="logs page-shell page-shell--standard">
    <div class="activity-header">
      <div>
        <h1>运行日志</h1>
        <p>{{ logSummary }}</p>
      </div>
      <button class="toolbar-btn primary" type="button" @click="loadLogs">刷新</button>
    </div>

    <div class="toolbar">
      <GlassSelect
        v-model="filterLevel"
        :options="levelOptions"
        aria-label="日志等级"
        @change="loadLogs"
      />
      <input v-model="searchText" placeholder="搜索日志内容" @keyup.enter="loadLogs" />
      <button class="toolbar-btn primary" type="button" @click="loadLogs">搜索</button>
      <button class="toolbar-btn danger" type="button" @click="clearLogs">清空</button>
    </div>

    <div class="activity-summary-strip" aria-label="日志等级汇总">
      <div v-for="item in levelSummary" :key="item.level">
        <strong>{{ item.count }}</strong>
        <span>{{ item.level }}</span>
      </div>
    </div>

    <div class="logs-container">
      <div v-if="loading" class="loading">加载中...</div>
      <div v-else-if="logs.length === 0" class="empty">暂无日志</div>
      <div v-else class="log-list">
        <div
          v-for="log in logs"
          :key="log.id"
          :class="'log-item level-' + log.level.toLowerCase()"
        >
          <span class="log-time">{{ formatTime(log.created_at) }}</span>
          <span :class="'log-level level-' + log.level.toLowerCase()">{{ log.level }}</span>
          <span class="log-message">{{ log.message }}</span>
        </div>
      </div>
    </div>

    <div class="pagination">
      <button @click="loadMore" :disabled="!hasMoreLogs || loading">加载更多</button>
    </div>
  </div>
</template>

<script>
import api from '../api'
import { requestConfirm } from '../utils/confirmDialog'
import GlassSelect from '../components/GlassSelect.vue'

export default {
  name: 'Logs',
  components: { GlassSelect },
  data() {
    return {
      logs: [],
      loading: false,
      filterLevel: '',
      levelOptions: [
        { value: '', label: '全部' },
        { value: 'INFO', label: 'INFO' },
        { value: 'WARNING', label: 'WARNING' },
        { value: 'ERROR', label: 'ERROR' },
      ],
      searchText: '',
      total: 0,
      limit: 100,
      offset: 0
    }
  },
  computed: {
    levelSummary() {
      return ['INFO', 'WARNING', 'ERROR'].map(level => ({
        level,
        count: this.logs.filter(log => String(log.level || '').toUpperCase() === level).length,
      }))
    },
    logSummary() {
      const levelLabel = this.filterLevel || '全部等级'
      const searchLabel = this.searchText.trim() ? ` · 关键词：${this.searchText.trim()}` : ''
      return `显示 ${this.logs.length} 条日志 · ${levelLabel}${searchLabel} · 可按等级和关键词筛选`
    },
    hasMoreLogs() {
      return this.logs.length < this.total
    },
  },
  mounted() {
    this.loadLogs()
  },
  methods: {
    async loadLogs({ append = false } = {}) {
      this.loading = true
      if (!append) {
        this.offset = 0
      }
      try {
        const resp = await api.getLogs(this.limit, this.filterLevel, { q: this.searchText, offset: this.offset })
        const payload = resp.data || {}
        const rows = Array.isArray(payload) ? payload : (payload.data || [])
        this.logs = append ? [...this.logs, ...rows] : rows
        this.total = Number(payload.total ?? this.logs.length) || this.logs.length
        this.offset = this.logs.length
      } catch (e) {
        console.error('Failed to load logs:', e)
      } finally {
        this.loading = false
      }
    },
    async loadMore() {
      if (!this.hasMoreLogs || this.loading) return
      await this.loadLogs({ append: true })
    },
    async clearLogs() {
      const confirmed = await requestConfirm({
        title: '清空日志',
        message: '确定清空所有日志？',
        details: '这个操作会删除当前记录的日志列表。',
        confirmText: '清空',
        tone: 'danger'
      })
      if (!confirmed) return
      try {
        await api.clearLogs()
        this.logs = []
        this.total = 0
        this.offset = 0
      } catch (e) {
        console.error('Failed to clear logs:', e)
      }
    },
    formatTime(timeStr) {
      if (!timeStr) return ''
      const d = new Date(timeStr)
      return d.toLocaleString('zh-CN')
    }
  }
}
</script>

<style scoped>
.logs {
  color: var(--text-primary);
}

.activity-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 14px;
}

.logs h1 { margin: 0; font-size: var(--type-page-title); line-height: 1.2; letter-spacing: 0; }
.activity-header p { margin: 6px 0 0; color: var(--text-secondary); font-size: var(--type-control); }
.toolbar { margin: 20px 0; display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }
.toolbar .glass-select { width: 132px; }
.toolbar input {
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
  transition: background var(--motion-fast), border-color var(--motion-fast), box-shadow var(--motion-fast);
}
.toolbar input:focus {
  border-color: var(--glass-active-border);
  background: var(--surface-specular-edge-strong), var(--surface-noise), var(--glass-active-material);
  box-shadow: var(--glass-active-shadow);
}
.toolbar input { flex: 1; min-width: 180px; max-width: 300px; }
.toolbar-btn {
  min-height: 44px;
  min-width: 82px;
  padding: 0 18px;
  border: 1px solid var(--glass-control-border);
  border-radius: 14px;
  background: var(--surface-specular-edge), var(--surface-noise), var(--material-glass-control);
  color: var(--text-primary);
  cursor: pointer;
  font: inherit;
  font-weight: 700;
  box-shadow: var(--glass-control-shadow);
  backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
  -webkit-backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
  transition: transform var(--motion-fast), background var(--motion-fast), border-color var(--motion-fast), box-shadow var(--motion-fast), color var(--motion-fast), opacity var(--motion-fast);
}
.toolbar-btn:hover:not(:disabled) {
  background: var(--surface-specular-edge-strong), var(--surface-noise), var(--material-glass-control-hover);
  border-color: var(--glass-control-border-hover);
  box-shadow: var(--glass-control-shadow-hover);
  transform: translateY(-1px);
}
.toolbar-btn.primary {
  background: var(--surface-specular-edge-strong), var(--surface-noise), var(--glass-active-material);
  border-color: var(--glass-active-border);
  color: var(--text-primary);
  box-shadow: var(--glass-active-shadow);
}
.toolbar-btn.danger {
  background: var(--badge-error-bg);
  border-color: var(--badge-error-border);
  color: var(--badge-error-text);
  box-shadow: var(--glass-control-shadow);
}
.toolbar-btn.danger:hover:not(:disabled) {
  background: var(--badge-error-bg);
  border-color: var(--badge-error-border);
  box-shadow: var(--glass-control-shadow-hover);
}

.activity-summary-strip {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
  margin-bottom: 14px;
}

.activity-summary-strip > div {
  min-width: 0;
  padding: 10px 12px;
  border: 1px solid var(--glass-control-border);
  border-radius: var(--radius-md);
  background: var(--surface-specular-edge), var(--surface-noise), var(--material-glass-control);
  box-shadow: var(--glass-surface-shadow);
  backdrop-filter: blur(var(--glass-blur-surface)) saturate(var(--glass-saturate-surface));
  -webkit-backdrop-filter: blur(var(--glass-blur-surface)) saturate(var(--glass-saturate-surface));
}

.activity-summary-strip strong {
  display: block;
  font-family: var(--font-mono);
  font-size: 18px;
}

.activity-summary-strip span {
  display: block;
  margin-top: 3px;
  color: var(--text-secondary);
  font-size: 12px;
}

.logs-container {
  background: var(--surface-specular-edge-strong), var(--surface-noise), var(--material-glass-sheet);
  border: 1px solid var(--glass-control-border);
  border-radius: var(--radius-md);
  box-shadow: var(--glass-surface-shadow);
  backdrop-filter: blur(var(--glass-blur-surface)) saturate(var(--glass-saturate-surface));
  -webkit-backdrop-filter: blur(var(--glass-blur-surface)) saturate(var(--glass-saturate-surface));
  overflow: hidden;
}
.log-list { max-height: 500px; overflow-y: auto; }
.log-item { display: flex; padding: 10px 15px; border-bottom: 1px solid var(--glass-control-border); font-family: var(--font-mono); font-size: var(--type-control); min-width: 0; }
.log-item:last-child { border-bottom: none; }
.log-time { color: var(--text-muted); width: 160px; flex-shrink: 0; }
.log-level { width: 70px; flex-shrink: 0; font-weight: bold; }
.level-info { color: var(--text-secondary); }
.level-warning { color: var(--badge-warning-text); }
.level-error { color: var(--badge-error-text); }
.log-message { flex: 1; word-break: break-all; }
.loading,
.empty {
  margin: 12px;
  padding: 40px;
  text-align: center;
  color: var(--text-secondary);
  border: 1px solid var(--glass-control-border);
  border-radius: var(--radius-md);
  background:
    var(--surface-specular-edge),
    var(--surface-noise),
    var(--material-glass-subtle);
}
.pagination { margin-top: 20px; text-align: center; }
.pagination button {
  min-height: 44px;
  padding: 0 30px;
  background: var(--surface-specular-edge), var(--surface-noise), var(--material-glass-control);
  color: var(--text-primary);
  border: 1px solid var(--glass-control-border);
  border-radius: 14px;
  cursor: pointer;
  font-weight: 700;
  box-shadow: var(--glass-control-shadow);
  backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
  -webkit-backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
  transition: transform var(--motion-fast), background var(--motion-fast), border-color var(--motion-fast), box-shadow var(--motion-fast), opacity var(--motion-fast);
}
.pagination button:hover:not(:disabled) {
  background: var(--surface-specular-edge-strong), var(--surface-noise), var(--material-glass-control-hover);
  border-color: var(--glass-control-border-hover);
  box-shadow: var(--glass-control-shadow-hover);
  transform: translateY(-1px);
}
.pagination button:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

@media (max-width: 768px) {
  .activity-header {
    flex-direction: column;
  }

  .toolbar {
    align-items: stretch;
  }

  .toolbar .glass-select,
  .toolbar input,
  .toolbar button {
    width: 100%;
    max-width: none;
  }

  .activity-summary-strip {
    grid-template-columns: 1fr;
  }

  .log-item {
    display: grid;
    grid-template-columns: 1fr auto;
    gap: 4px 10px;
  }

  .log-time,
  .log-level {
    width: auto;
  }

  .log-message {
    grid-column: 1 / -1;
  }
}
</style>
