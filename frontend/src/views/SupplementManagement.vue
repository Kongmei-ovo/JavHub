<template>
  <div class="supplement-page page-shell page-shell--workspace">
    <header class="supplement-topbar">
      <div>
        <h1>补全演员</h1>
      </div>
      <div class="topbar-actions">
        <button v-if="actorContext" class="btn btn-ghost btn-sm" type="button" @click="clearActorContext">更换演员</button>
        <button class="btn btn-ghost btn-sm" type="button" @click="openSourceHealth">来源状态</button>
        <button class="btn btn-ghost btn-sm" type="button" @click="openGlobalQueue">全局队列</button>
      </div>
    </header>
    <ActorPickerView v-if="showActorPicker" v-model:keyword="actorSearchKeyword" :actors="actorChoiceCards" :searched="actorSearched" :searching="actorSearching" :error="actorPickerLoadFailed()" :actor-avatar="actorAvatar" :actor-display-name="actorDisplayName" :actor-choice-status="actorChoiceStatus" @search="searchActorContext" @clear-search="clearActorSearch" @select="selectActorContext" @retry="loadRecentActorJobs" />
    <section v-else-if="actorContext" class="workspace-view">
      <div class="actor-workspace-hero apple-surface">
        <div class="actor-context-card">
          <div class="workspace-identity">
            <div class="workspace-avatar">
              <img
                v-if="actorContextAvatar"
                :src="actorContextAvatar"
                :alt="actorContextName"
                loading="eager"
                decoding="async"
                @error="handleWorkspaceAvatarError"
              />
              <span v-else>{{ actorContextName.slice(0, 1) || '?' }}</span>
            </div>
            <div class="workspace-title">
              <h2>{{ actorContextName }}</h2>
              <p>编号 {{ actorContext.id }}</p>
            </div>
          </div>
        </div>
        <div class="workspace-status">
          <span class="status-pill" :class="`status-${supplementStatus?.last_job?.status || 'idle'}`">{{ statusLabel(supplementStatus?.last_job?.status) }}</span>
          <div class="workspace-actions">
            <button class="btn btn-primary btn-sm" type="button" :disabled="isSupplementRunning" @click="startSupplement">{{ isSupplementRunning ? '补全中...' : '补全作品' }}</button>
            <button class="btn btn-ghost btn-sm" type="button" @click="refreshResolved">刷新版本条目</button>
            <button class="btn btn-ghost btn-sm" type="button" @click="goActorContext">返回演员页</button>
          </div>
        </div>
      </div>
      <div class="workspace-command-strip" :class="`tone-${workspaceRepairTone}`">
        <div class="command-strip-primary">
          <span class="status-pill" :class="`status-${supplementStatus?.last_job?.status || 'idle'}`">
            {{ workspaceRepairSummary }}
          </span>
          <div>
            <strong>修复台状态</strong>
            <p>按字段缺口、匹配候选和任务队列安排下一步动作。</p>
          </div>
        </div>
        <div class="task-state-track" aria-label="补全任务状态">
          <span class="task-state-dot" :class="{ active: isSupplementRunning, failed: isSupplementFailed }"></span>
          <span>{{ statusLabel(supplementStatus?.last_job?.status) }}</span>
          <small v-if="supplementStatus?.last_job?.id">任务 #{{ supplementStatus.last_job.id }}</small>
          <small v-else>暂无运行任务</small>
        </div>
        <div class="workspace-repair-actions" aria-label="修复台下一步动作">
          <button v-for="action in workspaceRepairActions" :key="action.key" type="button" class="workspace-repair-action" :class="workspaceRepairActionClass(action)" @click="runWorkspaceRepairAction(action)">
            <span class="repair-action-value">{{ action.value }}</span>
            <span class="repair-action-label">{{ action.label }}</span>
            <span class="repair-action-hint">{{ action.hint }}</span>
          </button>
        </div>
        <div v-if="workspaceTaskDetails.length" class="task-state-detail-grid" aria-label="补全任务详情">
          <span v-for="detail in workspaceTaskDetails" :key="detail.label" class="task-state-detail">
            <b>{{ detail.label }}</b>
            <em>{{ detail.value }}</em>
          </span>
        </div>
      </div>
      <div class="workspace-metrics">
        <div class="metric-card apple-surface">
          <span>{{ supplementStatus?.supplement_movies ?? '—' }}</span>
          <p>补全来源</p>
        </div>
        <div class="metric-card apple-surface">
          <span>{{ supplementStatus?.matched_r18 ?? '—' }}</span>
          <p>已匹配片库</p>
        </div>
        <div class="metric-card apple-surface">
          <span>{{ supplementStatus?.supplement_only ?? '—' }}</span>
          <p>补全新增</p>
        </div>
        <div class="metric-card apple-surface">
          <span>{{ supplementStatus?.resolved_videos ?? '—' }}</span>
          <p>含版本条目</p>
        </div>
      </div>
      <nav class="segmented-control apple-surface" aria-label="补全工作台视图">
        <button
          v-for="segment in workspaceSegments"
          :key="segment.key"
          type="button"
          :class="{ active: activeWorkspaceSegment === segment.key }"
          @click="setWorkspaceSegment(segment.key)"
        >
          <span class="segment-label">{{ segment.label }}</span>
          <span class="segment-count">{{ workspaceSegmentMeta(segment.key).count }}</span>
          <span class="segment-status">{{ workspaceSegmentMeta(segment.key).status }}</span>
        </button>
      </nav>
      <SupplementMoviesPanel v-if="activeWorkspaceSegment === 'movies'" :movie-filters="movieFilters" :match-filter-options="matchFilterOptions" :quality-filter-options="qualityFilterOptions" :movies-loading="moviesLoading" :supplement-movies="supplementMovies" :movies-total-pages="moviesTotalPages" :movie-page="moviePage" :batch-enriching="batchEnriching" :candidate-importing="candidateImporting" :enriching-movies="enrichingMovies" :apply-image-fallback="applyImageFallback" :movie-cover="movieCover" :movie-categories="movieCategories" :movie-match-class="movieMatchClass" :movie-match-label="movieMatchLabel" @apply-filters="applyMovieFilters" @batch-enrich="batchEnrichMovies" @create-candidates="createDownloadCandidates" @enrich="enrichMovie" @open-sources="openMovieSources" @go-page="goMoviePage" @refresh="loadMovies" @clear-filters="clearMovieFilters" />
      <section v-if="activeWorkspaceSegment === 'jobs'" class="workspace-panel apple-surface">
        <div class="panel-header">
          <div>
            <h2>任务队列</h2>
          </div>
          <div class="filter-bar compact">
            <GlassSelect v-model="jobFilters.status" :options="jobStatusOptions" size="compact" aria-label="任务状态筛选" @change="applyJobFilters" />
            <button class="btn btn-ghost btn-sm" type="button" @click="applyJobFilters">刷新</button>
          </div>
        </div>
        <JobList :jobs="jobs" :loading="jobsLoading" :actor-context="actorContext" :job-label="jobActorLabel" :status-label="statusLabel" @retry="retryJob" @cancel="cancelJob" @actor="applyJobActorContext" @refresh="loadJobs" @start-supplement="startSupplement" />
        <div v-if="jobsTotalPages > 1" class="pagination">
          <button class="btn btn-ghost btn-sm" :disabled="jobPage <= 1" @click="jobPage--; loadJobs()">上一页</button>
          <span>{{ jobPage }} / {{ jobsTotalPages }}</span>
          <button class="btn btn-ghost btn-sm" :disabled="jobPage >= jobsTotalPages" @click="jobPage++; loadJobs()">下一页</button>
        </div>
      </section>
      <section v-if="activeWorkspaceSegment === 'diagnostics'" class="workspace-panel apple-surface">
        <div class="panel-header">
          <div>
            <h2>来源诊断</h2>
          </div>
        </div>
        <div v-if="sourceDiagnosticsOpen" class="diagnostics-inline-state">
          <span class="status-pill" :class="sourceDiagnosticsLoading ? 'status-running' : 'status-succeeded'">
            {{ sourceDiagnosticsLoading ? '读取中' : '已载入' }}
          </span>
          <div>
            <h3>正在查看诊断：{{ diagnosticsMovieTitle }}</h3>
            <p>{{ diagnosticsMovieSubtitle || '字段来源、匹配候选和人工校正记录已在弹窗中展开。' }}</p>
          </div>
        </div>
        <div v-else class="empty-panel inner">
          <h3>从作品字段打开诊断</h3>
          <p>在作品字段列表中点击“诊断”，可查看该影片的字段来源、源身份、详情来源和匹配候选。</p>
        </div>
      </section>
      <SourceHealthPanel v-if="activeWorkspaceSegment === 'sourceHealth'" v-model:provider-smoke-form="providerSmokeForm" v-model:provider-smoke-report="providerSmokeReport" :provider-source-options="providerSourceOptions" :provider-smoke-loading="providerSmokeLoading" :provider-smoke-runs="providerSmokeRuns" :source-health-loading="sourceHealthLoading" :source-health-rows="sourceHealthRows" :source-action-loading="sourceActionLoading" :gfriends-avatar-job="gfriendsAvatarJob" :gfriends-avatar-syncing="gfriendsAvatarSyncing" :format-action-time="formatActionTime" :smoke-run-label="smokeRunLabel" :source-health-label="sourceHealthLabel" :source-budget-label="sourceBudgetLabel" :source-health-detail="sourceHealthDetail" @refresh-health="loadSourceHealth" @run-smoke="runProviderSmoke" @sync-gfriends-avatars="syncGfriendsAvatars" @view-avatar-jobs="viewGfriendsAvatarJobs" @load-smoke-runs="loadProviderSmokeRuns" @pause-source="pauseSource" @resume-source="resumeSource" />
    </section>
    <section v-else-if="showGlobalMovieRepair" class="global-movie-repair-view">
      <SupplementMoviesPanel v-if="activeWorkspaceSegment === 'movies' || showGlobalMovieRepair" :movie-filters="movieFilters" :match-filter-options="matchFilterOptions" :quality-filter-options="qualityFilterOptions" :movies-loading="moviesLoading" :supplement-movies="supplementMovies" :movies-total-pages="moviesTotalPages" :movie-page="moviePage" :batch-enriching="batchEnriching" :candidate-importing="candidateImporting" :enriching-movies="enrichingMovies" :apply-image-fallback="applyImageFallback" :movie-cover="movieCover" :movie-categories="movieCategories" :movie-match-class="movieMatchClass" :movie-match-label="movieMatchLabel" @apply-filters="applyMovieFilters" @batch-enrich="batchEnrichMovies" @create-candidates="createDownloadCandidates" @enrich="enrichMovie" @open-sources="openMovieSources" @go-page="goMoviePage" @refresh="loadMovies" @clear-filters="clearMovieFilters" />
    </section>
    <section v-else-if="showSourceHealthGlobal" class="global-source-health-view">
      <SourceHealthPanel v-model:provider-smoke-form="providerSmokeForm" v-model:provider-smoke-report="providerSmokeReport" :provider-source-options="providerSourceOptions" :provider-smoke-loading="providerSmokeLoading" :provider-smoke-runs="providerSmokeRuns" :source-health-loading="sourceHealthLoading" :source-health-rows="sourceHealthRows" :source-action-loading="sourceActionLoading" :gfriends-avatar-job="gfriendsAvatarJob" :gfriends-avatar-syncing="gfriendsAvatarSyncing" :format-action-time="formatActionTime" :smoke-run-label="smokeRunLabel" :source-health-label="sourceHealthLabel" :source-budget-label="sourceBudgetLabel" :source-health-detail="sourceHealthDetail" @refresh-health="loadSourceHealth" @run-smoke="runProviderSmoke" @sync-gfriends-avatars="syncGfriendsAvatars" @view-avatar-jobs="viewGfriendsAvatarJobs" @load-smoke-runs="loadProviderSmokeRuns" @pause-source="pauseSource" @resume-source="resumeSource" />
    </section>
    <section v-else-if="showGlobalQueue" class="global-queue-view">
      <div class="workspace-panel apple-surface">
        <div class="panel-header">
          <div>
            <h2>全局队列</h2>
            <p class="panel-subtitle">{{ globalQueueContextLabel }}</p>
          </div>
          <div class="filter-bar compact">
            <GlassSelect v-model="jobFilters.status" :options="jobStatusOptions" size="compact" aria-label="全局队列状态筛选" @change="loadJobs" />
            <button class="btn btn-ghost btn-sm" type="button" :disabled="recovering" @click="recoverStale">
              {{ recovering ? '恢复中...' : '恢复卡住任务' }}
            </button>
          </div>
        </div>
        <div v-if="globalQueueContextItems.length" class="queue-filter-summary" aria-label="全局队列筛选上下文">
          <span v-for="item in globalQueueContextItems" :key="item.label" class="queue-filter-chip">
            <b>{{ item.label }}</b>
            <em>{{ item.value }}</em>
          </span>
        </div>
        <JobList :jobs="jobs" :loading="jobsLoading" :actor-context="null" :job-label="jobActorLabel" :status-label="statusLabel" :context-label="globalQueueContextLabel" @retry="retryJob" @cancel="cancelJob" @actor="applyJobActorContext" @refresh="loadJobs" @start-supplement="clearActorContext" />
      </div>
    </section>
    <SupplementSourceDiagnosticsDialog v-if="sourceDiagnosticsOpen" v-model:manual-content-id="manualContentId" :source-diagnostics-loading="sourceDiagnosticsLoading" :source-diagnostics="sourceDiagnostics" :diagnostics-movie-title="diagnosticsMovieTitle" :diagnostics-movie-subtitle="diagnosticsMovieSubtitle" :manual-action-loading="manualActionLoading" :field-label="fieldLabel" :field-value-preview="fieldValuePreview" :manual-action-label="manualActionLabel" :format-action-time="formatActionTime" @close="closeMovieSources" @match="manualMatchMovie" @unmatch="manualUnmatchMovie" @ignore="manualIgnoreMovie" />
  </div>
</template>
<script>
import { defineAsyncComponent } from 'vue'
import api from '../api'
import { ElMessage } from '../utils/message.js'
import { actressImgUrl } from '../utils/imageUrl.js'
import { applyImageFallback } from '../utils/imageFallback.js'
import { displayName } from '../utils/displayLang.js'
import { requestConfirm } from '../utils/confirmDialog'
import GlassSelect from '../components/GlassSelect.vue'
const ActorPickerView = defineAsyncComponent(() => import('../features/supplement/ActorPickerView.vue'))
const JobList = defineAsyncComponent(() => import('../features/supplement/SupplementJobList.vue'))
const SourceHealthPanel = defineAsyncComponent(() => import('../features/supplement/SourceHealthPanel.vue'))
const SupplementMoviesPanel = defineAsyncComponent(() => import('../features/supplement/SupplementMoviesPanel.vue'))
const SupplementSourceDiagnosticsDialog = defineAsyncComponent(() => import('../features/supplement/SupplementSourceDiagnosticsDialog.vue'))
export default {
  name: 'SupplementManagement',
  components: {
    ActorPickerView,
    JobList,
    SourceHealthPanel,
    SupplementMoviesPanel,
    SupplementSourceDiagnosticsDialog,
    GlassSelect,
  },
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
      jobFilters: { status: '', actress_id: '', source: '', error_provider: '' },
      actorContext: null,
      actorContextLoading: false,
      actorSearchKeyword: '',
      actorSearchResults: [],
      actorSearching: false,
      actorSearched: false,
      showGlobalQueue: false,
      showSourceHealthGlobal: false,
      showGlobalMovieRepair: false,
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
      gfriendsAvatarJob: null,
      gfriendsAvatarSyncing: false,
      gfriendsAvatarPolling: null,
      hasInitialized: false,
      wasDeactivated: false,
      lastAppliedRouteKey: '',
      statsLoadedAt: 0,
      recentActorsLoadedAt: 0,
    }
  },
  computed: {
    showActorPicker() {
      return !this.actorContext && !this.showGlobalQueue && !this.showSourceHealthGlobal && !this.showGlobalMovieRepair
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
    actorContextAvatar() { return this.actorAvatar(this.actorContext) },
    isSupplementRunning() {
      const status = this.supplementStatus?.last_job?.status
      return status === 'running' || status === 'queued'
    },
    isSupplementFailed() { return this.supplementStatus?.last_job?.status === 'failed' },
    workspaceRepairTone() {
      if (this.isSupplementFailed) return 'failed'
      if (this.isSupplementRunning) return 'running'
      if ((this.supplementStatus?.supplement_only || 0) > 0) return 'candidate'
      if ((this.supplementStatus?.supplement_movies || 0) > (this.supplementStatus?.resolved_videos || 0)) return 'repair'
      return 'stable'
    },
    workspaceRepairSummary() {
      if (this.isSupplementFailed) return '任务失败待处理'
      if (this.isSupplementRunning) return '任务进行中'
      if ((this.supplementStatus?.supplement_only || 0) > 0) return '等待匹配确认'
      if ((this.supplementStatus?.supplement_movies || 0) > (this.supplementStatus?.resolved_videos || 0)) return '需要补字段'
      return '字段完整度稳定'
    },
    workspaceTaskDetails() {
      const job = this.supplementStatus?.last_job
      if (!job) return []
      const details = []
      if (job.last_error) details.push({ label: '失败原因', value: this.fieldValuePreview(job.last_error) })
      if (job.attempt_count) details.push({ label: '尝试次数', value: `${job.attempt_count}/3` })
      if (job.next_run_at && ['queued', 'running'].includes(job.status)) {
        details.push({ label: '下次执行', value: this.formatActionTime(job.next_run_at) })
      }
      if (this.isSupplementFailed) {
        details.push({ label: '下一步动作', value: '查看来源状态' })
      } else if (this.isSupplementRunning) {
        details.push({ label: '下一步动作', value: '等待任务结束' })
      } else if ((this.supplementStatus?.supplement_only || 0) > 0) {
        details.push({ label: '下一步动作', value: '确认匹配候选' })
      }
      return details
    },
    workspaceMovieFieldGapCount() {
      return this.supplementMovies.reduce((total, movie) => {
        return total + this.movieFieldChips(movie).filter(chip => !chip.value).length
      }, 0)
    },
    workspacePendingCandidateCount() {
      return this.supplementMovies.filter(movie => this.movieMatchClass(movie) === 'candidate').length
    },
    workspaceDetailTargetCount() {
      return this.supplementMovies.filter(movie => {
        return Boolean(movie?.source_movie_id) && this.movieFieldChips(movie).some(chip => !chip.value)
      }).length
    },
    workspaceRepairActions() {
      const job = this.supplementStatus?.last_job
      const actions = []
      if (this.isSupplementFailed) {
        actions.push({
          key: 'failed-source',
          target: 'sourceHealth',
          tone: 'failed',
          primary: true,
          value: '失败来源',
          label: '查看来源状态',
          hint: job?.last_error ? this.fieldValuePreview(job.last_error) : '查看来源冷却和降级状态',
        })
      }
      if (this.isSupplementRunning || this.isSupplementFailed || job?.id) {
        actions.push({
          key: 'task-queue',
          target: 'jobs',
          tone: this.isSupplementFailed ? 'failed' : (this.isSupplementRunning ? 'running' : 'stable'),
          primary: !actions.length,
          value: job?.id ? `#${job.id}` : '任务',
          label: '查看任务队列',
          hint: job?.attempt_count ? `尝试次数 ${job.attempt_count}/3` : '查看补全和详情任务',
        })
      }
      if (this.workspaceMovieFieldGapCount > 0 || this.workspaceDetailTargetCount > 0) {
        actions.push({
          key: 'field-gaps',
          target: 'movies',
          tone: 'ready',
          primary: !actions.length,
          value: this.workspaceMovieFieldGapCount,
          label: '字段缺口',
          hint: `修复作品字段 · ${this.workspaceDetailTargetCount} 部可补详情`,
        })
      }
      if (this.workspacePendingCandidateCount > 0 || this.sourceDiagnosticsOpen) {
        actions.push({
          key: 'diagnostics',
          target: 'diagnostics',
          tone: 'ready',
          primary: !actions.length,
          value: this.workspacePendingCandidateCount || '诊断',
          label: this.workspacePendingCandidateCount > 0 ? '候选确认' : '诊断入口',
          hint: '打开来源诊断',
        })
      }
      if (!actions.length) {
        actions.push({
          key: 'stable-source-health',
          target: 'sourceHealth',
          tone: 'stable',
          primary: true,
          value: '巡检',
          label: '诊断入口',
          hint: '查看来源状态',
        })
      }
      return actions.slice(0, 4)
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
    globalQueueSourceLabel() {
      const source = String(this.jobFilters.source || '').trim()
      if (!source) return '全部来源'
      if (this.jobFilters.source === 'all' && this.jobFilters.error_provider) return `含 ${this.jobFilters.error_provider} 的复合失败`
      if (this.jobFilters.source === 'all') return '包含多个来源的复合失败'
      if (source === 'gfriends') return 'gfriends 头像来源'
      return `${source} 来源`
    },
    globalQueueStatusLabel() {
      return this.jobFilters.status ? this.statusLabel(this.jobFilters.status) : '全部状态'
    },
    globalQueueContextLabel() {
      return `${this.globalQueueStatusLabel} · ${this.globalQueueSourceLabel}`
    },
    globalQueueContextItems() {
      return [
        { label: '状态', value: this.globalQueueStatusLabel },
        { label: '来源', value: this.globalQueueSourceLabel },
        ...(this.jobFilters.error_provider
          ? [{ label: '定位', value: this.jobFilters.error_provider, provider: this.jobFilters.error_provider }]
          : []),
        { label: '结果', value: this.jobsLoading ? '读取中' : `${this.jobsTotalCount || 0} 个任务` },
      ]
    },
    isGfriendsAvatarJobRunning() {
      const status = this.gfriendsAvatarJob?.status
      return status === 'queued' || status === 'running'
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
    if (!this.$route.query.actress_id && !['jobs', 'sources'].includes(this.$route.query.tab)) {
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
    this._stopGfriendsAvatarPolling()
  },
  beforeUnmount() {
    this._stopSupplementPolling()
    this._stopGfriendsAvatarPolling()
  },
  methods: {
    handleWorkspaceAvatarError(e) {
      applyImageFallback(e, { label: this.actorContextName?.slice(0, 1) || '?' })
    },
    supplementQueryKey(query = this.$route.query) {
      const field = (key) => {
        const value = query[key]
        if (Array.isArray(value)) return value[0] ? String(value[0]).trim() : ''
        return value == null ? '' : String(value).trim()
      }
      return JSON.stringify({
        tab: field('tab'),
        actress_id: field('actress_id'),
        source: field('source'),
        status: field('status'),
        error_provider: field('error_provider'),
        q: field('q'),
        quality: field('quality'),
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
      const source = typeof this.$route.query.source === 'string' ? this.$route.query.source.trim() : ''
      const status = typeof this.$route.query.status === 'string' ? this.$route.query.status.trim() : ''
      const errorProvider = typeof this.$route.query.error_provider === 'string' ? this.$route.query.error_provider.trim() : ''
      const q = typeof this.$route.query.q === 'string' ? this.$route.query.q.trim() : ''
      const quality = typeof this.$route.query.quality === 'string' ? this.$route.query.quality.trim() : ''
      this.jobFilters.source = source
      this.jobFilters.status = status
      this.jobFilters.error_provider = errorProvider
      if (this.movieFilters.q !== q) {
        this.movieFilters.q = q
        this.moviePage = 1
      }
      if (this.movieFilters.quality !== quality) {
        this.movieFilters.quality = quality
        this.moviePage = 1
      }
      if (actressId) {
        this.showGlobalQueue = false
        this.showSourceHealthGlobal = false
        this.showGlobalMovieRepair = false
        this.activeWorkspaceSegment = this.segmentFromTab(tab)
        await this.applyActorContext(actressId)
        await this.loadWorkspaceSegment(this.activeWorkspaceSegment)
        return
      }
      this.actorContext = null
      this.jobFilters.actress_id = ''
      this.movieFilters.actress_id = ''
      if (tab === 'jobs') {
        this.showSourceHealthGlobal = false
        this.showGlobalMovieRepair = false
        this.showGlobalQueue = true
        await this.loadJobs()
      } else if (tab === 'sources') {
        this.showGlobalQueue = false
        this.showGlobalMovieRepair = false
        this.showSourceHealthGlobal = true
        await this.loadSourceHealth()
      } else if (tab === 'movies' && quality) {
        this.showGlobalQueue = false
        this.showSourceHealthGlobal = false
        this.showGlobalMovieRepair = true
        this.activeWorkspaceSegment = 'movies'
        await this.loadMovies()
      } else {
        this.showGlobalQueue = false
        this.showSourceHealthGlobal = false
        this.showGlobalMovieRepair = false
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
      if (this.movieFilters.quality) query.quality = this.movieFilters.quality
      const routeChanged = await this.replaceSupplementRoute(query)
      if (!routeChanged) await this.loadWorkspaceSegment(segment)
    },
    workspaceSegmentMeta(key) {
      if (key === 'movies') {
        return { count: this.moviesTotalCount || this.supplementStatus?.supplement_movies || 0, status: this.movieFilters.quality || this.movieFilters.q ? '已筛选' : '字段池' }
      }
      if (key === 'jobs') {
        const runningJobs = this.jobs.filter(job => ['queued', 'running'].includes(job.status))
        const lastJobStatus = this.supplementStatus?.last_job?.status
        const lastJobCount = this.supplementStatus?.last_job?.id ? 1 : 0
        if (lastJobStatus === 'failed') {
          return { count: this.jobsTotalCount || this.jobs.length || lastJobCount, status: '任务失败' }
        }
        if (['queued', 'running'].includes(lastJobStatus) || runningJobs.length) {
          return { count: this.jobsTotalCount || this.jobs.length || lastJobCount, status: '任务进行中' }
        }
        return { count: this.jobsTotalCount || this.jobs.length || lastJobCount, status: '可调度' }
      }
      if (key === 'diagnostics') {
        return { count: this.sourceDiagnostics?.chosen_fields?.length || 0, status: this.sourceDiagnosticsOpen ? '检查中' : '待选择' }
      }
      if (key === 'sourceHealth') {
        return { count: this.sourceHealthRows.length, status: this.sourceHealthLoading ? '刷新中' : '来源池' }
      }
      return { count: 0, status: '' }
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
    recentActorFromJob(job) {
      const id = job.local_actress_id
      return {
        id,
        name: job.source_actor_name || `演员 ${id}`,
        name_kanji: job.source_actor_name || '',
        _recentJob: job,
      }
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
    actorPickerLoadFailed() {
      return this.actorPickerError === 'load_failed'
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
      this.jobFilters.source = ''
      this.jobFilters.error_provider = ''
      this.movieFilters.actress_id = ''
      this.movieFilters.q = ''
      this.actorSearchKeyword = ''
      this.actorSearchResults = []
      this.actorSearched = false
      this.showGlobalQueue = false
      this.showSourceHealthGlobal = false
      this.showGlobalMovieRepair = false
      await this.replaceSupplementRoute()
      this.loadRecentActorJobs({ silent: true })
    },
    async openGlobalQueue() {
      this.showGlobalQueue = true
      this.showSourceHealthGlobal = false
      this.showGlobalMovieRepair = false
      this.actorContext = null
      this.jobFilters.actress_id = ''
      this.jobFilters.source = ''
      this.jobFilters.status = ''
      this.jobFilters.error_provider = ''
      this.movieFilters.actress_id = ''
      this.movieFilters.q = ''
      const routeChanged = await this.replaceSupplementRoute({ tab: 'jobs' })
      if (!routeChanged) await this.loadJobs()
    },
    async openSourceHealth() {
      this.showGlobalQueue = false
      this.showSourceHealthGlobal = true
      this.showGlobalMovieRepair = false
      this.actorContext = null
      this.jobFilters.actress_id = ''
      this.jobFilters.source = ''
      this.jobFilters.error_provider = ''
      this.movieFilters.actress_id = ''
      this.movieFilters.q = ''
      const routeChanged = await this.replaceSupplementRoute({ tab: 'sources' })
      if (!routeChanged) await this.loadSourceHealth()
    },
    async viewGfriendsAvatarJobs() {
      this.showSourceHealthGlobal = false
      this.showGlobalQueue = true
      this.showGlobalMovieRepair = false
      this.actorContext = null
      this.jobFilters.actress_id = ''
      this.jobFilters.status = ''
      this.jobFilters.source = 'gfriends'
      this.jobFilters.error_provider = ''
      this.movieFilters.actress_id = ''
      this.movieFilters.q = ''
      const routeChanged = await this.replaceSupplementRoute({ tab: 'jobs', source: 'gfriends' })
      if (!routeChanged) await this.loadJobs()
    },
    goActorContext() {
      if (!this.actorContext) return
      const name = this.actorContext.name_kanji || this.actorContext.name_romaji || this.actorContext.name || ''
      this.$router.push({ path: `/actor/${encodeURIComponent(name || this.actorContext.id)}`, query: { name, actress_id: this.actorContext.id } })
    },
    async loadSupplementStatus({ poll = true } = {}) {
      if (!this.actorContext?.id) return
      const normalized = String(this.actorContext.id)
      try {
        const resp = await api.getSupplementActressStatus(normalized)
        this.supplementStatus = resp.data || resp
        if (poll && this.isSupplementRunning) this._startSupplementPolling()
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
        ElMessage.success('已刷新版本条目')
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
        if (!this.isSupplementRunning) {
          this._stopSupplementPolling()
          await this.refreshSupplementWorkspaceAfterPolling()
        }
      }, 4000)
    },
    _stopSupplementPolling() {
      if (this.supplementPolling) {
        clearInterval(this.supplementPolling)
        this.supplementPolling = null
      }
    },
    async refreshSupplementWorkspaceAfterPolling() {
      await Promise.all([
        this.loadJobs({ silent: true }),
        this.loadMovies({ silent: true }),
        this.loadSupplementStatus({ poll: false }),
      ])
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
    movieCover(movie) {
      return movie?.cover_thumb_url || movie?.cover_url || ''
    },
    movieCategories(movie) {
      const raw = movie?.category_names
      if (!raw) return ''
      let list = raw
      if (typeof raw === 'string') {
        try { list = JSON.parse(raw) } catch { return raw }
      }
      if (!Array.isArray(list)) return String(raw)
      return list.slice(0, 3).join(' · ')
    },
    movieFieldChips(movie) {
      return [
        { key: 'cover', label: '封面', value: this.movieCover(movie) ? '已取' : '' },
        { key: 'runtime', label: '时长', value: movie?.runtime_mins ? `${movie.runtime_mins}m` : '' },
        { key: 'maker', label: '厂商', value: movie?.maker_name || '' },
        { key: 'label', label: '厂牌', value: movie?.label_name || '' },
        { key: 'series', label: '系列', value: movie?.series_name || '' },
        { key: 'category', label: '分类', value: this.movieCategories(movie) || '' },
      ]
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
        summary: '简介',
        score: '评分',
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
      if (req.source_movie_id) return `${req.source || '来源'} · ${req.source_movie_id}`
      if (req.source) return `${req.source} 默认样本`
      if (req.samples?.length) return `${req.samples.length} 个样本`
      return '默认样本'
    },
    manualActionLabel(action) {
      const map = { match: '确认匹配', ignore: '忽略', unmatch: '解除匹配' }
      return map[action] || action || '人工操作'
    },
    workspaceRepairActionClass(action) {
      return {
        primary: action.primary,
        failed: action.tone === 'failed',
        ready: action.tone === 'ready',
        running: action.tone === 'running',
      }
    },
    async runWorkspaceRepairAction(action) {
      if (!action) return
      if (action.target === 'sourceHealth') {
        await this.setWorkspaceSegment('sourceHealth')
        return
      }
      if (action.target === 'jobs') {
        await this.setWorkspaceSegment('jobs')
        return
      }
      if (action.target === 'movies') {
        await this.setWorkspaceSegment('movies')
        return
      }
      if (action.target === 'diagnostics') {
        await this.setWorkspaceSegment('diagnostics')
      }
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
        await this.loadGfriendsAvatarJob({ silent: true })
      } catch (e) {
        console.error('Load source health failed:', e)
      } finally {
        if (showLoading) this.sourceHealthLoading = false
      }
    },
    async loadGfriendsAvatarJob({ silent = false } = {}) {
      try {
        const resp = await api.listSupplementJobs({ page: 1, page_size: 1, source: 'gfriends' })
        const data = resp.data || resp
        this.gfriendsAvatarJob = (data.data || [])[0] || null
        if (this.gfriendsAvatarJob && this.isGfriendsAvatarJobRunning && !this.gfriendsAvatarPolling) {
          this._startGfriendsAvatarPolling()
        } else if (!silent) {
          this._stopGfriendsAvatarPolling()
        }
      } catch (e) {
        console.error('Load gfriends avatar job failed:', e)
      }
    },
    async syncGfriendsAvatars() {
      if (this.gfriendsAvatarSyncing || this.isGfriendsAvatarJobRunning) return
      const confirmed = await requestConfirm({
        title: '同步演员头像？',
        message: '会拉取 gfriends Filetree、匹配本地演员、写入头像覆盖，并校验图片可访问性。',
        details: '这是全局维护任务，不绑定具体演员。已有运行中的头像同步任务时会复用该任务。',
        confirmText: '开始同步',
      })
      if (!confirmed) return
      this.gfriendsAvatarSyncing = true
      try {
        const resp = await api.startGfriendsAvatarSyncJob()
        const data = resp.data || resp
        ElMessage.success(data.existing ? '已有头像同步任务，已切换到任务状态' : '已加入头像同步队列')
        await this.loadGfriendsAvatarJob()
        this._startGfriendsAvatarPolling()
      } catch (e) {
        console.error('Start gfriends avatar sync failed:', e)
      } finally {
        this.gfriendsAvatarSyncing = false
      }
    },
    _startGfriendsAvatarPolling() {
      this._stopGfriendsAvatarPolling()
      this.gfriendsAvatarPolling = setInterval(async () => {
        await this.loadGfriendsAvatarJob({ silent: true })
        if (!this.isGfriendsAvatarJobRunning) {
          this._stopGfriendsAvatarPolling()
          await this.loadSourceHealth({ silent: true })
        }
      }, 4000)
    },
    _stopGfriendsAvatarPolling() {
      if (this.gfriendsAvatarPolling) {
        clearInterval(this.gfriendsAvatarPolling)
        this.gfriendsAvatarPolling = null
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
        this.recentActors = this.recentActorJobs.map(this.recentActorFromJob)
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
    async loadJobs({ silent = false } = {}) {
      const showLoading = !silent
      if (showLoading) this.jobsLoading = true
      try {
        const params = { page: this.jobPage, page_size: 20 }
        if (this.jobFilters.status) params.status = this.jobFilters.status
        if (this.jobFilters.actress_id) params.actress_id = this.jobFilters.actress_id
        if (this.jobFilters.source) params.source = this.jobFilters.source
        if (this.jobFilters.error_provider) params.error_provider = this.jobFilters.error_provider
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
      const routeChanged = await this.replaceSupplementRoute({
        tab: 'jobs',
        status: this.jobFilters.status,
        source: this.jobFilters.source,
        error_provider: this.jobFilters.error_provider,
        actress_id: this.jobFilters.actress_id,
      })
      if (!routeChanged) await this.loadJobs()
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
        const params = this.buildMovieFilterParams({ page: this.moviePage, page_size: 20 })
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
      const routeChanged = await this.replaceSupplementRoute({
        tab: this.tabFromSegment(this.activeWorkspaceSegment),
        actress_id: this.actorContext?.id,
        q: this.movieFilters.q,
        quality: this.movieFilters.quality,
      })
      if (!routeChanged) await this.loadMovies()
    },
    async clearMovieFilters() {
      this.movieFilters.matched = null
      this.movieFilters.quality = ''
      this.movieFilters.q = ''
      this.moviePage = 1
      await this.applyMovieFilters()
    },
    async goMoviePage(page) {
      this.moviePage = page
      await this.loadMovies()
    },
    buildMovieFilterParams(baseParams = {}) {
      const params = { ...baseParams }
      if (this.movieFilters.matched !== null) params.matched = this.movieFilters.matched
      if (this.movieFilters.actress_id) params.actress_id = this.movieFilters.actress_id
      if (this.movieFilters.q) params.q = this.movieFilters.q
      if (this.movieFilters.quality === 'missing_cover') params.missing_cover = true
      if (this.movieFilters.quality === 'missing_runtime') params.missing_runtime = true
      if (this.movieFilters.quality === 'missing_maker') params.missing_maker = true
      if (this.movieFilters.quality === 'missing_categories') params.missing_categories = true
      if (this.movieFilters.quality === 'low_completeness') params.max_completeness = 2
      return params
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
        const params = this.buildMovieFilterParams({ source: 'all', limit: 20 })
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
        const params = this.buildMovieFilterParams()
        if (this.actorContext?.id) params.actress_id = this.actorContext.id
        if (this.actorContextName) params.actress_name = this.actorContextName
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
<style scoped src="../features/supplement/supplementManagement.css"></style>
