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

    <section class="workspace-view">
      <!-- 待补全作品 owns its own header in both scopes: the per-actress 作品目录 hero
           when scoped, and the 全部待补全 aggregate header when unscoped. -->
      <component
        :is="activeTabComponent"
        :actor-context="actorContext"
        :actor-name="actorContextName"
        :initial-filters="activeTabFilters"
        :global-queue="activeTab === 'jobs' && !actorContext"
        :context-label="globalQueueContextLabel"
        :context-items="activeTab === 'jobs' && !actorContext ? globalQueueContextItems : []"
        :refresh-nonce="refreshNonce"
        :recomputing="isSupplementRunning"
        @actor="applyJobActorContext"
        @select="enterActorWorkspace"
        @start-supplement="actorContext ? startSupplement() : clearActorContext()"
        @back-to-list="backToActorList"
        @view-all="viewAllPending"
        @pick-actor="setActiveTab('actors')"
        @filters-change="handleFiltersChange"
        @jobs-requested="setActiveTab('jobs')"
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

const ActorsTab = defineAsyncComponent(() => import('../features/supplement/ActorsTab.vue'))
const JobsTab = defineAsyncComponent(() => import('../features/supplement/JobsTab.vue'))
const MoviesTab = defineAsyncComponent(() => import('../features/supplement/MoviesTab.vue'))
const SourcesHealthTab = defineAsyncComponent(() => import('../features/supplement/SourcesHealthTab.vue'))

export default {
  name: 'SupplementManagement',
  components: { ActorsTab, JobsTab, MoviesTab, SourcesHealthTab },
  data: () => ({
    actorContext: null, activeTab: 'actors',
    activeFilters: { status: '', source: '', error_provider: '', error_reason: '', q: '', quality: '' },
    supplementStatus: null, supplementPolling: null, refreshNonce: 0,
    movieSummary: { total: 0, movies: [], fieldGapCount: 0, pendingCandidateCount: 0, detailTargetCount: 0 },
    sourceSummary: { count: 0, degraded: false },
    actorSummary: { total: 0 },
    hasInitialized: false, wasDeactivated: false, lastAppliedRouteKey: '',
  }),
  computed: {
    actorContextName() { return this.actorContext ? this.actorDisplayName(this.actorContext) : '' },
    actorContextOriginal() {
      if (!this.actorContext) return ''
      const original = this.actorContext.name_kanji || this.actorContext.name_romaji || ''
      return original && original !== this.actorContextName ? original : ''
    },
    actorContextAvatar() { return this.actorAvatar(this.actorContext) },
    isSupplementRunning() { return ['running', 'queued'].includes(this.supplementStatus?.last_job?.status) },
    activeTabComponent() {
      return { actors: 'ActorsTab', movies: 'MoviesTab', jobs: 'JobsTab', sourceHealth: 'SourcesHealthTab' }[this.activeTab] || 'ActorsTab'
    },
    activeTabFilters() {
      return { ...this.activeFilters, actress_id: this.actorContext?.id || '' }
    },
    tabItems() {
      const s = this.supplementStatus, f = this.activeFilters
      return [
        { key: 'actors', label: '待补全演员', count: this.actorSummary.total, status: this.actorContext ? '已锁定演员' : '订阅池', nextStep: '选演员补全' },
        { key: 'movies', label: '待补全作品', count: this.movieSummary.total, status: f.quality || f.q ? '已筛选' : '字段池', nextStep: '先补字段' },
        { key: 'jobs', label: '任务队列', count: s?.last_job?.id ? 1 : 0, status: this.statusLabel(s?.last_job?.status), nextStep: '查看任务' },
        { key: 'sourceHealth', label: '来源健康', count: this.sourceSummary.count, status: this.sourceSummary.degraded ? '来源异常' : '来源池', nextStep: '查看降级来源' },
      ]
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
      if (this.$route.path === '/supplement/actors') return 'actors'
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
    tabFromRoute(tab) {
      if (tab === 'jobs') return 'jobs'
      if (tab === 'sources') return 'sourceHealth'
      if (tab === 'movies') return 'movies'
      if (tab === 'actors') return 'actors'
      // No explicit tab: a scoped actress lands on 待补全作品, otherwise 待补全演员.
      return this.$route.query.actress_id ? 'movies' : 'actors'
    },
    tabToRoute(tab) {
      if (tab === 'jobs') return 'jobs'
      if (tab === 'sourceHealth') return 'sources'
      if (tab === 'actors') return 'actors'
      return 'movies'
    },
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
      // actress_id must come AFTER the activeFilters spread — applyRouteState seeds an
      // empty actress_id into activeFilters, which would otherwise clobber the scoped id.
      const query = { tab: this.tabToRoute(tab), ...this.activeFilters, actress_id: this.actorContext?.id }
      const routeChanged = await this.replaceSupplementRoute(query)
      if (!routeChanged) this.refreshNonce++
    },
    handleFiltersChange(filters) {
      Object.assign(this.activeFilters, filters)
      this.replaceSupplementRoute({ tab: this.tabToRoute(this.activeTab), ...this.activeFilters, actress_id: this.actorContext?.id })
    },
    handleSummaryChange(summary) {
      if ('actorsTotal' in summary) { this.actorSummary = { total: summary.actorsTotal }; return }
      if (summary.movies) this.movieSummary = { ...this.movieSummary, ...summary }
      else this.sourceSummary = { ...this.sourceSummary, ...summary }
    },
    handleWorkspaceAvatarError(e) { applyImageFallback(e, { label: this.actorContextName?.slice(0, 1) || '?' }) },
    actorDisplayName(actor) {
      return actor?.name_kanji_translated
        || actor?.name_romaji_translated
        || displayName(actor, 'name_kanji', 'name_romaji')
        || actor?.name_kanji
        || actor?.name_romaji
        || actor?.name
        || actor?.actress_name
        || ''
    },
    actorAvatar(actor) { return actor?.image_url ? actressImgUrl(actor.image_url) : '' },
    enterActorWorkspace(actor) {
      if (!actor?.id) return
      this.actorContext = actor
      this.setActiveTab('movies')
    },
    async backToActorList() {
      await this.clearActorContext()
      this.setActiveTab('actors')
    },
    // From a scoped 作品目录, jump out to the unscoped 全部待补全 aggregate (stay on 作品 tab).
    async viewAllPending() {
      this._stopSupplementPolling()
      this.actorContext = null
      this.supplementStatus = null
      Object.assign(this.activeFilters, { status: '', source: '', error_provider: '', error_reason: '', q: '', quality: '', actress_id: '' })
      await this.replaceSupplementRoute({ tab: 'movies' })
    },
    async applyActorContext(actressId) {
      const normalized = String(actressId || '').trim()
      if (!normalized) return
      try { const r = await api.getActress(normalized); this.actorContext = r.data || r }
      catch {
        // Keep any richer context we already entered with (e.g. from 待补全演员); only stub if absent.
        if (String(this.actorContext?.id || '') !== normalized) this.actorContext = { id: normalized }
      }
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
    },
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
