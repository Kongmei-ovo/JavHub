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
import { computed, defineAsyncComponent, ref } from 'vue'
import { useRoute } from 'vue-router'
import api from '../api'
import DownloadStatsBar from '../features/home/DownloadStatsBar.vue'
import TaskList from '../features/home/TaskList.vue'
import * as homePresentation from '../features/home/homePresentation'
import { requestConfirm } from '../utils/confirmDialog'
import { useDownloadCandidates } from '../features/candidates/useDownloadCandidates.js'
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
const cleanObject = (target) => { Object.keys(target).forEach(key => { if (target[key] === undefined || target[key] === '' || target[key] === null) delete target[key] }); return target }

export default {
  name: 'Home',
  components: { DownloadStatsBar, TaskList, DownloadCandidatePanel, DownloaderManagementPanel },
  setup() {
    // 候选确认的真相源已下沉到 useDownloadCandidates composable，由 /candidates 独立页
    // 与 /downloads 旧 tab 共用；这里以「routePath: /downloads + tab=candidates」
    // 模拟既有路由行为，仅在 activeTab=='candidates' 时同步路由。
    const route = useRoute()
    const initialTab = ['candidates', 'downloaders'].includes(route.query.tab) ? route.query.tab : 'tasks'
    const activeTab = ref(initialTab)
    const candidateActive = computed(() => activeTab.value === 'candidates')
    const candidates = useDownloadCandidates({
      routePath: '/downloads',
      syncRoute: true,
      baseQuery: () => ({ tab: 'candidates' }),
      enabled: candidateActive,
    })
    return { activeTab, ...candidates }
  },
  data() {
    return {
      tasks: [], stats: { pending: 0, downloading: 0, completed: 0, failed: 0 }, statsLoaded: false, filterStatus: null, timer: null, retryingTasks: {},
      downloaders: { default_id: '', clients: [], types: [] }, downloaderTypes: createDefaultDownloaderTypes(), savingDownloaders: false, testingDownloaderId: '', downloaderTestMessages: {}, downloaderEditor: { open: false, mode: 'new', originalId: '', draft: null, previousType: '' }, downloaderIdSeed: 1,
    }
  },
  computed: {
    totalTaskCount() { return this.stats.pending + this.stats.downloading + this.stats.completed + this.stats.failed },
    filteredTasks() { return this.filterStatus ? this.tasks.filter(t => t.status === this.filterStatus) : this.tasks },
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
      if (tab === 'candidates' && this.applyRouteQuery(query)) changed = true
      return changed
    },
    cleanDownloadQuery(query = {}) { return cleanObject({ ...query }) },
    pushDownloadRoute(query = {}) { const next = this.cleanDownloadQuery(query); if (JSON.stringify(next) !== JSON.stringify(this.$route.query || {})) this.$router.push({ path: this.$route.path, query: next }).catch(() => {}) },
    replaceDownloadRoute(query = {}) { const next = this.cleanDownloadQuery(query); if (JSON.stringify(next) !== JSON.stringify(this.$route.query || {})) this.$router.replace({ path: this.$route.path, query: next }).catch(() => {}) },
    async loadTasks() { try { const resp = await api.getDownloads(); this.tasks = resp.data.data || []; this.stats = { pending: this.tasks.filter(t => t.status === 'pending').length, downloading: this.tasks.filter(t => t.status === 'downloading').length, completed: this.tasks.filter(t => t.status === 'completed').length, failed: this.tasks.filter(t => t.status === 'failed').length }; this.statsLoaded = true } catch (e) { console.error('Failed to load tasks:', e) } },
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
    setTaskRetrying(id, loading) { if (loading) this.retryingTasks = { ...this.retryingTasks, [id]: true }; else { const next = { ...this.retryingTasks }; delete next[id]; this.retryingTasks = next } },
    async remove(id) { if (!await requestConfirm({ title: '删除下载任务', message: `确认删除任务 #${id}？`, details: '只会移除 JavHub 中的任务记录，不会自动删除下载器里的文件。', confirmText: '删除', tone: 'danger' })) return; try { await api.deleteDownload(id); this.loadTasks() } catch (e) { console.error('Failed to delete:', e) } },
    async retry(task) { if (this.retryingTasks[task.id]) return; this.setTaskRetrying(task.id, true); try { await api.createDownload({ content_id: task.content_id || task.code, title: task.title, magnet: task.magnet, path: task.path, downloader_id: task.downloader_id || '' }); await this.loadTasks() } catch (e) { console.error('Failed to retry download:', e) } finally { this.setTaskRetrying(task.id, false) } },
    statusBadge: homePresentation.statusBadge,
    statusLabel: homePresentation.statusLabel,
    formatTime: homePresentation.formatDownloadTime,
  },
}
</script>

<style scoped src="../features/home/home.css"></style>
