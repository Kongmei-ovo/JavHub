<template>
  <div class="logs">
    <div class="activity-header apple-surface">
      <div>
        <h1>运行日志</h1>
        <p>{{ logSummary }}</p>
      </div>
      <button class="toolbar-btn primary" type="button" @click="loadLogs">刷新</button>
    </div>

    <div class="logs-control-panel apple-surface">
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

      <div class="log-window-meta">{{ logWindowSummary }}</div>

      <div v-if="activeLogFilters.length" class="filter-ledger" aria-label="当前日志筛选">
        <span v-for="filter in activeLogFilters" :key="filter.key" class="filter-token">{{ filter.label }}</span>
        <button class="filter-reset" type="button" :disabled="!hasActiveLogFilters" @click="clearLogFilters">清除筛选</button>
      </div>
    </div>

    <div class="logs-container" role="table" aria-label="运行日志">
      <div class="log-table-head" role="row">
        <span role="columnheader">时间</span>
        <span role="columnheader">等级</span>
        <span role="columnheader">消息</span>
      </div>
      <template v-if="loading && !logs.length">
        <AppleSkeleton
          v-if="loading"
          class="logs-state"
          variant="list"
          :items="6"
          label="日志加载中"
        />
      </template>
      <AppleErrorState
        v-else-if="logsError"
        class="logs-state"
        title="日志加载失败"
        :description="logsError"
        next-step="检查后端日志接口或清除筛选条件后再试。"
        retry-label="重试"
        secondary-action-label="清除筛选"
        source-label="Logs API"
        details="limit · level · query"
        :retrying="loading"
        @retry="loadLogs"
        @secondary-action="clearLogFilters"
      />
      <AppleEmptyState
        v-else-if="logs.length === 0"
        class="logs-state"
        title="暂无日志"
        :description="emptyLogDescription"
        next-step="清除筛选后可以查看全部日志，也可以刷新等待新事件写入。"
        action-label="刷新日志"
        secondary-action-label="清除筛选"
        density="compact"
        @action="loadLogs"
        @secondary-action="clearLogFilters"
      />
      <div v-else :class="{ 'is-loading-more': loading }" class="log-list" role="rowgroup">
        <div
          v-for="log in logs"
          :key="log.id"
          :class="'log-item level-' + log.level.toLowerCase()"
          role="row"
        >
          <span class="log-time" role="cell">{{ formatTime(log.created_at) }}</span>
          <span :class="'log-level level-' + log.level.toLowerCase()" role="cell">{{ log.level }}</span>
          <span class="log-message" role="cell">{{ log.message }}</span>
        </div>
      </div>
    </div>

    <div class="pagination">
      <button @click="loadMore" :disabled="!hasMoreLogs || loading">加载更多</button>
    </div>
  </div>
</template>

<script>
import api from '../../api'
import { requestConfirm } from '../../utils/confirmDialog'
import GlassSelect from '../../components/GlassSelect.vue'
import AppleSkeleton from '../../components/AppleSkeleton.vue'
import AppleEmptyState from '../../components/AppleEmptyState.vue'
import AppleErrorState from '../../components/AppleErrorState.vue'

export default {
  name: 'LogStreamPanel',
  components: { GlassSelect, AppleSkeleton, AppleEmptyState, AppleErrorState },
  data() {
    return {
      logs: [],
      loading: false,
      logsError: '',
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
    hasActiveLogFilters() {
      return Boolean(this.filterLevel || this.searchText.trim())
    },
    activeLogFilters() {
      const filters = []
      if (this.filterLevel) {
        filters.push({ key: 'level', label: `level:${this.filterLevel}` })
      }
      const query = this.searchText.trim()
      if (query) {
        filters.push({ key: 'query', label: query })
      }
      return filters
    },
    logWindowSummary() {
      const start = this.logs.length ? Math.max(1, this.offset - this.logs.length + 1) : 0
      const end = this.logs.length ? this.offset : 0
      return `${start}-${end} / ${this.total}`
    },
    emptyLogDescription() {
      if (this.filterLevel || this.searchText.trim()) return '当前筛选条件下没有日志记录。'
      return '系统还没有写入运行日志。'
    },
  },
  mounted() {
    this.applyRouteFilters()
    this.loadLogs()
  },
  watch: {
    // 从总览「近期告警」卡跳进来时带 ?level=ERROR；面板被 keep-alive 时
    // mounted 不会重跑，靠这个 watch 重新套用筛选并刷新。
    '$route.query.level'() {
      if (this.applyRouteFilters()) this.loadLogs()
    },
  },
  methods: {
    applyRouteFilters() {
      const level = String(this.$route.query.level || '').toUpperCase()
      const q = this.$route.query.q != null ? String(this.$route.query.q) : ''
      let changed = false
      if (level && level !== this.filterLevel) { this.filterLevel = level; changed = true }
      if (q && q !== this.searchText) { this.searchText = q; changed = true }
      return changed
    },
    async loadLogs({ append = false } = {}) {
      this.loading = true
      this.logsError = ''
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
        this.logsError = e?.response?.data?.detail || e?.message || '请稍后重试。'
        if (!append) {
          this.logs = []
          this.total = 0
          this.offset = 0
        }
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
    clearLogFilters() {
      this.filterLevel = ''
      this.searchText = ''
      this.loadLogs()
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
  min-height: 72px;
  margin-bottom: 10px;
  padding: 12px;
  border: 1px solid var(--glass-edge);
  border-radius: var(--radius-lg);
  background: var(--card);
  box-shadow: var(--shadow-card);
}

.logs h1 { margin: 0; font-size: var(--type-workbench-title); line-height: 1.16; letter-spacing: 0; }
.activity-header p { margin: 6px 0 0; color: var(--text-secondary); font-size: var(--type-control); }
.logs-control-panel {
  display: grid;
  grid-template-columns: minmax(280px, 1fr) minmax(300px, 0.72fr) auto;
  gap: 10px;
  margin-bottom: 10px;
  padding: 10px;
  border: 1px solid var(--glass-edge);
  border-radius: var(--radius-lg);
  background: var(--card);
  box-shadow: var(--shadow-card);
}

.log-window-meta {
  align-self: stretch;
  display: flex;
  align-items: center;
  justify-content: center;
  min-width: 132px;
  padding: 8px 10px;
  border: 1px solid var(--glass-control-border);
  border-radius: var(--radius-md);
  background: var(--surface-specular-edge), var(--surface-noise), var(--material-glass-control);
  color: var(--text-secondary);
  font-family: var(--font-mono);
  font-size: var(--type-caption);
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
  box-shadow: var(--glass-control-shadow);
  backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
  -webkit-backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
}

.filter-ledger {
  grid-column: 1 / -1;
  display: flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
  padding-top: 8px;
  border-top: 1px solid var(--glass-control-border);
}

.filter-token,
.filter-reset {
  min-width: 0;
  min-height: 28px;
  padding: 5px 9px;
  border-radius: var(--radius-sm);
  white-space: nowrap;
}

.filter-token {
  display: inline-flex;
  align-items: center;
  overflow: hidden;
  border: 1px solid var(--hairline);
  background: var(--card);
  color: var(--text-secondary);
  font-family: var(--font-mono);
  font-size: var(--type-micro);
  font-variant-numeric: tabular-nums;
  text-overflow: ellipsis;
}

.filter-reset {
  border: 1px solid var(--glass-control-border);
  background: var(--surface-specular-edge), var(--surface-noise), var(--material-glass-control);
  color: var(--text-primary);
  cursor: pointer;
  font: inherit;
  font-size: var(--type-micro);
  box-shadow: var(--glass-control-shadow);
  transition: transform var(--motion-standard), opacity var(--motion-fast);
}

.filter-reset:hover:not(:disabled) {
  border-color: var(--glass-control-border-hover);
  background: var(--surface-specular-edge-strong), var(--surface-noise), var(--material-glass-control-hover);
  box-shadow: var(--glass-control-shadow-hover);
}

.filter-reset:focus-visible {
  outline: none;
  border-color: var(--glass-control-border-hover);
  background: var(--surface-specular-edge-strong), var(--surface-noise), var(--material-glass-control-hover);
  box-shadow: var(--glass-control-shadow-hover), var(--focus-ring);
}

.filter-reset:active:not(:disabled) {
  transform: scale(0.985);
}

.filter-reset:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}
.toolbar { margin: 0; display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }
.toolbar .glass-select { width: 132px; }
.toolbar input {
  min-height: 38px;
  padding: 0 12px;
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
.toolbar input:focus {
  border-color: var(--glass-active-border);
  background: var(--surface-specular-edge-strong), var(--surface-noise), var(--glass-active-material);
  box-shadow: var(--glass-active-shadow);
}
.toolbar input { flex: 1; min-width: 180px; max-width: 300px; }
.toolbar-btn {
  min-height: 38px;
  min-width: 82px;
  padding: 0 14px;
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
  transition: transform var(--motion-standard), opacity var(--motion-fast);
}
.toolbar-btn:hover:not(:disabled) {
  background: var(--surface-specular-edge-strong), var(--surface-noise), var(--material-glass-control-hover);
  border-color: var(--glass-control-border-hover);
  box-shadow: var(--glass-control-shadow-hover);
  transform: translateY(-1px);
}
.toolbar-btn:focus-visible:not(:disabled) {
  outline: none;
  background: var(--surface-specular-edge-strong), var(--surface-noise), var(--material-glass-control-hover);
  border-color: var(--glass-control-border-hover);
  box-shadow: var(--glass-control-shadow-hover), var(--focus-ring);
  transform: translateY(-1px);
}
.toolbar-btn.primary {
  background: var(--surface-specular-edge-strong), var(--surface-noise), var(--glass-active-material);
  border-color: var(--glass-active-border);
  color: var(--text-primary);
  box-shadow: var(--glass-active-shadow);
}
.toolbar-btn.danger {
  background: var(--surface-specular-edge), var(--surface-noise), var(--badge-error-bg);
  border-color: var(--badge-error-border);
  color: var(--badge-error-text);
  box-shadow: var(--glass-control-shadow);
}
.toolbar-btn.danger:hover:not(:disabled) {
  background: var(--surface-specular-edge-strong), var(--surface-noise), var(--badge-error-bg);
  border-color: var(--badge-error-border);
  box-shadow: var(--glass-control-shadow-hover);
}
.toolbar-btn.danger:focus-visible:not(:disabled) {
  outline: none;
  background: var(--surface-specular-edge-strong), var(--surface-noise), var(--badge-error-bg);
  border-color: var(--badge-error-border);
  box-shadow: var(--glass-control-shadow-hover), 0 0 0 3px color-mix(in srgb, var(--badge-error-text) 18%, transparent);
  transform: translateY(-1px);
}

.activity-summary-strip {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
  margin: 0;
}

.activity-summary-strip > div {
  min-width: 0;
  padding: 8px 10px;
  border: 1px solid var(--hairline);
  border-radius: var(--radius-md);
  background: var(--card);
  box-shadow: var(--shadow-card);
}

.activity-summary-strip strong {
  display: block;
  font-family: var(--font-mono);
  font-size: var(--type-panel-title);
}

.activity-summary-strip span {
  display: block;
  margin-top: 3px;
  color: var(--text-secondary);
  font-size: var(--type-caption);
}

.logs-container {
  background: var(--card);
  border: 1px solid var(--hairline);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-card);
  overflow: hidden;
}

.logs-state {
  max-width: none;
  margin: 0;
  padding: 12px;
  border-radius: 0;
  box-shadow: none;
}

.logs-state:deep(.apple-skeleton-row) {
  min-height: 34px;
  border-radius: var(--radius-sm);
}

.logs-state:deep(.apple-state-copy) {
  text-align: left;
}

.log-table-head {
  position: sticky;
  top: 0;
  z-index: 1;
  display: grid;
  grid-template-columns: 168px 76px minmax(0, 1fr);
  gap: 10px;
  padding: 8px 12px;
  border-bottom: 1px solid var(--hairline);
  background: var(--card-2);
  color: var(--text-muted);
  font-size: var(--type-micro);
  font-weight: 650;
  box-shadow: none;
}
.log-list { max-height: 500px; overflow-y: auto; }
.log-list.is-loading-more { position: relative; padding-bottom: 36px; }
.log-list.is-loading-more::after {
  content: "loading next page";
  position: sticky;
  bottom: 0;
  display: flex;
  align-items: center;
  min-height: 30px;
  padding: 0 12px;
  border-top: 1px solid var(--glass-control-border);
  background: var(--surface-specular-edge), var(--surface-noise), var(--material-glass-control);
  color: var(--text-muted);
  font-family: var(--font-mono);
  font-size: var(--type-micro);
  font-variant-numeric: tabular-nums;
}

.log-item {
  position: relative;
  display: grid;
  grid-template-columns: 168px 76px minmax(0, 1fr);
  gap: 10px;
  align-items: center;
  min-height: 34px;
  padding: 7px 12px;
  border-bottom: 1px solid var(--hairline);
  font-family: var(--font-mono);
  font-size: var(--type-control);
  min-width: 0;
  transition: transform var(--motion-standard), opacity var(--motion-fast);
}
.log-item::before {
  content: "";
  position: absolute;
  left: 6px;
  top: 8px;
  bottom: 8px;
  grid-row: 1;
  width: 2px;
  border-radius: 999px;
  background: var(--hairline-strong);
}
.log-item:hover {
  background: var(--card-hover);
  box-shadow: inset 2px 0 0 var(--glass-active-border);
}
.log-item:last-child { border-bottom: none; }
.log-time { color: var(--text-muted); font-variant-numeric: tabular-nums; }
.log-level {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 22px;
  padding: 0 7px;
  border: 1px solid var(--hairline);
  border-radius: var(--radius-xs);
  background: var(--card);
  font-weight: bold;
}
.log-level.level-info,
.level-info {
  background: var(--card);
  color: var(--text-secondary);
}
.log-level.level-warning,
.level-warning {
  border-color: var(--badge-warning-border);
  background: var(--surface-specular-edge), var(--surface-noise), var(--badge-warning-bg);
  color: var(--badge-warning-text);
}
.log-item.level-warning::before { background: var(--badge-warning-border); }
.log-level.level-error,
.level-error {
  border-color: var(--badge-error-border);
  background: var(--surface-specular-edge), var(--surface-noise), var(--badge-error-bg);
  color: var(--badge-error-text);
}
.log-item.level-error::before { background: var(--badge-error-border); }
.log-message { min-width: 0; word-break: break-all; }
.loading,
.empty {
  margin: 12px;
  padding: 40px;
  text-align: center;
  color: var(--text-secondary);
  border: 1px solid var(--hairline);
  border-radius: var(--radius-md);
  background: var(--card);
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
  transition: transform var(--motion-standard), opacity var(--motion-fast);
}
.pagination button:hover:not(:disabled) {
  background: var(--surface-specular-edge-strong), var(--surface-noise), var(--material-glass-control-hover);
  border-color: var(--glass-control-border-hover);
  box-shadow: var(--glass-control-shadow-hover);
  transform: translateY(-1px);
}
.pagination button:focus-visible:not(:disabled) {
  outline: none;
  background: var(--surface-specular-edge-strong), var(--surface-noise), var(--material-glass-control-hover);
  border-color: var(--glass-control-border-hover);
  box-shadow: var(--glass-control-shadow-hover), var(--focus-ring);
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

  .activity-header .toolbar-btn {
    min-height: 40px;
  }

  .toolbar {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    align-items: stretch;
  }

  .toolbar .glass-select,
  .toolbar input,
  .toolbar button {
    width: 100%;
    min-height: 40px;
    max-width: none;
  }

  .toolbar input {
    grid-column: 1 / -1;
  }

  .activity-summary-strip {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .activity-summary-strip > div {
    padding: 7px 8px;
  }

  .logs-control-panel {
    grid-template-columns: 1fr;
  }

  .log-window-meta {
    min-width: 0;
    overflow: hidden;
    text-align: left;
    text-overflow: ellipsis;
    justify-content: flex-start;
  }

  .filter-ledger {
    align-items: stretch;
    flex-direction: column;
  }

  .filter-token,
  .filter-reset {
    width: 100%;
  }

  .logs-state {
    padding: 10px;
  }

  .pagination {
    margin-top: 10px;
  }

  .pagination button {
    width: 100%;
    min-height: 40px;
  }

  .log-table-head {
    display: none;
  }

  .log-item {
    display: grid;
    grid-template-columns: 4px 1fr auto;
    gap: 4px 10px;
  }

  .log-time,
  .log-level {
    width: auto;
  }

  .log-message {
    grid-column: 2 / -1;
  }
}
</style>
