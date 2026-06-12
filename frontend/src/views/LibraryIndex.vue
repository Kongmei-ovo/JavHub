<template>
  <div class="library-index page-shell page-shell--workspace">
    <div class="page-header">
      <div class="header-left">
        <h1>云盘索引</h1>
        <p class="header-subtitle">
          <span>{{ summary.total_files }} 个文件</span>
          <span v-if="summary.matched"> · {{ summary.matched }} 已匹配</span>
          <span v-if="summary.unmatched" class="warn-hint"> · {{ summary.unmatched }} 待匹配</span>
        </p>
      </div>
      <div class="header-actions">
        <button class="btn btn-ghost" type="button" :disabled="scanRunning" @click="refresh">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="16" height="16"><polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 11-2.12-9.36L23 10"/></svg>
          刷新
        </button>
        <button class="btn btn-primary" type="button" :disabled="scanRunning" @click="startScan">
          <span v-if="scanRunning" class="spinner"></span>
          <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="16" height="16"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/></svg>
          {{ scanRunning ? '扫描中…' : '全量扫描' }}
        </button>
      </div>
    </div>

    <!-- 摘要卡 -->
    <div class="li-stats">
      <div class="li-stat">
        <span class="li-stat__label">文件总数</span>
        <span class="li-stat__num">{{ summary.total_files }}</span>
      </div>
      <div class="li-stat">
        <span class="li-stat__label">已匹配</span>
        <span class="li-stat__num">{{ summary.matched }}</span>
      </div>
      <div class="li-stat" :class="{ 'li-stat--warn': summary.unmatched > 0 }">
        <span class="li-stat__label">待匹配</span>
        <span class="li-stat__num">{{ summary.unmatched }}</span>
      </div>
      <div class="li-stat">
        <span class="li-stat__label">库内番号</span>
        <span class="li-stat__num">{{ summary.distinct_titles }}</span>
      </div>
      <div class="li-stat">
        <span class="li-stat__label">最近扫描</span>
        <span class="li-stat__text">{{ latestScanText }}</span>
      </div>
    </div>

    <!-- 未匹配文件 -->
    <section class="li-section">
      <header class="li-section__head">
        <h2>待匹配文件</h2>
        <span v-if="unmatchedTotal" class="li-section__count">{{ unmatchedTotal }} 个</span>
      </header>

      <div v-if="unmatchedLoading" class="li-empty">加载中…</div>
      <div v-else-if="!unmatchedFiles.length" class="li-empty">没有待匹配的文件 🎉</div>
      <div v-else class="li-table-wrap">
        <table class="li-table">
          <thead>
            <tr>
              <th>文件名</th>
              <th>路径</th>
              <th class="num">大小</th>
              <th style="width: 280px">番号</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="file in unmatchedFiles" :key="file.id">
              <td class="mono" :title="file.name">{{ file.name }}</td>
              <td class="dim" :title="file.path">{{ shortPath(file.path) }}</td>
              <td class="num dim">{{ formatSize(file.size) }}</td>
              <td>
                <div class="li-match-row">
                  <input
                    v-model="matchDrafts[file.id]"
                    class="li-input"
                    type="text"
                    placeholder="ABC-123"
                    spellcheck="false"
                    @keyup.enter="matchFile(file)"
                  />
                  <button
                    class="btn btn-primary btn-sm"
                    type="button"
                    :disabled="!String(matchDrafts[file.id] || '').trim() || busyIds.has(file.id)"
                    @click="matchFile(file)"
                  >匹配</button>
                  <button
                    class="btn btn-ghost btn-sm"
                    type="button"
                    :disabled="busyIds.has(file.id)"
                    @click="ignoreFile(file)"
                  >忽略</button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
        <div v-if="unmatchedTotal > unmatchedFiles.length" class="li-more">
          <button class="btn btn-ghost" type="button" :disabled="unmatchedLoading" @click="loadMore">
            加载更多（{{ unmatchedFiles.length }} / {{ unmatchedTotal }}）
          </button>
        </div>
      </div>
    </section>
  </div>
</template>

<script>
import api, { formatApiError } from '../api'
import { ElMessage } from '../utils/message.js'

const PAGE_SIZE = 50

export default {
  name: 'LibraryIndex',
  data() {
    return {
      summary: { total_files: 0, matched: 0, unmatched: 0, ignored: 0, distinct_titles: 0 },
      latestScan: null,
      scanRunning: false,
      unmatchedFiles: [],
      unmatchedTotal: 0,
      unmatchedPage: 1,
      unmatchedLoading: false,
      matchDrafts: {},
      busyIds: new Set(),
      pollTimer: null,
    }
  },
  computed: {
    latestScanText() {
      if (!this.latestScan) return '从未'
      const status = { running: '进行中', done: '完成', failed: '失败' }[this.latestScan.status] || this.latestScan.status
      const time = this.latestScan.finished_at || this.latestScan.started_at || ''
      const short = String(time).replace('T', ' ').slice(0, 16)
      return `${status} ${short}`
    },
  },
  mounted() {
    this.refresh()
  },
  beforeUnmount() {
    this.stopPolling()
  },
  methods: {
    async refresh() {
      await Promise.allSettled([this.loadSummary(), this.loadScanStatus(), this.loadUnmatched(true)])
    },
    async loadSummary() {
      try {
        const res = await api.getLibrarySummary()
        this.summary = res.data
      } catch (e) {}
    },
    async loadScanStatus() {
      try {
        const res = await api.getLibraryScanStatus()
        this.scanRunning = !!res.data.running
        this.latestScan = res.data.latest
        if (this.scanRunning) this.startPolling()
        else this.stopPolling()
      } catch (e) {}
    },
    async loadUnmatched(reset = false) {
      if (reset) {
        this.unmatchedPage = 1
        this.unmatchedFiles = []
      }
      this.unmatchedLoading = true
      try {
        const res = await api.getLibraryFiles({ status: 'unmatched', page: this.unmatchedPage, page_size: PAGE_SIZE })
        const items = res.data.items || []
        this.unmatchedFiles = reset ? items : [...this.unmatchedFiles, ...items]
        this.unmatchedTotal = res.data.total || 0
        for (const file of items) {
          if (this.matchDrafts[file.id] === undefined) {
            this.matchDrafts[file.id] = file.guessed_code || ''
          }
        }
      } catch (err) {
        ElMessage.error(formatApiError(err, { service: '云盘索引', action: '加载', fallback: '加载未匹配文件失败' }).message)
      } finally {
        this.unmatchedLoading = false
      }
    },
    loadMore() {
      this.unmatchedPage += 1
      this.loadUnmatched()
    },
    async startScan() {
      try {
        await api.triggerLibraryScan({ mode: 'full' })
        ElMessage.success('扫描已开始')
        this.scanRunning = true
        this.startPolling()
      } catch (err) {
        ElMessage.error(formatApiError(err, { service: '云盘索引', action: '扫描', fallback: '触发扫描失败' }).message)
      }
    },
    startPolling() {
      if (this.pollTimer) return
      this.pollTimer = setInterval(async () => {
        await this.loadScanStatus()
        if (!this.scanRunning) {
          this.stopPolling()
          await Promise.allSettled([this.loadSummary(), this.loadUnmatched(true)])
          ElMessage.success('扫描完成')
        }
      }, 3000)
    },
    stopPolling() {
      if (this.pollTimer) {
        clearInterval(this.pollTimer)
        this.pollTimer = null
      }
    },
    async matchFile(file) {
      const code = String(this.matchDrafts[file.id] || '').trim()
      if (!code) return
      this.busyIds.add(file.id)
      this.busyIds = new Set(this.busyIds)
      try {
        const res = await api.matchLibraryFile(file.id, code)
        if (res.data.metadata_found === false) {
          ElMessage.warning(`已匹配 ${res.data.content_id}，但元数据库暂无此番号`)
        } else {
          ElMessage.success(`已匹配 ${res.data.content_id}`)
        }
        this.unmatchedFiles = this.unmatchedFiles.filter(f => f.id !== file.id)
        this.unmatchedTotal = Math.max(this.unmatchedTotal - 1, 0)
        this.loadSummary()
      } catch (err) {
        ElMessage.error(formatApiError(err, { service: '云盘索引', action: '匹配', fallback: '匹配失败' }).message)
      } finally {
        this.busyIds.delete(file.id)
        this.busyIds = new Set(this.busyIds)
      }
    },
    async ignoreFile(file) {
      this.busyIds.add(file.id)
      this.busyIds = new Set(this.busyIds)
      try {
        await api.ignoreLibraryFile(file.id)
        this.unmatchedFiles = this.unmatchedFiles.filter(f => f.id !== file.id)
        this.unmatchedTotal = Math.max(this.unmatchedTotal - 1, 0)
        this.loadSummary()
      } catch (err) {
        ElMessage.error(formatApiError(err, { service: '云盘索引', action: '忽略', fallback: '操作失败' }).message)
      } finally {
        this.busyIds.delete(file.id)
        this.busyIds = new Set(this.busyIds)
      }
    },
    shortPath(path) {
      const parts = String(path || '').split('/')
      return parts.length > 3 ? `…/${parts.slice(-3, -1).join('/')}` : path
    },
    formatSize(bytes) {
      const size = Number(bytes || 0)
      if (size >= 1 << 30) return `${(size / (1 << 30)).toFixed(1)} GB`
      if (size >= 1 << 20) return `${(size / (1 << 20)).toFixed(0)} MB`
      if (size > 0) return `${(size / 1024).toFixed(0)} KB`
      return '-'
    },
  },
}
</script>

<style scoped>
.warn-hint { color: var(--badge-warning-text); }

.li-stats {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: var(--space-3);
  margin-bottom: var(--space-6);
}
.li-stat {
  padding: var(--space-4);
  border-radius: var(--radius-lg);
  border: 1px solid var(--border-light);
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}
.li-stat--warn .li-stat__num { color: var(--badge-warning-text); }
.li-stat__label { font-size: var(--type-caption-1); color: var(--text-secondary); }
.li-stat__num { font-size: var(--type-section-title); font-weight: 700; font-variant-numeric: tabular-nums; }
.li-stat__text { font-size: var(--type-caption-1); color: var(--text-secondary); }

.li-section__head { display: flex; align-items: baseline; gap: var(--space-3); margin-bottom: var(--space-3); }
.li-section__head h2 { font-size: var(--type-section-title); margin: 0; }
.li-section__count { font-size: var(--type-caption-1); color: var(--text-secondary); }

.li-empty { padding: var(--space-8); text-align: center; color: var(--text-secondary); }

.li-table-wrap { overflow-x: auto; }
.li-table { width: 100%; border-collapse: collapse; font-size: var(--type-body); }
.li-table th { text-align: left; padding: var(--space-2) var(--space-3); color: var(--text-secondary); font-weight: 600; border-bottom: 1px solid var(--border-light); }
.li-table td { padding: var(--space-2) var(--space-3); border-bottom: 1px solid var(--border-light); vertical-align: middle; }
.li-table .num { text-align: right; white-space: nowrap; }
.li-table .mono { font-family: var(--font-mono); max-width: 320px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.li-table .dim { color: var(--text-secondary); max-width: 220px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

.li-match-row { display: flex; gap: var(--space-2); align-items: center; }
.li-input {
  width: 110px;
  padding: var(--space-1) var(--space-2);
  font-family: var(--font-mono);
  font-size: var(--type-body);
  border-radius: var(--radius-sm, 8px);
  border: 1px solid var(--border-light);
  background: transparent;
  color: inherit;
}
.btn-sm { padding: var(--space-1) var(--space-3); font-size: var(--type-caption-1); }
.li-more { padding: var(--space-4); text-align: center; }
</style>
