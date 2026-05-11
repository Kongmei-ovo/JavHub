<template>
  <div class="supplement-page apple-reveal">
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

    <section v-if="showActorPicker" class="actor-picker-view">
      <div class="supplement-hero apple-surface">
        <div class="hero-copy">
          <p class="eyebrow">Actor First</p>
          <h2>选择一位演员开始补全</h2>
          <p>演员卡片是主入口。搜索只是辅助筛选，选中后进入该演员的作品字段、任务队列和来源诊断工作台。</p>
        </div>
      </div>

      <section class="section-block">
        <div class="section-title-row">
          <div>
            <p class="eyebrow">{{ actorSearched ? 'Filtered' : 'Recent' }}</p>
            <h2>选择补全演员</h2>
          </div>
          <span class="soft-count">{{ actorChoiceCards.length }} 位演员</span>
        </div>

        <div class="actor-picker-card">
          <div class="actor-filter-bar apple-surface">
            <div class="search-shell compact-search">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true">
                <circle cx="11" cy="11" r="7"></circle>
                <path d="M16.5 16.5 21 21"></path>
              </svg>
              <input
                v-model="actorSearchKeyword"
                placeholder="输入演员名筛选卡片"
                @keyup.enter="searchActorContext"
              />
              <button
                class="btn btn-ghost btn-sm"
                type="button"
                :disabled="actorSearching || !actorSearchKeyword.trim()"
                @click="searchActorContext"
              >{{ actorSearching ? '筛选中...' : '筛选' }}</button>
              <button
                v-if="actorSearched"
                class="btn btn-ghost btn-sm"
                type="button"
                @click="clearActorSearch"
              >清除</button>
            </div>
          </div>
        </div>

        <div v-if="actorChoiceCards.length" class="actor-choice-grid">
          <button
            v-for="actor in actorChoiceCards"
            :key="actor.id"
            class="actor-choice-card apple-surface"
            type="button"
            @click="selectActorContext(actor)"
          >
            <span class="select-orb" aria-hidden="true">
              <img
                v-if="actorAvatar(actor)"
                :src="actorAvatar(actor)"
                :alt="actorDisplayName(actor)"
                @error="$event.target.style.display = 'none'"
              />
              <span v-else>{{ actorDisplayName(actor).slice(0, 1) || '?' }}</span>
            </span>
            <span class="actor-card-copy">
              <strong>{{ actorDisplayName(actor) }}</strong>
              <span>ID {{ actor.id }}</span>
              <small>{{ actorChoiceStatus(actor) }}</small>
            </span>
            <span class="actor-card-action">选择</span>
          </button>
        </div>
        <div v-else-if="actorSearched && !actorSearching" class="empty-panel apple-surface">
          <h3>没有匹配演员</h3>
          <p>换一个日文名、罗马音或关键词再试。</p>
        </div>
        <div v-else class="empty-panel apple-surface">
          <h3>暂无可选演员</h3>
          <p>搜索演员后会出现可选择的演员卡片。</p>
        </div>
      </section>
    </section>

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
        </div>
        <div class="filter-bar">
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
            v-model="movieFilters.q"
            placeholder="搜索番号/标题"
            class="filter-input"
            @keyup.enter="loadMovies"
          />
          <button class="btn btn-ghost btn-sm" type="button" @click="loadMovies">筛选</button>
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
            <select v-model="jobFilters.status" @change="loadJobs" class="filter-select">
              <option value="">全部状态</option>
              <option value="queued">排队中</option>
              <option value="running">运行中</option>
              <option value="succeeded">已完成</option>
              <option value="failed">失败</option>
            </select>
            <button class="btn btn-ghost btn-sm" type="button" @click="loadJobs">刷新</button>
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
    </section>

    <section v-else-if="showGlobalQueue" class="global-queue-view">
      <div class="workspace-panel apple-surface">
        <div class="panel-header">
          <div>
            <p class="eyebrow">Global Queue</p>
            <h2>全局队列</h2>
          </div>
          <div class="filter-bar compact">
            <select v-model="jobFilters.status" @change="loadJobs" class="filter-select">
              <option value="">全部状态</option>
              <option value="queued">排队中</option>
              <option value="running">运行中</option>
              <option value="succeeded">已完成</option>
              <option value="failed">失败</option>
            </select>
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
            <div v-if="sourceDiagnostics.match_candidates?.length" class="diagnostics-table">
              <div class="diagnostics-row diagnostics-row-head">
                <span>content_id</span>
                <span>分数</span>
                <span>状态</span>
              </div>
              <div v-for="candidate in sourceDiagnostics.match_candidates" :key="candidate.candidate_content_id" class="diagnostics-row">
                <span>{{ candidate.candidate_content_id }}</span>
                <span>{{ candidate.score }}</span>
                <span>{{ candidate.status }}</span>
              </div>
            </div>
            <div v-else class="empty-inline">暂无匹配候选</div>
          </section>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { h } from 'vue'
import api from '../api'
import { ElMessage } from 'element-plus'
import { actressImgUrl } from '../utils/imageUrl.js'
import { displayName } from '../utils/displayLang.js'

const JobList = {
  name: 'JobList',
  props: {
    jobs: { type: Array, default: () => [] },
    loading: { type: Boolean, default: false },
    actorContext: { type: Object, default: null },
    jobLabel: { type: Function, required: true },
    statusLabel: { type: Function, required: true },
  },
  emits: ['retry', 'cancel', 'actor'],
  render() {
    if (this.loading) {
      return h('div', { class: 'loading-wrap' }, [h('div', { class: 'spinner-large' })])
    }
    if (!this.jobs.length) {
      return h('div', { class: 'empty-inline' }, '暂无任务')
    }
    return h('div', { class: 'ios-list job-list' }, this.jobs.map(job => h('article', { class: 'ios-row job-row', key: job.id }, [
      h('div', { class: 'job-main' }, [
        h('div', { class: 'job-avatar' }, job.source_actor_name?.slice(0, 1) || String(job.local_actress_id || '?').slice(0, 1)),
        h('div', { class: 'job-copy' }, [
          h('strong', this.jobLabel(job)),
          h('span', `#${job.id} · ${job.created_at ? new Date(job.created_at).toLocaleString() : ''}`),
          job.last_error ? h('small', { class: job.status === 'failed' ? 'job-error' : 'job-warning' }, job.last_error) : null,
        ]),
      ]),
      h('div', { class: 'job-actions' }, [
        h('span', { class: ['status-pill', `status-${job.status}`] }, this.statusLabel(job.status)),
        job.local_actress_id && !this.actorContext ? h('button', { class: 'btn btn-ghost btn-sm', type: 'button', onClick: () => this.$emit('actor', job) }, '查看演员') : null,
        job.status === 'failed' ? h('button', { class: 'btn btn-primary btn-sm', type: 'button', onClick: () => this.$emit('retry', job.id) }, '重试') : null,
        job.status === 'queued' || job.status === 'running' ? h('button', { class: 'btn btn-ghost btn-sm', type: 'button', onClick: () => this.$emit('cancel', job.id) }, '取消') : null,
      ]),
    ])))
  },
}

export default {
  name: 'SupplementManagement',
  components: { JobList },
  data() {
    return {
      stats: null,
      statsLoading: false,
      jobs: [],
      jobsLoading: false,
      recentJobs: [],
      recentActors: [],
      recentJobsLoading: false,
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
      ],
      supplementStatus: null,
      supplementPolling: null,
      recovering: false,
      supplementMovies: [],
      moviesLoading: false,
      enrichingMovies: {},
      batchEnriching: false,
      moviePage: 1,
      moviesTotalCount: 0,
      moviesTotalPages: 1,
      movieFilters: { matched: false, quality: '', actress_id: '', q: '' },
      sourceDiagnosticsOpen: false,
      sourceDiagnosticsLoading: false,
      sourceDiagnostics: null,
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
  },
  watch: {
    '$route.query': {
      handler() {
        this.applyRouteState()
      },
      deep: true,
    },
  },
  mounted() {
    this.applyRouteState()
    this.loadStats()
    this.loadRecentActorJobs()
  },
  beforeUnmount() {
    this._stopSupplementPolling()
  },
  methods: {
    async applyRouteState() {
      const tab = this.$route.query.tab
      const actressId = this.$route.query.actress_id
      if (actressId) {
        this.showGlobalQueue = false
        this.activeWorkspaceSegment = this.segmentFromTab(tab)
        await this.applyActorContext(actressId)
        if (this.activeWorkspaceSegment === 'jobs') await this.loadJobs()
        if (this.activeWorkspaceSegment === 'movies') await this.loadMovies()
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
      return 'movies'
    },
    tabFromSegment(segment) {
      if (segment === 'jobs') return 'jobs'
      if (segment === 'diagnostics') return 'stats'
      return 'movies'
    },
    setWorkspaceSegment(segment) {
      this.activeWorkspaceSegment = segment
      this.$router.replace({ path: '/supplement', query: { tab: this.tabFromSegment(segment), actress_id: this.actorContext?.id } })
      if (segment === 'jobs') this.loadJobs()
      if (segment === 'movies') this.loadMovies()
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
      await this.$router.replace({ path: '/supplement', query: { tab: this.tabFromSegment(this.activeWorkspaceSegment), actress_id: actor.id } })
      await this.applyActorContext(actor.id)
      await this.loadMovies()
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
      await this.$router.replace({ path: '/supplement', query: { tab: this.tabFromSegment(nextSegment), actress_id: job.local_actress_id } })
      await this.applyActorContext(job.local_actress_id)
      if (nextSegment === 'jobs') await this.loadJobs()
      if (nextSegment === 'movies') await this.loadMovies()
    },
    clearActorContext() {
      this._stopSupplementPolling()
      this.actorContext = null
      this.supplementStatus = null
      this.jobFilters.actress_id = ''
      this.movieFilters.actress_id = ''
      this.actorSearchKeyword = ''
      this.actorSearchResults = []
      this.actorSearched = false
      this.showGlobalQueue = false
      this.$router.replace({ path: '/supplement' })
      this.loadRecentActorJobs()
    },
    openGlobalQueue() {
      this.showGlobalQueue = true
      this.actorContext = null
      this.jobFilters.actress_id = ''
      this.movieFilters.actress_id = ''
      this.$router.replace({ path: '/supplement', query: { tab: 'jobs' } })
      this.loadJobs()
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
      } catch (e) {
        console.error('Load movie sources failed:', e)
      } finally {
        this.sourceDiagnosticsLoading = false
      }
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
    async loadRecentActorJobs() {
      this.recentJobsLoading = true
      try {
        const resp = await api.listSupplementJobs({ page: 1, page_size: 16 })
        const data = resp.data || resp
        this.recentJobs = data.data || []
        await this.loadRecentActors()
      } catch (e) {
        console.error('Load recent supplement jobs failed:', e)
      } finally {
        this.recentJobsLoading = false
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
        await api.recoverStaleSupplementJobs(30)
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
.filter-input,
.filter-select {
  min-height: 40px;
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

.filter-input,
.filter-select {
  padding: 0 14px;
  font-size: 13px;
}

.filter-input:focus,
.filter-select:focus {
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
    grid-template-columns: repeat(3, 1fr);
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
}
</style>
