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
      if (!confirm('确定清空所有日志？')) return
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
.toolbar { margin: 20px 0; display: flex; gap: 10px; align-items: center; }
.toolbar select, .toolbar input { padding: 8px; border: 1px solid #ddd; border-radius: 4px; }
.toolbar input { flex: 1; max-width: 300px; }
.toolbar button { padding: 8px 16px; border: none; border-radius: 4px; cursor: pointer; background: #4CAF50; color: white; }
.toolbar button.danger { background: #f44336; }
.logs-container { background: white; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); overflow: hidden; }
.log-list { max-height: 500px; overflow-y: auto; }
.log-item { display: flex; padding: 10px 15px; border-bottom: 1px solid #eee; font-family: monospace; font-size: 13px; }
.log-item:last-child { border-bottom: none; }
.log-time { color: #999; width: 160px; flex-shrink: 0; }
.log-level { width: 70px; flex-shrink: 0; font-weight: bold; }
.level-info { color: #2196f3; }
.level-warning { color: #ff9800; }
.level-error { color: #f44336; }
.log-message { flex: 1; word-break: break-all; }
.loading, .empty { padding: 40px; text-align: center; color: #666; }
.pagination { margin-top: 20px; text-align: center; }
.pagination button { padding: 10px 30px; background: #4CAF50; color: white; border: none; border-radius: 4px; cursor: pointer; }
</style>
