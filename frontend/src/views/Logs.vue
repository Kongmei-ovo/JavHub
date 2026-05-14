<template>
  <div class="logs page-shell page-shell--standard">
    <h1>日志查看</h1>

    <div class="toolbar">
      <GlassSelect
        v-model="filterLevel"
        :options="levelOptions"
        aria-label="日志等级"
        @change="loadLogs"
      />
      <input v-model="searchText" placeholder="搜索日志内容" @keyup.enter="loadLogs" />
      <button class="toolbar-btn primary" type="button" @click="loadLogs">刷新</button>
      <button class="toolbar-btn danger" type="button" @click="clearLogs">清空</button>
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
      <button @click="loadMore" :disabled="logs.length >= total">加载更多</button>
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
      limit: 100
    }
  },
  mounted() {
    this.loadLogs()
  },
  methods: {
    async loadLogs() {
      this.loading = true
      try {
        const resp = await api.getLogs(this.limit, this.filterLevel)
        this.logs = resp.data
        this.total = this.logs.length
      } catch (e) {
        console.error('Failed to load logs:', e)
      } finally {
        this.loading = false
      }
    },
    async loadMore() {
      this.limit += 100
      await this.loadLogs()
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
.logs h1 { margin: 0; font-size: var(--type-page-title); line-height: 1.2; letter-spacing: 0; }
.toolbar { margin: 20px 0; display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }
.toolbar .glass-select { width: 132px; }
.toolbar input {
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
.toolbar input:focus {
  border-color: var(--border-light);
  background: var(--bg-card-hover);
  box-shadow: 0 0 0 3px rgba(var(--accent-rgb), 0.08);
}
.toolbar input { flex: 1; min-width: 180px; max-width: 300px; }
.toolbar-btn {
  min-height: 44px;
  min-width: 82px;
  padding: 0 18px;
  border: 1px solid var(--border);
  border-radius: 14px;
  cursor: pointer;
  font: inherit;
  font-weight: 700;
  transition: background var(--motion-fast), border-color var(--motion-fast), color var(--motion-fast), transform var(--motion-fast);
}
.toolbar-btn:hover {
  transform: translateY(-1px);
}
.toolbar-btn.primary {
  background: var(--accent);
  border-color: var(--accent);
  color: var(--text-on-accent);
}
.toolbar-btn.danger {
  background: rgba(255, 55, 95, 0.1);
  border-color: rgba(255, 55, 95, 0.28);
  color: #FF375F;
}
.toolbar-btn.danger:hover {
  background: rgba(255, 55, 95, 0.16);
  border-color: rgba(255, 55, 95, 0.42);
}
.logs-container { background: var(--bg-card); border: 1px solid var(--border); border-radius: var(--radius-md); box-shadow: var(--shadow-card); overflow: hidden; }
.log-list { max-height: 500px; overflow-y: auto; }
.log-item { display: flex; padding: 10px 15px; border-bottom: 1px solid var(--border); font-family: monospace; font-size: var(--type-control); min-width: 0; }
.log-item:last-child { border-bottom: none; }
.log-time { color: var(--text-muted); width: 160px; flex-shrink: 0; }
.log-level { width: 70px; flex-shrink: 0; font-weight: bold; }
.level-info { color: var(--text-secondary); }
.level-warning { color: #ff9800; }
.level-error { color: #f44336; }
.log-message { flex: 1; word-break: break-all; }
.loading, .empty { padding: 40px; text-align: center; color: var(--text-secondary); }
.pagination { margin-top: 20px; text-align: center; }
.pagination button {
  min-height: 44px;
  padding: 0 30px;
  background: var(--accent-bg);
  color: var(--text-primary);
  border: 1px solid var(--border);
  border-radius: 14px;
  cursor: pointer;
  font-weight: 700;
}
.pagination button:hover:not(:disabled) {
  background: var(--bg-card-hover);
  border-color: var(--border-light);
}
.pagination button:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

@media (max-width: 768px) {
  .toolbar {
    align-items: stretch;
  }

  .toolbar .glass-select,
  .toolbar input,
  .toolbar button {
    width: 100%;
    max-width: none;
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
