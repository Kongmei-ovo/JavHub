<template>
  <div class="downloads-page page-shell page-shell--gallery">
    <header class="page-header">
      <div class="header-left">
        <h1>下载中心</h1>
        <p class="header-subtitle">
          <span>{{ totalTaskCount }} 个任务</span>
          <span v-if="stats.downloading > 0" class="downloading-hint"> · {{ stats.downloading }} 个下载中</span>
          <span v-if="stats.pending > 0" class="downloading-hint"> · {{ stats.pending }} 个待处理</span>
        </p>
      </div>
      <div class="header-actions">
        <button class="btn btn-ghost" type="button" @click="$router.push('/search')">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="16" height="16"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/></svg>
          浏览影库
        </button>
        <button class="btn btn-ghost" type="button" @click="openAddSheet">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="16" height="16"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
          添加下载
        </button>
        <RefreshButton @click="loadTasks" />
      </div>
    </header>

    <DownloadStatsBar
      :stats="stats"
      :stats-loaded="statsLoaded"
      @select-status="setTaskStatus"
    />

    <button v-if="filterStatus" class="filter-bar" type="button" @click="clearTaskStatus">
      <span class="filter-hint">筛选：<strong>{{ statusLabel(filterStatus) }}</strong>（点击清除）</span>
    </button>

    <div class="download-tabs" aria-label="下载工作区">
      <button class="tab-btn" type="button" :class="{ active: activeTab === 'tasks' }" @click="openTaskTab">下载任务</button>
      <button class="tab-btn" type="button" :class="{ active: activeTab === 'downloaders' }" @click="openDownloaderTab">
        下载源
        <span v-if="enabledDownloaderCount" class="tab-badge subtle">{{ enabledDownloaderCount }}</span>
      </button>
      <button class="tab-btn" type="button" :class="{ active: activeTab === 'indexer' }" @click="openIndexerTab">
        索引源
        <span v-if="torznabLoaded && torznab.enabled" class="tab-badge subtle">已启用</span>
      </button>
    </div>

    <DownloaderManagementPanel
      v-if="activeTab === 'downloaders'"
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

    <IndexerSourcePanel
      v-else-if="activeTab === 'indexer'"
      :model-value="torznab"
      :saving="savingTorznab"
      :status-message="torznabStatus"
      @save="saveTorznab"
    />

    <TaskList
      v-else
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
      @parse="openAddSheet"
    />

    <AddDownloadSheet :open="showAddSheet" @close="showAddSheet = false" @added="onDownloadAdded" />
  </div>
</template>

<script>
import { defineAsyncComponent } from 'vue'
import api from '../api'
import DownloadStatsBar from '../features/downloads/DownloadStatsBar.vue'
import TaskList from '../features/downloads/TaskList.vue'
import AddDownloadSheet from '../features/downloads/AddDownloadSheet.vue'
import * as downloadPresentation from '../features/downloads/downloadPresentation'
import { requestConfirm } from '../utils/confirmDialog'
import RefreshButton from '../components/RefreshButton.vue'
import {
  createDefaultDownloaderTypes,
  downloaderAddressPlaceholder as defaultDownloaderAddressPlaceholder,
  downloaderPathPlaceholder as defaultDownloaderPathPlaceholder,
  downloaderTypeMark as defaultDownloaderTypeMark,
  supportsDownloaderTags as defaultSupportsDownloaderTags,
  tokenPlaceholder as defaultTokenPlaceholder,
} from '../features/downloaders/downloaderPresentation'

const DownloaderManagementPanel = defineAsyncComponent(() => import('../features/downloaders/DownloaderManagementPanel.vue'))
const IndexerSourcePanel = defineAsyncComponent(() => import('../features/downloads/IndexerSourcePanel.vue'))
const DEFAULT_TORZNAB = { enabled: false, name: 'torznab', base_url: '', api_key: '', indexer: 'all', categories: '', limit: 20, timeout: 15 }
const cleanObject = (target) => {
  Object.keys(target).forEach((key) => {
    if (target[key] === undefined || target[key] === '' || target[key] === null) delete target[key]
  })
  return target
}

export default {
  name: 'Downloads',
  components: { DownloadStatsBar, TaskList, AddDownloadSheet, DownloaderManagementPanel, IndexerSourcePanel, RefreshButton },
  data() {
    return {
      activeTab: 'tasks',
      showAddSheet: false,
      tasks: [],
      stats: { pending: 0, downloading: 0, completed: 0, failed: 0 },
      statsLoaded: false,
      filterStatus: null,
      timer: null,
      retryingTasks: {},
      downloaders: { default_id: '', clients: [], types: [] },
      downloaderTypes: createDefaultDownloaderTypes(),
      savingDownloaders: false,
      testingDownloaderId: '',
      downloaderTestMessages: {},
      downloaderEditor: { open: false, mode: 'new', originalId: '', draft: null, previousType: '' },
      downloaderIdSeed: 1,
      torznab: { ...DEFAULT_TORZNAB },
      torznabLoaded: false,
      savingTorznab: false,
      torznabStatus: '',
    }
  },
  computed: {
    totalTaskCount() {
      return this.stats.pending + this.stats.downloading + this.stats.completed + this.stats.failed
    },
    filteredTasks() {
      return this.filterStatus ? this.tasks.filter(task => task.status === this.filterStatus) : this.tasks
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
      return '可以从影库或磁链解析添加下载任务。'
    },
    taskEmptyTitle() {
      return `暂无${this.filterStatus ? this.statusLabel(this.filterStatus) : ''}任务`
    },
    taskEmptyPrimaryLabel() {
      return this.filterStatus ? '清除筛选' : '浏览影库'
    },
  },
  created() {
    if (this.$route.query.tab === 'candidates') {
      this.$router.replace({ path: '/candidates', query: this.candidateRedirectQuery(this.$route.query) }).catch(() => {})
      return
    }
    this.applyDownloadRoute(this.$route.query)
  },
  mounted() {
    if (this.$route.query.tab === 'candidates') return
    this.loadTasks()
    if (this.activeTab === 'downloaders') this.loadDownloaders()
    if (this.activeTab === 'indexer') this.loadTorznab()
    this.timer = setInterval(this.loadTasks, 30000)
  },
  beforeUnmount() {
    if (this.timer) clearInterval(this.timer)
  },
  watch: {
    '$route.query'(query) {
      if (query.tab === 'candidates') {
        this.$router.replace({ path: '/candidates', query: this.candidateRedirectQuery(query) }).catch(() => {})
        return
      }
      if (!this.applyDownloadRoute(query)) return
      if (this.activeTab === 'downloaders') this.loadDownloaders()
      if (this.activeTab === 'indexer' && !this.torznabLoaded) this.loadTorznab()
    },
  },
  methods: {
    candidateRedirectQuery(query = {}) {
      const next = { ...query }
      delete next.tab
      return cleanObject(next)
    },
    applyDownloadRoute(query = {}) {
      let changed = false
      const tab = ['downloaders', 'indexer'].includes(query.tab) ? query.tab : 'tasks'
      if (this.activeTab !== tab) {
        this.activeTab = tab
        changed = true
      }
      const taskStatus = tab === 'tasks' ? (query.task_status || '') : ''
      if ((this.filterStatus || '') !== taskStatus) {
        this.filterStatus = taskStatus || null
        changed = true
      }
      return changed
    },
    cleanDownloadQuery(query = {}) {
      return cleanObject({ ...query })
    },
    pushDownloadRoute(query = {}) {
      const next = this.cleanDownloadQuery(query)
      if (JSON.stringify(next) !== JSON.stringify(this.$route.query || {})) {
        this.$router.push({ path: this.$route.path, query: next }).catch(() => {})
      }
    },
    async loadTasks() {
      try {
        const resp = await api.getDownloads()
        this.tasks = resp.data.data || []
        this.stats = {
          pending: this.tasks.filter(task => task.status === 'pending').length,
          downloading: this.tasks.filter(task => task.status === 'downloading').length,
          completed: this.tasks.filter(task => task.status === 'completed').length,
          failed: this.tasks.filter(task => task.status === 'failed').length,
        }
        this.statsLoaded = true
      } catch (error) {
        console.error('Failed to load tasks:', error)
      }
    },
    openDownloaderTab() {
      this.pushDownloadRoute({ tab: 'downloaders' })
    },
    openTaskTab() {
      this.pushDownloadRoute({ tab: 'tasks', task_status: this.filterStatus || undefined })
    },
    openIndexerTab() {
      this.pushDownloadRoute({ tab: 'indexer' })
    },
    async loadTorznab() {
      try {
        const resp = await api.getConfig()
        const data = resp.data || {}
        const torznab = (data.sources && data.sources.torznab) || {}
        this.torznab = { ...DEFAULT_TORZNAB, ...torznab }
        this.torznabLoaded = true
      } catch (error) {
        console.error('Failed to load indexer config:', error)
        this.torznabStatus = '索引源配置加载失败，请刷新重试。'
      }
    },
    async saveTorznab(draft) {
      this.savingTorznab = true
      this.torznabStatus = ''
      try {
        const payload = { ...draft }
        // 空 API Key 表示不修改已保存的密钥，由后端保留现值
        if (!payload.api_key) delete payload.api_key
        await api.updateConfig({ sources: { torznab: payload } })
        this.torznab = { ...DEFAULT_TORZNAB, ...draft, api_key: '' }
        this.torznabLoaded = true
        this.torznabStatus = '索引源配置已保存。'
        this.$message?.success?.('索引源配置已保存')
      } catch (error) {
        console.error('Failed to save indexer config:', error)
        this.torznabStatus = '保存失败，请稍后重试。'
        this.$message?.error?.('保存失败')
      } finally {
        this.savingTorznab = false
      }
    },
    setTaskStatus(status) {
      this.pushDownloadRoute({ tab: 'tasks', task_status: status })
    },
    clearTaskStatus() {
      this.pushDownloadRoute({ tab: 'tasks' })
    },
    handleTaskEmptyAction() {
      if (this.filterStatus) this.clearTaskStatus()
      else this.$router.push('/search')
    },
    openAddSheet() {
      this.showAddSheet = true
    },
    onDownloadAdded() {
      this.loadTasks()
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
      } catch (error) {
        console.error('Failed to load downloaders:', error)
      }
    },
    makeDownloaderId(type = 'qbittorrent') {
      let id = `${type}-${this.downloaderIdSeed++}`
      while (this.downloaderClients.some(client => client.id === id)) id = `${type}-${this.downloaderIdSeed++}`
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
        previousType: 'qbittorrent',
      }
    },
    editDownloader(client) {
      this.downloaderEditor = {
        open: true,
        mode: 'edit',
        originalId: client.id,
        draft: this.normalizeDownloaderDraft({ ...client }),
        previousType: client.type,
      }
    },
    closeDownloaderEditor() {
      this.downloaderEditor = { open: false, mode: 'new', originalId: '', draft: null, previousType: '' }
    },
    applyDownloaderEditor() {
      const draft = this.downloaderEditor.draft
      if (!draft) return
      const client = this.normalizeDownloaderDraft(draft)
      this.downloaders.clients = this.downloaderEditor.mode === 'new'
        ? [...this.downloaderClients, client]
        : this.downloaderClients.map(item => item.id === this.downloaderEditor.originalId ? client : item)
      if (!this.downloaders.default_id || this.downloaders.default_id === this.downloaderEditor.originalId) {
        this.downloaders.default_id = client.id
      }
      this.closeDownloaderEditor()
    },
    syncDownloaderDraftDefaults() {
      const draft = this.downloaderEditor.draft
      if (!draft) return
      const previousPlaceholder = this.downloaderAddressPlaceholder(this.downloaderEditor.previousType)
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
      if (this.downloaders.default_id === id) this.downloaders.default_id = this.downloaderClients[0]?.id || ''
    },
    setDefaultDownloader(id) {
      this.downloaders.default_id = id
    },
    downloaderTypeLabel(type) {
      return this.downloaderTypes.find(item => item.value === type)?.label || type || '下载器'
    },
    downloaderTypeMark(type) {
      return defaultDownloaderTypeMark(type)
    },
    downloaderAddressPlaceholder(type) {
      return defaultDownloaderAddressPlaceholder(type)
    },
    downloaderPathPlaceholder(type) {
      return defaultDownloaderPathPlaceholder(type)
    },
    supportsDownloaderTags(type) {
      return defaultSupportsDownloaderTags(type)
    },
    shortDownloaderAddress: downloadPresentation.shortDownloaderAddress,
    downloaderPathSummary: downloadPresentation.downloaderPathSummary,
    tokenPlaceholder(type) {
      return defaultTokenPlaceholder(type)
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
        })),
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
      } catch (error) {
        console.error('Save downloaders failed:', error)
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
          [client.id]: {
            ok: Boolean(resp.data.ok),
            message: resp.data.ok
              ? `连接正常：${resp.data.message || 'OK'}`
              : `连接失败：${resp.data.message || '未知错误'}`,
          },
        }
      } catch (error) {
        this.downloaderTestMessages = {
          ...this.downloaderTestMessages,
          [client.id]: {
            ok: false,
            message: `连接失败：${error.response?.data?.detail || error.message}`,
          },
        }
      } finally {
        this.testingDownloaderId = ''
      }
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
    async remove(id) {
      const confirmed = await requestConfirm({
        title: '删除下载任务',
        message: `确认删除任务 #${id}？`,
        details: '只会移除 JavHub 中的任务记录，不会自动删除下载器里的文件。',
        confirmText: '删除',
        tone: 'danger',
      })
      if (!confirmed) return
      try {
        await api.deleteDownload(id)
        await this.loadTasks()
      } catch (error) {
        console.error('Failed to delete:', error)
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
          downloader_id: task.downloader_id || '',
        })
        await this.loadTasks()
      } catch (error) {
        console.error('Failed to retry download:', error)
      } finally {
        this.setTaskRetrying(task.id, false)
      }
    },
    statusBadge: downloadPresentation.statusBadge,
    statusLabel: downloadPresentation.statusLabel,
    formatTime: downloadPresentation.formatDownloadTime,
  },
}
</script>

<style scoped src="../features/downloads/downloads.css"></style>
