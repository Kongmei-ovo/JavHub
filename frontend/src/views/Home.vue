<template>
  <div class="home page-shell page-shell--workspace">
    <div class="page-header">
      <div class="header-left">
        <h1>下载管理</h1>
        <p class="header-subtitle">
          <span class="total-tasks">{{ totalTaskCount }} 个任务</span>
          <span v-if="stats.downloading > 0" class="downloading-hint"> · {{ stats.downloading }} 个下载中</span>
          <span v-if="candidateStats.candidate > 0" class="downloading-hint"> · {{ candidateStats.candidate }} 个候选待确认</span>
        </p>
      </div>
      <div class="header-actions">
        <button class="btn btn-ghost" type="button" @click="$router.push('/search')">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="16" height="16"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/></svg>
          搜索影片
        </button>
        <button class="btn btn-ghost" type="button" @click="$router.push('/genres')">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="16" height="16"><path d="M4 19.5A2.5 2.5 0 016.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 014 19.5v-15A2.5 2.5 0 016.5 2z"/></svg>
          浏览分类
        </button>
        <button class="btn btn-primary" type="button" @click="loadTasks">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="16" height="16"><polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 11-2.12-9.36L23 10"/></svg>
          刷新
        </button>
      </div>
    </div>

    <DownloadStatsBar :stats="stats" :candidate-stats="candidateStats" :stats-loaded="statsLoaded" @select-status="setTaskStatus" @open-preset="openCandidatePreset" />

    <div v-if="candidateFilterLedger.length" class="candidate-filter-ledger" aria-label="当前候选筛选">
      <span v-for="filter in candidateFilterLedger" :key="filter.key" class="candidate-filter-token">{{ filter.label }}</span>
    </div>
    <div v-if="filterStatus" class="filter-bar" @click="clearTaskStatus">
      <span class="filter-hint">筛选: <strong>{{ filterStatus }}</strong> (点击清除)</span>
    </div>
    <div class="download-tabs">
      <button class="tab-btn" type="button" :class="{ active: activeTab === 'tasks' }" @click="openTaskTab">真实任务</button>
      <button class="tab-btn" type="button" :class="{ active: activeTab === 'candidates' }" @click="openCandidateTab">下载候选 <span v-if="candidateStats.candidate" class="tab-badge">{{ candidateStats.candidate }}</span></button>
      <button class="tab-btn" type="button" :class="{ active: activeTab === 'downloaders' }" @click="openDownloaderTab">下载源 <span v-if="enabledDownloaderCount" class="tab-badge subtle">{{ enabledDownloaderCount }}</span></button>
    </div>

    <DownloadCandidatePanel
      v-if="activeTab === 'candidates'"
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
      :candidate-repair-scope="candidateRepairScope"
      :filtered-candidates="filteredCandidates"
      :candidate-mutations="candidateMutations"
      :magnet-editor="magnetEditor"
      :candidate-detail="candidateDetail"
      @update-candidate-search="updateCandidateSearch"
      @search="submitCandidateSearch"
      @set-status="setCandidateStatus"
      @set-needs-magnet="setNeedsMagnet"
      @set-source="setCandidateSource"
      @set-latest-event="setCandidateLatestEvent"
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
    <TaskList
      v-else-if="activeTab === 'tasks'"
      :tasks="filteredTasks"
      :retrying-tasks="retryingTasks"
      :status-badge="statusBadge"
      :status-label="statusLabel"
      :format-time="formatTime"
      :downloader-type-label="downloaderTypeLabel"
      :task-empty-title="taskEmptyTitle"
      :task-empty-hint="taskEmptyHint"
      :task-empty-primary-label="taskEmptyPrimaryLabel"
      @retry="retry"
      @remove="remove"
      @empty-action="handleTaskEmptyAction"
      @parse="$router.push('/parse')"
    />
  </div>
</template>

<script>
import { defineAsyncComponent } from 'vue'
import api from '../api'
import DownloadStatsBar from '../features/home/DownloadStatsBar.vue'
import TaskList from '../features/home/TaskList.vue'
import * as homePresentation from '../features/home/homePresentation'
import { requestConfirm } from '../utils/confirmDialog'
import {
  createDefaultDownloaderTypes,
  downloaderAddressPlaceholder as defaultDownloaderAddressPlaceholder,
  downloaderPathPlaceholder as defaultDownloaderPathPlaceholder,
  downloaderTypeMark as defaultDownloaderTypeMark,
  supportsDownloaderTags as defaultSupportsDownloaderTags,
  tokenPlaceholder as defaultTokenPlaceholder,
} from '../features/downloaders/downloaderPresentation'

const DownloadCandidatePanel = defineAsyncComponent(() => import('../features/candidates/DownloadCandidatePanel.vue'))
const DownloaderManagementPanel = defineAsyncComponent(() => import('../features/downloaders/DownloaderManagementPanel.vue'))
const candidateStats = () => ({ candidate: 0, approved: 0, rejected: 0, sent: 0, failed: 0, needs_magnet: 0, by_source: {}, candidate_by_source: {} })
const eventLabels = { without_event: '未处理', magnet_enrich_failed: '补磁力失败', magnet_enriched: '已补磁力', policy_skipped: '策略跳过', process_failed: '处理失败', approve_failed: '批准失败', supplement_imported: '补全导入' }
const cleanObject = (target) => { Object.keys(target).forEach(key => { if (target[key] === undefined || target[key] === '' || target[key] === null) delete target[key] }); return target }

export default {
  name: 'Home',
  components: { DownloadStatsBar, TaskList, DownloadCandidatePanel, DownloaderManagementPanel },
  data() {
    const q = this.$route.query
    return {
      activeTab: ['candidates', 'downloaders'].includes(q.tab) ? q.tab : 'tasks',
      tasks: [], candidates: [], stats: { pending: 0, downloading: 0, completed: 0, failed: 0 }, statsLoaded: false, filterStatus: null, timer: null, retryingTasks: {},
      candidateStats: candidateStats(), candidatePage: Number(this.$route.query.page || 1) || 1, candidatePageSize: 50, candidateTotal: 0, candidateTotalPages: 1, selectingCandidates: false, selectedCandidateIds: [], bulkCandidateLoading: false, candidateBatchProcessing: '', candidateRuns: [], candidateRunsLoading: false, candidateMutations: {},
      candidateFilter: { status: q.status || 'candidate', source: q.source || '', actress_id: q.actress_id || '', q: q.q || '', needs_magnet: q.needs_magnet === '1' ? true : (q.needs_magnet === '0' ? false : null), missing_cover: this.$route.query.missing_cover === '1', latest_event_action: q.latest_event_action || '' },
      magnetEditor: { open: false, candidate: null, value: '' }, candidateDetail: { open: false, loading: false, data: null },
      downloaders: { default_id: '', clients: [], types: [] }, downloaderTypes: createDefaultDownloaderTypes(), savingDownloaders: false, testingDownloaderId: '', downloaderTestMessages: {}, downloaderEditor: { open: false, mode: 'new', originalId: '', draft: null, previousType: '' }, downloaderIdSeed: 1,
    }
  },
  computed: {
    totalTaskCount() { return this.stats.pending + this.stats.downloading + this.stats.completed + this.stats.failed },
    filteredTasks() { return this.filterStatus ? this.tasks.filter(t => t.status === this.filterStatus) : this.tasks },
    filteredCandidates() { return this.candidates },
    candidateFilterLedger() {
      if (this.activeTab !== 'candidates') return []
      const items = [{ key: 'status', label: homePresentation.candidateStatusLabel(this.candidateFilter.status || 'candidate') }]
      if (this.candidateFilter.needs_magnet === true) items.push({ key: 'needs_magnet', label: '待补磁力' })
      if (this.candidateFilter.needs_magnet === false) items.push({ key: 'ready', label: '可批准' })
      if (this.candidateFilter.missing_cover) items.push({ key: 'missing_cover', label: '缺封面' })
      if (this.candidateFilter.source) items.push({ key: 'source', label: `来源 ${homePresentation.candidateSourceLabel(this.candidateFilter.source)}` })
      if (this.candidateFilter.latest_event_action) items.push({ key: 'event', label: `最近 ${this.candidateEventActionLabel(this.candidateFilter.latest_event_action)}` })
      if (this.candidateFilter.actress_id) items.push({ key: 'actor', label: `演员 ${this.candidateFilter.actress_id}` })
      if (this.candidateFilter.q) items.push({ key: 'q', label: `搜索 ${this.candidateFilter.q}` })
      items.push({ key: 'total', label: `当前 ${this.candidateTotal} 条` })
      return items
    },
    visibleMagnetTargetCount() { return this.filteredCandidates.filter(candidate => (candidate.status === 'candidate' || candidate.status === 'failed') && !candidate.magnet).length },
    candidateRepairScopeLabel() { if (this.candidateFilter.needs_magnet === true) return '待补磁力修复'; if (this.candidateFilter.missing_cover) return '缺封面候选修复'; if (this.candidateFilter.latest_event_action) return `最近 ${this.candidateEventActionLabel(this.candidateFilter.latest_event_action)}`; return '' },
    candidateRepairScope() {
      const scopeLabel = this.candidateRepairScopeLabel
      if (!scopeLabel) return null
      const visibleMagnetTargets = this.visibleMagnetTargetCount
      return { scopeLabel: this.candidateRepairScopeLabel, total: this.candidateTotal, visibleCount: this.filteredCandidates.length, visibleMagnetTargets }
    },
    downloaderClients() { return this.downloaders.clients || [] },
    enabledDownloaderCount() { return this.downloaderClients.filter(client => client.enabled).length },
    defaultDownloaderLabel() { const client = this.downloaderClients.find(item => item.id === this.downloaders.default_id); return client?.name || this.downloaderTypeLabel(client?.type) || '未设置' },
    taskEmptyHint() { if (this.filterStatus) return '当前筛选没有任务，可以清除筛选查看全部。'; if (this.candidateStats.candidate > 0) return '已有下载候选待确认，优先处理候选再下发任务。'; return '可以从影片检索或磁链解析添加下载任务。' },
    taskEmptyTitle() { return `暂无${this.filterStatus ? this.statusLabel(this.filterStatus) : ''}任务` },
    taskEmptyPrimaryLabel() { if (this.filterStatus) return '清除筛选'; if (this.candidateStats.candidate > 0) return `查看 ${this.candidateStats.candidate} 个候选`; return '搜索影片' },
  },
  mounted() { this.applyDownloadRoute(this.$route.query); this.loadTasks(); if (this.activeTab === 'candidates') { this.loadCandidates(); this.loadCandidateRuns() } else this.loadCandidateSummary(); if (this.activeTab === 'downloaders') this.loadDownloaders(); this.timer = setInterval(this.loadTasks, 30000) },
  beforeUnmount() { if (this.timer) clearInterval(this.timer) },
  watch: { '$route.query'(query) { if (!this.applyDownloadRoute(query)) return; if (this.activeTab === 'candidates') { this.loadCandidates(); this.loadCandidateRuns() } else if (this.activeTab === 'downloaders') this.loadDownloaders() } },
  methods: {
    applyDownloadRoute(query = {}) {
      let changed = false
      const tab = ['tasks', 'candidates', 'downloaders'].includes(query.tab) ? query.tab : 'tasks'
      if (this.activeTab !== tab) { this.activeTab = tab; changed = true }
      const taskStatus = tab === 'tasks' ? (query.task_status || '') : ''
      if ((this.filterStatus || '') !== taskStatus) { this.filterStatus = taskStatus || null; changed = true }
      const nextFilter = { status: tab === 'candidates' ? (query.status || 'candidate') : this.candidateFilter.status, source: tab === 'candidates' ? (query.source || '') : this.candidateFilter.source, actress_id: tab === 'candidates' ? (query.actress_id || '') : this.candidateFilter.actress_id, q: tab === 'candidates' ? (query.q || '') : this.candidateFilter.q, needs_magnet: query.needs_magnet === '1' ? true : (query.needs_magnet === '0' ? false : null), missing_cover: tab === 'candidates' ? query.missing_cover === '1' : this.candidateFilter.missing_cover, latest_event_action: tab === 'candidates' ? (query.latest_event_action || '') : this.candidateFilter.latest_event_action, page: tab === 'candidates' ? (Number(query.page || 1) || 1) : this.candidatePage }
      const { page, ...filterOnly } = nextFilter
      if (this.candidatePage !== page) { this.candidatePage = page; changed = true }
      if (JSON.stringify(filterOnly) !== JSON.stringify(this.candidateFilter)) { this.candidateFilter = filterOnly; changed = true }
      return changed
    },
    cleanDownloadQuery(query = {}) { return cleanObject({ ...query }) },
    pushDownloadRoute(query = {}) { const next = this.cleanDownloadQuery(query); if (JSON.stringify(next) !== JSON.stringify(this.$route.query || {})) this.$router.push({ path: this.$route.path, query: next }).catch(() => {}) },
    replaceDownloadRoute(query = {}) { const next = this.cleanDownloadQuery(query); if (JSON.stringify(next) !== JSON.stringify(this.$route.query || {})) this.$router.replace({ path: this.$route.path, query: next }).catch(() => {}) },
    candidateRouteQuery(overrides = {}) {
      const filter = { ...this.candidateFilter, page: this.candidatePage, ...overrides }, query = { tab: 'candidates' }
      if (filter.status) query.status = filter.status
      if (filter.source) query.source = filter.source
      if (filter.actress_id) query.actress_id = filter.actress_id
      if (filter.q) query.q = filter.q
      if (filter.needs_magnet === true) query.needs_magnet = '1'
      if (filter.needs_magnet === false) query.needs_magnet = '0'
      if (filter.missing_cover) query.missing_cover = '1'
      if (filter.latest_event_action) query.latest_event_action = filter.latest_event_action
      if (filter.page && Number(filter.page) > 1) query.page = String(Number(filter.page))
      return query
    },
    async loadTasks() { try { const resp = await api.getDownloads(); this.tasks = resp.data.data || []; this.stats = { pending: this.tasks.filter(t => t.status === 'pending').length, downloading: this.tasks.filter(t => t.status === 'downloading').length, completed: this.tasks.filter(t => t.status === 'completed').length, failed: this.tasks.filter(t => t.status === 'failed').length }; this.statsLoaded = true } catch (e) { console.error('Failed to load tasks:', e) } },
    async loadCandidates() {
      try {
        const params = {}
        if (this.candidateFilter.status) params.status = this.candidateFilter.status
        if (this.candidateFilter.source) params.source = this.candidateFilter.source
        if (this.candidateFilter.actress_id) params.actress_id = this.candidateFilter.actress_id
        if (this.candidateFilter.q) params.q = this.candidateFilter.q
        if (this.candidateFilter.needs_magnet !== null) params.needs_magnet = this.candidateFilter.needs_magnet
        if (this.candidateFilter.missing_cover) params.missing_cover = this.candidateFilter.missing_cover
        if (this.candidateFilter.latest_event_action) params.latest_event_action = this.candidateFilter.latest_event_action
        params.page = this.candidatePage; params.page_size = this.candidatePageSize; params.include_stats = false
        const resp = await api.listDownloadCandidates(params)
        this.candidates = resp.data.data || []; this.candidateTotal = Number(resp.data.total || this.candidates.length) || 0; this.candidateTotalPages = Number(resp.data.total_pages || 1) || 1
        this.selectedCandidateIds = this.selectedCandidateIds.filter(id => this.candidates.some(c => c.id === id)); this.syncCandidateRoute(); await this.loadCandidateSummary()
      } catch (e) { console.error('Failed to load candidates:', e) }
    },
    async loadCandidateSummary() { try { const resp = await api.getDownloadCandidateSummary({ status: 'candidate', include_sources: true }); this.candidateStats = resp.data || this.candidateStats } catch (e) { console.error('Failed to load candidate summary:', e) } },
    async loadCandidateRuns() { this.candidateRunsLoading = true; try { const resp = await api.listDownloadCandidateRuns(5); this.candidateRuns = resp.data.data || [] } catch (e) { console.error('Failed to load candidate runs:', e) } finally { this.candidateRunsLoading = false } },
    openCandidateTab() { this.pushDownloadRoute(this.candidateRouteQuery({ page: 1 })) },
    openDownloaderTab() { this.pushDownloadRoute({ tab: 'downloaders' }) },
    openTaskTab() { this.pushDownloadRoute({ tab: 'tasks', task_status: this.filterStatus || undefined }) },
    setTaskStatus(status) { this.pushDownloadRoute({ tab: 'tasks', task_status: status }) },
    clearTaskStatus() { this.pushDownloadRoute({ tab: 'tasks' }) },
    handleTaskEmptyAction() {
      if (this.filterStatus) this.clearTaskStatus()
      else if (this.candidateStats.candidate > 0) this.openCandidatePreset({ status: 'candidate', source: '' })
      else this.$router.push('/search')
    },
    updateCandidateSearch(value) { this.candidateFilter = { ...this.candidateFilter, q: value } },
    submitCandidateSearch() { this.pushDownloadRoute(this.candidateRouteQuery({ q: this.candidateFilter.q, page: 1 })) },
    async loadDownloaders() { try { const resp = await api.listDownloaders(), data = resp.data || {}; this.downloaders = { default_id: data.default_id || '', clients: (data.clients || []).map(client => ({ ...client })), types: data.types || this.downloaderTypes }; this.downloaderTypes = this.downloaders.types.length ? this.downloaders.types : this.downloaderTypes; if (!this.downloaders.default_id && this.downloaders.clients[0]) this.downloaders.default_id = this.downloaders.clients[0].id } catch (e) { console.error('Failed to load downloaders:', e) } },
    makeDownloaderId(type = 'qbittorrent') { let id = `${type}-${this.downloaderIdSeed++}`; while (this.downloaderClients.some(client => client.id === id)) id = `${type}-${this.downloaderIdSeed++}`; return id },
    createDownloaderDraft(type = 'qbittorrent') { return { id: this.makeDownloaderId(type), type, name: this.downloaderTypeLabel(type), enabled: true, address: this.downloaderAddressPlaceholder(type), username: '', password: '', token: '', default_path: '', category: '', tags: '', paused: false, timeout: 30 } },
    normalizeDownloaderDraft(draft) { return { id: draft.id, type: draft.type || 'qbittorrent', name: draft.name || this.downloaderTypeLabel(draft.type), enabled: Boolean(draft.enabled), address: draft.address || '', username: draft.username || '', password: draft.password || '', token: draft.token || '', default_path: draft.default_path || '', category: draft.category || '', tags: draft.tags || '', paused: Boolean(draft.paused), timeout: Number(draft.timeout || 30), password_configured: Boolean(draft.password_configured), token_configured: Boolean(draft.token_configured) } },
    openNewDownloader() { this.downloaderEditor = { open: true, mode: 'new', originalId: '', draft: this.createDownloaderDraft('qbittorrent'), previousType: 'qbittorrent' } },
    editDownloader(client) { this.downloaderEditor = { open: true, mode: 'edit', originalId: client.id, draft: this.normalizeDownloaderDraft({ ...client }), previousType: client.type } },
    closeDownloaderEditor() { this.downloaderEditor = { open: false, mode: 'new', originalId: '', draft: null, previousType: '' } },
    applyDownloaderEditor() { const draft = this.downloaderEditor.draft; if (!draft) return; const client = this.normalizeDownloaderDraft(draft); this.downloaders.clients = this.downloaderEditor.mode === 'new' ? [...this.downloaderClients, client] : this.downloaderClients.map(item => item.id === this.downloaderEditor.originalId ? client : item); if (!this.downloaders.default_id || this.downloaders.default_id === this.downloaderEditor.originalId) this.downloaders.default_id = client.id; this.closeDownloaderEditor() },
    syncDownloaderDraftDefaults() { const draft = this.downloaderEditor.draft; if (!draft) return; const previousPlaceholder = this.downloaderAddressPlaceholder(this.downloaderEditor.previousType); if (!draft.name || this.downloaderTypes.some(type => type.label === draft.name)) draft.name = this.downloaderTypeLabel(draft.type); if (!draft.address || draft.address === previousPlaceholder) draft.address = this.downloaderAddressPlaceholder(draft.type); this.downloaderEditor.previousType = draft.type },
    removeDownloader(id) { this.downloaders.clients = this.downloaderClients.filter(client => client.id !== id); if (this.downloaders.default_id === id) this.downloaders.default_id = this.downloaderClients[0]?.id || '' },
    setDefaultDownloader(id) { this.downloaders.default_id = id },
    downloaderTypeLabel(type) { return this.downloaderTypes.find(item => item.value === type)?.label || type || '下载器' },
    downloaderTypeMark(type) { return defaultDownloaderTypeMark(type) },
    downloaderAddressPlaceholder(type) { return defaultDownloaderAddressPlaceholder(type) },
    downloaderPathPlaceholder(type) { return defaultDownloaderPathPlaceholder(type) },
    supportsDownloaderTags(type) { return defaultSupportsDownloaderTags(type) },
    shortDownloaderAddress: homePresentation.shortDownloaderAddress,
    downloaderPathSummary: homePresentation.downloaderPathSummary,
    tokenPlaceholder(type) { return defaultTokenPlaceholder(type) },
    normalizedDownloaderPayload() { return { default_id: this.downloaders.default_id, clients: this.downloaderClients.map(client => ({ id: client.id, type: client.type, name: client.name, enabled: Boolean(client.enabled), address: client.address || '', username: client.username || '', password: client.password || '', token: client.token || '', default_path: client.default_path || '', category: client.category || '', tags: client.tags || '', paused: Boolean(client.paused), timeout: Number(client.timeout || 30) })) } },
    async saveDownloaders() { if (this.savingDownloaders) return; this.savingDownloaders = true; try { const resp = await api.updateDownloaders(this.normalizedDownloaderPayload()); this.downloaders = { default_id: resp.data.default_id || '', clients: (resp.data.clients || []).map(client => ({ ...client })), types: resp.data.types || this.downloaderTypes }; this.$message?.success?.('下载源已保存') } catch (e) { console.error('Save downloaders failed:', e) } finally { this.savingDownloaders = false } },
    async testDownloader(client) { if (this.testingDownloaderId) return; this.testingDownloaderId = client.id; try { const resp = await api.testDownloader(client); this.downloaderTestMessages = { ...this.downloaderTestMessages, [client.id]: { ok: Boolean(resp.data.ok), message: resp.data.ok ? `连接正常：${resp.data.message || 'OK'}` : `连接失败：${resp.data.message || '未知错误'}` } } } catch (e) { this.downloaderTestMessages = { ...this.downloaderTestMessages, [client.id]: { ok: false, message: `连接失败：${e.response?.data?.detail || e.message}` } } } finally { this.testingDownloaderId = '' } },
    syncCandidateRoute() { if (this.activeTab === 'candidates') this.replaceDownloadRoute(this.candidateRouteQuery()) },
    setCandidateStatus(status) { this.pushDownloadRoute(this.candidateRouteQuery({ status, needs_magnet: null, page: 1 })) },
    setNeedsMagnet(needs) { this.pushDownloadRoute(this.candidateRouteQuery({ status: 'candidate', needs_magnet: needs, page: 1 })) },
    setCandidateSource(source) { this.pushDownloadRoute(this.candidateRouteQuery({ source, page: 1 })) },
    setCandidateLatestEvent(action) { this.pushDownloadRoute(this.candidateRouteQuery({ latest_event_action: action, page: 1 })) },
    openCandidatePreset({ status = 'candidate', source = '', needs_magnet = null } = {}) { this.pushDownloadRoute(this.candidateRouteQuery({ status, source, needs_magnet, page: 1 })) },
    goCandidatePage(page) { const nextPage = Math.max(1, Math.min(this.candidateTotalPages, Number(page) || 1)); if (nextPage !== this.candidatePage) this.pushDownloadRoute(this.candidateRouteQuery({ page: nextPage })) },
    applyCandidateRunFilters(run, overrides = {}) { const filters = { ...(run.filters || {}), ...overrides }; this.pushDownloadRoute(this.candidateRouteQuery({ status: filters.status || 'candidate', source: filters.source || '', actress_id: filters.actress_id || '', q: filters.q || '', needs_magnet: filters.needs_magnet === undefined ? null : filters.needs_magnet, missing_cover: Boolean(filters.missing_cover), latest_event_action: filters.latest_event_action || '', page: 1 })) },
    toggleCandidateSelection() { this.selectingCandidates = !this.selectingCandidates; if (!this.selectingCandidates) this.selectedCandidateIds = [] },
    toggleCandidateSelected(id) { this.selectedCandidateIds = this.selectedCandidateIds.includes(id) ? this.selectedCandidateIds.filter(item => item !== id) : [...this.selectedCandidateIds, id] },
    selectAllVisibleCandidates() { this.selectedCandidateIds = [...new Set([...this.selectedCandidateIds, ...this.candidates.map(c => c.id)])] },
    clearCandidateSelection() { this.selectedCandidateIds = [] },
    isCandidateMutating(id) { return Boolean(this.candidateMutations[id]) || this.bulkCandidateLoading || Boolean(this.candidateBatchProcessing) },
    setCandidateMutation(id, action) { this.candidateMutations = { ...this.candidateMutations, [id]: action } },
    clearCandidateMutation(id) { const next = { ...this.candidateMutations }; delete next[id]; this.candidateMutations = next },
    setTaskRetrying(id, loading) { if (loading) this.retryingTasks = { ...this.retryingTasks, [id]: true }; else { const next = { ...this.retryingTasks }; delete next[id]; this.retryingTasks = next } },
    async bulkRejectCandidates() { if (this.selectedCandidateIds.length === 0 || this.bulkCandidateLoading) return; if (!await requestConfirm({ title: '批量拒绝候选', message: `确认拒绝 ${this.selectedCandidateIds.length} 个下载候选？`, details: '拒绝后可在已拒绝筛选中批量恢复。', confirmText: '拒绝', tone: 'danger' })) return; this.bulkCandidateLoading = true; try { await api.bulkRejectDownloadCandidates(this.selectedCandidateIds); this.selectedCandidateIds = []; await this.loadCandidates() } catch (e) { console.error('Bulk reject candidates failed:', e) } finally { this.bulkCandidateLoading = false } },
    async bulkRestoreCandidates() { if (this.selectedCandidateIds.length === 0 || this.bulkCandidateLoading) return; this.bulkCandidateLoading = true; try { await api.bulkRestoreDownloadCandidates(this.selectedCandidateIds); this.selectedCandidateIds = []; await this.loadCandidates() } catch (e) { console.error('Bulk restore candidates failed:', e) } finally { this.bulkCandidateLoading = false } },
    editCandidateMagnet(candidate) { if (!this.isCandidateMutating(candidate.id)) this.magnetEditor = { open: true, candidate, value: candidate.magnet || '' } },
    closeMagnetEditor() { if (!this.magnetEditor.candidate || !this.isCandidateMutating(this.magnetEditor.candidate.id)) this.magnetEditor = { open: false, candidate: null, value: '' } },
    updateMagnetEditorValue(value) { this.magnetEditor = { ...this.magnetEditor, value } },
    async submitMagnetEditor() { const candidate = this.magnetEditor.candidate, magnet = this.magnetEditor.value.trim(); if (!candidate || !magnet || this.isCandidateMutating(candidate.id)) return; this.setCandidateMutation(candidate.id, 'magnet'); try { await api.updateDownloadCandidateMagnet(candidate.id, magnet); this.closeMagnetEditor(); await this.loadCandidates() } catch (e) { console.error('Update candidate magnet failed:', e) } finally { this.clearCandidateMutation(candidate.id) } },
    candidateFilterPayload(overrides = {}) { return cleanObject({ status: this.candidateFilter.status || 'candidate', source: this.candidateFilter.source || undefined, actress_id: this.candidateFilter.actress_id ? Number(this.candidateFilter.actress_id) : undefined, q: this.candidateFilter.q || undefined, needs_magnet: this.candidateFilter.needs_magnet, missing_cover: this.candidateFilter.missing_cover || undefined, latest_event_action: this.candidateFilter.latest_event_action || undefined, limit: this.candidates.length || 50, ...overrides }) },
    async enrichCandidateMagnet(candidate) { if (this.isCandidateMutating(candidate.id)) return; this.setCandidateMutation(candidate.id, 'enrich'); try { const action = (await api.enrichDownloadCandidateMagnet(candidate.id)).data?.action; if (action === 'magnet_enriched') this.$message?.success?.('已补充 magnet'); else if (action === 'magnet_not_found') this.$message?.warning?.('未找到可用 magnet'); else if (action === 'already_has_magnet') this.$message?.info?.('候选已有 magnet'); await this.loadCandidates() } catch (e) { console.error('Enrich candidate magnet failed:', e) } finally { this.clearCandidateMutation(candidate.id) } },
    async processCandidate(candidate) { if (this.isCandidateMutating(candidate.id)) return; if (!await requestConfirm({ title: '按策略处理候选', message: `确认按当前策略处理 ${candidate.dvd_id || candidate.content_id}？`, details: '可能会补充磁力并下发到下载源；不满足策略时会保持候选状态。', confirmText: '处理' })) return; this.setCandidateMutation(candidate.id, 'process'); try { const action = (await api.processDownloadCandidate(candidate.id, { enrich: true })).data?.action; if (action === 'sent') this.$message?.success?.('候选已下发下载'); else if (action === 'manual_required') this.$message?.info?.('当前为人工批准策略'); else if (action?.startsWith('skipped')) this.$message?.info?.('候选未满足策略条件'); else if (action?.startsWith('failed')) this.$message?.error?.('候选处理失败'); await this.loadCandidates(); await this.loadTasks() } catch (e) { console.error('Process candidate failed:', e) } finally { this.clearCandidateMutation(candidate.id) } },
    async enrichVisibleCandidateMagnets() {
      if (this.candidateBatchProcessing) return
      const targets = this.candidates.filter(candidate => (candidate.status === 'candidate' || candidate.status === 'failed') && !candidate.magnet)
      if (!targets.length) return this.$message?.info?.('当前列表没有待补磁力的候选')
      const confirmed = await requestConfirm({
        title: '批量补充磁力',
        message: `确认为当前列表中的 ${targets.length} 个下载候选查找并写入磁力？当前筛选总量 ${this.candidateTotal} 个。`,
        details: '会逐个访问候选的磁力来源，并把找到的磁力保存到候选记录。',
        confirmText: '开始补磁力',
      })
      if (!confirmed) return
      this.candidateBatchProcessing = 'enrich'
      try {
        let enriched = 0
        for (const candidate of targets) if ((await api.enrichDownloadCandidateMagnet(candidate.id)).data?.action === 'magnet_enriched') enriched += 1
        this.$message?.success?.(`已检查 ${targets.length} 个，补磁力 ${enriched} 个`)
        await this.loadCandidates()
      } catch (e) {
        console.error('Batch enrich candidates failed:', e)
      } finally {
        this.candidateBatchProcessing = ''
      }
    },
    async processVisibleCandidates() { if (this.candidateBatchProcessing) return; this.candidateBatchProcessing = 'dry-run'; let preview; try { preview = (await api.processDownloadCandidates(this.candidateFilterPayload({ enrich: true, dry_run: true }))).data || {} } catch (e) { console.error('Preview candidate processing failed:', e); this.candidateBatchProcessing = ''; return } if (!await requestConfirm({ title: '按策略处理候选', message: this.processPreviewMessage(preview), details: this.processPreviewDetails(preview.counts || {}, preview.limits || {}), confirmText: '处理' })) return; this.candidateBatchProcessing = 'process'; try { const resp = await api.processDownloadCandidates(this.candidateFilterPayload({ enrich: true })), counts = resp.data?.counts || {}, skipped = (counts.manual_required || 0) + (counts.skipped_source || 0) + (counts.skipped_missing_magnet || 0) + (counts.skipped_status || 0); this.$message?.success?.(`处理 ${resp.data?.total || 0} 个：下发 ${counts.sent || 0}，跳过 ${skipped}`); await this.loadCandidates(); await this.loadCandidateRuns(); await this.loadTasks() } catch (e) { console.error('Batch process candidates failed:', e) } finally { this.candidateBatchProcessing = '' } },
    processPreviewMessage(preview = {}) { const counts = preview.counts || {}; return `预演 ${preview.total || 0} 个：可直接下发 ${counts.would_send || 0}，需补磁力 ${counts.would_enrich_magnet || 0}，受上限跳过 ${counts.would_skip_limit || 0}。` },
    processPreviewDetails(counts = {}, limits = {}) { const skipped = Object.entries(counts).filter(([action]) => action.startsWith('skipped') || action === 'manual_required').reduce((sum, [, value]) => sum + Number(value || 0), 0), remaining = limits.remaining === null || limits.remaining === undefined ? '不限' : limits.remaining; return `策略跳过 ${skipped}。单次上限 ${limits.per_run || '不限'}，24 小时上限 ${limits.per_24h || '不限'}，当前剩余额度 ${remaining}。` },
    candidateEventActionLabel(action) { return eventLabels[action] || action },
    async retryFailedCandidateRun(run) { if (!run?.id || this.candidateBatchProcessing) return; if (!await requestConfirm({ title: '重试失败候选', message: `确认重试本次处理中的 ${run.failed || 0} 个失败候选？`, details: '会复用当时策略并重新补磁力/下发，仍失败的候选会留在失败队列。', confirmText: '重试' })) return; this.candidateBatchProcessing = 'retry-run'; try { const resp = await api.retryDownloadCandidateRunFailed(run.id, { enrich: true }), counts = resp.data?.counts || {}; this.$message?.success?.(`已重试 ${resp.data?.total || 0} 个：下发 ${counts.sent || 0}，失败 ${counts.failed_downloader || 0}`); await this.loadCandidates(); await this.loadCandidateRuns(); await this.loadTasks() } catch (e) { console.error('Retry failed candidate run failed:', e) } finally { this.candidateBatchProcessing = '' } },
    async openCandidateDetail(candidate) { this.candidateDetail = { open: true, loading: true, data: candidate }; try { const resp = await api.getDownloadCandidate(candidate.id); this.candidateDetail = { open: true, loading: false, data: resp.data.data } } catch (e) { console.error('Load candidate detail failed:', e); this.candidateDetail = { open: true, loading: false, data: candidate } } },
    closeCandidateDetail() { this.candidateDetail = { open: false, loading: false, data: null } },
    async approveCandidate(candidate) { if (this.isCandidateMutating(candidate.id)) return; if (!await requestConfirm({ title: '批准下载候选', message: `确认批准 ${candidate.dvd_id || candidate.content_id} 并下发下载？`, details: candidate.magnet ? '会创建真实下载任务并发送到当前默认下载源。' : '该候选没有磁力链接，批准可能失败或需要先补磁力。', confirmText: '批准' })) return; this.setCandidateMutation(candidate.id, 'approve'); try { await api.approveDownloadCandidate(candidate.id); await this.loadCandidates(); await this.loadTasks() } catch (e) { console.error('Approve candidate failed:', e) } finally { this.clearCandidateMutation(candidate.id) } },
    async rejectCandidate(candidate) { if (this.isCandidateMutating(candidate.id)) return; if (!await requestConfirm({ title: '拒绝下载候选', message: `确认拒绝 ${candidate.dvd_id || candidate.content_id}？`, details: candidate.title || '', confirmText: '拒绝', tone: 'danger' })) return; this.setCandidateMutation(candidate.id, 'reject'); try { await api.rejectDownloadCandidate(candidate.id); await this.loadCandidates() } catch (e) { console.error('Reject candidate failed:', e) } finally { this.clearCandidateMutation(candidate.id) } },
    goCandidateActor(candidate) { if (!candidate.actress_id) return; const name = candidate.actress_name || candidate.actress_id; this.$router.push({ path: `/actor/${encodeURIComponent(name)}`, query: { name, actress_id: candidate.actress_id } }) },
    goCandidateSupplement(candidate) { if (candidate.actress_id) this.$router.push({ path: '/supplement', query: { tab: 'movies', actress_id: candidate.actress_id, q: candidate.dvd_id || candidate.content_id || '' } }) },
    async remove(id) { if (!await requestConfirm({ title: '删除下载任务', message: `确认删除任务 #${id}？`, details: '只会移除 JavHub 中的任务记录，不会自动删除下载器里的文件。', confirmText: '删除', tone: 'danger' })) return; try { await api.deleteDownload(id); this.loadTasks() } catch (e) { console.error('Failed to delete:', e) } },
    async retry(task) { if (this.retryingTasks[task.id]) return; this.setTaskRetrying(task.id, true); try { await api.createDownload({ content_id: task.content_id || task.code, title: task.title, magnet: task.magnet, path: task.path, downloader_id: task.downloader_id || '' }); await this.loadTasks() } catch (e) { console.error('Failed to retry download:', e) } finally { this.setTaskRetrying(task.id, false) } },
    statusBadge: homePresentation.statusBadge,
    statusLabel: homePresentation.statusLabel,
    formatTime: homePresentation.formatDownloadTime,
  },
}
</script>

<style scoped src="../features/home/home.css"></style>
