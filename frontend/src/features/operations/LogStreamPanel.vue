<template>
  <div class="logs">
    <!-- 控制条：筛选 + 搜索 + 动作，统计与分页窗口并入一条 meta，不再单列玻璃小卡 -->
    <div class="logs-bar">
      <div class="logs-bar-controls">
        <GlassSelect
          v-model="filterLevel"
          :options="levelOptions"
          aria-label="日志等级"
          @change="loadLogs"
        />
        <input v-model="searchText" class="logs-search" placeholder="搜索日志内容" @keyup.enter="loadLogs" />
        <button class="btn btn-primary btn-sm" type="button" @click="loadLogs">搜索</button>
        <span class="logs-bar-spacer"></span>
        <button class="btn btn-ghost btn-sm logs-danger" type="button" @click="clearLogs">清空</button>
        <RefreshButton :loading="loading" @click="loadLogs" />
      </div>

      <div class="logs-meta">
        <div class="logs-counts" aria-label="日志等级汇总">
          <span class="logs-count"><strong>{{ countFor('INFO') }}</strong> INFO</span>
          <span class="logs-count is-warn"><strong>{{ countFor('WARNING') }}</strong> WARNING</span>
          <span class="logs-count is-bad"><strong>{{ countFor('ERROR') }}</strong> ERROR</span>
        </div>
        <div class="logs-window">{{ logWindowSummary }}</div>
      </div>

      <div v-if="activeLogFilters.length" class="logs-filters" aria-label="当前日志筛选">
        <span v-for="filter in activeLogFilters" :key="filter.key" class="logs-filter-chip">{{ filter.label }}</span>
        <button class="logs-filter-clear" type="button" :disabled="!hasActiveLogFilters" @click="clearLogFilters">清除筛选</button>
      </div>
    </div>

    <div class="logs-table" role="table" aria-label="运行日志">
      <div class="logs-head" role="row">
        <span role="columnheader">时间</span>
        <span role="columnheader">等级</span>
        <span role="columnheader">消息</span>
      </div>
      <AppleSkeleton
        v-if="loading && !logs.length"
        class="logs-state"
        variant="list"
        :items="6"
        label="日志加载中"
      />
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
      <div v-else :class="{ 'is-loading-more': loading }" class="logs-rows" role="rowgroup">
        <div
          v-for="log in logs"
          :key="log.id"
          :class="'logs-row is-' + toneFor(log.level)"
          role="row"
        >
          <span class="logs-row-time" role="cell">{{ formatTime(log.created_at) }}</span>
          <span class="logs-row-level" role="cell">{{ log.level }}</span>
          <span class="logs-row-msg" role="cell">{{ log.message }}</span>
        </div>
      </div>
    </div>

    <div v-if="hasMoreLogs" class="logs-more">
      <button class="btn btn-ghost btn-sm" type="button" :disabled="loading" @click="loadMore">加载更多</button>
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
import RefreshButton from '../../components/RefreshButton.vue'

export default {
  name: 'LogStreamPanel',
  components: { GlassSelect, AppleSkeleton, AppleEmptyState, AppleErrorState, RefreshButton },
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
    countFor(level) {
      return this.logs.filter(log => String(log.level || '').toUpperCase() === level).length
    },
    toneFor(level) {
      const upper = String(level || '').toUpperCase()
      if (upper === 'ERROR') return 'bad'
      if (upper === 'WARNING') return 'warn'
      return 'info'
    },
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
  display: flex;
  flex-direction: column;
  gap: 16px;
  color: var(--text-primary);
}

/* ---- control bar: filter + search + actions, stats folded into one meta line ---- */
.logs-bar {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 16px 20px;
  border-radius: var(--radius-card);
  background: var(--card);
  border: 1px solid var(--hairline);
}

.logs-bar-controls {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.logs-bar-spacer { flex: 1 1 auto; }
.logs .glass-select { width: 128px; }

.logs-search {
  flex: 1 1 220px;
  min-width: 160px;
  max-width: 360px;
  min-height: 32px;
  padding: 0 12px;
  border: 1px solid var(--hairline);
  border-radius: var(--radius-sm);
  background: var(--surface-card);
  color: var(--text-primary);
  font: inherit;
  font-size: var(--type-callout);
  outline: none;
}
.logs-search::placeholder { color: var(--text-muted); }
.logs-search:focus { border-color: var(--accent); }

.logs-danger { color: var(--bad); }

/* meta line: level counts + result window, divided by a hairline */
.logs-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
  padding-top: 12px;
  border-top: 1px solid var(--hairline);
}

.logs-counts { display: flex; gap: 20px; flex-wrap: wrap; }

.logs-count {
  display: inline-flex;
  align-items: baseline;
  gap: 8px;
  font-size: var(--type-caption);
  color: var(--text-muted);
}

.logs-count strong {
  font-family: var(--font-mono);
  font-size: var(--type-callout);
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  color: var(--text-secondary);
}

.logs-count.is-warn strong { color: var(--warn); }
.logs-count.is-bad strong { color: var(--bad); }

.logs-window {
  font-family: var(--font-mono);
  font-size: var(--type-caption);
  font-variant-numeric: tabular-nums;
  color: var(--text-muted);
}

.logs-filters {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  padding-top: 12px;
  border-top: 1px solid var(--hairline);
}

.logs-filter-chip {
  display: inline-flex;
  align-items: center;
  padding: 4px 8px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--hairline);
  background: var(--surface-card);
  color: var(--text-secondary);
  font-family: var(--font-mono);
  font-size: var(--type-micro);
  font-variant-numeric: tabular-nums;
}

.logs-filter-clear {
  padding: 4px 8px;
  border: none;
  background: none;
  color: var(--accent);
  font-size: var(--type-caption);
  font-weight: 550;
  cursor: pointer;
}
.logs-filter-clear:hover:not(:disabled) { text-decoration: underline; }
.logs-filter-clear:disabled { opacity: 0.45; cursor: not-allowed; }

/* ---- table ---- */
.logs-table {
  border-radius: var(--radius-sheet);
  background: var(--card);
  border: 1px solid var(--hairline);
  overflow: hidden;
}

.logs-head {
  position: sticky;
  top: 0;
  z-index: 1;
  display: grid;
  grid-template-columns: 168px 72px minmax(0, 1fr);
  gap: 12px;
  padding: 12px 16px;
  border-bottom: 1px solid var(--hairline);
  background: var(--card);
  color: var(--text-muted);
  font-size: var(--type-micro);
  font-weight: 650;
  letter-spacing: 0.2px;
}

.logs-rows { max-height: 560px; overflow-y: auto; }
.logs-rows.is-loading-more { position: relative; padding-bottom: 32px; }
.logs-rows.is-loading-more::after {
  content: "加载下一页…";
  position: sticky;
  bottom: 0;
  display: flex;
  align-items: center;
  min-height: 28px;
  padding: 0 16px;
  border-top: 1px solid var(--hairline);
  background: var(--card);
  color: var(--text-muted);
  font-family: var(--font-mono);
  font-size: var(--type-micro);
}

.logs-row {
  position: relative;
  display: grid;
  grid-template-columns: 168px 72px minmax(0, 1fr);
  gap: 12px;
  align-items: center;
  min-height: 32px;
  padding: 8px 16px;
  border-bottom: 1px solid var(--hairline);
  font-family: var(--font-mono);
  font-size: var(--type-caption);
  min-width: 0;
}
.logs-row:last-child { border-bottom: none; }

/* level shown via a thin left bar + colored level word; rows stay neutral (no full-row tint) */
.logs-row::before {
  content: "";
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 2px;
  background: transparent;
}
.logs-row.is-warn::before { background: var(--warn); }
.logs-row.is-bad::before { background: var(--bad); }
.logs-row:hover { background: var(--surface-card); }

.logs-row-time { color: var(--text-muted); font-variant-numeric: tabular-nums; }

.logs-row-level {
  font-size: var(--type-micro);
  font-weight: 700;
  letter-spacing: 0.3px;
  color: var(--text-muted);
}
.logs-row.is-warn .logs-row-level { color: var(--warn); }
.logs-row.is-bad .logs-row-level { color: var(--bad); }

.logs-row-msg { min-width: 0; color: var(--text-secondary); word-break: break-word; }

/* ---- async states ---- */
.logs-state { max-width: none; margin: 0; padding: 16px; border-radius: 0; box-shadow: none; }
.logs-state:deep(.apple-skeleton-row) { min-height: 32px; border-radius: var(--radius-sm); }
.logs-state:deep(.apple-state-copy) { text-align: left; }

.logs-more { text-align: center; }

@media (max-width: 768px) {
  .logs-bar-controls {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    align-items: stretch;
  }
  .logs .glass-select,
  .logs-search,
  .logs-bar-controls .btn {
    width: 100%;
    max-width: none;
  }
  .logs-search { grid-column: 1 / -1; min-height: 40px; }
  .logs-bar-spacer { display: none; }

  .logs-head { display: none; }

  .logs-row {
    grid-template-columns: 1fr auto;
    gap: 4px 12px;
    padding-left: 12px;
  }
  .logs-row-time { grid-column: 1; }
  .logs-row-level { grid-column: 2; text-align: right; }
  .logs-row-msg { grid-column: 1 / -1; }
}
</style>
