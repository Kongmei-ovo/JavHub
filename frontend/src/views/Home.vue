<template>
  <div class="home page-shell page-shell--workspace">
    <!-- 页面头部 -->
    <div class="page-header">
      <div class="header-left">
        <h1>下载管理</h1>
        <p class="header-subtitle">
          <span class="total-tasks">{{ stats.pending + stats.downloading + stats.completed + stats.failed }} 个任务</span>
          <span v-if="stats.downloading > 0" class="downloading-hint">
            · {{ stats.downloading }} 个下载中
          </span>
          <span v-if="candidateStats.candidate > 0" class="downloading-hint">
            · {{ candidateStats.candidate }} 个候选待确认
          </span>
        </p>
      </div>
      <div class="header-actions">
        <button class="btn btn-ghost" type="button" @click="$router.push('/search')">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="16" height="16">
            <circle cx="11" cy="11" r="8"/>
            <path d="m21 21-4.35-4.35"/>
          </svg>
          搜索影片
        </button>
        <button class="btn btn-ghost" type="button" @click="$router.push('/genres')">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="16" height="16">
            <path d="M4 19.5A2.5 2.5 0 016.5 17H20"/>
            <path d="M6.5 2H20v20H6.5A2.5 2.5 0 014 19.5v-15A2.5 2.5 0 016.5 2z"/>
          </svg>
          浏览分类
        </button>
        <button class="btn btn-primary" type="button" @click="loadTasks">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="16" height="16">
            <polyline points="23 4 23 10 17 10"/>
            <path d="M20.49 15a9 9 0 11-2.12-9.36L23 10"/>
          </svg>
          刷新
        </button>
      </div>
    </div>

    <!-- 统计卡片 -->
    <div class="stats-bar">
      <div class="stat-card" @click="setTaskStatus('pending')">
        <div class="stat-icon pending">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
            <circle cx="12" cy="12" r="10"/>
            <polyline points="12 6 12 12 16 14"/>
          </svg>
        </div>
        <div class="stat-info">
          <div class="stat-num" :class="{ 'animate-in': statsLoaded }">{{ stats.pending }}</div>
          <div class="stat-label">待处理</div>
        </div>
      </div>
      <div class="stat-card" @click="setTaskStatus('downloading')">
        <div class="stat-icon downloading">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
            <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/>
            <polyline points="7 10 12 15 17 10"/>
            <line x1="12" y1="15" x2="12" y2="3"/>
          </svg>
        </div>
        <div class="stat-info">
          <div class="stat-num">{{ stats.downloading }}</div>
          <div class="stat-label">下载中</div>
        </div>
      </div>
      <div class="stat-card" @click="setTaskStatus('completed')">
        <div class="stat-icon completed">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
            <path d="M22 11.08V12a10 10 0 11-5.93-9.14"/>
            <polyline points="22 4 12 14.01 9 11.01"/>
          </svg>
        </div>
        <div class="stat-info">
          <div class="stat-num">{{ stats.completed }}</div>
          <div class="stat-label">已完成</div>
        </div>
      </div>
      <div class="stat-card" @click="setTaskStatus('failed')">
        <div class="stat-icon failed">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
            <circle cx="12" cy="12" r="10"/>
            <line x1="15" y1="9" x2="9" y2="15"/>
            <line x1="9" y1="9" x2="15" y2="15"/>
          </svg>
        </div>
        <div class="stat-info">
          <div class="stat-num">{{ stats.failed }}</div>
          <div class="stat-label">失败</div>
        </div>
      </div>
    </div>

    <div class="candidate-overview">
      <button class="candidate-metric" type="button" @click="openCandidatePreset({ status: 'candidate', source: '' })">
        <span class="metric-value">{{ candidateStats.candidate || 0 }}</span>
        <span class="metric-label">待确认候选</span>
      </button>
      <button class="candidate-metric" type="button" @click="openCandidatePreset({ status: 'candidate', needs_magnet: true, source: '' })">
        <span class="metric-value">{{ candidateStats.needs_magnet || 0 }}</span>
        <span class="metric-label">待补磁力</span>
      </button>
      <button class="candidate-metric" type="button" @click="openCandidatePreset({ status: 'candidate', needs_magnet: false, source: '' })">
        <span class="metric-value">{{ readyCandidateCount }}</span>
        <span class="metric-label">可批准</span>
      </button>
      <button class="candidate-metric" type="button" @click="openCandidatePreset({ status: 'candidate', source: 'subscription' })">
        <span class="metric-value">{{ candidateStats.candidate_by_source?.subscription || 0 }}</span>
        <span class="metric-label">订阅发现</span>
      </button>
      <button class="candidate-metric" type="button" @click="openCandidatePreset({ status: 'candidate', source: 'inventory' })">
        <span class="metric-value">{{ candidateStats.candidate_by_source?.inventory || 0 }}</span>
        <span class="metric-label">库存发现</span>
      </button>
      <button class="candidate-metric" type="button" @click="openCandidatePreset({ status: 'candidate', source: 'supplement' })">
        <span class="metric-value">{{ candidateStats.candidate_by_source?.supplement || 0 }}</span>
        <span class="metric-label">补全发现</span>
      </button>
    </div>

    <!-- 任务过滤栏 -->
    <div v-if="filterStatus" class="filter-bar" @click="clearTaskStatus">
      <span class="filter-hint">筛选: <strong>{{ filterStatus }}</strong> (点击清除)</span>
    </div>

    <div class="download-tabs">
      <button class="tab-btn" type="button" :class="{ active: activeTab === 'tasks' }" @click="openTaskTab">真实任务</button>
      <button class="tab-btn" type="button" :class="{ active: activeTab === 'candidates' }" @click="openCandidateTab">
        下载候选
        <span v-if="candidateStats.candidate" class="tab-badge">{{ candidateStats.candidate }}</span>
      </button>
      <button class="tab-btn" type="button" :class="{ active: activeTab === 'downloaders' }" @click="openDownloaderTab">
        下载源
        <span v-if="enabledDownloaderCount" class="tab-badge subtle">{{ enabledDownloaderCount }}</span>
      </button>
    </div>

    <!-- 任务卡片网格 -->
    <div v-if="activeTab === 'tasks' && filteredTasks.length > 0" class="tasks-grid">
      <div
        v-for="task in filteredTasks"
        :key="task.id"
        class="task-card av-card"
      >
        <div class="task-cover">
          <div class="cover-placeholder">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="40" height="40">
              <rect x="2" y="2" width="20" height="20" rx="2.18" ry="2.18"/>
              <line x1="7" y1="2" x2="7" y2="22"/>
              <line x1="17" y1="2" x2="17" y2="22"/>
              <line x1="2" y1="12" x2="22" y2="12"/>
              <line x1="2" y1="7" x2="7" y2="7"/>
              <line x1="2" y1="17" x2="7" y2="17"/>
              <line x1="17" y1="17" x2="22" y2="17"/>
              <line x1="17" y1="7" x2="22" y2="7"/>
            </svg>
          </div>
          <div class="cover-overlay">
            <span class="cover-code">{{ task.content_id || task.code }}</span>
          </div>
          <!-- 下载进度条 -->
          <div v-if="task.status === 'downloading'" class="progress-overlay">
            <div class="progress-bar">
              <div class="progress-bar-fill progress-bar-fill-demo"></div>
            </div>
          </div>
        </div>

        <div class="task-info">
          <h3 class="task-title" :title="task.title">{{ task.title }}</h3>
          <div class="task-meta">
            <span :class="['badge', statusBadge(task.status)]">{{ statusLabel(task.status) }}</span>
            <span class="task-time">{{ formatTime(task.created_at) }}</span>
          </div>
          <div class="task-downloader">{{ task.downloader_name || downloaderTypeLabel(task.downloader_type) || '默认下载源' }}</div>
          <div v-if="task.error_msg" class="task-error">{{ task.error_msg }}</div>
        </div>

        <div class="task-actions">
          <button
            v-if="task.status === 'failed'"
            class="btn btn-primary"
            type="button"
            :disabled="retryingTasks[task.id]"
            @click="retry(task)"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="14" height="14">
              <polyline points="23 4 23 10 17 10"/>
              <path d="M20.49 15a9 9 0 11-2.12-9.36L23 10"/>
            </svg>
            {{ retryingTasks[task.id] ? '重试中...' : '重试' }}
          </button>
          <button class="btn btn-ghost" type="button" @click="remove(task.id)">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="14" height="14">
              <polyline points="3 6 5 6 21 6"/>
              <path d="M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2"/>
            </svg>
            删除
          </button>
        </div>
      </div>
    </div>

    <DownloadCandidatePanel
      v-else-if="activeTab === 'candidates'"
      :candidate-filter="candidateFilter"
      :candidate-stats="candidateStats"
      :selecting-candidates="selectingCandidates"
      :selected-candidate-ids="selectedCandidateIds"
      :candidate-batch-processing="candidateBatchProcessing"
      :bulk-candidate-loading="bulkCandidateLoading"
      :candidate-runs="candidateRuns"
      :candidate-runs-loading="candidateRunsLoading"
      :candidate-total-pages="candidateTotalPages"
      :candidate-page="candidatePage"
      :candidate-total="candidateTotal"
      :filtered-candidates="filteredCandidates"
      :candidate-mutations="candidateMutations"
      :magnet-editor="magnetEditor"
      :candidate-detail="candidateDetail"
      @update-candidate-search="updateCandidateSearch"
      @search="submitCandidateSearch"
      @set-status="setCandidateStatus"
      @set-needs-magnet="setNeedsMagnet"
      @set-source="setCandidateSource"
      @toggle-selection="toggleCandidateSelection"
      @enrich-visible="enrichVisibleCandidateMagnets"
      @process-visible="processVisibleCandidates"
      @select-all-visible="selectAllVisibleCandidates"
      @clear-selection="clearCandidateSelection"
      @bulk-reject="bulkRejectCandidates"
      @bulk-restore="bulkRestoreCandidates"
      @refresh-runs="loadCandidateRuns"
      @apply-run="applyCandidateRunFilters"
      @apply-run-failed="applyCandidateRunFilters($event, { status: 'failed' })"
      @retry-failed-run="retryFailedCandidateRun"
      @go-page="goCandidatePage"
      @toggle-selected="toggleCandidateSelected"
      @open-detail="openCandidateDetail"
      @go-actor="goCandidateActor"
      @go-supplement="goCandidateSupplement"
      @edit-magnet="editCandidateMagnet"
      @enrich-magnet="enrichCandidateMagnet"
      @approve="approveCandidate"
      @process="processCandidate"
      @reject="rejectCandidate"
      @close-magnet-editor="closeMagnetEditor"
      @update-magnet-editor-value="updateMagnetEditorValue"
      @submit-magnet-editor="submitMagnetEditor"
      @close-detail="closeCandidateDetail"
    />

    <DownloaderManagementPanel
      v-else-if="activeTab === 'downloaders'"
      :downloaders="downloaders"
      :downloader-types="downloaderTypes"
      :downloader-clients="downloaderClients"
      :enabled-downloader-count="enabledDownloaderCount"
      :default-downloader-label="defaultDownloaderLabel"
      :saving-downloaders="savingDownloaders"
      :testing-downloader-id="testingDownloaderId"
      :downloader-test-messages="downloaderTestMessages"
      :downloader-editor="downloaderEditor"
      :downloader-type-label="downloaderTypeLabel"
      :downloader-type-mark="downloaderTypeMark"
      :short-downloader-address="shortDownloaderAddress"
      :downloader-path-summary="downloaderPathSummary"
      :supports-downloader-tags="supportsDownloaderTags"
      :downloader-address-placeholder="downloaderAddressPlaceholder"
      :downloader-path-placeholder="downloaderPathPlaceholder"
      :token-placeholder="tokenPlaceholder"
      @refresh="loadDownloaders"
      @create="openNewDownloader"
      @edit="editDownloader"
      @test="testDownloader"
      @set-default="setDefaultDownloader"
      @remove="removeDownloader"
      @save="saveDownloaders"
      @close-editor="closeDownloaderEditor"
      @sync-draft-defaults="syncDownloaderDraftDefaults"
      @apply-editor="applyDownloaderEditor"
    />

    <AppleEmptyState
      v-else-if="activeTab === 'tasks'"
      class="empty-state"
      :title="taskEmptyTitle"
      :description="taskEmptyHint"
      next-step="可以清除筛选、处理下载候选，或从影片检索和磁链解析添加新任务。"
      :action-label="taskEmptyPrimaryLabel"
      secondary-action-label="磁链解析"
      density="compact"
      @action="handleTaskEmptyAction"
      @secondary-action="$router.push('/parse')"
    >
      <template #icon>
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
          <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/>
          <polyline points="7 10 12 15 17 10"/>
          <line x1="12" y1="15" x2="12" y2="3"/>
        </svg>
      </template>
    </AppleEmptyState>

  </div>
</template>

<script>
import { defineAsyncComponent } from 'vue'
import api from '../api'
import AppleEmptyState from '../components/AppleEmptyState.vue'
import { requestConfirm } from '../utils/confirmDialog'

const DownloadCandidatePanel = defineAsyncComponent(() => import('../features/candidates/DownloadCandidatePanel.vue'))
const DownloaderManagementPanel = defineAsyncComponent(() => import('../features/downloaders/DownloaderManagementPanel.vue'))

export default {
  name: 'Home',
  components: { AppleEmptyState, DownloadCandidatePanel, DownloaderManagementPanel },
  data() {
    return {
      activeTab: ['candidates', 'downloaders'].includes(this.$route.query.tab) ? this.$route.query.tab : 'tasks',
      tasks: [],
      candidates: [],
      downloaders: { default_id: '', clients: [], types: [] },
      downloaderTypes: [
        { value: 'openlist', label: 'OpenList / 115' },
        { value: 'qbittorrent', label: 'qBittorrent' },
        { value: 'transmission', label: 'Transmission' },
        { value: 'synology', label: 'Synology Download Station' },
        { value: 'aria2', label: 'Aria2' },
        { value: 'deluge', label: 'Deluge' },
        { value: 'flood', label: 'Flood' },
        { value: 'rutorrent', label: 'ruTorrent' },
        { value: 'utorrent', label: 'µTorrent / uTorrent' },
      ],
      savingDownloaders: false,
      testingDownloaderId: '',
      downloaderTestMessages: {},
      stats: { pending: 0, downloading: 0, completed: 0, failed: 0 },
      candidateStats: {
        candidate: 0,
        approved: 0,
        rejected: 0,
        sent: 0,
        failed: 0,
        needs_magnet: 0,
        by_source: {},
        candidate_by_source: {},
      },
      filterStatus: null,
      candidateFilter: {
        status: this.$route.query.status || 'candidate',
        source: this.$route.query.source || '',
        actress_id: this.$route.query.actress_id || '',
        q: this.$route.query.q || '',
        needs_magnet: this.$route.query.needs_magnet === '1' ? true : (this.$route.query.needs_magnet === '0' ? false : null)
      },
      candidatePage: Number(this.$route.query.page || 1) || 1,
      candidatePageSize: 50,
      candidateTotal: 0,
      candidateTotalPages: 1,
      timer: null,
      selectingCandidates: false,
      selectedCandidateIds: [],
      bulkCandidateLoading: false,
      candidateBatchProcessing: '',
      candidateRuns: [],
      candidateRunsLoading: false,
      candidateMutations: {},
      retryingTasks: {},
      statsLoaded: false,
      magnetEditor: {
        open: false,
        candidate: null,
        value: ''
      },
      candidateDetail: {
        open: false,
        loading: false,
        data: null
      },
      downloaderEditor: {
        open: false,
        mode: 'new',
        originalId: '',
        draft: null,
        previousType: ''
      },
      downloaderIdSeed: 1
    }
  },
  computed: {
    filteredTasks() {
      if (!this.filterStatus) return this.tasks
      return this.tasks.filter(t => t.status === this.filterStatus)
    },
    filteredCandidates() {
      return this.candidates
    },
    readyCandidateCount() {
      return Math.max((this.candidateStats.candidate || 0) - (this.candidateStats.needs_magnet || 0), 0)
    },
    downloaderClients() {
      return this.downloaders.clients || []
    },
    enabledDownloaderCount() {
      return this.downloaderClients.filter(client => client.enabled).length
    },
    defaultDownloaderLabel() {
      const client = this.downloaderClients.find(item => item.id === this.downloaders.default_id)
      return client?.name || this.downloaderTypeLabel(client?.type) || '未设置'
    },
    taskEmptyHint() {
      if (this.filterStatus) return '当前筛选没有任务，可以清除筛选查看全部。'
      if (this.candidateStats.candidate > 0) return '已有下载候选待确认，优先处理候选再下发任务。'
      return '可以从影片检索或磁链解析添加下载任务。'
    },
    taskEmptyTitle() {
      return `暂无${this.filterStatus ? this.statusLabel(this.filterStatus) : ''}任务`
    },
    taskEmptyPrimaryLabel() {
      if (this.filterStatus) return '清除筛选'
      if (this.candidateStats.candidate > 0) return `查看 ${this.candidateStats.candidate} 个候选`
      return '搜索影片'
    }
  },
  mounted() {
    this.applyDownloadRoute(this.$route.query, { initial: true })
    this.loadTasks()
    if (this.activeTab === 'candidates') this.loadCandidates()
    else this.loadCandidateSummary()
    if (this.activeTab === 'candidates') this.loadCandidateRuns()
    if (this.activeTab === 'downloaders') this.loadDownloaders()
    this.timer = setInterval(this.loadTasks, 30000)
  },
  beforeUnmount() {
    if (this.timer) clearInterval(this.timer)
  },
  watch: {
    '$route.query'(query) {
      const changed = this.applyDownloadRoute(query)
      if (!changed) return
      if (this.activeTab === 'candidates') {
        this.loadCandidates()
        this.loadCandidateRuns()
      } else if (this.activeTab === 'downloaders') {
        this.loadDownloaders()
      }
    }
  },
  methods: {
    applyDownloadRoute(query = {}) {
      let changed = false
      const tab = ['tasks', 'candidates', 'downloaders'].includes(query.tab) ? query.tab : 'tasks'
      if (this.activeTab !== tab) { this.activeTab = tab; changed = true }
      const taskStatus = tab === 'tasks' ? (query.task_status || '') : ''
      if ((this.filterStatus || '') !== taskStatus) { this.filterStatus = taskStatus || null; changed = true }
      const nextFilter = {
        status: tab === 'candidates' ? (query.status || 'candidate') : this.candidateFilter.status,
        source: tab === 'candidates' ? (query.source || '') : this.candidateFilter.source,
        actress_id: tab === 'candidates' ? (query.actress_id || '') : this.candidateFilter.actress_id,
        q: tab === 'candidates' ? (query.q || '') : this.candidateFilter.q,
        needs_magnet: query.needs_magnet === '1' ? true : (query.needs_magnet === '0' ? false : null),
        page: tab === 'candidates' ? (Number(query.page || 1) || 1) : this.candidatePage,
      }
      const { page, ...filterOnly } = nextFilter
      if (this.candidatePage !== page) { this.candidatePage = page; changed = true }
      if (JSON.stringify(filterOnly) !== JSON.stringify(this.candidateFilter)) {
        this.candidateFilter = filterOnly
        changed = true
      }
      return changed
    },
    cleanDownloadQuery(query = {}) {
      const next = { ...query }
      Object.keys(next).forEach(key => {
        if (next[key] === '' || next[key] === null || next[key] === undefined) delete next[key]
      })
      return next
    },
    pushDownloadRoute(query = {}) {
      const next = this.cleanDownloadQuery(query)
      if (JSON.stringify(next) !== JSON.stringify(this.$route.query || {})) {
        this.$router.push({ path: this.$route.path, query: next }).catch(() => {})
      }
    },
    replaceDownloadRoute(query = {}) {
      const next = this.cleanDownloadQuery(query)
      if (JSON.stringify(next) !== JSON.stringify(this.$route.query || {})) {
        this.$router.replace({ path: this.$route.path, query: next }).catch(() => {})
      }
    },
    candidateRouteQuery(overrides = {}) {
      const filter = { ...this.candidateFilter, page: this.candidatePage, ...overrides }
      const query = { tab: 'candidates' }
      if (filter.status) query.status = filter.status
      if (filter.source) query.source = filter.source
      if (filter.actress_id) query.actress_id = filter.actress_id
      if (filter.q) query.q = filter.q
      if (filter.needs_magnet === true) query.needs_magnet = '1'
      if (filter.needs_magnet === false) query.needs_magnet = '0'
      if (filter.page && Number(filter.page) > 1) query.page = String(Number(filter.page))
      return query
    },
    async loadTasks() {
      try {
        const resp = await api.getDownloads()
        this.tasks = resp.data.data || []
        this.stats = {
          pending: this.tasks.filter(t => t.status === 'pending').length,
          downloading: this.tasks.filter(t => t.status === 'downloading').length,
          completed: this.tasks.filter(t => t.status === 'completed').length,
          failed: this.tasks.filter(t => t.status === 'failed').length
        }
        this.statsLoaded = true
      } catch (e) {
        console.error('Failed to load tasks:', e)
      }
    },
    async loadCandidates() {
      try {
        const params = {}
        if (this.candidateFilter.status) params.status = this.candidateFilter.status
        if (this.candidateFilter.source) params.source = this.candidateFilter.source
        if (this.candidateFilter.actress_id) params.actress_id = this.candidateFilter.actress_id
        if (this.candidateFilter.q) params.q = this.candidateFilter.q
        if (this.candidateFilter.needs_magnet !== null) params.needs_magnet = this.candidateFilter.needs_magnet
        params.page = this.candidatePage
        params.page_size = this.candidatePageSize
        params.include_stats = false
        const resp = await api.listDownloadCandidates(params)
        this.candidates = resp.data.data || []
        this.candidateTotal = Number(resp.data.total || this.candidates.length) || 0
        this.candidateTotalPages = Number(resp.data.total_pages || 1) || 1
        this.selectedCandidateIds = this.selectedCandidateIds.filter(id => this.candidates.some(c => c.id === id))
        this.syncCandidateRoute()
        await this.loadCandidateSummary()
      } catch (e) {
        console.error('Failed to load candidates:', e)
      }
    },
    async loadCandidateSummary() {
      try {
        const resp = await api.getDownloadCandidateSummary({ status: 'candidate', include_sources: true })
        this.candidateStats = resp.data || this.candidateStats
      } catch (e) {
        console.error('Failed to load candidate summary:', e)
      }
    },
    async loadCandidateRuns() {
      this.candidateRunsLoading = true
      try {
        const resp = await api.listDownloadCandidateRuns(5)
        this.candidateRuns = resp.data.data || []
      } catch (e) {
        console.error('Failed to load candidate runs:', e)
      } finally {
        this.candidateRunsLoading = false
      }
    },
    openCandidateTab() {
      this.pushDownloadRoute(this.candidateRouteQuery({ page: 1 }))
    },
    openDownloaderTab() {
      this.pushDownloadRoute({ tab: 'downloaders' })
    },
    openTaskTab() {
      this.pushDownloadRoute({ tab: 'tasks', task_status: this.filterStatus || undefined })
    },
    setTaskStatus(status) {
      this.pushDownloadRoute({ tab: 'tasks', task_status: status })
    },
    clearTaskStatus() {
      this.pushDownloadRoute({ tab: 'tasks' })
    },
    handleTaskEmptyAction() {
      if (this.filterStatus) {
        this.clearTaskStatus()
      } else if (this.candidateStats.candidate > 0) {
        this.openCandidatePreset({ status: 'candidate', source: '' })
      } else {
        this.$router.push('/search')
      }
    },
    updateCandidateSearch(value) {
      this.candidateFilter = { ...this.candidateFilter, q: value }
    },
    submitCandidateSearch() {
      this.pushDownloadRoute(this.candidateRouteQuery({ q: this.candidateFilter.q, page: 1 }))
    },
    async loadDownloaders() {
      try {
        const resp = await api.listDownloaders()
        const data = resp.data || {}
        this.downloaders = {
          default_id: data.default_id || '',
          clients: (data.clients || []).map(client => ({ ...client })),
          types: data.types || this.downloaderTypes,
        }
        this.downloaderTypes = this.downloaders.types.length ? this.downloaders.types : this.downloaderTypes
        if (!this.downloaders.default_id && this.downloaders.clients[0]) {
          this.downloaders.default_id = this.downloaders.clients[0].id
        }
      } catch (e) {
        console.error('Failed to load downloaders:', e)
      }
    },
    makeDownloaderId(type = 'qbittorrent') {
      let id = `${type}-${this.downloaderIdSeed++}`
      while (this.downloaderClients.some(client => client.id === id)) {
        id = `${type}-${this.downloaderIdSeed++}`
      }
      return id
    },
    createDownloaderDraft(type = 'qbittorrent') {
      return {
        id: this.makeDownloaderId(type),
        type,
        name: this.downloaderTypeLabel(type),
        enabled: true,
        address: this.downloaderAddressPlaceholder(type),
        username: '',
        password: '',
        token: '',
        default_path: '',
        category: '',
        tags: '',
        paused: false,
        timeout: 30,
      }
    },
    normalizeDownloaderDraft(draft) {
      return {
        id: draft.id,
        type: draft.type || 'qbittorrent',
        name: draft.name || this.downloaderTypeLabel(draft.type),
        enabled: Boolean(draft.enabled),
        address: draft.address || '',
        username: draft.username || '',
        password: draft.password || '',
        token: draft.token || '',
        default_path: draft.default_path || '',
        category: draft.category || '',
        tags: draft.tags || '',
        paused: Boolean(draft.paused),
        timeout: Number(draft.timeout || 30),
        password_configured: Boolean(draft.password_configured),
        token_configured: Boolean(draft.token_configured),
      }
    },
    openNewDownloader() {
      this.downloaderEditor = {
        open: true,
        mode: 'new',
        originalId: '',
        draft: this.createDownloaderDraft('qbittorrent'),
        previousType: 'qbittorrent'
      }
    },
    editDownloader(client) {
      this.downloaderEditor = {
        open: true,
        mode: 'edit',
        originalId: client.id,
        draft: this.normalizeDownloaderDraft({ ...client }),
        previousType: client.type
      }
    },
    closeDownloaderEditor() {
      this.downloaderEditor = { open: false, mode: 'new', originalId: '', draft: null, previousType: '' }
    },
    applyDownloaderEditor() {
      const draft = this.downloaderEditor.draft
      if (!draft) return
      const client = this.normalizeDownloaderDraft(draft)
      if (this.downloaderEditor.mode === 'new') {
        this.downloaders.clients = [...this.downloaderClients, client]
        if (!this.downloaders.default_id) this.downloaders.default_id = client.id
      } else {
        this.downloaders.clients = this.downloaderClients.map(item => (
          item.id === this.downloaderEditor.originalId ? client : item
        ))
        if (this.downloaders.default_id === this.downloaderEditor.originalId) {
          this.downloaders.default_id = client.id
        }
      }
      this.closeDownloaderEditor()
    },
    syncDownloaderDraftDefaults() {
      const draft = this.downloaderEditor.draft
      if (!draft) return
      const previousType = this.downloaderEditor.previousType
      const previousPlaceholder = this.downloaderAddressPlaceholder(previousType)
      if (!draft.name || this.downloaderTypes.some(type => type.label === draft.name)) {
        draft.name = this.downloaderTypeLabel(draft.type)
      }
      if (!draft.address || draft.address === previousPlaceholder) {
        draft.address = this.downloaderAddressPlaceholder(draft.type)
      }
      this.downloaderEditor.previousType = draft.type
    },
    removeDownloader(id) {
      this.downloaders.clients = this.downloaderClients.filter(client => client.id !== id)
      if (this.downloaders.default_id === id) {
        this.downloaders.default_id = this.downloaderClients[0]?.id || ''
      }
    },
    setDefaultDownloader(id) {
      this.downloaders.default_id = id
    },
    downloaderTypeLabel(type) {
      return this.downloaderTypes.find(item => item.value === type)?.label || type || '下载器'
    },
    downloaderTypeMark(type) {
      const map = {
        openlist: '115',
        qbittorrent: 'QB',
        transmission: 'TR',
        synology: 'SY',
        aria2: 'A2',
        deluge: 'DE',
        flood: 'FL',
        rutorrent: 'RU',
        utorrent: 'µT',
      }
      return map[type] || String(type || 'DL').slice(0, 2).toUpperCase()
    },
    downloaderAddressPlaceholder(type) {
      const map = {
        openlist: 'https://fox.oplist.org',
        qbittorrent: 'http://localhost:8080',
        transmission: 'http://localhost:9091',
        synology: 'http://nas:5000',
        aria2: 'http://localhost:6800',
        deluge: 'http://localhost:8112',
        flood: 'http://localhost:3000',
        rutorrent: 'https://myrut.com/rutorrent',
        utorrent: 'http://127.0.0.1:8080/gui/',
      }
      return map[type] || 'http://localhost'
    },
    downloaderPathPlaceholder(type) {
      if (type === 'synology') return 'video/downloads'
      if (type === 'qbittorrent') return '/downloads 或 category:Movies'
      if (type === 'openlist') return '/115/AV'
      if (type === 'utorrent') return 'movie\\ 或留空'
      return '/downloads'
    },
    supportsDownloaderTags(type) {
      return ['qbittorrent', 'transmission', 'deluge', 'flood', 'rutorrent', 'utorrent'].includes(type)
    },
    shortDownloaderAddress(address) {
      const value = String(address || '').trim()
      if (!value) return ''
      try {
        const url = new URL(value)
        return `${url.host}${url.pathname === '/' ? '' : url.pathname}`.replace(/\/$/, '')
      } catch (_) {
        return value.replace(/^https?:\/\//, '').replace(/\/$/, '')
      }
    },
    downloaderPathSummary(client) {
      if (client.default_path) return client.default_path
      if (client.category) return `分类 ${client.category}`
      return '默认路径'
    },
    tokenPlaceholder(type) {
      return type === 'aria2' ? 'rpc-secret，可选' : '可选'
    },
    normalizedDownloaderPayload() {
      return {
        default_id: this.downloaders.default_id,
        clients: this.downloaderClients.map(client => ({
          id: client.id,
          type: client.type,
          name: client.name,
          enabled: Boolean(client.enabled),
          address: client.address || '',
          username: client.username || '',
          password: client.password || '',
          token: client.token || '',
          default_path: client.default_path || '',
          category: client.category || '',
          tags: client.tags || '',
          paused: Boolean(client.paused),
          timeout: Number(client.timeout || 30),
        }))
      }
    },
    async saveDownloaders() {
      if (this.savingDownloaders) return
      this.savingDownloaders = true
      try {
        const resp = await api.updateDownloaders(this.normalizedDownloaderPayload())
        this.downloaders = {
          default_id: resp.data.default_id || '',
          clients: (resp.data.clients || []).map(client => ({ ...client })),
          types: resp.data.types || this.downloaderTypes,
        }
        this.$message?.success?.('下载源已保存')
      } catch (e) {
        console.error('Save downloaders failed:', e)
      } finally {
        this.savingDownloaders = false
      }
    },
    async testDownloader(client) {
      if (this.testingDownloaderId) return
      this.testingDownloaderId = client.id
      try {
        const resp = await api.testDownloader(client)
        this.downloaderTestMessages = {
          ...this.downloaderTestMessages,
          [client.id]: { ok: Boolean(resp.data.ok), message: resp.data.ok ? `连接正常：${resp.data.message || 'OK'}` : `连接失败：${resp.data.message || '未知错误'}` }
        }
      } catch (e) {
        this.downloaderTestMessages = {
          ...this.downloaderTestMessages,
          [client.id]: { ok: false, message: `连接失败：${e.response?.data?.detail || e.message}` }
        }
      } finally {
        this.testingDownloaderId = ''
      }
    },
    syncCandidateRoute() {
      if (this.activeTab !== 'candidates') return
      this.replaceDownloadRoute(this.candidateRouteQuery())
    },
    setCandidateStatus(status) {
      this.pushDownloadRoute(this.candidateRouteQuery({ status, needs_magnet: null, page: 1 }))
    },
    setNeedsMagnet(needs) {
      this.pushDownloadRoute(this.candidateRouteQuery({ status: 'candidate', needs_magnet: needs, page: 1 }))
    },
    setCandidateSource(source) {
      this.pushDownloadRoute(this.candidateRouteQuery({ source, page: 1 }))
    },
    openCandidatePreset({ status = 'candidate', source = '', needs_magnet = null } = {}) {
      this.pushDownloadRoute(this.candidateRouteQuery({ status, source, needs_magnet, page: 1 }))
    },
    goCandidatePage(page) {
      const nextPage = Math.max(1, Math.min(this.candidateTotalPages, Number(page) || 1))
      if (nextPage === this.candidatePage) return
      this.pushDownloadRoute(this.candidateRouteQuery({ page: nextPage }))
    },
    applyCandidateRunFilters(run, overrides = {}) {
      const filters = { ...(run.filters || {}), ...overrides }
      this.pushDownloadRoute(this.candidateRouteQuery({
        status: filters.status || 'candidate',
        source: filters.source || '',
        actress_id: filters.actress_id || '',
        q: filters.q || '',
        needs_magnet: filters.needs_magnet === undefined ? null : filters.needs_magnet,
        page: 1,
      }))
    },
    toggleCandidateSelection() {
      this.selectingCandidates = !this.selectingCandidates
      if (!this.selectingCandidates) this.selectedCandidateIds = []
    },
    toggleCandidateSelected(id) {
      if (this.selectedCandidateIds.includes(id)) {
        this.selectedCandidateIds = this.selectedCandidateIds.filter(item => item !== id)
      } else {
        this.selectedCandidateIds = [...this.selectedCandidateIds, id]
      }
    },
    selectAllVisibleCandidates() {
      this.selectedCandidateIds = [...new Set([...this.selectedCandidateIds, ...this.candidates.map(c => c.id)])]
    },
    clearCandidateSelection() {
      this.selectedCandidateIds = []
    },
    isCandidateMutating(id) {
      return Boolean(this.candidateMutations[id]) || this.bulkCandidateLoading || Boolean(this.candidateBatchProcessing)
    },
    setCandidateMutation(id, action) {
      this.candidateMutations = { ...this.candidateMutations, [id]: action }
    },
    clearCandidateMutation(id) {
      const next = { ...this.candidateMutations }
      delete next[id]
      this.candidateMutations = next
    },
    setTaskRetrying(id, loading) {
      if (loading) {
        this.retryingTasks = { ...this.retryingTasks, [id]: true }
        return
      }
      const next = { ...this.retryingTasks }
      delete next[id]
      this.retryingTasks = next
    },
    async bulkRejectCandidates() {
      if (this.selectedCandidateIds.length === 0 || this.bulkCandidateLoading) return
      const confirmed = await requestConfirm({
        title: '批量拒绝候选',
        message: `确认拒绝 ${this.selectedCandidateIds.length} 个下载候选？`,
        details: '拒绝后可在已拒绝筛选中批量恢复。',
        confirmText: '拒绝',
        tone: 'danger'
      })
      if (!confirmed) return
      this.bulkCandidateLoading = true
      try {
        await api.bulkRejectDownloadCandidates(this.selectedCandidateIds)
        this.selectedCandidateIds = []
        await this.loadCandidates()
      } catch (e) {
        console.error('Bulk reject candidates failed:', e)
      } finally {
        this.bulkCandidateLoading = false
      }
    },
    async bulkRestoreCandidates() {
      if (this.selectedCandidateIds.length === 0 || this.bulkCandidateLoading) return
      this.bulkCandidateLoading = true
      try {
        await api.bulkRestoreDownloadCandidates(this.selectedCandidateIds)
        this.selectedCandidateIds = []
        await this.loadCandidates()
      } catch (e) {
        console.error('Bulk restore candidates failed:', e)
      } finally {
        this.bulkCandidateLoading = false
      }
    },
    async editCandidateMagnet(candidate) {
      if (this.isCandidateMutating(candidate.id)) return
      this.magnetEditor = {
        open: true,
        candidate,
        value: candidate.magnet || ''
      }
    },
    closeMagnetEditor() {
      if (this.magnetEditor.candidate && this.isCandidateMutating(this.magnetEditor.candidate.id)) return
      this.magnetEditor = { open: false, candidate: null, value: '' }
    },
    updateMagnetEditorValue(value) {
      this.magnetEditor = { ...this.magnetEditor, value }
    },
    async submitMagnetEditor() {
      const candidate = this.magnetEditor.candidate
      const magnet = this.magnetEditor.value.trim()
      if (!candidate || !magnet || this.isCandidateMutating(candidate.id)) return
      this.setCandidateMutation(candidate.id, 'magnet')
      try {
        await api.updateDownloadCandidateMagnet(candidate.id, magnet)
        this.closeMagnetEditor()
        await this.loadCandidates()
      } catch (e) {
        console.error('Update candidate magnet failed:', e)
      } finally {
        this.clearCandidateMutation(candidate.id)
      }
    },
    candidateFilterPayload(overrides = {}) {
      const payload = {
        status: this.candidateFilter.status || 'candidate',
        source: this.candidateFilter.source || undefined,
        actress_id: this.candidateFilter.actress_id ? Number(this.candidateFilter.actress_id) : undefined,
        q: this.candidateFilter.q || undefined,
        needs_magnet: this.candidateFilter.needs_magnet,
        limit: this.candidates.length || 50,
        ...overrides,
      }
      Object.keys(payload).forEach((key) => {
        if (payload[key] === undefined || payload[key] === '') delete payload[key]
      })
      return payload
    },
    async enrichCandidateMagnet(candidate) {
      if (this.isCandidateMutating(candidate.id)) return
      this.setCandidateMutation(candidate.id, 'enrich')
      try {
        const resp = await api.enrichDownloadCandidateMagnet(candidate.id)
        const action = resp.data?.action
        if (action === 'magnet_enriched') this.$message?.success?.('已补充 magnet')
        else if (action === 'magnet_not_found') this.$message?.warning?.('未找到可用 magnet')
        else if (action === 'already_has_magnet') this.$message?.info?.('候选已有 magnet')
        await this.loadCandidates()
      } catch (e) {
        console.error('Enrich candidate magnet failed:', e)
      } finally {
        this.clearCandidateMutation(candidate.id)
      }
    },
    async processCandidate(candidate) {
      if (this.isCandidateMutating(candidate.id)) return
      const confirmed = await requestConfirm({
        title: '按策略处理候选',
        message: `确认按当前策略处理 ${candidate.dvd_id || candidate.content_id}？`,
        details: '可能会补充磁力并下发到下载源；不满足策略时会保持候选状态。',
        confirmText: '处理',
      })
      if (!confirmed) return
      this.setCandidateMutation(candidate.id, 'process')
      try {
        const resp = await api.processDownloadCandidate(candidate.id, { enrich: true })
        const action = resp.data?.action
        if (action === 'sent') this.$message?.success?.('候选已下发下载')
        else if (action === 'manual_required') this.$message?.info?.('当前为人工批准策略')
        else if (action?.startsWith('skipped')) this.$message?.info?.('候选未满足策略条件')
        else if (action?.startsWith('failed')) this.$message?.error?.('候选处理失败')
        await this.loadCandidates()
        await this.loadTasks()
      } catch (e) {
        console.error('Process candidate failed:', e)
      } finally {
        this.clearCandidateMutation(candidate.id)
      }
    },
    async enrichVisibleCandidateMagnets() {
      if (this.candidateBatchProcessing) return
      const targets = this.candidates.filter(candidate => (
        (candidate.status === 'candidate' || candidate.status === 'failed') && !candidate.magnet
      ))
      if (!targets.length) {
        this.$message?.info?.('当前列表没有待补磁力的候选')
        return
      }
      const confirmed = await requestConfirm({
        title: '批量补充磁力',
        message: `确认为当前列表中的 ${targets.length} 个下载候选查找并写入磁力？`,
        details: '会逐个访问候选的磁力来源，并把找到的磁力保存到候选记录。',
        confirmText: '开始补磁力',
      })
      if (!confirmed) return
      this.candidateBatchProcessing = 'enrich'
      try {
        let enriched = 0
        for (const candidate of targets) {
          const resp = await api.enrichDownloadCandidateMagnet(candidate.id)
          if (resp.data?.action === 'magnet_enriched') enriched += 1
        }
        this.$message?.success?.(`已检查 ${targets.length} 个，补磁力 ${enriched} 个`)
        await this.loadCandidates()
      } catch (e) {
        console.error('Batch enrich candidates failed:', e)
      } finally {
        this.candidateBatchProcessing = ''
      }
    },
    async processVisibleCandidates() {
      if (this.candidateBatchProcessing) return
      this.candidateBatchProcessing = 'dry-run'
      let preview
      try {
        const resp = await api.processDownloadCandidates(this.candidateFilterPayload({ enrich: true, dry_run: true }))
        preview = resp.data || {}
      } catch (e) {
        console.error('Preview candidate processing failed:', e)
        this.candidateBatchProcessing = ''
        return
      }
      const previewCounts = preview.counts || {}
      const confirmed = await requestConfirm({
        title: '按策略处理候选',
        message: this.processPreviewMessage(preview),
        details: this.processPreviewDetails(previewCounts, preview.limits || {}),
        confirmText: '处理',
      })
      if (!confirmed) return
      this.candidateBatchProcessing = 'process'
      try {
        const resp = await api.processDownloadCandidates(this.candidateFilterPayload({ enrich: true }))
        const counts = resp.data?.counts || {}
        const skipped = (counts.manual_required || 0) + (counts.skipped_source || 0) + (counts.skipped_missing_magnet || 0) + (counts.skipped_status || 0)
        this.$message?.success?.(`处理 ${resp.data?.total || 0} 个：下发 ${counts.sent || 0}，跳过 ${skipped}`)
        await this.loadCandidates()
        await this.loadCandidateRuns()
        await this.loadTasks()
      } catch (e) {
        console.error('Batch process candidates failed:', e)
      } finally {
        this.candidateBatchProcessing = ''
      }
    },
    processPreviewMessage(preview = {}) {
      const counts = preview.counts || {}
      const wouldSend = counts.would_send || 0
      const wouldEnrich = counts.would_enrich_magnet || 0
      const skippedLimit = counts.would_skip_limit || 0
      return `预演 ${preview.total || 0} 个：可直接下发 ${wouldSend}，需补磁力 ${wouldEnrich}，受上限跳过 ${skippedLimit}。`
    },
    processPreviewDetails(counts = {}, limits = {}) {
      const skipped = Object.entries(counts)
        .filter(([action]) => action.startsWith('skipped') || action === 'manual_required')
        .reduce((sum, [, value]) => sum + Number(value || 0), 0)
      const remaining = limits.remaining === null || limits.remaining === undefined ? '不限' : limits.remaining
      const perRun = limits.per_run || 0
      const per24h = limits.per_24h || 0
      return `策略跳过 ${skipped}。单次上限 ${perRun || '不限'}，24 小时上限 ${per24h || '不限'}，当前剩余额度 ${remaining}。`
    },
    async retryFailedCandidateRun(run) {
      if (!run?.id || this.candidateBatchProcessing) return
      const confirmed = await requestConfirm({
        title: '重试失败候选',
        message: `确认重试本次处理中的 ${run.failed || 0} 个失败候选？`,
        details: '会复用当时策略并重新补磁力/下发，仍失败的候选会留在失败队列。',
        confirmText: '重试',
      })
      if (!confirmed) return
      this.candidateBatchProcessing = 'retry-run'
      try {
        const resp = await api.retryDownloadCandidateRunFailed(run.id, { enrich: true })
        const counts = resp.data?.counts || {}
        this.$message?.success?.(`已重试 ${resp.data?.total || 0} 个：下发 ${counts.sent || 0}，失败 ${counts.failed_downloader || 0}`)
        await this.loadCandidates()
        await this.loadCandidateRuns()
        await this.loadTasks()
      } catch (e) {
        console.error('Retry failed candidate run failed:', e)
      } finally {
        this.candidateBatchProcessing = ''
      }
    },
    async openCandidateDetail(candidate) {
      this.candidateDetail = { open: true, loading: true, data: candidate }
      try {
        const resp = await api.getDownloadCandidate(candidate.id)
        this.candidateDetail = { open: true, loading: false, data: resp.data.data }
      } catch (e) {
        console.error('Load candidate detail failed:', e)
        this.candidateDetail = { open: true, loading: false, data: candidate }
      }
    },
    closeCandidateDetail() {
      this.candidateDetail = { open: false, loading: false, data: null }
    },
    eventActionLabel(action) {
      const map = {
        upsert: '写入候选',
        magnet_updated: '手动更新磁力',
        magnet_enriched: '自动补充磁力',
        magnet_enrich_failed: '磁力补充失败',
        magnet_enrich_skipped: '跳过补磁力',
        policy_skipped: '策略跳过',
        auto_approved: '自动下发',
        approved: '人工批准',
        approve_failed: '批准失败',
        process_failed: '处理失败',
        rejected: '拒绝候选',
        bulk_rejected: '批量拒绝',
        bulk_restored: '批量恢复',
      }
      return map[action] || action
    },
    candidateRunPolicyLabel(policy) {
      const map = { manual: '人工批准', rules: '规则自动', auto: '全自动' }
      return map[policy] || '人工批准'
    },
    candidateRunTriggerLabel(trigger) {
      const map = { manual: '人工触发', system: '系统触发' }
      return map[trigger] || trigger || '未知触发'
    },
    async approveCandidate(candidate) {
      if (this.isCandidateMutating(candidate.id)) return
      const confirmed = await requestConfirm({
        title: '批准下载候选',
        message: `确认批准 ${candidate.dvd_id || candidate.content_id} 并下发下载？`,
        details: candidate.magnet ? '会创建真实下载任务并发送到当前默认下载源。' : '该候选没有磁力链接，批准可能失败或需要先补磁力。',
        confirmText: '批准',
      })
      if (!confirmed) return
      this.setCandidateMutation(candidate.id, 'approve')
      try {
        await api.approveDownloadCandidate(candidate.id)
        await this.loadCandidates()
        await this.loadTasks()
      } catch (e) {
        console.error('Approve candidate failed:', e)
      } finally {
        this.clearCandidateMutation(candidate.id)
      }
    },
    async rejectCandidate(candidate) {
      if (this.isCandidateMutating(candidate.id)) return
      const confirmed = await requestConfirm({
        title: '拒绝下载候选',
        message: `确认拒绝 ${candidate.dvd_id || candidate.content_id}？`,
        details: candidate.title || '',
        confirmText: '拒绝',
        tone: 'danger'
      })
      if (!confirmed) return
      this.setCandidateMutation(candidate.id, 'reject')
      try {
        await api.rejectDownloadCandidate(candidate.id)
        await this.loadCandidates()
      } catch (e) {
        console.error('Reject candidate failed:', e)
      } finally {
        this.clearCandidateMutation(candidate.id)
      }
    },
    goCandidateActor(candidate) {
      if (!candidate.actress_id) return
      const name = candidate.actress_name || candidate.actress_id
      this.$router.push({
        path: `/actor/${encodeURIComponent(name)}`,
        query: { name, actress_id: candidate.actress_id },
      })
    },
    goCandidateSupplement(candidate) {
      if (!candidate.actress_id) return
      this.$router.push({
        path: '/supplement',
        query: { tab: 'movies', actress_id: candidate.actress_id, q: candidate.dvd_id || candidate.content_id || '' },
      })
    },
    async remove(id) {
      const confirmed = await requestConfirm({
        title: '删除下载任务',
        message: `确认删除任务 #${id}？`,
        details: '只会移除 JavHub 中的任务记录，不会自动删除下载器里的文件。',
        confirmText: '删除',
        tone: 'danger'
      })
      if (!confirmed) return
      try {
        await api.deleteDownload(id)
        this.loadTasks()
      } catch (e) {
        console.error('Failed to delete:', e)
      }
    },
    async retry(task) {
      if (this.retryingTasks[task.id]) return
      this.setTaskRetrying(task.id, true)
      try {
        await api.createDownload({
          content_id: task.content_id || task.code,
          title: task.title,
          magnet: task.magnet,
          path: task.path,
          downloader_id: task.downloader_id || ''
        })
        await this.loadTasks()
      } catch (e) {
        console.error('Failed to retry download:', e)
      } finally {
        this.setTaskRetrying(task.id, false)
      }
    },
    statusBadge(status) {
      const map = { pending: 'badge-pending', downloading: 'badge-info', completed: 'badge-success', failed: 'badge-error' }
      return map[status] || 'badge-pending'
    },
    statusLabel(status) {
      const map = { pending: '待处理', downloading: '下载中', completed: '已完成', failed: '失败' }
      return map[status] || status
    },
    candidateBadge(status) {
      const map = { candidate: 'badge-pending', approved: 'badge-info', sent: 'badge-success', failed: 'badge-error', rejected: 'badge-pending' }
      return map[status] || 'badge-pending'
    },
    candidateStatusLabel(status) {
      const map = { candidate: '待确认', approved: '已批准', sent: '已下发', failed: '失败', rejected: '已拒绝' }
      return map[status] || status
    },
    candidateSourceLabel(source) {
      const map = { subscription: '订阅', inventory: '库存', supplement: '补全', manual: '手动' }
      return map[source] || source || '未知来源'
    },
    formatTime(time) {
      if (!time) return ''
      const d = new Date(time)
      return `${d.getMonth()+1}/${d.getDate()} ${d.getHours().toString().padStart(2,'0')}:${d.getMinutes().toString().padStart(2,'0')}`
    }
  }
}
</script>

<style scoped src="../features/home/home.css"></style>
