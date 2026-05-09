<template>
  <div class="supplement-page">
    <div class="page-header">
      <h1>补全管理</h1>
    </div>

    <!-- Tabs -->
    <div class="tabs">
      <button
        v-for="tab in tabs"
        :key="tab.key"
        class="tab-btn"
        :class="{ active: activeTab === tab.key }"
        @click="activeTab = tab.key"
      >{{ tab.label }}</button>
    </div>

    <!-- Stats Tab -->
    <div v-if="activeTab === 'stats'" class="tab-content">
      <div v-if="statsLoading" class="loading-wrap">
        <div class="spinner-large"></div>
      </div>
      <div v-else-if="stats" class="stats-grid">
        <div class="stat-card">
          <span class="stat-value">{{ stats.total_movies ?? 0 }}</span>
          <span class="stat-label">补全影片</span>
        </div>
        <div class="stat-card">
          <span class="stat-value">{{ stats.matched_r18 ?? 0 }}</span>
          <span class="stat-label">已匹配 r18</span>
        </div>
        <div class="stat-card">
          <span class="stat-value">{{ stats.supplement_only ?? 0 }}</span>
          <span class="stat-label">仅补全</span>
        </div>
        <div class="stat-card">
          <span class="stat-value">{{ stats.resolved_videos ?? 0 }}</span>
          <span class="stat-label">resolved 影片</span>
        </div>
        <div class="stat-card">
          <span class="stat-value">{{ stats.total_source_items ?? 0 }}</span>
          <span class="stat-label">原始条目</span>
        </div>
        <div class="stat-card">
          <span class="stat-value">{{ stats.resolved_actress_links ?? 0 }}</span>
          <span class="stat-label">演员关联</span>
        </div>
        <div v-if="stats.jobs_by_status" class="stat-card stat-card-wide">
          <div class="job-status-row">
            <span class="status-chip queued">排队 {{ stats.jobs_by_status.queued ?? 0 }}</span>
            <span class="status-chip running">运行 {{ stats.jobs_by_status.running ?? 0 }}</span>
            <span class="status-chip succeeded">成功 {{ stats.jobs_by_status.succeeded ?? 0 }}</span>
            <span class="status-chip failed">失败 {{ stats.jobs_by_status.failed ?? 0 }}</span>
          </div>
          <span class="stat-label">任务状态</span>
        </div>
      </div>
    </div>

    <!-- Jobs Tab -->
    <div v-if="activeTab === 'jobs'" class="tab-content">
      <div class="toolbar">
        <div class="filters">
          <select v-model="jobFilters.status" @change="loadJobs" class="filter-select">
            <option value="">全部状态</option>
            <option value="queued">排队中</option>
            <option value="running">运行中</option>
            <option value="succeeded">已完成</option>
            <option value="failed">失败</option>
          </select>
          <input
            v-model="jobFilters.actress_id"
            placeholder="演员 ID"
            class="filter-input"
            @keyup.enter="loadJobs"
          />
          <button class="btn btn-ghost btn-sm" @click="loadJobs">筛选</button>
        </div>
        <button class="btn btn-ghost btn-sm" @click="recoverStale" :disabled="recovering">
          {{ recovering ? '恢复中...' : '恢复卡住任务' }}
        </button>
      </div>

      <div v-if="jobsLoading" class="loading-wrap"><div class="spinner-large"></div></div>
      <div v-else>
        <div class="job-list">
          <div v-for="job in jobs" :key="job.id" class="job-item">
            <div class="job-main">
              <div class="job-info">
                <span class="job-id">#{{ job.id }}</span>
                <span class="job-actor">{{ job.source_actor_name || `演员 ${job.local_actress_id}` }}</span>
                <span
                  class="job-status"
                  :class="`status-${job.status}`"
                >{{ statusLabel(job.status) }}</span>
              </div>
              <div class="job-counters">
                <span v-if="job.total_found">发现 {{ job.total_found }}</span>
                <span v-if="job.supplement_created">补全 {{ job.supplement_created }}</span>
                <span v-if="job.matched_r18">匹配 {{ job.matched_r18 }}</span>
              </div>
              <div class="job-time">
                {{ job.created_at ? new Date(job.created_at).toLocaleString() : '' }}
              </div>
            </div>
            <div v-if="job.last_error && job.status === 'failed'" class="job-error">
              {{ job.last_error }}
            </div>
            <div class="job-actions">
              <button
                v-if="job.status === 'failed'"
                class="btn btn-primary btn-sm"
                @click="retryJob(job.id)"
              >重试</button>
              <button
                v-if="job.status === 'queued' || job.status === 'running'"
                class="btn btn-ghost btn-sm"
                @click="cancelJob(job.id)"
              >取消</button>
            </div>
          </div>
          <div v-if="!jobs.length && !jobsLoading" class="empty-state-mini">暂无任务</div>
        </div>
        <div v-if="jobsTotalPages > 1" class="pagination">
          <button class="btn btn-ghost btn-sm" :disabled="jobPage <= 1" @click="jobPage--; loadJobs()">上一页</button>
          <span>{{ jobPage }} / {{ jobsTotalPages }}</span>
          <button class="btn btn-ghost btn-sm" :disabled="jobPage >= jobsTotalPages" @click="jobPage++; loadJobs()">下一页</button>
        </div>
      </div>
    </div>

    <!-- Movies Tab -->
    <div v-if="activeTab === 'movies'" class="tab-content">
      <div class="toolbar">
        <div class="filters">
          <select v-model="movieFilters.matched" @change="loadMovies" class="filter-select">
            <option :value="null">全部</option>
            <option :value="false">未匹配</option>
            <option :value="true">已匹配</option>
          </select>
          <select v-model="movieFilters.quality" @change="loadMovies" class="filter-select">
            <option value="">全部质量</option>
            <option value="missing_cover">缺封面</option>
            <option value="missing_runtime">缺时长</option>
            <option value="missing_maker">缺厂商</option>
            <option value="missing_categories">缺分类</option>
            <option value="low_completeness">低完整度</option>
          </select>
          <input
            v-model="movieFilters.actress_id"
            placeholder="演员 ID"
            class="filter-input"
            @keyup.enter="loadMovies"
          />
          <input
            v-model="movieFilters.q"
            placeholder="搜索番号/标题"
            class="filter-input"
            @keyup.enter="loadMovies"
          />
          <button class="btn btn-ghost btn-sm" @click="loadMovies">筛选</button>
        </div>
        <button class="btn btn-primary btn-sm" :disabled="batchEnriching" @click="batchEnrichMovies">
          {{ batchEnriching ? '批量排队中...' : '批量补详情' }}
        </button>
      </div>

      <div v-if="moviesLoading" class="loading-wrap"><div class="spinner-large"></div></div>
      <div v-else>
        <div class="movie-list">
          <div v-for="movie in supplementMovies" :key="movie.id" class="movie-item">
            <div class="movie-main">
              <span class="movie-number">{{ movie.dvd_id || movie.canonical_number || '—' }}</span>
              <span class="movie-title">{{ movie.title || movie.dvd_id || movie.canonical_number || '—' }}</span>
              <span class="movie-actress">{{ movie.actress_name || '' }}</span>
              <span class="movie-date">{{ movie.release_date || '' }}</span>
              <span
                class="movie-match"
                :class="{ 'matched': movie.matched_content_id }"
              >
                {{ movie.matched_content_id ? `已匹配 ${movie.matched_content_id}` : '未匹配' }}
              </span>
            </div>
            <div class="movie-actions">
              <button
                v-if="movie.source_movie_id"
                class="btn btn-primary btn-sm"
                :disabled="enrichingMovies[movie.id]"
                @click="enrichMovie(movie)"
              >{{ enrichingMovies[movie.id] ? '排队中...' : '补详情' }}</button>
              <a
                v-if="movie.matched_content_id"
                :href="`/search?q=${movie.matched_content_id}`"
                class="btn btn-ghost btn-sm"
                target="_blank"
              >查看主库</a>
              <a
                v-if="movie.source_url"
                :href="movie.source_url"
                class="btn btn-ghost btn-sm"
                target="_blank"
              >来源</a>
            </div>
          </div>
          <div v-if="!supplementMovies.length && !moviesLoading" class="empty-state-mini">暂无补全影片</div>
        </div>
        <div v-if="moviesTotalPages > 1" class="pagination">
          <button class="btn btn-ghost btn-sm" :disabled="moviePage <= 1" @click="moviePage--; loadMovies()">上一页</button>
          <span>{{ moviePage }} / {{ moviesTotalPages }}</span>
          <button class="btn btn-ghost btn-sm" :disabled="moviePage >= moviesTotalPages" @click="moviePage++; loadMovies()">下一页</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import api from '../api'

export default {
  name: 'SupplementManagement',
  data() {
    return {
      activeTab: 'stats',
      tabs: [
        { key: 'stats', label: '概览' },
        { key: 'jobs', label: '任务队列' },
        { key: 'movies', label: '补全影片' },
      ],
      // Stats
      stats: null,
      statsLoading: false,
      // Jobs
      jobs: [],
      jobsLoading: false,
      jobPage: 1,
      jobsTotalCount: 0,
      jobsTotalPages: 1,
      jobFilters: { status: '', actress_id: '' },
      recovering: false,
      // Movies
      supplementMovies: [],
      moviesLoading: false,
      enrichingMovies: {},
      batchEnriching: false,
      moviePage: 1,
      moviesTotalCount: 0,
      moviesTotalPages: 1,
      movieFilters: { matched: false, quality: '', actress_id: '', q: '' },
    }
  },
  watch: {
    activeTab(tab) {
      if (tab === 'stats' && !this.stats) this.loadStats()
      if (tab === 'jobs' && !this.jobs.length) this.loadJobs()
      if (tab === 'movies' && !this.supplementMovies.length) this.loadMovies()
    },
  },
  mounted() {
    const tab = this.$route.query.tab
    if (['stats', 'jobs', 'movies'].includes(tab)) this.activeTab = tab
    const actressId = this.$route.query.actress_id
    if (actressId) {
      this.jobFilters.actress_id = actressId
      this.movieFilters.actress_id = actressId
    }
    this.loadStats()
    if (this.activeTab === 'jobs') this.loadJobs()
    if (this.activeTab === 'movies') this.loadMovies()
  },
  methods: {
    statusLabel(status) {
      const map = { queued: '排队中', running: '运行中', succeeded: '已完成', failed: '失败' }
      return map[status] || status || '未知'
    },
    async loadStats() {
      this.statsLoading = true
      try {
        const resp = await api.getSupplementStats()
        this.stats = resp.data || resp
      } catch (e) {
        console.error('Load supplement stats failed:', e)
      } finally {
        this.statsLoading = false
      }
    },
    async loadJobs() {
      this.jobsLoading = true
      try {
        const params = { page: this.jobPage, page_size: 20 }
        if (this.jobFilters.status) params.status = this.jobFilters.status
        if (this.jobFilters.actress_id) params.actress_id = this.jobFilters.actress_id
        const resp = await api.listSupplementJobs(params)
        const data = resp.data || resp
        this.jobs = data.data || []
        this.jobsTotalCount = data.total_count || 0
        this.jobsTotalPages = data.total_pages || 1
      } catch (e) {
        console.error('Load supplement jobs failed:', e)
      } finally {
        this.jobsLoading = false
      }
    },
    async retryJob(jobId) {
      try {
        await api.retrySupplementJob(jobId)
        await this.loadJobs()
      } catch (e) {
        console.error('Retry job failed:', e)
      }
    },
    async cancelJob(jobId) {
      try {
        await api.cancelSupplementJob(jobId)
        await this.loadJobs()
      } catch (e) {
        console.error('Cancel job failed:', e)
      }
    },
    async recoverStale() {
      this.recovering = true
      try {
        const resp = await api.recoverStaleSupplementJobs(30)
        const data = resp.data || resp
        console.log(`Recovered ${data.recovered ?? 0} stale jobs`)
        await this.loadJobs()
      } catch (e) {
        console.error('Recover stale failed:', e)
      } finally {
        this.recovering = false
      }
    },
    async loadMovies() {
      this.moviesLoading = true
      try {
        const params = { page: this.moviePage, page_size: 20 }
        if (this.movieFilters.matched !== null) params.matched = this.movieFilters.matched
        if (this.movieFilters.actress_id) params.actress_id = this.movieFilters.actress_id
        if (this.movieFilters.q) params.q = this.movieFilters.q
        if (this.movieFilters.quality === 'missing_cover') params.missing_cover = true
        if (this.movieFilters.quality === 'missing_runtime') params.missing_runtime = true
        if (this.movieFilters.quality === 'missing_maker') params.missing_maker = true
        if (this.movieFilters.quality === 'missing_categories') params.missing_categories = true
        if (this.movieFilters.quality === 'low_completeness') params.max_completeness = 2
        const resp = await api.listSupplementMovies(params)
        const data = resp.data || resp
        this.supplementMovies = data.data || []
        this.moviesTotalCount = data.total_count || 0
        this.moviesTotalPages = data.total_pages || 1
      } catch (e) {
        console.error('Load supplement movies failed:', e)
      } finally {
        this.moviesLoading = false
      }
    },
    async enrichMovie(movie) {
      if (!movie?.source_movie_id || this.enrichingMovies[movie.id]) return
      this.enrichingMovies = { ...this.enrichingMovies, [movie.id]: true }
      try {
        await api.startSupplementMovieDetailJob(movie.source_movie_id, movie.source || 'avbase')
        await this.loadJobs()
      } catch (e) {
        console.error('Start movie detail job failed:', e)
      } finally {
        const next = { ...this.enrichingMovies }
        delete next[movie.id]
        this.enrichingMovies = next
      }
    },
    async batchEnrichMovies() {
      if (this.batchEnriching) return
      this.batchEnriching = true
      try {
        const params = { source: 'avbase', limit: 20 }
        if (this.movieFilters.matched !== null) params.matched = this.movieFilters.matched
        if (this.movieFilters.actress_id) params.actress_id = this.movieFilters.actress_id
        if (this.movieFilters.q) params.q = this.movieFilters.q
        if (this.movieFilters.quality === 'missing_cover') params.missing_cover = true
        if (this.movieFilters.quality === 'missing_runtime') params.missing_runtime = true
        if (this.movieFilters.quality === 'missing_maker') params.missing_maker = true
        if (this.movieFilters.quality === 'missing_categories') params.missing_categories = true
        if (this.movieFilters.quality === 'low_completeness') params.max_completeness = 2
        await api.startSupplementMovieDetailBatchJobs(params)
        await this.loadJobs()
      } catch (e) {
        console.error('Start batch movie detail jobs failed:', e)
      } finally {
        this.batchEnriching = false
      }
    },
  },
}
</script>

<style scoped>
.supplement-page {
  max-width: 1400px;
  margin: 0 auto;
  padding: 24px 40px 40px;
}

.page-header h1 {
  font-size: 24px;
  font-weight: 700;
  color: var(--text-primary);
  margin-bottom: 20px;
}

/* Tabs */
.tabs {
  display: flex;
  gap: 4px;
  border-bottom: 1px solid var(--border);
  margin-bottom: 20px;
}

.tab-btn {
  background: none;
  border: none;
  padding: 10px 20px;
  font-size: 14px;
  font-weight: 500;
  color: var(--text-muted);
  cursor: pointer;
  border-bottom: 2px solid transparent;
  transition: all 0.2s;
}

.tab-btn:hover {
  color: var(--text-secondary);
}

.tab-btn.active {
  color: var(--text-primary);
  border-bottom-color: var(--accent);
  font-weight: 600;
}

/* Stats */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 16px;
}

.stat-card {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 20px;
  background: var(--bg-secondary);
  border: 1px solid var(--border);
  border-radius: 12px;
}

.stat-card-wide {
  grid-column: span 2;
}

.stat-value {
  font-size: 28px;
  font-weight: 700;
  color: var(--text-primary);
}

.stat-label {
  font-size: 13px;
  color: var(--text-muted);
}

.job-status-row {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 4px;
}

.status-chip {
  font-size: 12px;
  padding: 3px 10px;
  border-radius: 10px;
  font-weight: 600;
}

.status-chip.queued { background: rgba(59, 130, 246, 0.15); color: #60a5fa; }
.status-chip.running { background: rgba(251, 191, 36, 0.15); color: #fbbf24; }
.status-chip.succeeded { background: rgba(34, 197, 94, 0.15); color: #4ade80; }
.status-chip.failed { background: rgba(239, 68, 68, 0.15); color: #f87171; }

/* Toolbar */
.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  flex-wrap: wrap;
  gap: 8px;
}

.filters {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  align-items: center;
}

.filter-select,
.filter-input {
  padding: 6px 12px;
  font-size: 13px;
  background: var(--bg-secondary);
  border: 1px solid var(--border);
  border-radius: 8px;
  color: var(--text-primary);
  outline: none;
}

.filter-input {
  width: 140px;
}

.filter-select:focus,
.filter-input:focus {
  border-color: var(--accent);
}

/* Jobs */
.job-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.job-item {
  padding: 14px 18px;
  background: var(--bg-secondary);
  border: 1px solid var(--border);
  border-radius: 12px;
}

.job-main {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
}

.job-info {
  display: flex;
  align-items: center;
  gap: 10px;
}

.job-id {
  font-size: 13px;
  color: var(--text-muted);
  font-family: monospace;
}

.job-actor {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
}

.job-status {
  font-size: 12px;
  padding: 2px 8px;
  border-radius: 8px;
  font-weight: 600;
}

.status-queued { background: rgba(59, 130, 246, 0.15); color: #60a5fa; }
.status-running { background: rgba(251, 191, 36, 0.15); color: #fbbf24; }
.status-succeeded { background: rgba(34, 197, 94, 0.15); color: #4ade80; }
.status-failed { background: rgba(239, 68, 68, 0.15); color: #f87171; }

.job-counters {
  display: flex;
  gap: 12px;
  font-size: 13px;
  color: var(--text-secondary);
}

.job-time {
  font-size: 12px;
  color: var(--text-muted);
}

.job-error {
  margin-top: 8px;
  padding: 6px 10px;
  background: rgba(239, 68, 68, 0.08);
  border-radius: 6px;
  font-size: 12px;
  color: #f87171;
}

.job-actions {
  display: flex;
  gap: 6px;
  margin-top: 8px;
}

/* Movies */
.movie-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.movie-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 18px;
  background: var(--bg-secondary);
  border: 1px solid var(--border);
  border-radius: 10px;
  gap: 12px;
  flex-wrap: wrap;
}

.movie-main {
  display: flex;
  align-items: center;
  gap: 12px;
  flex: 1;
  min-width: 0;
  flex-wrap: wrap;
}

.movie-number {
  font-family: monospace;
  font-size: 13px;
  font-weight: 600;
  color: var(--accent);
  white-space: nowrap;
}

.movie-title {
  font-size: 14px;
  color: var(--text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 300px;
}

.movie-actress {
  font-size: 13px;
  color: var(--text-muted);
}

.movie-date {
  font-size: 13px;
  color: var(--text-muted);
}

.movie-match {
  font-size: 12px;
  padding: 2px 8px;
  border-radius: 8px;
  background: rgba(239, 68, 68, 0.1);
  color: #f87171;
  white-space: nowrap;
}

.movie-match.matched {
  background: rgba(34, 197, 94, 0.1);
  color: #4ade80;
}

.movie-actions {
  display: flex;
  gap: 6px;
}

/* Pagination */
.pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  margin-top: 16px;
  font-size: 13px;
  color: var(--text-secondary);
}

/* Shared */
.loading-wrap {
  text-align: center;
  padding: 40px;
  color: var(--text-secondary);
}

.spinner-large {
  width: 36px;
  height: 36px;
  border: 3px solid rgba(255,255,255,0.1);
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  margin: 0 auto 12px;
}

.empty-state-mini {
  text-align: center;
  padding: 40px;
  color: var(--text-muted);
  font-size: 14px;
}

.btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  border: none;
  transition: all 0.2s;
  text-decoration: none;
}

.btn-primary {
  background: var(--accent);
  color: var(--bg-primary);
}

.btn-primary:hover {
  opacity: 0.9;
}

.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-ghost {
  background: rgba(255, 255, 255, 0.06);
  color: var(--text-secondary);
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.btn-ghost:hover {
  background: rgba(255, 255, 255, 0.1);
}

.btn-sm {
  padding: 6px 14px;
  font-size: 13px;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

@media (max-width: 768px) {
  .supplement-page {
    padding: 16px;
  }
  .stats-grid {
    grid-template-columns: repeat(2, 1fr);
  }
  .stat-card-wide {
    grid-column: span 2;
  }
  .movie-title {
    max-width: 160px;
  }
}
</style>
