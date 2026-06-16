<template>
  <div class="supplement-page page-shell page-shell--workspace">
    <header class="supplement-topbar">
      <div>
        <h1>补全演员</h1>
        <p class="topbar-sub">字段补全工作台 · 实时追踪补全来源、字段缺口与诊断进度</p>
      </div>
      <div class="topbar-actions">
        <button v-if="actorContext" class="btn btn-ghost btn-sm" type="button" @click="clearActorContext">更换演员</button>
      </div>
    </header>

    <nav class="segmented-control" aria-label="补全工作台视图">
      <button v-for="tab in tabItems" :key="tab.key" type="button" :class="{ active: activeTab === tab.key }" @click="setActiveTab(tab.key)">
        <span class="segment-label">{{ tab.label }}</span>
        <span class="segment-count">{{ tab.count }}</span>
        <span class="segment-status">{{ tab.status }}</span>
        <span class="segment-next-step">{{ tab.nextStep }}</span>
      </button>
    </nav>

    <ActorPickerView
      v-if="showActorPicker"
      v-model:keyword="actorSearchKeyword"
      :actors="actorChoiceCards"
      :searched="actorSearched"
      :searching="actorSearching"
      :error="actorPickerLoadFailed()"
      :actor-avatar="actorAvatar"
      :actor-display-name="actorDisplayName"
      :actor-choice-status="actorChoiceStatus"
      @search="searchActorContext"
      @clear-search="clearActorSearch"
      @select="selectActorContext"
      @retry="loadRecentActorJobs"
    />

    <section v-else class="workspace-view">
      <div v-if="actorContext" class="actor-workspace-hero" :style="heroAccentStyle">
        <div class="workspace-identity">
          <div class="workspace-avatar" :style="actorContextAvatar ? null : heroAvatarStyle">
            <img v-if="actorContextAvatar" :src="actorContextAvatar" :alt="actorContextName" loading="eager" decoding="async" @error="handleWorkspaceAvatarError" />
            <span v-else>{{ actorContextName.slice(0, 1) || '?' }}</span>
          </div>
          <div class="workspace-title">
            <h2>{{ actorContextName }}</h2>
            <p class="workspace-sub">编号 {{ String(actorContext.id).padStart(5, '0') }}<span v-if="actorContextRomaji"> · {{ actorContextRomaji }}</span></p>
            <div class="workspace-status-row">
              <span class="status-pill" :class="`status-${heroStatus}`">{{ statusLabel(heroStatus) }}</span>
              <span v-if="heroRecent" class="workspace-recent">{{ heroRecent }}</span>
            </div>
          </div>
        </div>
        <div class="workspace-actions">
          <button class="btn btn-primary" type="button" :disabled="isSupplementRunning" @click="startSupplement">
            <span v-if="isSupplementRunning" class="spin-ring" aria-hidden="true"></span>
            <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16"><path d="M12 5v14M5 12h14"/></svg>
            {{ isSupplementRunning ? '补全中…' : '补全作品' }}
          </button>
          <button class="btn btn-ghost" type="button" @click="refreshResolved">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="15" height="15"><polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 11-2.12-9.36L23 10"/></svg>
            刷新版本条目
          </button>
          <button class="btn btn-quiet btn-sm" type="button" @click="goActorContext">返回演员页</button>
        </div>
      </div>

      <div v-if="actorContext" class="workspace-metrics">
        <div v-for="metric in workspaceMetrics" :key="metric.label" class="metric-card">
          <div class="metric-top"><span class="metric-label">{{ metric.label }}</span><span class="metric-dot" :class="`metric-dot-${metric.icon}`"></span></div>
          <div class="metric-num">{{ metric.value }}</div>
        </div>
      </div>

      <component
        :is="activeTabComponent"
        :actor-context="actorContext"
        :actor-name="actorContextName"
        :initial-filters="activeTabFilters"
        :global-queue="activeTab === 'jobs' && !actorContext"
        :context-label="globalQueueContextLabel"
        :context-items="activeTab === 'jobs' && !actorContext ? globalQueueContextItems : []"
        :refresh-nonce="refreshNonce"
        :movies="movieSummary.movies"
        :field-gap-count="movieSummary.fieldGapCount"
        :pending-candidate-count="movieSummary.pendingCandidateCount"
        :detail-target-count="movieSummary.detailTargetCount"
        :focus-movie="diagnosticsFocusMovie"
        @actor="applyJobActorContext"
        @start-supplement="actorContext ? startSupplement() : clearActorContext()"
        @filters-change="handleFiltersChange"
        @jobs-requested="setActiveTab('jobs')"
        @sources-opened="openSourcesFromMovie"
        @view-avatar-jobs="viewGfriendsAvatarJobs"
        @movies-requested="setActiveTab('movies')"
        @movies-refresh-requested="refreshNonce++"
        @summary-change="handleSummaryChange"
      />
    </section>
  </div>
</template>

<script>
import { defineAsyncComponent } from 'vue'
import api from '../api'
import { ElMessage } from '../utils/message.js'
import { actressImgUrl } from '../utils/imageUrl.js'
import { applyImageFallback } from '../utils/imageFallback.js'
import { displayName } from '../utils/displayLang.js'

const ActorPickerView = defineAsyncComponent(() => import('../features/supplement/ActorPickerView.vue'))
const JobsTab = defineAsyncComponent(() => import('../features/supplement/JobsTab.vue'))
const MoviesTab = defineAsyncComponent(() => import('../features/supplement/MoviesTab.vue'))
const SourcesHealthTab = defineAsyncComponent(() => import('../features/supplement/SourcesHealthTab.vue'))
const RepairLaneTab = defineAsyncComponent(() => import('../features/supplement/RepairLaneTab.vue'))

export default {
  name: 'SupplementManagement',
  components: { ActorPickerView, JobsTab, MoviesTab, SourcesHealthTab, RepairLaneTab },
  data: () => ({
    actorContext: null, actorSearchKeyword: '', actorSearchResults: [], actorSearching: false, actorSearched: false, actorPickerError: '',
    recentJobs: [], recentActors: [], activeTab: 'movies',
    activeFilters: { status: '', source: '', error_provider: '', error_reason: '', q: '', quality: '' },
    supplementStatus: null, supplementPolling: null, refreshNonce: 0, diagnosticsFocusMovie: null,
    movieSummary: { total: 0, movies: [], fieldGapCount: 0, pendingCandidateCount: 0, detailTargetCount: 0 },
    sourceSummary: { count: 0, degraded: false },
    hasInitialized: false, wasDeactivated: false, lastAppliedRouteKey: '',
  }),
  computed: {
    showActorPicker() { return !this.actorContext && !this.isGlobalTab },
    isGlobalTab() { return ['jobs', 'sourceHealth', 'movies'].includes(this.activeTab) && !this.activeFilters.actress_id },
    actorChoiceCards() { return this.actorSearchResults.length || this.actorSearched ? this.actorSearchResults : this.recentActors },
    actorContextName() { return this.actorContext ? this.actorDisplayName(this.actorContext) : '' },
    actorContextAvatar() { return this.actorAvatar(this.actorContext) },
    isSupplementRunning() { return ['running', 'queued'].includes(this.supplementStatus?.last_job?.status) },
    activeTabComponent() {
      return { movies: 'MoviesTab', jobs: 'JobsTab', sourceHealth: 'SourcesHealthTab', diagnostics: 'RepairLaneTab' }[this.activeTab] || 'MoviesTab'
    },
    activeTabFilters() {
      return { ...this.activeFilters, actress_id: this.actorContext?.id || '' }
    },
    tabItems() {
      const s = this.supplementStatus, f = this.activeFilters
      return [
        { key: 'movies', label: '作品字段', count: this.movieSummary.total, status: f.quality || f.q ? '已筛选' : '字段池', nextStep: '先补字段' },
        { key: 'jobs', label: '任务队列', count: s?.last_job?.id ? 1 : 0, status: this.statusLabel(s?.last_job?.status), nextStep: '查看任务' },
        { key: 'diagnostics', label: '来源诊断', count: this.movieSummary.pendingCandidateCount, status: '待选择', nextStep: '打开诊断' },
        { key: 'sourceHealth', label: '来源状态', count: this.sourceSummary.count, status: this.sourceSummary.degraded ? '来源异常' : '来源池', nextStep: '查看降级来源' },
      ]
    },
    workspaceMetrics() {
      const s = this.supplementStatus
      return [
        { label: '补全来源', value: s?.supplement_movies ?? '-', icon: 'stack' },
        { label: '已匹配片库', value: s?.matched_r18 ?? '-', icon: 'matched' },
        { label: '补全新增', value: s?.supplement_only ?? '-', icon: 'plus' },
        { label: '含版本条目', value: s?.resolved_videos ?? '-', icon: 'clock' },
      ]
    },
    actorContextRomaji() {
      const r = this.actorContext?.name_romaji, k = this.actorContext?.name_kanji
      return r && r !== k ? r : ''
    },
    heroStatus() { return this.supplementStatus?.last_job?.status || 'idle' },
    heroRecent() {
      const j = this.supplementStatus?.last_job
      if (!j) return ''
      if (j.last_error && j.status === 'failed') return j.last_error
      if (j.status === 'running') return `运行中${j.attempt_count ? ` · 第 ${j.attempt_count} 次尝试` : ''}`
      if (j.status === 'queued') return '排队中 · 等待空闲来源'
      if (j.finished_at) return `${this.statusLabel(j.status)} · ${this.formatRelativeTime(j.finished_at)}`
      return ''
    },
    heroAccent() {
      const seed = String(this.actorContext?.id || this.actorContextName || 'jh')
      let h = 5381
      for (let i = 0; i < seed.length; i++) h = ((h << 5) + h + seed.charCodeAt(i)) & 0xffffffff
      const hue = Math.abs(h) % 360
      return { hue, hue2: (hue + 38) % 360 }
    },
    heroAccentStyle() {
      const { hue, hue2 } = this.heroAccent
      return { '--hero-accent-1': `hsl(${hue} 62% 60%)`, '--hero-accent-2': `hsl(${hue2} 56% 48%)` }
    },
    heroAvatarStyle() {
      const { hue, hue2 } = this.heroAccent
      return { background: `linear-gradient(135deg, hsl(${hue} 60% 58%), hsl(${hue2} 55% 46%))` }
    },
    globalQueueStatusLabel() { return this.activeFilters.status ? this.statusLabel(this.activeFilters.status) : '全部状态' },
    globalQueueSourceLabel() {
      const source = String(this.activeFilters.source || '').trim()
      if (!source) return '全部来源'
      if (source === 'all' && this.activeFilters.error_provider) return `含 ${this.activeFilters.error_provider} 的复合失败`
      if (source === 'all') return '包含多个来源的复合失败'
      if (source === 'gfriends') return 'gfriends 头像来源'
      return `${source} 来源`
    },
    globalQueueContextLabel() { return `${this.globalQueueStatusLabel} · ${this.globalQueueSourceLabel}` },
    globalQueueContextItems() {
      const f = this.activeFilters
      const items = [{ label: '状态', value: this.globalQueueStatusLabel }, { label: '来源', value: this.globalQueueSourceLabel }]
      if (f.error_provider) items.push({ label: '定位', value: f.error_provider })
      if (f.error_reason) items.push({ label: '原因', value: f.error_reason })
      return items
    },
  },
  watch: {
    '$route.fullPath': {
      handler() {
        if (this.isSupplementRoute()) this.applyRouteState()
      },
    },
  },
  mounted() {
    this.hasInitialized = true
    this.applyRouteState({ force: true })
    if (!this.$route.query.actress_id && !['jobs', 'sources'].includes(this.$route.query.tab)) this.loadRecentActorJobs()
  },
  activated() {
    if (!this.hasInitialized || !this.wasDeactivated || !this.isSupplementRoute()) return
    this.wasDeactivated = false
    this.applyRouteState()
    if (this.isSupplementRunning) this._startSupplementPolling()
  },
  deactivated() { this.wasDeactivated = true; this._stopSupplementPolling() },
  beforeUnmount() { this._stopSupplementPolling() },
  methods: {
    statusLabel(status) {
      const map = { queued: '排队中', running: '运行中', succeeded: '已完成', failed: '失败', idle: '待开始' }
      return map[status] || status || '待开始'
    },
    formatRelativeTime(value) {
      if (!value) return ''
      const t = new Date(value).getTime()
      if (Number.isNaN(t)) return ''
      const m = Math.round((Date.now() - t) / 60000)
      if (m < 1) return '刚刚'
      if (m < 60) return `${m} 分钟前`
      const h = Math.round(m / 60)
      if (h < 24) return `${h} 小时前`
      const d = Math.round(h / 24)
      if (d < 30) return `${d} 天前`
      const date = new Date(value)
      return `${date.getMonth() + 1}/${date.getDate()}`
    },
    supplementQueryKey(query = this.$route.query) {
      const field = key => Array.isArray(query[key]) ? String(query[key][0] || '').trim() : String(query[key] || '').trim()
      return JSON.stringify({ tab: field('tab'), actress_id: field('actress_id'), status: field('status'), source: field('source'), error_provider: field('error_provider'), error_reason: field('error_reason'), q: field('q'), quality: field('quality') })
    },
    buildSupplementQuery(query = {}) {
      return Object.entries(query).reduce((result, [key, value]) => {
        if (value !== undefined && value !== null && value !== '') result[key] = String(value)
        return result
      }, {})
    },
    isSupplementRoute() { return this.$route.path === '/supplement' || this.$route.path.startsWith('/supplement/') },
    supplementRouteTab() {
      if (this.$route.path === '/supplement/movies') return 'movies'
      if (this.$route.path === '/supplement/jobs') return 'jobs'
      if (this.$route.path === '/supplement/sources') return 'sources'
      if (this.$route.path === '/supplement/stats') return 'stats'
      return this.$route.query.tab
    },
    async replaceSupplementRoute(query = {}) {
      const nextQuery = this.buildSupplementQuery(query)
      if (this.$route.path === '/supplement' && this.supplementQueryKey(nextQuery) === this.supplementQueryKey()) return false
      await this.$router.replace({ path: '/supplement', query: nextQuery })
      return true
    },
    tabFromRoute(tab) { return tab === 'jobs' ? 'jobs' : tab === 'sources' ? 'sourceHealth' : tab === 'stats' ? 'diagnostics' : 'movies' },
    tabToRoute(tab) { return tab === 'jobs' ? 'jobs' : tab === 'sourceHealth' ? 'sources' : tab === 'diagnostics' ? 'stats' : 'movies' },
    async applyRouteState({ force = false } = {}) {
      const routeKey = this.supplementQueryKey()
      if (!force && routeKey === this.lastAppliedRouteKey) return
      this.lastAppliedRouteKey = routeKey
      this.activeTab = this.tabFromRoute(this.supplementRouteTab())
      Object.assign(this.activeFilters, {
        status: this.$route.query.status || '',
        source: this.$route.query.source || '',
        error_provider: this.$route.query.error_provider || '',
        error_reason: this.$route.query.error_reason || '',
        q: this.$route.query.q || '',
        quality: this.$route.query.quality || '',
        actress_id: this.$route.query.actress_id || '',
      })
      if (this.$route.query.actress_id) await this.applyActorContext(this.$route.query.actress_id)
      else this.actorContext = null
      this.refreshNonce++
    },
    async setActiveTab(tab) {
      this.activeTab = tab
      const query = { tab: this.tabToRoute(tab), actress_id: this.actorContext?.id, ...this.activeFilters }
      const routeChanged = await this.replaceSupplementRoute(query)
      if (!routeChanged) this.refreshNonce++
    },
    handleFiltersChange(filters) {
      Object.assign(this.activeFilters, filters)
      this.replaceSupplementRoute({ tab: this.tabToRoute(this.activeTab), actress_id: this.actorContext?.id, ...this.activeFilters })
    },
    handleSummaryChange(summary) {
      if (summary.movies) this.movieSummary = { ...this.movieSummary, ...summary }
      else this.sourceSummary = { ...this.sourceSummary, ...summary }
    },
    handleWorkspaceAvatarError(e) { applyImageFallback(e, { label: this.actorContextName?.slice(0, 1) || '?' }) },
    actorDisplayName(actor) { return displayName(actor, 'name_kanji', 'name_romaji') || actor?.name_kanji || actor?.name_romaji || actor?.name || `演员 ${actor?.id}` },
    actorAvatar(actor) { return actor?.image_url ? actressImgUrl(actor.image_url) : '' },
    actorChoiceStatus(actor) { return actor?._recentJob ? `${this.statusLabel(actor._recentJob.status)}` : '选择后进入补全工作台' },
    actorPickerLoadFailed() { return this.actorPickerError === 'load_failed' },
    clearActorSearch() { this.actorSearchKeyword = ''; this.actorSearchResults = []; this.actorSearched = false },
    async searchActorContext() {
      const keyword = this.actorSearchKeyword.trim()
      if (!keyword) return
      this.actorSearching = true; this.actorSearched = true; this.actorSearchResults = []
      try {
        const resp = await api.searchActors(keyword)
        const data = resp.data || resp
        this.actorSearchResults = data.data || data || []
      } finally { this.actorSearching = false }
    },
    recentActorFromJob(job) { return { id: job.local_actress_id, name: job.source_actor_name || `演员 ${job.local_actress_id}`, name_kanji: job.source_actor_name || '', _recentJob: job } },
    async loadRecentActorJobs() {
      this.actorPickerError = ''
      try {
        const data = (await api.listSupplementJobs({ page: 1, page_size: 16 })).data || {}
        this.recentJobs = data.data || []
        const seen = new Set()
        this.recentActors = this.recentJobs.filter(j => j.local_actress_id && !seen.has(j.local_actress_id) && seen.add(j.local_actress_id)).slice(0, 6).map(this.recentActorFromJob)
      } catch { this.recentJobs = []; this.recentActors = []; this.actorPickerError = 'load_failed' }
    },
    async selectActorContext(actor) {
      if (!actor?.id) return
      this.actorContext = actor
      this.actorSearchKeyword = this.actorDisplayName(actor)
      await this.replaceSupplementRoute({ tab: this.tabToRoute(this.activeTab), actress_id: actor.id, ...this.activeFilters })
    },
    async applyActorContext(actressId) {
      const normalized = String(actressId || '').trim()
      if (!normalized) return
      try { const r = await api.getActress(normalized); this.actorContext = r.data || r }
      catch { this.actorContext = { id: normalized } }
      await this.loadSupplementStatus()
    },
    async applyJobActorContext(job) {
      if (!job?.local_actress_id) return
      await this.replaceSupplementRoute({ tab: 'jobs', actress_id: job.local_actress_id })
    },
    async clearActorContext() {
      this._stopSupplementPolling()
      this.actorContext = null; this.supplementStatus = null
      Object.assign(this.activeFilters, { status: '', source: '', error_provider: '', error_reason: '', q: '', quality: '', actress_id: '' })
      await this.replaceSupplementRoute()
      await this.loadRecentActorJobs()
    },
    async viewGfriendsAvatarJobs() { this.activeTab = 'jobs'; this.actorContext = null; await this.replaceSupplementRoute({ tab: 'jobs', source: 'gfriends' }) },
    async openSourcesFromMovie(movie) { this.diagnosticsFocusMovie = movie; await this.setActiveTab('diagnostics') },
    goActorContext() {
      if (!this.actorContext) return
      const name = this.actorContext.name_kanji || this.actorContext.name_romaji || this.actorContext.name || ''
      this.$router.push({ path: `/actor/${encodeURIComponent(name || this.actorContext.id)}`, query: { name, actress_id: this.actorContext.id } })
    },
    async loadSupplementStatus({ poll = true } = {}) {
      if (!this.actorContext?.id) return
      const resp = await api.getSupplementActressStatus(this.actorContext.id)
      this.supplementStatus = resp.data || resp
      if (poll && this.isSupplementRunning) this._startSupplementPolling()
    },
    async startSupplement() {
      if (!this.actorContext?.id || this.isSupplementRunning) return
      await api.startSupplementFilmographyJob(this.actorContext.id)
      ElMessage.success('已加入补全队列')
      await this.loadSupplementStatus()
      await this.setActiveTab('jobs')
    },
    async refreshResolved() {
      if (!this.actorContext?.id) return
      await api.refreshSupplementActressResolved(this.actorContext.id)
      ElMessage.success('已刷新版本条目')
      await this.loadSupplementStatus()
      this.refreshNonce++
    },
    _startSupplementPolling() {
      this._stopSupplementPolling()
      this.supplementPolling = setInterval(async () => {
        await this.loadSupplementStatus({ poll: false })
        if (!this.isSupplementRunning) { this._stopSupplementPolling(); this.refreshNonce++ }
      }, 4000)
    },
    _stopSupplementPolling() {
      if (this.supplementPolling) { clearInterval(this.supplementPolling); this.supplementPolling = null }
    },
  },
}
</script>
<style scoped src="../features/supplement/supplementManagement.css"></style>
