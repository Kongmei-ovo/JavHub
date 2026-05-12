<template>
  <div class="logs">
    <h1>日志查看</h1>

    <div class="toolbar">
      <select v-model="filterLevel" @change="loadLogs">
        <option value="">全部</option>
        <option value="INFO">INFO</option>
        <option value="WARNING">WARNING</option>
        <option value="ERROR">ERROR</option>
      </select>
      <input v-model="searchText" placeholder="搜索日志内容" @keyup.enter="loadLogs" />
      <button @click="loadLogs">刷新</button>
      <button class="danger" @click="clearLogs">清空</button>
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

export default {
  name: 'Logs',
  data() {
    return {
      logs: [],
      loading: false,
      filterLevel: '',
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
  max-width: 1180px;
  margin: 0 auto;
  padding: 24px;
  color: var(--text-primary);
}
.logs h1 { margin: 0; font-size: 28px; line-height: 1.2; }
.toolbar { margin: 20px 0; display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }
.toolbar select, .toolbar input {
  min-height: 44px;
  padding: 0 12px;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  background: var(--bg-card);
  color: var(--text-primary);
}
.toolbar input { flex: 1; min-width: 180px; max-width: 300px; }
.toolbar button { min-height: 44px; padding: 0 18px; border: none; border-radius: 999px; cursor: pointer; background: #4CAF50; color: white; font-weight: 700; }
.toolbar button.danger { background: #f44336; }
.logs-container { background: var(--bg-card); border: 1px solid var(--border); border-radius: var(--radius-md); box-shadow: 0 2px 4px rgba(0,0,0,0.1); overflow: hidden; }
.log-list { max-height: 500px; overflow-y: auto; }
.log-item { display: flex; padding: 10px 15px; border-bottom: 1px solid var(--border); font-family: monospace; font-size: 13px; min-width: 0; }
.log-item:last-child { border-bottom: none; }
.log-time { color: var(--text-muted); width: 160px; flex-shrink: 0; }
.log-level { width: 70px; flex-shrink: 0; font-weight: bold; }
.level-info { color: #2196f3; }
.level-warning { color: #ff9800; }
.level-error { color: #f44336; }
.log-message { flex: 1; word-break: break-all; }
.loading, .empty { padding: 40px; text-align: center; color: var(--text-secondary); }
.pagination { margin-top: 20px; text-align: center; }
.pagination button { min-height: 44px; padding: 0 30px; background: #4CAF50; color: white; border: none; border-radius: 999px; cursor: pointer; font-weight: 700; }

@media (max-width: 768px) {
  .logs {
    padding: 20px 16px 40px;
  }

  .toolbar {
    align-items: stretch;
  }

  .toolbar select,
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
