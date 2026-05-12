<template>
  <div class="supplement-page">
    <header class="supplement-topbar">
      <div>
        <p class="eyebrow">Supplement Studio</p>
        <h1>补全演员</h1>
      </div>
      <div class="topbar-actions">
        <button
          v-if="actorContext"
          class="btn btn-ghost btn-sm"
          type="button"
          @click="clearActorContext"
        >更换演员</button>
        <button
          class="btn btn-ghost btn-sm"
          type="button"
          @click="openGlobalQueue"
        >全局队列</button>
      </div>
    </header>

    <ActorPickerView
      v-if="showActorPicker"
      v-model:keyword="actorSearchKeyword"
      :actors="actorChoiceCards"
      :searched="actorSearched"
      :searching="actorSearching"
      :error="actorPickerError"
      :actor-avatar="actorAvatar"
      :actor-display-name="actorDisplayName"
      :actor-choice-status="actorChoiceStatus"
      @search="searchActorContext"
      @clear-search="clearActorSearch"
      @select="selectActorContext"
      @retry="loadRecentActorJobs"
    />

    <section v-else-if="actorContext" class="workspace-view">
      <div class="actor-workspace-hero apple-surface">
        <div class="actor-context-card">
          <div class="workspace-identity">
          <div class="workspace-avatar">
            <img
              v-if="actorContextAvatar"
              :src="actorContextAvatar"
              :alt="actorContextName"
              @error="$event.target.style.display = 'none'"
            />
            <span v-else>{{ actorContextName.slice(0, 1) || '?' }}</span>
          </div>
          <div class="workspace-title">
            <p class="eyebrow">当前演员上下文</p>
            <h2>{{ actorContextName }}</h2>
            <p>ID {{ actorContext.id }}</p>
          </div>
        </div>
        </div>
        <div class="workspace-status">
          <span
            class="status-pill"
            :class="`status-${supplementStatus?.last_job?.status || 'idle'}`"
          >{{ statusLabel(supplementStatus?.last_job?.status) }}</span>
          <div class="workspace-actions">
            <button
              class="btn btn-primary btn-sm"
              type="button"
              :disabled="isSupplementRunning"
              @click="startSupplement"
            >{{ isSupplementRunning ? '补全中...' : '补全作品' }}</button>
            <button class="btn btn-ghost btn-sm" type="button" @click="refreshResolved">刷新可展示</button>
            <button class="btn btn-ghost btn-sm" type="button" @click="goActorContext">返回演员页</button>
          </div>
        </div>
      </div>

      <div class="workspace-metrics">
        <div class="metric-card apple-surface">
          <span>{{ supplementStatus?.supplement_movies ?? '—' }}</span>
          <p>补全影片</p>
        </div>
        <div class="metric-card apple-surface">
          <span>{{ supplementStatus?.matched_r18 ?? '—' }}</span>
          <p>已匹配</p>
        </div>
        <div class="metric-card apple-surface">
          <span>{{ supplementStatus?.supplement_only ?? '—' }}</span>
          <p>仅补全</p>
        </div>
        <div class="metric-card apple-surface">
          <span>{{ supplementStatus?.resolved_videos ?? '—' }}</span>
          <p>可展示</p>
        </div>
      </div>

      <nav class="segmented-control apple-surface" aria-label="补全工作台视图">
        <button
          v-for="segment in workspaceSegments"
          :key="segment.key"
          type="button"
          :class="{ active: activeWorkspaceSegment === segment.key }"
          @click="setWorkspaceSegment(segment.key)"
        >{{ segment.label }}</button>
      </nav>

      <section v-if="activeWorkspaceSegment === 'movies'" class="workspace-panel apple-surface">
        <div class="panel-header">
          <div>
            <p class="eyebrow">Fields</p>
            <h2>作品字段</h2>
          </div>
          <button class="btn btn-primary btn-sm" type="button" :disabled="batchEnriching" @click="batchEnrichMovies">
            {{ batchEnriching ? '批量排队中...' : '批量补详情' }}
          </button>
          <button class="btn btn-ghost btn-sm" type="button" :disabled="candidateImporting" @click="createDownloadCandidates">
            {{ candidateImporting ? '生成中...' : '生成下载候选' }}
          </button>
        </div>
        <div class="filter-bar">
          <GlassSelect
            v-model="movieFilters.matched"
            :options="matchFilterOptions"
            size="compact"
            aria-label="影片匹配状态"
            @change="applyMovieFilters"
          />
          <GlassSelect
            v-model="movieFilters.quality"
            :options="qualityFilterOptions"
            size="compact"
            aria-label="影片质量筛选"
            @change="applyMovieFilters"
          />
          <input
            v-model="movieFilters.q"
            placeholder="搜索番号/标题"
            class="filter-input"
            @keyup.enter="applyMovieFilters"
          />
          <button class="btn btn-ghost btn-sm" type="button" @click="applyMovieFilters">筛选</button>
        </div>
        <div v-if="moviesLoading" class="loading-wrap"><div class="spinner-large"></div></div>
        <div v-else class="ios-list">
          <article v-for="movie in supplementMovies" :key="movie.id" class="ios-row movie-row">
            <div class="movie-row-main">
              <strong>{{ movie.dvd_id || movie.canonical_number || '—' }}</strong>
              <span>{{ movie.title || movie.dvd_id || movie.canonical_number || '—' }}</span>
              <small>{{ movie.release_date || '未知日期' }}</small>
            </div>
            <div class="movie-row-actions">
              <span class="status-pill" :class="`match-${movieMatchClass(movie)}`">{{ movieMatchLabel(movie) }}</span>
              <button
                v-if="movie.source_movie_id"
                class="btn btn-primary btn-sm"
                type="button"
                :disabled="enrichingMovies[movie.id]"
                @click="enrichMovie(movie)"
              >{{ enrichingMovies[movie.id] ? '排队中...' : '补详情' }}</button>
              <button class="btn btn-ghost btn-sm" type="button" @click="openMovieSources(movie)">诊断</button>
            </div>
          </article>
          <div v-if="!supplementMovies.length" class="empty-inline">暂无补全影片</div>
        </div>
        <div v-if="moviesTotalPages > 1" class="pagination">
          <button class="btn btn-ghost btn-sm" :disabled="moviePage <= 1" @click="moviePage--; loadMovies()">上一页</button>
          <span>{{ moviePage }} / {{ moviesTotalPages }}</span>
          <button class="btn btn-ghost btn-sm" :disabled="moviePage >= moviesTotalPages" @click="moviePage++; loadMovies()">下一页</button>
        </div>
      </section>

      <section v-if="activeWorkspaceSegment === 'jobs'" class="workspace-panel apple-surface">
        <div class="panel-header">
          <div>
            <p class="eyebrow">Queue</p>
            <h2>任务队列</h2>
          </div>
          <div class="filter-bar compact">
            <GlassSelect
              v-model="jobFilters.status"
              :options="jobStatusOptions"
              size="compact"
              aria-label="任务状态筛选"
              @change="applyJobFilters"
            />
            <button class="btn btn-ghost btn-sm" type="button" @click="applyJobFilters">刷新</button>
          </div>
        </div>
        <JobList
          :jobs="jobs"
          :loading="jobsLoading"
          :actor-context="actorContext"
          :job-label="jobActorLabel"
          :status-label="statusLabel"
          @retry="retryJob"
          @cancel="cancelJob"
          @actor="applyJobActorContext"
        />
        <div v-if="jobsTotalPages > 1" class="pagination">
          <button class="btn btn-ghost btn-sm" :disabled="jobPage <= 1" @click="jobPage--; loadJobs()">上一页</button>
          <span>{{ jobPage }} / {{ jobsTotalPages }}</span>
          <button class="btn btn-ghost btn-sm" :disabled="jobPage >= jobsTotalPages" @click="jobPage++; loadJobs()">下一页</button>
        </div>
      </section>

      <section v-if="activeWorkspaceSegment === 'diagnostics'" class="workspace-panel apple-surface">
        <div class="panel-header">
          <div>
            <p class="eyebrow">Sources</p>
            <h2>来源诊断</h2>
          </div>
        </div>
        <div class="empty-panel inner">
          <h3>从作品字段打开诊断</h3>
          <p>在作品字段列表中点击“诊断”，可查看该影片的字段来源、源身份、详情来源和匹配候选。</p>
        </div>
      </section>

      <SourceHealthPanel
        v-if="activeWorkspaceSegment === 'sourceHealth'"
        v-model:provider-smoke-form="providerSmokeForm"
        v-model:provider-smoke-report="providerSmokeReport"
        :provider-source-options="providerSourceOptions"
        :provider-smoke-loading="providerSmokeLoading"
        :provider-smoke-runs="providerSmokeRuns"
        :source-health-loading="sourceHealthLoading"
        :source-health-rows="sourceHealthRows"
        :source-action-loading="sourceActionLoading"
        :format-action-time="formatActionTime"
        :smoke-run-label="smokeRunLabel"
        :source-health-label="sourceHealthLabel"
        :source-budget-label="sourceBudgetLabel"
        :source-health-detail="sourceHealthDetail"
        @refresh-health="loadSourceHealth"
        @run-smoke="runProviderSmoke"
        @load-smoke-runs="loadProviderSmokeRuns"
        @pause-source="pauseSource"
        @resume-source="resumeSource"
      />
    </section>

    <section v-else-if="showGlobalQueue" class="global-queue-view">
      <div class="workspace-panel apple-surface">
        <div class="panel-header">
          <div>
            <p class="eyebrow">Global Queue</p>
            <h2>全局队列</h2>
          </div>
          <div class="filter-bar compact">
            <GlassSelect
              v-model="jobFilters.status"
              :options="jobStatusOptions"
              size="compact"
              aria-label="全局队列状态筛选"
              @change="loadJobs"
            />
            <button class="btn btn-ghost btn-sm" type="button" :disabled="recovering" @click="recoverStale">
              {{ recovering ? '恢复中...' : '恢复卡住任务' }}
            </button>
          </div>
        </div>
        <JobList
          :jobs="jobs"
          :loading="jobsLoading"
          :actor-context="null"
          :job-label="jobActorLabel"
          :status-label="statusLabel"
          @retry="retryJob"
          @cancel="cancelJob"
          @actor="applyJobActorContext"
        />
      </div>
    </section>

    <div v-if="sourceDiagnosticsOpen" class="diagnostics-overlay" @click.self="closeMovieSources">
      <div class="diagnostics-panel apple-surface">
        <div class="diagnostics-header">
          <div>
            <p class="eyebrow">Diagnostics</p>
            <h2>{{ diagnosticsMovieTitle }}</h2>
            <p>{{ diagnosticsMovieSubtitle }}</p>
          </div>
          <button class="btn btn-ghost btn-sm" type="button" @click="closeMovieSources">关闭</button>
        </div>
        <div v-if="sourceDiagnosticsLoading" class="loading-wrap"><div class="spinner-large"></div></div>
        <div v-else-if="sourceDiagnostics" class="diagnostics-body">
          <section class="diagnostics-section">
            <h3>选中字段</h3>
            <div v-if="sourceDiagnostics.chosen_fields?.length" class="diagnostics-table">
              <div class="diagnostics-row diagnostics-row-head">
                <span>字段</span>
                <span>来源</span>
                <span>值</span>
              </div>
              <div v-for="field in sourceDiagnostics.chosen_fields" :key="`chosen-${field.field_name}`" class="diagnostics-row">
                <span>{{ fieldLabel(field.field_name) }}</span>
                <span>{{ field.source }}</span>
                <span class="diagnostics-value">{{ fieldValuePreview(field.field_value) }}</span>
              </div>
            </div>
            <div v-else class="empty-inline">暂无字段来源</div>
          </section>
          <section class="diagnostics-section">
            <h3>源身份</h3>
            <div v-if="sourceDiagnostics.identities?.length" class="identity-list">
              <a
                v-for="identity in sourceDiagnostics.identities"
                :key="`${identity.source}-${identity.source_movie_id}`"
                :href="identity.source_url || '#'"
                class="identity-chip"
                target="_blank"
              >{{ identity.source }}: {{ identity.source_movie_id }}</a>
            </div>
            <div v-else class="empty-inline">暂无源身份</div>
          </section>
          <section class="diagnostics-section">
            <h3>详情来源</h3>
            <div v-if="sourceDiagnostics.details?.length" class="detail-source-list">
              <div v-for="detail in sourceDiagnostics.details" :key="`${detail.source}-${detail.source_movie_id}`" class="detail-source-item">
                <strong>{{ detail.source }} · {{ detail.source_movie_id }}</strong>
                <span>{{ [detail.runtime_mins && `${detail.runtime_mins} 分钟`, detail.maker_name, detail.label_name, detail.genres?.slice(0, 4).join(' / ')].filter(Boolean).join(' · ') }}</span>
              </div>
            </div>
            <div v-else class="empty-inline">暂无详情来源</div>
          </section>
          <section class="diagnostics-section">
            <h3>匹配候选</h3>
            <div class="manual-match-bar">
              <input
                v-model="manualContentId"
                placeholder="输入 content_id 人工确认"
                class="filter-input"
                @keyup.enter="manualMatchMovie()"
              />
              <button class="btn btn-primary btn-sm" type="button" :disabled="manualActionLoading || !manualContentId.trim()" @click="manualMatchMovie()">确认匹配</button>
              <button class="btn btn-ghost btn-sm" type="button" :disabled="manualActionLoading" @click="manualUnmatchMovie">解除匹配</button>
              <button class="btn btn-ghost btn-sm danger" type="button" :disabled="manualActionLoading" @click="manualIgnoreMovie">忽略</button>
            </div>
            <div v-if="sourceDiagnostics.match_candidates?.length" class="diagnostics-table">
              <div class="diagnostics-row diagnostics-row-head diagnostics-row-candidates">
                <span>content_id</span>
                <span>分数</span>
                <span>状态</span>
                <span>操作</span>
              </div>
              <div v-for="candidate in sourceDiagnostics.match_candidates" :key="candidate.candidate_content_id" class="diagnostics-row diagnostics-row-candidates">
                <span>{{ candidate.candidate_content_id }}</span>
                <span>{{ candidate.score }}</span>
                <span>{{ candidate.status }}</span>
                <span>
                  <button class="btn btn-ghost btn-xs" type="button" :disabled="manualActionLoading" @click="manualMatchMovie(candidate.candidate_content_id)">确认</button>
                </span>
              </div>
            </div>
            <div v-else class="empty-inline">暂无匹配候选</div>
          </section>
          <section class="diagnostics-section">
            <h3>人工校正记录</h3>
            <div v-if="sourceDiagnostics.manual_actions?.length" class="manual-action-list">
              <div v-for="action in sourceDiagnostics.manual_actions" :key="`${action.action}-${action.created_at}`" class="manual-action-item">
                <strong>{{ manualActionLabel(action.action) }}</strong>
                <span>{{ action.content_id || action.previous_content_id || '无 content_id' }}</span>
                <small>{{ action.reason || '未填写原因' }} · {{ formatActionTime(action.created_at) }}</small>
              </div>
            </div>
            <div v-else class="empty-inline">暂无人工校正记录</div>
          </section>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import api from '../api'
import { ElMessage } from 'element-plus'
import { actressImgUrl } from '../utils/imageUrl.js'
import { displayName } from '../utils/displayLang.js'
import GlassSelect from '../components/GlassSelect.vue'
import JobList from '../features/supplement/SupplementJobList.vue'
import ActorPickerView from '../features/supplement/ActorPickerView.vue'
import SourceHealthPanel from '../features/supplement/SourceHealthPanel.vue'

export default {
  name: 'SupplementManagement',
  components: { ActorPickerView, JobList, SourceHealthPanel, GlassSelect },
  data() {
    return {
      stats: null,
      statsLoading: false,
      jobs: [],
      jobsLoading: false,
      recentJobs: [],
      recentActors: [],
      recentJobsLoading: false,
      actorPickerError: '',
      jobPage: 1,
      jobsTotalCount: 0,
      jobsTotalPages: 1,
      jobFilters: { status: '', actress_id: '' },
      actorContext: null,
      actorContextLoading: false,
      actorSearchKeyword: '',
      actorSearchResults: [],
      actorSearching: false,
      actorSearched: false,
      showGlobalQueue: false,
      activeWorkspaceSegment: 'movies',
      workspaceSegments: [
        { key: 'movies', label: '作品字段' },
        { key: 'jobs', label: '任务队列' },
        { key: 'diagnostics', label: '来源诊断' },
        { key: 'sourceHealth', label: '来源状态' },
      ],
      matchFilterOptions: [
        { value: null, label: '全部' },
        { value: false, label: '未匹配' },
        { value: true, label: '已匹配' },
      ],
      qualityFilterOptions: [
        { value: '', label: '全部质量' },
        { value: 'missing_cover', label: '缺封面' },
        { value: 'missing_runtime', label: '缺时长' },
        { value: 'missing_maker', label: '缺厂商' },
        { value: 'missing_categories', label: '缺分类' },
        { value: 'low_completeness', label: '低完整度' },
      ],
      jobStatusOptions: [
        { value: '', label: '全部状态' },
        { value: 'queued', label: '排队中' },
        { value: 'running', label: '运行中' },
        { value: 'succeeded', label: '已完成' },
        { value: 'failed', label: '失败' },
      ],
      supplementStatus: null,
      supplementPolling: null,
      recovering: false,
      supplementMovies: [],
      moviesLoading: false,
      enrichingMovies: {},
      batchEnriching: false,
      candidateImporting: false,
      moviePage: 1,
      moviesTotalCount: 0,
      moviesTotalPages: 1,
      movieFilters: { matched: false, quality: '', actress_id: '', q: '' },
      sourceDiagnosticsOpen: false,
      sourceDiagnosticsLoading: false,
      sourceDiagnostics: null,
      manualContentId: '',
      manualActionLoading: false,
      sourceHealth: [],
      sourceBudgets: [],
      sourceHealthLoading: false,
      sourceActionLoading: '',
      providerSmokeLoading: false,
      providerSmokeReport: null,
      providerSmokeForm: { source: '', sourceMovieId: '' },
      providerSmokeRuns: [],
      hasInitialized: false,
      wasDeactivated: false,
      lastAppliedRouteKey: '',
      statsLoadedAt: 0,
      recentActorsLoadedAt: 0,
    }
  },
  computed: {
    showActorPicker() {
      return !this.actorContext && !this.showGlobalQueue
    },
    recentActorJobs() {
      const seen = new Set()
      const result = []
      for (const job of this.recentJobs) {
        if (!job.local_actress_id || seen.has(job.local_actress_id)) continue
        seen.add(job.local_actress_id)
        result.push(job)
      }
      return result.slice(0, 6)
    },
    actorChoiceCards() {
      if (this.actorSearchResults.length || this.actorSearched) {
        return this.actorSearchResults
      }
      return this.recentActors
    },
    actorContextName() {
      if (!this.actorContext) return ''
      return this.actorDisplayName(this.actorContext)
    },
    actorContextAvatar() {
      return this.actorAvatar(this.actorContext)
    },
    isSupplementRunning() {
      const status = this.supplementStatus?.last_job?.status
      return status === 'running' || status === 'queued'
    },
    diagnosticsMovieTitle() {
      const movie = this.sourceDiagnostics?.movie
      return movie?.dvd_id || movie?.canonical_number || '来源诊断'
    },
    diagnosticsMovieSubtitle() {
      const movie = this.sourceDiagnostics?.movie
      return movie?.title || movie?.matched_content_id || ''
    },
    sourceHealthRows() {
      const budgets = new Map((this.sourceBudgets || []).map(item => [item.source, item]))
      return (this.sourceHealth || []).map(source => ({
        ...source,
        budget: budgets.get(source.source) || null,
      }))
    },
    providerSourceOptions() {
      return [
        { value: '', label: '默认样本' },
        ...this.sourceHealthRows.map(source => ({
          value: source.source,
          label: source.display_name || source.source,
        })),
      ]
    },
  },
  watch: {
    '$route.fullPath': {
      handler() {
        if (this.$route.path !== '/supplement') return
        this.applyRouteState()
      },
    },
  },
  mounted() {
    this.hasInitialized = true
    this.applyRouteState({ force: true })
    this.loadStats()
    if (!this.$route.query.actress_id && this.$route.query.tab !== 'jobs') {
      this.loadRecentActorJobs()
    }
  },
  activated() {
    if (!this.hasInitialized || !this.wasDeactivated || this.$route.path !== '/supplement') return
    this.wasDeactivated = false
    this.applyRouteState()
    const now = Date.now()
    if (now - this.statsLoadedAt > 60000) this.loadStats({ silent: true })
    if (this.showActorPicker && now - this.recentActorsLoadedAt > 60000) {
      this.loadRecentActorJobs({ silent: true })
    }
    if (this.isSupplementRunning) this._startSupplementPolling()
  },
  deactivated() {
    this.wasDeactivated = true
    this._stopSupplementPolling()
  },
  beforeUnmount() {
    this._stopSupplementPolling()
  },
  methods: {
    supplementQueryKey(query = this.$route.query) {
      const field = (key) => {
        const value = query[key]
        if (Array.isArray(value)) return value[0] ? String(value[0]).trim() : ''
        return value == null ? '' : String(value).trim()
      }
      return JSON.stringify({
        tab: field('tab'),
        actress_id: field('actress_id'),
        q: field('q'),
      })
    },
    buildSupplementQuery(query = {}) {
      return Object.entries(query).reduce((result, [key, value]) => {
        if (value === undefined || value === null || value === '') return result
        result[key] = String(value)
        return result
      }, {})
    },
    async replaceSupplementRoute(query = {}) {
      const nextQuery = this.buildSupplementQuery(query)
      if (this.$route.path === '/supplement' && this.supplementQueryKey(nextQuery) === this.supplementQueryKey()) {
        return false
      }
      await this.$router.replace({ path: '/supplement', query: nextQuery })
      return true
    },
    async loadWorkspaceSegment(segment, options = {}) {
      if (segment === 'jobs') await this.loadJobs(options)
      if (segment === 'movies') await this.loadMovies(options)
      if (segment === 'sourceHealth') await this.loadSourceHealth(options)
    },
    async applyRouteState({ force = false } = {}) {
      if (this.$route.path !== '/supplement') return
      const routeKey = this.supplementQueryKey()
      if (!force && routeKey === this.lastAppliedRouteKey) return
      this.lastAppliedRouteKey = routeKey
      const tab = this.$route.query.tab
      const actressId = this.$route.query.actress_id
      const q = typeof this.$route.query.q === 'string' ? this.$route.query.q.trim() : ''
      if (this.movieFilters.q !== q) {
        this.movieFilters.q = q
        this.moviePage = 1
      }
      if (actressId) {
        this.showGlobalQueue = false
        this.activeWorkspaceSegment = this.segmentFromTab(tab)
        await this.applyActorContext(actressId)
        await this.loadWorkspaceSegment(this.activeWorkspaceSegment)
        return
      }
      this.actorContext = null
      this.jobFilters.actress_id = ''
      this.movieFilters.actress_id = ''
      if (tab === 'jobs') {
        this.showGlobalQueue = true
        await this.loadJobs()
      } else {
        this.showGlobalQueue = false
      }
    },
    segmentFromTab(tab) {
      if (tab === 'jobs') return 'jobs'
      if (tab === 'stats') return 'diagnostics'
      if (tab === 'sources') return 'sourceHealth'
      return 'movies'
    },
    tabFromSegment(segment) {
      if (segment === 'jobs') return 'jobs'
      if (segment === 'diagnostics') return 'stats'
      if (segment === 'sourceHealth') return 'sources'
      return 'movies'
    },
    async setWorkspaceSegment(segment) {
      this.activeWorkspaceSegment = segment
      const query = { tab: this.tabFromSegment(segment), actress_id: this.actorContext?.id }
      if (this.movieFilters.q) query.q = this.movieFilters.q
      const routeChanged = await this.replaceSupplementRoute(query)
      if (!routeChanged) await this.loadWorkspaceSegment(segment)
    },
    statusLabel(status) {
      const map = { queued: '排队中', running: '运行中', succeeded: '已完成', failed: '失败', idle: '待开始' }
      return map[status] || status || '待开始'
    },
    jobLabel(job) {
      if (job.job_type === 'movie_detail') {
        return job.source_movie_id ? `影片 ${job.source_movie_id}` : '影片详情'
      }
      return job.source_actor_name || (job.local_actress_id ? `演员 ${job.local_actress_id}` : '演员任务')
    },
    jobActorLabel(job) {
      const base = this.jobLabel(job)
      const actorName = this.actorContext ? this.actorContextName : (job.source_actor_name || '')
      const actorId = job.local_actress_id || this.actorContext?.id
      if (!actorName && !actorId) return base
      const actor = actorName || `演员 ${actorId}`
      return base.includes(actor) ? base : `${actor} · ${base}`
    },
    jobActorInitial(job) {
      return (job.source_actor_name || String(job.local_actress_id || '?')).slice(0, 1)
    },
    actorDisplayName(actor) {
      if (!actor) return ''
      return displayName(actor, 'name_kanji', 'name_romaji')
        || actor.name_kanji
        || actor.name_romaji
        || actor.name
        || `演员 ${actor.id}`
    },
    actorAvatar(actor) {
      if (!actor?.image_url) return ''
      return actressImgUrl(actor.image_url)
    },
    actorChoiceStatus(actor) {
      if (!actor) return ''
      if (actor._recentJob) {
        return `${this.jobLabel(actor._recentJob)} · ${this.statusLabel(actor._recentJob.status)}`
      }
      return '选择后进入补全工作台'
    },
    async searchActorContext() {
      const keyword = this.actorSearchKeyword.trim()
      if (!keyword) return
      this.actorSearching = true
      this.actorSearched = true
      this.actorSearchResults = []
      try {
        const resp = await api.searchActors(keyword)
        const data = resp.data || resp
        this.actorSearchResults = data.data || data || []
      } catch (e) {
        console.error('Search actor failed:', e)
      } finally {
        this.actorSearching = false
      }
    },
    clearActorSearch() {
      this.actorSearchKeyword = ''
      this.actorSearchResults = []
      this.actorSearched = false
    },
    async selectActorContext(actor) {
      if (!actor?.id) return
      this.actorContext = actor
      this.actorSearchKeyword = this.actorDisplayName(actor)
      this.actorSearchResults = []
      this.actorSearched = false
      this.jobPage = 1
      this.moviePage = 1
      const query = { tab: this.tabFromSegment(this.activeWorkspaceSegment), actress_id: actor.id }
      if (this.movieFilters.q) query.q = this.movieFilters.q
      const routeChanged = await this.replaceSupplementRoute(query)
      if (!routeChanged) {
        await this.applyActorContext(actor.id)
        await this.loadMovies()
      }
    },
    async applyActorContext(actressId) {
      const normalized = String(actressId || '').trim()
      if (!normalized) return
      this.jobFilters.actress_id = normalized
      this.movieFilters.actress_id = normalized
      this.actorContextLoading = true
      try {
        const resp = await api.getActress(normalized)
        this.actorContext = resp.data || resp
      } catch (e) {
        console.warn('Load actor context failed:', e)
        this.actorContext = { id: normalized }
      } finally {
        this.actorContextLoading = false
      }
      await this.loadSupplementStatus()
    },
    async applyJobActorContext(job) {
      if (!job?.local_actress_id) return
      this.jobPage = 1
      this.moviePage = 1
      const nextSegment = this.showGlobalQueue ? 'jobs' : this.activeWorkspaceSegment
      this.activeWorkspaceSegment = nextSegment
      const routeChanged = await this.replaceSupplementRoute({ tab: this.tabFromSegment(nextSegment), actress_id: job.local_actress_id })
      if (!routeChanged) {
        await this.applyActorContext(job.local_actress_id)
        await this.loadWorkspaceSegment(nextSegment)
      }
    },
    async clearActorContext() {
      this._stopSupplementPolling()
      this.actorContext = null
      this.supplementStatus = null
      this.jobFilters.actress_id = ''
      this.movieFilters.actress_id = ''
      this.movieFilters.q = ''
      this.actorSearchKeyword = ''
      this.actorSearchResults = []
      this.actorSearched = false
      this.showGlobalQueue = false
      await this.replaceSupplementRoute()
      this.loadRecentActorJobs({ silent: true })
    },
    async openGlobalQueue() {
      this.showGlobalQueue = true
      this.actorContext = null
      this.jobFilters.actress_id = ''
      this.movieFilters.actress_id = ''
      this.movieFilters.q = ''
      const routeChanged = await this.replaceSupplementRoute({ tab: 'jobs' })
      if (!routeChanged) await this.loadJobs()
    },
    goActorContext() {
      if (!this.actorContext) return
      const name = this.actorContext.name_kanji || this.actorContext.name_romaji || this.actorContext.name || ''
      this.$router.push({ path: `/actor/${encodeURIComponent(name || this.actorContext.id)}`, query: { name, actress_id: this.actorContext.id } })
    },
    async loadSupplementStatus() {
      if (!this.actorContext?.id) return
      const normalized = String(this.actorContext.id)
      try {
        const resp = await api.getSupplementActressStatus(normalized)
        this.supplementStatus = resp.data || resp
        if (this.isSupplementRunning) this._startSupplementPolling()
      } catch (e) {
        console.warn('Load supplement status failed:', e)
      }
    },
    async startSupplement() {
      if (!this.actorContext?.id || this.isSupplementRunning) return
      try {
        await api.startSupplementFilmographyJob(this.actorContext.id)
        ElMessage.success('已加入补全队列')
        await this.loadSupplementStatus()
        this.activeWorkspaceSegment = 'jobs'
        await this.loadJobs()
      } catch (e) {
        console.error('Start supplement failed:', e)
      }
    },
    async refreshResolved() {
      if (!this.actorContext?.id) return
      try {
        await api.refreshSupplementActressResolved(this.actorContext.id)
        ElMessage.success('已刷新可展示影片')
        await this.loadSupplementStatus()
        await this.loadMovies()
      } catch (e) {
        console.error('Refresh resolved failed:', e)
      }
    },
    _startSupplementPolling() {
      this._stopSupplementPolling()
      this.supplementPolling = setInterval(async () => {
        await this.loadSupplementStatus()
        if (!this.isSupplementRunning) this._stopSupplementPolling()
      }, 4000)
    },
    _stopSupplementPolling() {
      if (this.supplementPolling) {
        clearInterval(this.supplementPolling)
        this.supplementPolling = null
      }
    },
    movieMatchState(movie) {
      if (movie?.matched_content_id) return 'matched'
      if (movie?.match_status === 'manual_ignored') return 'ignored'
      if (movie?.match_status === 'candidate' || (movie?.match_candidate_count ?? 0) > 0) return 'candidate'
      return 'supplement-only'
    },
    movieMatchClass(movie) {
      return this.movieMatchState(movie)
    },
    movieMatchLabel(movie) {
      const state = this.movieMatchState(movie)
      if (state === 'matched') return `已匹配 ${movie.matched_content_id}`
      if (state === 'candidate') return (movie.match_candidate_count ?? 0) > 0 ? `待确认 ${movie.match_candidate_count}` : '待确认'
      if (state === 'ignored') return '已忽略'
      return '仅补全'
    },
    fieldLabel(fieldName) {
      const map = {
        title: '标题',
        release_date: '发行日',
        runtime_mins: '时长',
        cover_url: '封面',
        cover_thumb_url: '缩略图',
        maker_name: '厂商',
        label_name: '厂牌',
        series_name: '系列',
        category_names: '分类',
        actor_names: '演员',
        sample_image_urls: '样张',
        sample_movie_url: '预告',
        source_url: '来源链接',
        display_number: '展示番号',
        normalized_number: '规范番号',
      }
      return map[fieldName] || fieldName
    },
    fieldValuePreview(value) {
      if (!value) return ''
      const text = String(value)
      return text.length > 140 ? `${text.slice(0, 140)}...` : text
    },
    closeMovieSources() {
      this.sourceDiagnosticsOpen = false
      this.sourceDiagnostics = null
      this.manualContentId = ''
    },
    async openMovieSources(movie) {
      if (!movie?.id) return
      this.activeWorkspaceSegment = 'diagnostics'
      this.sourceDiagnosticsOpen = true
      this.sourceDiagnosticsLoading = true
      this.sourceDiagnostics = null
      try {
        const resp = await api.getSupplementMovieSources(movie.id)
        this.sourceDiagnostics = resp.data || resp
        this.manualContentId = this.sourceDiagnostics?.movie?.matched_content_id || ''
      } catch (e) {
        console.error('Load movie sources failed:', e)
      } finally {
        this.sourceDiagnosticsLoading = false
      }
    },
    async manualMatchMovie(candidateContentId = '') {
      const movieId = this.sourceDiagnostics?.movie?.id
      const contentId = String(candidateContentId || this.manualContentId || '').trim()
      if (!movieId || !contentId || this.manualActionLoading) return
      this.manualActionLoading = true
      try {
        await api.matchSupplementMovie(movieId, contentId, '人工确认匹配')
        ElMessage.success('已确认匹配')
        await this.reloadCurrentDiagnostics()
      } catch (e) {
        console.error('Manual match failed:', e)
      } finally {
        this.manualActionLoading = false
      }
    },
    async manualIgnoreMovie() {
      const movieId = this.sourceDiagnostics?.movie?.id
      if (!movieId || this.manualActionLoading) return
      this.manualActionLoading = true
      try {
        await api.ignoreSupplementMovie(movieId, '人工忽略')
        ElMessage.success('已忽略该补全影片')
        await this.reloadCurrentDiagnostics()
      } catch (e) {
        console.error('Manual ignore failed:', e)
      } finally {
        this.manualActionLoading = false
      }
    },
    async manualUnmatchMovie() {
      const movieId = this.sourceDiagnostics?.movie?.id
      if (!movieId || this.manualActionLoading) return
      this.manualActionLoading = true
      try {
        await api.unmatchSupplementMovie(movieId, '人工解除匹配')
        ElMessage.success('已解除匹配')
        await this.reloadCurrentDiagnostics()
      } catch (e) {
        console.error('Manual unmatch failed:', e)
      } finally {
        this.manualActionLoading = false
      }
    },
    async reloadCurrentDiagnostics() {
      const movieId = this.sourceDiagnostics?.movie?.id
      if (!movieId) return
      const resp = await api.getSupplementMovieSources(movieId)
      this.sourceDiagnostics = resp.data || resp
      this.manualContentId = this.sourceDiagnostics?.movie?.matched_content_id || ''
      await this.loadMovies()
      await this.loadSupplementStatus()
    },
    sourceHealthLabel(status) {
      const map = { healthy: '健康', degraded: '降级', cooling_down: '冷却中', paused: '已暂停', unknown: '未检测' }
      return map[status] || status || '未检测'
    },
    sourceHealthDetail(source) {
      if (!source) return ''
      const failures = source.consecutive_failures ? `连续失败 ${source.consecutive_failures}` : '无连续失败'
      if (source.cooldown_until) return `${failures} · 冷却至 ${new Date(source.cooldown_until).toLocaleTimeString()}`
      return `${failures} · 成功 ${source.success_count || 0} / 失败 ${source.failure_count || 0}`
    },
    sourceBudgetLabel(budget) {
      if (!budget) return '预算状态未加载'
      const lock = budget.global_lock_enabled ? '全局锁已启用' : '仅本进程'
      return `${lock} · 本进程 ${budget.local_active || 0} 个请求`
    },
    smokeRunLabel(run) {
      const req = run?.request || {}
      if (req.source_movie_id) return `${req.source || 'source'} · ${req.source_movie_id}`
      if (req.source) return `${req.source} 默认样本`
      if (req.samples?.length) return `${req.samples.length} 个样本`
      return '默认样本'
    },
    manualActionLabel(action) {
      const map = { match: '确认匹配', ignore: '忽略', unmatch: '解除匹配' }
      return map[action] || action || '人工操作'
    },
    formatActionTime(value) {
      if (!value) return ''
      return new Date(value).toLocaleString()
    },
    async loadSourceHealth({ silent = false } = {}) {
      const showLoading = !silent
      if (showLoading) this.sourceHealthLoading = true
      try {
        const [healthResp, budgetResp, smokeRunsResp] = await Promise.all([
          api.listSupplementSourcesHealth(),
          api.listSupplementSourcesBudgets(),
          api.listSupplementProviderSmokeRuns(5, this.providerSmokeForm.source),
        ])
        this.sourceHealth = healthResp.data || healthResp || []
        this.sourceBudgets = budgetResp.data || budgetResp || []
        this.providerSmokeRuns = smokeRunsResp.data || smokeRunsResp || []
      } catch (e) {
        console.error('Load source health failed:', e)
      } finally {
        if (showLoading) this.sourceHealthLoading = false
      }
    },
    async loadProviderSmokeRuns() {
      try {
        const resp = await api.listSupplementProviderSmokeRuns(5, this.providerSmokeForm.source)
        this.providerSmokeRuns = resp.data || resp || []
      } catch (e) {
        console.error('Load provider smoke history failed:', e)
      }
    },
    async runProviderSmoke() {
      if (this.providerSmokeLoading) return
      const source = (this.providerSmokeForm.source || '').trim()
      const sourceMovieId = (this.providerSmokeForm.sourceMovieId || '').trim()
      if (sourceMovieId && !source) {
        ElMessage.warning('自定义样本需要先选择来源')
        return
      }
      const payload = {}
      if (source) payload.source = source
      if (sourceMovieId) {
        payload.source_movie_id = sourceMovieId
        payload.name = `${source} ${sourceMovieId}`
      }
      this.providerSmokeLoading = true
      try {
        const resp = await api.runSupplementProviderSmoke(payload)
        this.providerSmokeReport = resp.data || resp
        await this.loadProviderSmokeRuns()
      } catch (e) {
        console.error('Run provider smoke failed:', e)
      } finally {
        this.providerSmokeLoading = false
      }
    },
    async pauseSource(source) {
      if (!source || this.sourceActionLoading) return
      this.sourceActionLoading = source
      try {
        await api.pauseSupplementSource(source, 'manual pause from supplement management', 24 * 60)
        await this.loadSourceHealth()
      } catch (e) {
        console.error('Pause source failed:', e)
      } finally {
        this.sourceActionLoading = ''
      }
    },
    async resumeSource(source) {
      if (!source || this.sourceActionLoading) return
      this.sourceActionLoading = source
      try {
        await api.resumeSupplementSource(source)
        await this.loadSourceHealth()
      } catch (e) {
        console.error('Resume source failed:', e)
      } finally {
        this.sourceActionLoading = ''
      }
    },
    async loadStats({ silent = false } = {}) {
      const showLoading = !silent
      if (showLoading) this.statsLoading = true
      try {
        const resp = await api.getSupplementStats()
        this.stats = resp.data || resp
        this.statsLoadedAt = Date.now()
      } catch (e) {
        console.error('Load supplement stats failed:', e)
      } finally {
        if (showLoading) this.statsLoading = false
      }
    },
    async loadRecentActorJobs({ silent = false } = {}) {
      const hasCachedData = this.recentJobs.length || this.recentActors.length
      const showLoading = !silent
      if (showLoading) this.recentJobsLoading = true
      this.actorPickerError = ''
      try {
        const resp = await api.listSupplementJobs({ page: 1, page_size: 16 })
        const data = resp.data || resp
        this.recentJobs = data.data || []
        await this.loadRecentActors()
        this.recentActorsLoadedAt = Date.now()
      } catch (e) {
        console.error('Load recent supplement jobs failed:', e)
        if (!hasCachedData) {
          this.recentJobs = []
          this.recentActors = []
          this.actorPickerError = 'load_failed'
        }
      } finally {
        if (showLoading) this.recentJobsLoading = false
      }
    },
    async loadRecentActors() {
      const jobs = this.recentActorJobs
      const actors = []
      for (const job of jobs) {
        try {
          const resp = await api.getActress(job.local_actress_id)
          actors.push({ ...(resp.data || resp), _recentJob: job })
        } catch (e) {
          actors.push({
            id: job.local_actress_id,
            name: job.source_actor_name || `演员 ${job.local_actress_id}`,
            _recentJob: job,
          })
        }
      }
      this.recentActors = actors
    },
    async loadJobs({ silent = false } = {}) {
      const showLoading = !silent
      if (showLoading) this.jobsLoading = true
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
        if (showLoading) this.jobsLoading = false
      }
    },
    async applyJobFilters() {
      this.jobPage = 1
      await this.loadJobs()
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
        await api.recoverStaleSupplementJobs(30)
        await this.loadJobs()
      } catch (e) {
        console.error('Recover stale failed:', e)
      } finally {
        this.recovering = false
      }
    },
    async loadMovies({ silent = false } = {}) {
      const showLoading = !silent
      if (showLoading) this.moviesLoading = true
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
        if (showLoading) this.moviesLoading = false
      }
    },
    async applyMovieFilters() {
      this.moviePage = 1
      await this.loadMovies()
    },
    async enrichMovie(movie) {
      if (!movie?.source_movie_id || this.enrichingMovies[movie.id]) return
      this.enrichingMovies = { ...this.enrichingMovies, [movie.id]: true }
      try {
        await api.startSupplementMovieDetailJob(movie.source_movie_id, 'all', movie.local_actress_id || this.actorContext?.id)
        ElMessage.success('已加入详情任务队列')
        this.activeWorkspaceSegment = 'jobs'
        this.jobPage = 1
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
        const params = { source: 'all', limit: 20 }
        if (this.movieFilters.matched !== null) params.matched = this.movieFilters.matched
        if (this.movieFilters.actress_id) params.actress_id = this.movieFilters.actress_id
        if (this.movieFilters.q) params.q = this.movieFilters.q
        if (this.movieFilters.quality === 'missing_cover') params.missing_cover = true
        if (this.movieFilters.quality === 'missing_runtime') params.missing_runtime = true
        if (this.movieFilters.quality === 'missing_maker') params.missing_maker = true
        if (this.movieFilters.quality === 'missing_categories') params.missing_categories = true
        if (this.movieFilters.quality === 'low_completeness') params.max_completeness = 2
        await api.startSupplementMovieDetailBatchJobs(params)
        ElMessage.success('已批量加入详情任务队列')
        this.activeWorkspaceSegment = 'jobs'
        this.jobPage = 1
        await this.loadJobs()
      } catch (e) {
        console.error('Start batch movie detail jobs failed:', e)
      } finally {
        this.batchEnriching = false
      }
    },
    async createDownloadCandidates() {
      if (this.candidateImporting) return
      this.candidateImporting = true
      try {
        const params = { limit: 100 }
        if (this.actorContext?.id) params.actress_id = this.actorContext.id
        if (this.actorContextName) params.actress_name = this.actorContextName
        if (this.movieFilters.q) params.q = this.movieFilters.q
        const resp = await api.createSupplementDownloadCandidates(params)
        const data = resp.data || resp
        ElMessage.success(`已生成 ${data.created || 0} 个下载候选，已有 ${data.existing || 0} 个`)
        this.$router.push({
          path: '/downloads',
          query: {
            tab: 'candidates',
            status: 'candidate',
            source: 'supplement',
            ...(this.actorContext?.id ? { actress_id: this.actorContext.id } : {}),
            ...(this.movieFilters.q ? { q: this.movieFilters.q } : {}),
          },
        })
      } catch (e) {
        console.error('Create supplement download candidates failed:', e)
      } finally {
        this.candidateImporting = false
      }
    },
  },
}
</script>

<style scoped>
.supplement-page {
  max-width: 1360px;
  margin: 0 auto;
  padding: 28px 40px 48px;
}

.supplement-topbar,
.section-title-row,
.panel-header,
.actor-workspace-hero {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
}

.supplement-topbar {
  margin-bottom: 22px;
}

.eyebrow {
  margin: 0 0 5px;
  color: var(--text-muted);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

h1,
h2,
h3,
p {
  margin: 0;
}

.supplement-topbar h1 {
  font-size: 30px;
  line-height: 1.1;
  color: var(--text-primary);
}

.topbar-actions,
.workspace-actions,
.filter-bar,
.movie-row-actions,
.job-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.supplement-hero {
  display: block;
  padding: 28px;
  margin-bottom: 26px;
  border-radius: var(--radius-sheet);
}

.hero-copy h2 {
  max-width: 620px;
  font-size: 34px;
  line-height: 1.08;
  color: var(--text-primary);
}

.hero-copy p:last-child {
  max-width: 560px;
  margin-top: 12px;
  color: var(--text-secondary);
  font-size: 14px;
  line-height: 1.7;
}

.search-shell {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px;
  border: 1px solid var(--border-light);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.06);
  box-shadow: inset 0 1px 1px rgba(255,255,255,0.04);
}

.actor-filter-bar {
  padding: 10px;
  margin-bottom: 16px;
  border-radius: 999px;
}

.compact-search {
  width: 100%;
  padding: 6px 8px;
  background: rgba(255, 255, 255, 0.035);
}

.actor-filter-bar .btn {
  min-width: 68px;
  justify-content: center;
  white-space: nowrap;
  flex-shrink: 0;
}

.search-shell svg {
  width: 20px;
  height: 20px;
  margin-left: 8px;
  color: var(--text-muted);
  flex-shrink: 0;
}

.search-shell input,
.filter-input {
  min-height: 44px;
  color: var(--text-primary);
  background: rgba(255, 255, 255, 0.045);
  border: 1px solid transparent;
  border-radius: 999px;
  outline: none;
}

.search-shell input {
  width: 100%;
  min-width: 0;
  padding: 0;
  background: transparent;
  border: 0;
  font-size: 15px;
}

.filter-input {
  padding: 0 14px;
  font-size: 13px;
}

.filter-input:focus {
  border-color: var(--border-light);
  background: rgba(255, 255, 255, 0.07);
}

.section-block {
  margin-top: 26px;
}

.section-title-row {
  margin-bottom: 14px;
}

.section-title-row h2,
.panel-header h2 {
  font-size: 20px;
  color: var(--text-primary);
}

.soft-count {
  color: var(--text-muted);
  font-size: 13px;
}

.actor-choice-grid,
.actor-result-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 16px;
}

.actor-choice-card,
.actor-result-card,
.recent-actor-row {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  width: 100%;
  min-height: 230px;
  padding: 20px 16px;
  color: var(--text-primary);
  border: 1px solid var(--border);
  cursor: pointer;
  text-align: center;
  transition: transform var(--motion-standard), border-color var(--motion-standard), background var(--motion-standard), box-shadow var(--motion-standard);
}

.actor-choice-card:hover,
.actor-result-card:hover,
.recent-actor-row:hover {
  transform: translateY(-5px);
  border-color: var(--border-light);
  background: var(--surface-card-hover);
  box-shadow: var(--shadow-floating);
}

.select-orb,
.actor-result-avatar,
.workspace-avatar,
.recent-avatar,
.job-avatar {
  overflow: hidden;
  background: var(--bg-secondary);
  color: var(--text-secondary);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  font-weight: 800;
}

.select-orb,
.actor-result-avatar {
  width: 92px;
  height: 92px;
  border-radius: 50%;
  box-shadow: inset 0 1px 1px rgba(255,255,255,0.12), 0 18px 36px rgba(0, 0, 0, 0.42);
}

.select-orb img,
.actor-result-avatar img,
.workspace-avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  object-position: top center;
}

.actor-card-copy,
.actor-result-main,
.recent-main,
.job-copy,
.movie-row-main {
  display: grid;
  gap: 4px;
  min-width: 0;
}

.actor-card-copy strong,
.actor-result-main strong,
.recent-main strong,
.job-copy strong,
.movie-row-main strong {
  color: var(--text-primary);
  font-size: 14px;
}

.actor-card-copy span,
.actor-card-copy small,
.actor-result-main span,
.recent-main span,
.job-copy span,
.movie-row-main span,
.movie-row-main small {
  color: var(--text-muted);
  font-size: 12px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.actor-card-copy small {
  max-width: 190px;
  margin: 0 auto;
}

.actor-card-action {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 32px;
  padding: 0 16px;
  margin-top: 2px;
  border-radius: 999px;
  background: var(--accent);
  color: var(--bg-primary);
  font-size: 13px;
  font-weight: 700;
}

.actor-result-status {
  margin-left: auto;
  color: var(--text-secondary);
  font-size: 12px;
  white-space: nowrap;
}

.recent-actor-list {
  display: grid;
  gap: 10px;
}

.recent-avatar,
.job-avatar {
  width: 42px;
  height: 42px;
  border-radius: 50%;
}

.recent-time {
  margin-left: auto;
  color: var(--text-muted);
  font-size: 12px;
}

.empty-panel {
  padding: 28px;
  text-align: center;
}

.empty-panel.inner {
  background: rgba(255, 255, 255, 0.035);
  border-radius: var(--radius-card);
}

.empty-panel h3 {
  color: var(--text-primary);
  font-size: 16px;
}

.empty-panel p {
  margin-top: 8px;
  color: var(--text-muted);
  font-size: 13px;
}

.actor-workspace-hero {
  padding: 22px;
  margin-bottom: 14px;
  border-radius: var(--radius-sheet);
}

.workspace-identity {
  display: flex;
  align-items: center;
  gap: 16px;
  min-width: 0;
}

.workspace-avatar {
  width: 76px;
  height: 76px;
  border-radius: 50%;
  font-size: 24px;
}

.workspace-title h2 {
  color: var(--text-primary);
  font-size: 28px;
  line-height: 1.1;
}

.workspace-title p:last-child {
  margin-top: 5px;
  color: var(--text-muted);
  font-size: 13px;
}

.workspace-status {
  display: grid;
  justify-items: end;
  gap: 12px;
}

.workspace-metrics {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  margin: 14px 0;
}

.metric-card {
  padding: 16px;
}

.metric-card span {
  color: var(--text-primary);
  font-size: 26px;
  font-weight: 800;
}

.metric-card p {
  margin-top: 4px;
  color: var(--text-muted);
  font-size: 12px;
}

.segmented-control {
  display: inline-flex;
  gap: 4px;
  padding: 5px;
  margin: 4px 0 16px;
  border-radius: 999px;
}

.segmented-control button {
  min-width: 96px;
  padding: 9px 16px;
  color: var(--text-secondary);
  background: transparent;
  border: 0;
  border-radius: 999px;
  cursor: pointer;
  transition: background var(--motion-fast), color var(--motion-fast);
}

.segmented-control button.active {
  color: var(--bg-primary);
  background: var(--accent);
}

.workspace-panel {
  padding: 18px;
  border-radius: var(--radius-card);
}

.panel-header {
  margin-bottom: 14px;
}

.filter-bar {
  margin-bottom: 14px;
}

.filter-bar.compact {
  margin-bottom: 0;
}

.filter-bar .glass-select {
  min-width: 132px;
}

.ios-list {
  display: grid;
  gap: 8px;
}

.workspace-panel :deep(.ios-list) {
  display: grid;
  gap: 8px;
}

.ios-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 13px 14px;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.035);
  border: 1px solid rgba(255, 255, 255, 0.06);
}

.workspace-panel :deep(.ios-row) {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 13px 14px;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.035);
  border: 1px solid rgba(255, 255, 255, 0.06);
}

.job-main {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
}

.workspace-panel :deep(.job-main) {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
}

.workspace-panel :deep(.job-avatar) {
  width: 42px;
  height: 42px;
  border-radius: 50%;
  overflow: hidden;
  background: var(--bg-secondary);
  color: var(--text-secondary);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  font-weight: 800;
}

.workspace-panel :deep(.job-copy) {
  display: grid;
  gap: 4px;
  min-width: 0;
}

.workspace-panel :deep(.job-copy strong) {
  color: var(--text-primary);
  font-size: 14px;
}

.workspace-panel :deep(.job-copy span) {
  color: var(--text-muted);
  font-size: 12px;
}

.job-copy small {
  color: var(--text-muted);
  font-size: 12px;
  line-height: 1.4;
}

.job-copy small.job-error {
  color: var(--badge-error-text);
}

.workspace-panel :deep(.job-copy small) {
  color: var(--text-muted);
  font-size: 12px;
  line-height: 1.4;
}

.workspace-panel :deep(.job-copy small.job-error) {
  color: var(--badge-error-text);
}

.job-copy small.job-warning {
  color: var(--badge-warning-text);
}

.workspace-panel :deep(.job-copy small.job-warning) {
  color: var(--badge-warning-text);
}

.workspace-panel :deep(.job-actions) {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.movie-row-main {
  flex: 1;
}

.movie-row-main strong {
  font-family: var(--font-mono);
  color: var(--accent);
}

.status-pill {
  display: inline-flex;
  align-items: center;
  min-height: 26px;
  padding: 3px 9px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
  white-space: nowrap;
  background: var(--badge-info-bg);
  border: 1px solid var(--badge-info-border);
  color: var(--badge-info-text);
}

.workspace-panel :deep(.status-pill) {
  display: inline-flex;
  align-items: center;
  min-height: 26px;
  padding: 3px 9px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
  white-space: nowrap;
  background: var(--badge-info-bg);
  border: 1px solid var(--badge-info-border);
  color: var(--badge-info-text);
}

.status-succeeded,
.match-matched {
  background: var(--badge-success-bg);
  border-color: var(--badge-success-border);
  color: var(--badge-success-text);
}

.workspace-panel :deep(.status-succeeded) {
  background: var(--badge-success-bg);
  border-color: var(--badge-success-border);
  color: var(--badge-success-text);
}

.status-running,
.status-queued,
.match-candidate {
  background: var(--badge-warning-bg);
  border-color: var(--badge-warning-border);
  color: var(--badge-warning-text);
}

.workspace-panel :deep(.status-running),
.workspace-panel :deep(.status-queued) {
  background: var(--badge-warning-bg);
  border-color: var(--badge-warning-border);
  color: var(--badge-warning-text);
}

.status-failed {
  background: var(--badge-error-bg);
  border-color: var(--badge-error-border);
  color: var(--badge-error-text);
}

.workspace-panel :deep(.status-failed) {
  background: var(--badge-error-bg);
  border-color: var(--badge-error-border);
  color: var(--badge-error-text);
}

.match-supplement-only,
.status-idle {
  background: var(--badge-info-bg);
  border-color: var(--badge-info-border);
  color: var(--badge-info-text);
}

.match-ignored {
  background: var(--badge-pending-bg);
  border-color: var(--badge-pending-border);
  color: var(--badge-pending-text);
}

.pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  margin-top: 16px;
  color: var(--text-muted);
  font-size: 13px;
}

.empty-inline {
  padding: 20px;
  color: var(--text-muted);
  text-align: center;
}

.loading-wrap {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 140px;
}

.spinner-large {
  width: 28px;
  height: 28px;
  border: 2px solid var(--white-20);
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

.diagnostics-overlay {
  position: fixed;
  inset: 0;
  z-index: 1200;
  display: flex;
  justify-content: center;
  align-items: flex-start;
  padding: 56px 24px;
  background: rgba(0, 0, 0, 0.58);
  overflow: auto;
}

.diagnostics-panel {
  width: min(980px, 100%);
  max-height: calc(100vh - 112px);
  overflow: auto;
  border-radius: var(--radius-sheet);
}

.diagnostics-header {
  position: sticky;
  top: 0;
  z-index: 1;
  display: flex;
  justify-content: space-between;
  gap: 16px;
  padding: 18px 22px;
  background: rgba(0, 0, 0, 0.82);
  border-bottom: 1px solid var(--border);
  backdrop-filter: blur(20px);
}

.diagnostics-header h2 {
  color: var(--text-primary);
  font-size: 20px;
}

.diagnostics-header p {
  margin-top: 4px;
  color: var(--text-muted);
  font-size: 13px;
}

.diagnostics-body {
  display: grid;
  gap: 18px;
  padding: 18px 22px 24px;
}

.diagnostics-section h3 {
  margin-bottom: 10px;
  color: var(--text-primary);
  font-size: 14px;
}

.diagnostics-table {
  display: grid;
  gap: 1px;
  overflow: hidden;
  border: 1px solid var(--border);
  border-radius: 14px;
}

.diagnostics-row {
  display: grid;
  grid-template-columns: 140px 110px minmax(0, 1fr);
  gap: 12px;
  padding: 10px 12px;
  background: rgba(255, 255, 255, 0.04);
  color: var(--text-secondary);
  font-size: 12px;
}

.diagnostics-row-candidates {
  grid-template-columns: minmax(120px, 1fr) 80px 110px 90px;
}

.diagnostics-row-head {
  color: var(--text-primary);
  font-weight: 700;
  background: rgba(255, 255, 255, 0.07);
}

.diagnostics-value {
  overflow-wrap: anywhere;
  color: var(--text-primary);
}

.identity-list,
.detail-source-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.identity-chip,
.detail-source-item {
  padding: 8px 11px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid var(--border);
  color: var(--text-secondary);
  font-size: 12px;
}

.detail-source-item {
  display: grid;
  gap: 4px;
}

.detail-source-item strong {
  color: var(--text-primary);
}

.manual-match-bar {
  display: grid;
  grid-template-columns: minmax(180px, 1fr) auto auto auto;
  gap: 10px;
  margin-bottom: 12px;
}

.btn-xs {
  min-height: 28px;
  padding: 5px 9px;
  font-size: 11px;
}

.btn.danger {
  color: #ff6b87;
  border-color: rgba(255, 107, 135, 0.28);
}

.source-health-toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: flex-end;
}

.provider-smoke-panel {
  display: grid;
  gap: 12px;
  margin-bottom: 14px;
}

.provider-smoke-controls {
  display: grid;
  grid-template-columns: minmax(150px, 220px) minmax(180px, 1fr) auto;
  gap: 10px;
  margin-bottom: 14px;
}

.provider-smoke-controls .glass-select {
  width: 100%;
}

.provider-smoke-summary {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 14px;
  padding: 12px 14px;
  border: 1px solid var(--border);
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.045);
}

.provider-smoke-summary div {
  display: grid;
  gap: 2px;
}

.provider-smoke-summary strong {
  color: var(--text-primary);
  font-size: 18px;
}

.provider-smoke-summary span,
.provider-smoke-summary small {
  color: var(--text-muted);
  font-size: 12px;
}

.provider-smoke-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 12px;
}

.provider-smoke-history {
  display: grid;
  gap: 10px;
  margin-bottom: 14px;
  padding: 12px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.035);
}

.provider-smoke-history-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.provider-smoke-history-head strong {
  color: var(--text-primary);
}

.provider-smoke-run-list {
  display: grid;
  gap: 8px;
}

.provider-smoke-run {
  display: grid;
  grid-template-columns: minmax(140px, 1fr) auto minmax(120px, 1fr);
  gap: 10px;
  align-items: center;
  min-width: 0;
  padding: 9px 10px;
  border: 1px solid var(--border);
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.035);
  color: inherit;
  cursor: pointer;
  text-align: left;
}

.provider-smoke-run span,
.provider-smoke-run small {
  color: var(--text-muted);
  font-size: 12px;
  overflow-wrap: anywhere;
}

.provider-smoke-run strong {
  color: var(--text-primary);
}

.provider-smoke-card {
  display: grid;
  gap: 7px;
  min-width: 0;
  padding: 12px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.045);
}

.provider-smoke-card.failed {
  border-color: rgba(255, 107, 135, 0.3);
}

.provider-smoke-card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.provider-smoke-card strong {
  min-width: 0;
  overflow-wrap: anywhere;
  color: var(--text-primary);
}

.provider-smoke-card p,
.provider-smoke-card small {
  color: var(--text-muted);
  font-size: 12px;
  overflow-wrap: anywhere;
}

.provider-smoke-detail {
  display: grid;
  gap: 3px;
  padding-top: 4px;
}

.provider-smoke-detail span {
  color: var(--text-muted);
  font-size: 11px;
}

.source-health-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 12px;
}

.source-health-card {
  display: grid;
  gap: 10px;
  padding: 14px;
  border: 1px solid var(--border);
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.045);
}

.source-health-card strong {
  display: block;
  color: var(--text-primary);
  font-size: 15px;
}

.source-health-card span,
.source-health-card p,
.source-health-card small {
  color: var(--text-muted);
  font-size: 12px;
}

.source-budget-meter {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 12px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.045);
}

.source-budget-meter strong {
  font-size: 18px;
}

.source-budget-meter span,
.source-budget-meter small {
  color: var(--text-muted);
  font-size: 11px;
}

.source-budget-meter small {
  text-align: right;
}

.source-health-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

.manual-action-list {
  display: grid;
  gap: 8px;
}

.manual-action-item {
  display: grid;
  grid-template-columns: 120px minmax(120px, 1fr) minmax(180px, 2fr);
  gap: 10px;
  padding: 10px 12px;
  border: 1px solid var(--border);
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.045);
}

.manual-action-item strong {
  color: var(--text-primary);
  font-size: 12px;
}

.manual-action-item span,
.manual-action-item small {
  color: var(--text-muted);
  font-size: 12px;
}

.health-healthy {
  color: #6ee7a8;
  background: rgba(52, 199, 89, 0.12);
}

.health-degraded {
  color: #ffd166;
  background: rgba(255, 204, 0, 0.12);
}

.health-cooling_down {
  color: #ff6b87;
  background: rgba(255, 107, 135, 0.12);
}

.health-paused {
  color: var(--text-primary);
  background: rgba(255, 255, 255, 0.14);
}

.health-unknown {
  color: var(--text-muted);
}

@media (max-width: 860px) {
  .supplement-page {
    padding: 20px 16px 36px;
  }

  .supplement-topbar,
  .actor-workspace-hero,
  .panel-header,
  .section-title-row {
    align-items: flex-start;
    flex-direction: column;
  }

  .supplement-hero {
    grid-template-columns: 1fr;
    padding: 20px;
  }

  .hero-copy h2 {
    font-size: 28px;
  }

  .workspace-status {
    justify-items: start;
  }

  .workspace-metrics {
    grid-template-columns: repeat(2, 1fr);
  }

  .segmented-control {
    display: grid;
    width: 100%;
    grid-template-columns: repeat(2, 1fr);
  }

  .segmented-control button {
    min-width: 0;
    padding: 9px 8px;
  }

  .ios-row,
  .movie-row-actions,
  .job-actions {
    align-items: flex-start;
    flex-direction: column;
  }

  .movie-row-actions,
  .job-actions {
    width: 100%;
  }

  .filter-bar,
  .filter-bar .glass-select {
    width: 100%;
  }

  .manual-match-bar,
  .provider-smoke-controls,
  .provider-smoke-run,
  .diagnostics-row-candidates,
  .manual-action-item {
    grid-template-columns: 1fr;
  }
}
</style>
