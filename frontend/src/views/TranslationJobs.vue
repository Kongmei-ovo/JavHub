<template>
  <div class="translation-page page-shell page-shell--workspace">
    <header class="translation-header">
      <div>
        <h1>翻译作业</h1>
      </div>
      <div class="header-actions">
        <button class="btn btn-ghost" type="button" :disabled="loading || statsLoading" @click="refreshOverview">
          {{ loading || statsLoading ? '刷新中...' : '刷新' }}
        </button>
        <button class="btn btn-primary" type="button" @click="setActiveSegment('create')">创建作业</button>
      </div>
    </header>

    <nav class="segmented-control apple-surface" aria-label="翻译作业视图">
      <button
        v-for="segment in segments"
        :key="segment.key"
        type="button"
        :class="{ active: activeSegment === segment.key }"
        @click="setActiveSegment(segment.key)"
      >{{ segment.label }}</button>
    </nav>

    <section v-if="activeSegment === 'overview'" class="workspace-panel apple-surface">
      <div class="panel-header">
        <div>
          <h2>总览</h2>
        </div>
      </div>

      <div class="overview-dashboard">
        <section class="coverage-hero" :class="{ loading: overviewLoading }" aria-label="标题覆盖">
          <template v-if="overviewLoading || overviewNeedsRefresh">
            <div class="coverage-donut skeleton-donut" aria-hidden="true"></div>
            <div class="coverage-hero-copy">
              <span class="overview-kicker">标题覆盖</span>
              <div class="coverage-placeholder-title">{{ overviewLoading ? '加载中' : '待刷新' }}</div>
              <p>{{ overviewLoading ? '正在计算覆盖率' : '未加载覆盖统计' }}</p>
              <div class="overview-track skeleton-track" aria-label="标题翻译覆盖率加载中">
                <div></div>
              </div>
            </div>
          </template>
          <template v-else>
            <div class="coverage-donut" :style="{ '--coverage-angle': `${percentValue(coverageTitle) * 3.6}deg` }">
              <div>
                <strong>{{ coveragePercent(coverageTitle) }}</strong>
                <span>标题覆盖</span>
              </div>
            </div>
            <div class="coverage-hero-copy">
              <span class="overview-kicker">标题覆盖</span>
              <div class="coverage-count">
                <strong>{{ formatNumber(coverageTitle.translated || 0) }}</strong>
                <span>/ {{ formatNumber(coverageTitle.total || 0) }}</span>
              </div>
              <p>剩余 {{ formatNumber(coverageTitle.untranslated || 0) }} 条标题需要翻译</p>
              <div class="overview-track" aria-label="标题翻译覆盖率">
                <div :style="{ transform: `scaleX(${percentValue(coverageTitle) / 100})` }"></div>
              </div>
            </div>
          </template>
        </section>

        <section class="metadata-overview" :class="{ loading: overviewLoading }" aria-label="元数据覆盖">
          <div class="overview-section-head">
            <div>
              <span class="overview-kicker">元数据覆盖</span>
              <strong>{{ overviewLoading ? '加载中' : (overviewNeedsRefresh ? '待刷新' : coveragePercent(metadataCoverage)) }}</strong>
            </div>
            <small>{{ overviewLoading ? '统计中' : (overviewNeedsRefresh ? '未加载' : `${formatNumber(metadataCoverage.untranslated || 0)} 未翻译`) }}</small>
          </div>
          <div class="coverage-row-list">
            <div v-for="row in coverageRows" :key="row.key" class="coverage-row" :class="{ 'coverage-row--loading': overviewLoading || overviewNeedsRefresh }">
              <div class="coverage-row-label">
                <strong>{{ row.label }}</strong>
                <span>{{ overviewLoading ? '加载中' : (overviewNeedsRefresh ? '等待刷新' : `${formatNumber(row.translated)} / ${formatNumber(row.total)}`) }}</span>
              </div>
              <div class="overview-track compact" :class="{ 'skeleton-track': overviewLoading || overviewNeedsRefresh }" :aria-label="`${row.label}覆盖率`">
                <div :style="{ transform: `scaleX(${(overviewLoading || overviewNeedsRefresh) ? 0.52 : row.percent / 100})` }"></div>
              </div>
              <span class="coverage-percent">{{ (overviewLoading || overviewNeedsRefresh) ? '...' : `${row.percent}%` }}</span>
            </div>
          </div>
        </section>

        <section class="overview-signals" aria-label="工作台和缓存">
          <div class="signal-card" :class="{ loading: overviewLoading || overviewNeedsRefresh }">
            <span class="overview-kicker">待处理工作台</span>
            <strong>{{ overviewLoading ? '加载中' : (overviewNeedsRefresh ? '待刷新' : formatNumber(workbenchPendingCount)) }}</strong>
            <small>{{ overviewLoading ? '校对状态统计中' : (overviewNeedsRefresh ? '未加载统计' : `机翻 ${formatNumber(reviewStatsByStatus.machine_translated || 0)} · 未翻译 ${formatNumber(reviewStatsByStatus.untranslated || 0)}`) }}</small>
          </div>
          <div class="signal-card" :class="{ quiet: !(reviewStatsByStatus.failed || 0), loading: overviewLoading || overviewNeedsRefresh }">
            <span class="overview-kicker">失败条目</span>
            <strong>{{ overviewLoading ? '加载中' : (overviewNeedsRefresh ? '待刷新' : formatNumber(reviewStatsByStatus.failed || 0)) }}</strong>
            <small>{{ overviewLoading ? '风险统计中' : (overviewNeedsRefresh ? '未加载统计' : `已校对 ${formatNumber(reviewStatsByStatus.reviewed || 0)} · 人工 ${formatNumber(reviewStatsByStatus.manual_edited || 0)}`) }}</small>
          </div>
          <div class="signal-card" :class="{ loading: overviewLoading || overviewNeedsRefresh }">
            <span class="overview-kicker">缓存与映射</span>
            <strong>{{ overviewLoading ? '加载中' : (overviewNeedsRefresh ? '待刷新' : formatNumber(stats.ai_cache || 0)) }}</strong>
            <small>{{ overviewLoading ? '缓存统计中' : (overviewNeedsRefresh ? '未加载统计' : `标题缓存 ${formatNumber(coverageTitle.cached || 0)} · 正式映射 ${formatNumber(coverageTitle.mapped || stats.title || 0)}`) }}</small>
          </div>
        </section>

        <aside class="job-control-card" :class="{ empty: !jobControlJob }" aria-label="任务状态">
          <div class="job-control-head">
            <div>
              <span class="overview-kicker">任务状态</span>
              <strong>{{ jobControlJob ? `#${jobControlJob.id} · ${jobTypeLabel(jobControlJob.job_type)}` : '暂无作业' }}</strong>
            </div>
            <span class="status-pill" :class="jobStatusClass(jobControlJob?.status)">{{ statusLabel(jobControlJob?.status) }}</span>
          </div>

          <div class="job-control-progress">
            <div class="job-progress-label">
              <span>进度</span>
              <strong>{{ jobProgressValue(jobControlJob) }}%</strong>
            </div>
            <div class="overview-track" aria-label="当前作业进度">
              <div :style="{ transform: `scaleX(${jobProgressValue(jobControlJob) / 100})` }"></div>
            </div>
          </div>

          <div class="job-control-metrics">
            <div>
              <span>处理</span>
              <strong>{{ formatNumber(jobControlJob?.processed || 0) }} / {{ formatNumber(jobControlJob?.total || 0) }}</strong>
            </div>
            <div>
              <span>翻译</span>
              <strong>{{ formatNumber(jobControlJob?.translated || 0) }}</strong>
            </div>
            <div>
              <span>跳过</span>
              <strong>{{ formatNumber(jobControlJob?.skipped || 0) }}</strong>
            </div>
            <div :class="{ danger: (jobControlJob?.failed || 0) > 0 }">
              <span>失败</span>
              <strong>{{ formatNumber(jobControlJob?.failed || 0) }}</strong>
            </div>
          </div>

          <div class="job-control-meta">
            <span>创建 {{ formatTime(jobControlJob?.created_at) }}</span>
            <span>耗时 {{ durationText(jobControlJob?.duration_seconds) }}</span>
            <span>源 {{ providerOrderLabel(jobControlJob?.provider_order) }}</span>
          </div>

          <div v-if="jobControlJob?.error_msg" class="job-error">{{ jobControlJob.error_msg }}</div>

          <div class="job-control-actions">
            <button v-if="canPauseCurrentJob" class="btn btn-ghost btn-sm" type="button" :disabled="pausingJob" @click="pauseJob">
              {{ pausingJob ? '暂停中...' : '暂停作业' }}
            </button>
            <button class="btn btn-primary btn-sm" type="button" :disabled="!canStartContinuationJob" @click="continueJobFromLatest">
              {{ startingJob ? '继续中...' : '继续翻译' }}
            </button>
            <button class="btn btn-ghost btn-sm" type="button" @click="setActiveSegment('history')">历史记录</button>
          </div>

          <small v-if="!jobControlJob" class="muted">会按当前默认字段从剩余内容继续处理。</small>
        </aside>
      </div>
    </section>

    <section v-else-if="activeSegment === 'create'" class="workspace-panel apple-surface">
      <div class="panel-header">
        <div>
          <h2>创建作业</h2>
        </div>
        <span class="chain-pill">{{ selectedProviderOrderLabel }}</span>
      </div>

      <div class="notice-row">
        <strong>批量作业默认不使用智能兜底</strong>
        <span>默认先查正式映射，再走低成本翻译源；简介仍由实时链路处理。</span>
      </div>

      <div class="form-grid">
        <label class="field">
          <span>翻译字段</span>
          <GlassSelect
            v-model="jobForm.job_type"
            :options="jobTypeOptions"
            aria-label="翻译字段"
          />
        </label>
        <label class="field">
          <span>作业模式</span>
          <GlassSelect
            v-model="jobForm.mode"
            :options="jobModeOptions"
            aria-label="作业模式"
          />
        </label>
      </div>

      <div class="notice-row secondary">
        <strong>{{ jobModeLabel }}</strong>
        <span>{{ jobModeHint }}</span>
      </div>

      <div class="provider-list">
        <label
          v-for="provider in providerOptions"
          :key="provider.key"
          class="provider-row"
          :class="{ enabled: selectedProvider === provider.key }"
        >
          <input v-model="selectedProvider" type="radio" name="translation-provider" :value="provider.key" />
          <div>
            <strong>{{ provider.label }}</strong>
            <small>{{ provider.hint }}</small>
          </div>
          <span class="provider-status">{{ providerStatusLabel(provider.key) }}</span>
        </label>
      </div>

      <div class="panel-footer-actions">
        <button class="btn btn-primary" type="button" :disabled="startingJob || !selectedProvider" @click="startJob">
          {{ startingJob ? '启动中...' : '开始翻译作业' }}
        </button>
      </div>
      <div v-if="jobMessage" class="message-line" :class="jobMessageType">{{ jobMessage }}</div>
    </section>

    <TranslationSourcesPanel
      v-else-if="activeSegment === 'sources'"
      :translation-config="translationConfig"
      :saving-config="savingConfig"
      :selected-provider="selectedProvider"
      :ai-provider-status-label="providerStatusLabel('ai')"
      @save="saveTranslationConfig"
    />

    <TranslationReviewPanel
      v-else-if="activeSegment === 'review'"
      :review-type="reviewType"
      :review-status="reviewStatus"
      :review-status-options="reviewStatusOptions"
      :review-query="reviewQuery"
      :review-page="reviewPage"
      :review-page-size="reviewPageSize"
      :review-page-size-options="reviewPageSizeOptions"
      :review-total="reviewTotal"
      :review-total-count="reviewTotalCount"
      :review-total-pages="reviewTotalPages"
      :review-unreviewed="reviewUnreviewed"
      :review-stats-by-status="reviewStatsByStatus"
      :review-items="reviewItems"
      :review-loading="reviewLoading"
      :retrying-items="retryingItems"
      :review-message="reviewMessage"
      :review-message-type="reviewMessageType"
      :review-history-item="reviewHistoryItem"
      :review-history="reviewHistory"
      :review-history-loading="reviewHistoryLoading"
      :translation-type-labels="translationTypeLabels"
      :translation-type-options="translationTypeOptions"
      @load-items="loadTranslationItems"
      @retry-items="retryReviewItems"
      @save-item="saveReviewItem"
      @mark-item="markReviewItem"
      @show-history="showItemHistory"
      @reset-item="resetReviewItem"
      @close-history="reviewHistoryItem = null"
      @restore-history="restoreHistoryItem"
      @update-review-type="reviewType = $event"
      @update-review-status="reviewStatus = $event"
      @update-review-query="reviewQuery = $event"
      @update-review-page-size="reviewPageSize = $event"
      @update-item-edit-text="updateReviewItemEditText"
    />

    <section v-else-if="activeSegment === 'mappings'" class="workspace-panel apple-surface">
      <div class="panel-header">
        <div>
          <h2>映射导入</h2>
        </div>
      </div>
      <div class="mapping-layout">
        <label class="field">
          <span>映射类型</span>
          <GlassSelect
            v-model="translationType"
            :options="translationTypeOptions"
            aria-label="映射类型"
          />
        </label>
        <div class="mapping-stat">
          <strong>{{ currentCoverage.translated || stats[translationType] || 0 }}</strong>
          <span>当前 {{ translationTypeLabels[translationType] }} 已翻译 · 未翻译 {{ currentCoverage.untranslated || 0 }}</span>
        </div>
        <div class="mapping-actions">
          <button class="btn btn-ghost" type="button" @click="exportTranslation">导出 {{ translationTypeLabels[translationType] }}</button>
          <label class="btn btn-ghost import-button">
            导入 {{ translationTypeLabels[translationType] }}
            <input type="file" accept=".json" @change="importTranslation" />
          </label>
        </div>
      </div>
      <div v-if="mappingMessage" class="message-line" :class="mappingMessageType">{{ mappingMessage }}</div>
    </section>

    <section v-else-if="activeSegment === 'history'" class="workspace-panel apple-surface">
      <div class="panel-header">
        <div>
          <h2>历史记录</h2>
        </div>
        <button class="btn btn-ghost btn-sm" type="button" @click="loadJobs">刷新历史</button>
      </div>
      <div class="history-layout">
        <div v-if="jobs.length" class="history-list">
          <button
            v-for="job in jobs"
            :key="job.id"
            v-memo="[job.id, job.status, job.progress_percent, job.translated, job.failed, selectedJob?.id]"
            class="history-row"
            type="button"
            :class="{ active: selectedJob?.id === job.id }"
            @click="selectJob(job)"
          >
            <div>
              <strong>#{{ job.id }} · {{ jobTypeLabel(job.job_type) }}</strong>
              <span>{{ statusLabel(job.status) }} · {{ formatTime(job.created_at) }}</span>
            </div>
            <small>{{ job.progress_percent || 0 }}% · 成功 {{ job.translated || 0 }} · 失败 {{ job.failed || 0 }}</small>
          </button>
        </div>
        <div v-else class="empty-panel">暂无历史作业</div>

        <aside v-if="selectedJob" class="result-summary">
          <strong>结果摘要</strong>
          <span>处理 {{ selectedJob.processed || 0 }} / {{ selectedJob.total || 0 }}</span>
          <span>翻译 {{ selectedJob.translated || 0 }} · 跳过 {{ selectedJob.skipped || 0 }} · 失败 {{ selectedJob.failed || 0 }}</span>
          <span>耗时 {{ durationText(selectedJob.duration_seconds) }}</span>
          <span>源 {{ providerOrderLabel(selectedJob.provider_order) }}</span>
          <span v-if="selectedJob.error_msg" class="error-text">{{ selectedJob.error_msg }}</span>
        </aside>
      </div>
    </section>
  </div>
</template>

<script>
import { defineAsyncComponent } from 'vue'
import { ElMessage } from '../utils/message.js'
import api from '../api'
import { requestConfirm } from '../utils/confirmDialog'
import GlassSelect from '../components/GlassSelect.vue'
import { DEFAULT_CONFIG, TRANSLATION_TYPE_LABELS } from '../features/config/configDefaults.js'
import {
  PROVIDER_KEYS,
  PROVIDER_META,
  firstNetworkProvider,
  normalizeProvider,
  providerLabel,
  providerOrderLabel,
} from '../utils/translationProviders.js'
import {
  coveragePercent,
  durationText,
  formatNumber,
  jobProgressValue,
  jobStatusClass,
  jobTypeLabel,
  percentValue,
  statusLabel,
} from '../utils/translationJobPresentation.js'

const TranslationSourcesPanel = defineAsyncComponent(() => import('../features/translations/TranslationSourcesPanel.vue'))
const TranslationReviewPanel = defineAsyncComponent(() => import('../features/translations/TranslationReviewPanel.vue'))

const BASE_BATCH_ORDER = ['cache', 'mapping']
const TRANSLATION_STATS_CACHE_KEY = 'javhub_translation_stats_cache'
let cachedTranslationStats = null
const JOB_TYPE_OPTIONS = [
  { value: 'library_titles', label: '库内影片标题', hint: '独立处理片库标题，默认走低成本源。' },
  { value: 'metadata_categories', label: '题材名称', hint: '只翻译题材名称。' },
  { value: 'metadata_series', label: '系列名称', hint: '只翻译系列名称。' },
  { value: 'metadata_makers', label: '厂商名称', hint: '只翻译厂商名称。' },
  { value: 'metadata_labels', label: '厂牌名称', hint: '只翻译厂牌名称。' },
  { value: 'metadata_actresses', label: '演员名称', hint: '只翻译演员名称。' },
  { value: 'metadata_names', label: '全部元数据名称', hint: '题材、系列、厂商、厂牌、演员一起处理。' },
]
const JOB_MODE_OPTIONS = [
  { value: 'remaining', label: '补剩余', hint: '跳过已有正式映射，优先处理失败项，适合中断后继续。' },
  { value: 'refresh_all', label: '全量重翻', hint: '忽略已有译文，用新的翻译结果覆盖。' },
]
const TRANSLATION_TYPE_OPTIONS = Object.entries(TRANSLATION_TYPE_LABELS)
  .map(([value, label]) => ({ value, label }))
const WORKBENCH_STATUS_OPTIONS = [
  { value: 'all', label: '全部状态' },
  { value: 'untranslated', label: '未翻译' },
  { value: 'failed', label: '失败' },
  { value: 'machine_translated', label: '机翻' },
  { value: 'reviewed', label: '已校对' },
  { value: 'manual_edited', label: '人工修改' },
  { value: 'invalid', label: '无效' },
]
function cloneTranslationConfig() {
  return JSON.parse(JSON.stringify(DEFAULT_CONFIG.translation))
}

export default {
  name: 'TranslationJobs',
  components: { GlassSelect, TranslationSourcesPanel, TranslationReviewPanel },
  data() {
    return {
      activeSegment: 'overview',
      segments: [
        { key: 'overview', label: '总览' },
        { key: 'create', label: '创建作业' },
        { key: 'sources', label: '翻译源' },
        { key: 'review', label: '校对台' },
        { key: 'mappings', label: '映射导入' },
        { key: 'history', label: '历史记录' },
      ],
      loading: false,
      statsLoading: false,
      statsLoaded: false,
      savingConfig: false,
      startingJob: false,
      pausingJob: false,
      stats: {},
      jobs: [],
      currentJob: null,
      selectedJob: null,
      jobTypeOptions: JOB_TYPE_OPTIONS,
      jobModeOptions: JOB_MODE_OPTIONS,
      pollTimer: null,
      translationConfig: cloneTranslationConfig(),
      translationType: 'title',
      translationTypeLabels: TRANSLATION_TYPE_LABELS,
      translationTypeOptions: TRANSLATION_TYPE_OPTIONS,
      reviewType: 'actress',
      reviewStatus: 'all',
      reviewStatusOptions: WORKBENCH_STATUS_OPTIONS,
      reviewQuery: '',
      reviewPage: 1,
      reviewPageSize: 30,
      reviewPageSizeOptions: [
        { value: 30, label: '30' },
        { value: 50, label: '50' },
        { value: 100, label: '100' },
        { value: 200, label: '200' },
      ],
      reviewTotalCount: 0,
      reviewTotalPages: 1,
      reviewItems: [],
      reviewStats: {},
      reviewLoading: false,
      retryingItems: false,
      reviewMessage: '',
      reviewMessageType: 'info',
      reviewHistoryItem: null,
      reviewHistory: [],
      reviewHistoryLoading: false,
      mappingMessage: '',
      mappingMessageType: 'info',
      jobMessage: '',
      jobMessageType: 'info',
      selectedProvider: 'google_free',
      providerOptions: PROVIDER_KEYS.map(key => ({ key, ...PROVIDER_META[key] })),
      jobForm: {
        job_type: 'library_titles',
        mode: 'remaining',
      },
    }
  },
  computed: {
    coverage() {
      return this.stats.coverage || {}
    },
    coverageTitle() {
      return this.coverage.title || {}
    },
    currentCoverage() {
      return this.coverage[this.translationType] || {}
    },
    workbenchStats() {
      return this.reviewStats.total !== undefined ? this.reviewStats : (this.stats.workbench || {})
    },
    reviewStatsByStatus() {
      return this.workbenchStats.by_status || {}
    },
    reviewTotal() {
      return this.workbenchStats.total || this.reviewTotalCount || 0
    },
    reviewUnreviewed() {
      return (this.reviewStatsByStatus.machine_translated || 0) + (this.reviewStatsByStatus.untranslated || 0) + (this.reviewStatsByStatus.failed || 0)
    },
    metadataCoverage() {
      return ['actress', 'category', 'series', 'maker', 'label'].reduce((acc, key) => {
        const item = this.coverage[key] || {}
        acc.total += item.total || 0
        acc.translated += item.translated || 0
        acc.untranslated += item.untranslated || 0
        return acc
      }, { total: 0, translated: 0, untranslated: 0 })
    },
    coverageRows() {
      return [
        { key: 'actress', label: '演员' },
        { key: 'category', label: '题材' },
        { key: 'series', label: '系列' },
        { key: 'maker', label: '厂商' },
        { key: 'label', label: '厂牌' },
      ].map(row => {
        const item = this.coverage[row.key] || {}
        return {
          ...row,
          total: item.total || 0,
          translated: item.translated || 0,
          untranslated: item.untranslated || 0,
          percent: this.percentValue(item),
        }
      })
    },
    workbenchPendingCount() {
      return (this.reviewStatsByStatus.machine_translated || 0)
        + (this.reviewStatsByStatus.untranslated || 0)
        + (this.reviewStatsByStatus.failed || 0)
    },
    overviewLoading() {
      return this.statsLoading && !Object.keys(this.coverage || {}).length
    },
    overviewNeedsRefresh() {
      return !this.statsLoading && !this.statsLoaded
    },
    jobControlJob() {
      return this.currentJob || this.jobs[0] || this.selectedJob || null
    },
    selectedProviderOrder() {
      return [...BASE_BATCH_ORDER, this.selectedProvider]
    },
    selectedProviderOrderLabel() {
      return this.providerOrderLabel(this.selectedProviderOrder)
    },
    canPauseCurrentJob() {
      return Boolean(this.currentJob?.id && ['pending', 'running'].includes(this.currentJob.status))
    },
    canStartContinuationJob() {
      const status = this.jobControlJob?.status
      return !this.startingJob
        && Boolean(this.selectedProvider)
        && !['pending', 'running'].includes(status)
    },
    selectedJobMode() {
      return JOB_MODE_OPTIONS.find(option => option.value === this.jobForm.mode) || JOB_MODE_OPTIONS[0]
    },
    jobModeLabel() {
      return this.selectedJobMode.label
    },
    jobModeHint() {
      return this.selectedJobMode.hint
    },
  },
  async mounted() {
    this.loadCachedStats()
    await this.reloadAll()
  },
  beforeUnmount() {
    this.stopPolling()
  },
  methods: {
    async setActiveSegment(segment) {
      this.activeSegment = segment
      if (segment === 'review' && !this.reviewItems.length) {
        await this.loadTranslationItems(1)
      }
    },
    async reloadAll() {
      this.loading = true
      try {
        await Promise.all([this.loadConfig(), this.loadJobs()])
        this.pickCurrentJob()
        if (this.activeSegment === 'review') await this.loadTranslationItems(this.reviewPage)
      } finally {
        this.loading = false
      }
    },
    async refreshOverview() {
      this.loading = true
      try {
        await Promise.all([this.loadConfig(), this.loadJobs()])
        this.pickCurrentJob()
        if (this.activeSegment === 'review') await this.loadTranslationItems(this.reviewPage)
        await this.loadStats()
      } finally {
        this.loading = false
      }
    },
    async loadConfig() {
      try {
        const resp = await api.getConfig()
        const remote = resp.data?.translation || {}
        this.translationConfig = this.mergeTranslationConfig(remote)
        this.syncProvidersFromConfig()
      } catch (error) {
        console.error('Failed to load translation config:', error)
        ElMessage.error('翻译配置加载失败')
      }
    },
    translationStatsStorage() {
      try {
        return typeof window !== 'undefined' ? window.localStorage : null
      } catch (error) {
        return null
      }
    },
    loadCachedStats() {
      try {
        if (cachedTranslationStats) {
          this.stats = cachedTranslationStats
          this.statsLoaded = true
          return
        }
        const storage = this.translationStatsStorage()
        const cached = storage?.getItem(TRANSLATION_STATS_CACHE_KEY)
        if (!cached) return
        const parsed = JSON.parse(cached)
        if (!parsed || typeof parsed !== 'object') return
        cachedTranslationStats = parsed
        this.stats = parsed
        this.statsLoaded = true
      } catch (error) {
        console.warn('Failed to load cached translation stats:', error)
      }
    },
    saveCachedStats(stats) {
      try {
        cachedTranslationStats = stats || {}
        const storage = this.translationStatsStorage()
        storage?.setItem(TRANSLATION_STATS_CACHE_KEY, JSON.stringify(cachedTranslationStats))
      } catch (error) {
        console.warn('Failed to save cached translation stats:', error)
      }
    },
    mergeTranslationConfig(remote = {}) {
      const base = cloneTranslationConfig()
      const merged = { ...base, ...remote }
      for (const key of ['google_free', 'baidu', 'deepl', 'microsoft']) {
        merged[key] = { ...(base[key] || {}), ...((remote && remote[key]) || {}) }
      }
      delete merged.openai_compatible
      merged.provider = this.normalizeProvider(merged.provider || this.firstNetworkProvider(merged.batch_provider_order) || this.firstNetworkProvider(merged.provider_order))
      if (!Array.isArray(merged.provider_order)) merged.provider_order = [...base.provider_order]
      if (!Array.isArray(merged.batch_provider_order)) merged.batch_provider_order = [...base.batch_provider_order]
      if (!merged.realtime_mode || merged.realtime_mode === 'sync') merged.realtime_mode = 'cache_only'
      merged.batch_concurrency = Math.max(1, Math.min(Number(merged.batch_concurrency || 32), 64))
      merged.batch_size = Math.max(1, Math.min(Number(merged.batch_size || 200), 200))
      merged.batch_char_limit = Math.max(500, Math.min(Number(merged.batch_char_limit || 24000), 24000))
      merged.source_page_size = Math.max(20, Math.min(Number(merged.source_page_size || 500), 1000))
      merged.scan_pages_per_batch = Math.max(1, Math.min(Number(merged.scan_pages_per_batch || 8), 64))
      merged.baidu.qps = Math.max(0, Number(merged.baidu.qps ?? 1) || 0)
      merged.baidu.timeout = Math.max(1, Number(merged.baidu.timeout || 15))
      return merged
    },
    async loadStats() {
      this.statsLoading = true
      try {
        const resp = await api.getTranslationStats()
        this.stats = resp.data || {}
        this.saveCachedStats(this.stats)
        this.statsLoaded = true
      } catch (error) {
        console.error('Failed to load translation stats:', error)
        if (!this.statsLoaded) this.stats = {}
      } finally {
        this.statsLoading = false
      }
    },
    async loadJobs() {
      try {
        const resp = await api.listTranslationJobs(50)
        this.jobs = resp.data?.data || []
        if (!this.selectedJob && this.jobs.length) this.selectedJob = this.jobs[0]
        if (this.selectedJob) {
          this.selectedJob = this.jobs.find(job => job.id === this.selectedJob.id) || this.selectedJob
        }
      } catch (error) {
        console.error('Failed to load translation jobs:', error)
        this.jobs = []
      }
    },
    pickCurrentJob() {
      const running = this.jobs.find(job => ['pending', 'running'].includes(job.status))
      this.currentJob = running || this.jobs[0] || null
      if (running) this.startPolling(running.id)
    },
    syncProvidersFromConfig() {
      this.selectedProvider = this.normalizeProvider(this.translationConfig.provider)
      this.syncSelectedProviderToConfig()
    },
    syncSelectedProviderToConfig() {
      this.translationConfig.provider = this.selectedProvider
      this.translationConfig.batch_provider_order = this.selectedProviderOrder
      this.translationConfig.provider_order = this.selectedProviderOrder
    },
    async saveTranslationConfig() {
      this.savingConfig = true
      this.syncSelectedProviderToConfig()
      const payload = {
        translation: {
          ...this.translationConfig,
          provider: this.selectedProvider,
          provider_order: this.selectedProviderOrder,
          batch_provider_order: this.selectedProviderOrder,
          realtime_mode: this.translationConfig.realtime_mode || 'cache_only',
          batch_concurrency: Math.max(1, Math.min(Number(this.translationConfig.batch_concurrency || 32), 64)),
          batch_size: Math.max(1, Math.min(Number(this.translationConfig.batch_size || 200), 200)),
          batch_char_limit: Math.max(500, Math.min(Number(this.translationConfig.batch_char_limit || 24000), 24000)),
          source_page_size: Math.max(20, Math.min(Number(this.translationConfig.source_page_size || 500), 1000)),
          scan_pages_per_batch: Math.max(1, Math.min(Number(this.translationConfig.scan_pages_per_batch || 8), 64)),
          baidu: {
            ...this.translationConfig.baidu,
            qps: Math.max(0, Number(this.translationConfig.baidu.qps ?? 1) || 0),
            timeout: Math.max(1, Number(this.translationConfig.baidu.timeout || 15)),
          },
        },
      }
      try {
        await api.updateConfig(payload)
        ElMessage.success('翻译源配置已保存')
        await this.loadStats()
      } catch (error) {
        console.error('Failed to save translation config:', error)
        ElMessage.error('保存翻译源失败')
      } finally {
        this.savingConfig = false
      }
    },
    async startJob() {
      const confirmed = await requestConfirm({
        title: this.jobForm.mode === 'refresh_all' ? '开始全量重翻' : '开始翻译作业',
        message: this.jobForm.mode === 'refresh_all'
          ? `确认用 ${this.providerLabel(this.selectedProvider)} 重新翻译「${this.jobTypeLabel(this.jobForm.job_type)}」？`
          : `确认用 ${this.providerLabel(this.selectedProvider)} 翻译「${this.jobTypeLabel(this.jobForm.job_type)}」的剩余内容？`,
        details: this.jobForm.mode === 'refresh_all'
          ? '全量重翻会忽略已有译文，并可能覆盖现有正式映射。'
          : '会创建真实翻译作业，消耗当前翻译源配额，并写入翻译缓存或映射。',
        confirmText: this.jobForm.mode === 'refresh_all' ? '开始重翻' : '开始翻译',
        tone: this.jobForm.mode === 'refresh_all' ? 'danger' : 'default',
      })
      if (!confirmed) return
      this.startingJob = true
      this.jobMessage = ''
      this.jobMessageType = 'info'
      try {
        const resp = await api.startTranslationJob({
          job_type: this.jobForm.job_type,
          provider: this.selectedProvider,
          mode: this.jobForm.mode,
        })
        const job = resp.data || {}
        this.currentJob = job
        this.selectedJob = job
        this.activeSegment = 'overview'
        this.jobMessage = `作业 #${job.id || ''} 已启动`
        this.jobMessageType = 'success'
        ElMessage.success('翻译作业已启动')
        await this.loadJobs()
        if (job.id) this.startPolling(job.id)
      } catch (error) {
        console.error('Failed to start translation job:', error)
        this.jobMessage = error.response?.data?.detail || '启动翻译作业失败'
        this.jobMessageType = 'error'
      } finally {
        this.startingJob = false
      }
    },
    async continueJobFromLatest() {
      if (!this.canStartContinuationJob) return
      const job = this.jobControlJob
      if (job?.job_type) this.jobForm.job_type = job.job_type
      this.jobForm.mode = 'remaining'
      await this.startJob()
    },
    startPolling(jobId) {
      this.stopPolling()
      this.pollTimer = setInterval(() => this.refreshCurrentJob(jobId), 2000)
      this.refreshCurrentJob(jobId)
    },
    stopPolling() {
      if (this.pollTimer) {
        clearInterval(this.pollTimer)
        this.pollTimer = null
      }
    },
    async pauseJob() {
      if (!this.canPauseCurrentJob) return
      this.pausingJob = true
      try {
        const resp = await api.pauseTranslationJob(this.currentJob.id)
        const job = resp.data || {}
        this.currentJob = job
        this.selectedJob = job
        this.jobs = [job, ...this.jobs.filter(item => item.id !== job.id)]
        this.stopPolling()
        ElMessage.success('翻译作业已暂停')
        this.loadStats()
        await this.loadJobs()
      } catch (error) {
        console.error('Failed to pause translation job:', error)
        ElMessage.error(error.response?.data?.detail || '暂停翻译作业失败')
      } finally {
        this.pausingJob = false
      }
    },
    async refreshCurrentJob(jobId) {
      try {
        const resp = await api.getTranslationJob(jobId)
        const job = resp.data || null
        if (!job) return
        this.currentJob = job
        this.jobs = [job, ...this.jobs.filter(item => item.id !== job.id)]
        if (this.selectedJob?.id === job.id) this.selectedJob = job
        if (['completed', 'failed', 'paused'].includes(job.status)) {
          this.stopPolling()
          this.loadStats()
          await this.loadJobs()
          this.pickCurrentJob()
        }
      } catch (error) {
        console.error('Failed to refresh translation job:', error)
        this.stopPolling()
      }
    },
    selectJob(job) {
      this.selectedJob = job
      this.activeSegment = 'history'
    },
    async exportTranslation() {
      this.mappingMessage = ''
      try {
        const resp = await api.exportTranslations(this.translationType)
        const blob = new Blob([resp.data], { type: 'application/json;charset=utf-8' })
        const url = URL.createObjectURL(blob)
        const link = document.createElement('a')
        link.href = url
        link.download = `translations_${this.translationType}.json`
        document.body.appendChild(link)
        link.click()
        document.body.removeChild(link)
        URL.revokeObjectURL(url)
        this.mappingMessage = '导出已开始'
        this.mappingMessageType = 'success'
      } catch (error) {
        console.error('Failed to export translations:', error)
        this.mappingMessage = '导出失败'
        this.mappingMessageType = 'error'
      }
    },
    async importTranslation(event) {
      const file = event.target.files?.[0]
      if (!file) return
      const confirmed = await requestConfirm({
        title: '导入翻译映射',
        message: `确认导入 ${file.name} 到「${this.translationTypeLabels[this.translationType] || this.translationType}」？`,
        details: '导入会写入正式映射，已有同源文本可能被更新。',
        confirmText: '导入',
      })
      if (!confirmed) {
        event.target.value = ''
        return
      }
      this.mappingMessage = ''
      try {
        const resp = await api.importTranslations(this.translationType, file)
        this.mappingMessage = `导入完成：${resp.data?.imported || 0} 条`
        this.mappingMessageType = 'success'
        await this.loadStats()
      } catch (error) {
        console.error('Failed to import translations:', error)
        this.mappingMessage = error.response?.data?.detail || '导入失败，请确认 JSON 格式'
        this.mappingMessageType = 'error'
      } finally {
        event.target.value = ''
      }
    },
    async loadTranslationItems(page = 1) {
      this.reviewLoading = true
      this.reviewMessage = ''
      this.reviewPage = Math.max(1, Number(page) || 1)
      try {
        const params = {
          type: this.reviewType,
          page: this.reviewPage,
          page_size: this.reviewPageSize,
        }
        if (this.reviewStatus && this.reviewStatus !== 'all') params.status = this.reviewStatus
        if (this.reviewQuery.trim()) params.q = this.reviewQuery.trim()
        const resp = await api.listTranslationItems(params)
        const data = resp.data || {}
        this.reviewItems = (data.data || []).map(item => ({
          ...item,
          edit_text: item.translated_text || '',
        }))
        this.reviewTotalCount = data.total_count || 0
        this.reviewTotalPages = data.total_pages || 1
        this.reviewStats = data.stats || {}
      } catch (error) {
        console.error('Failed to load translation workbench:', error)
        this.reviewMessage = error.response?.data?.detail || '校对台加载失败'
        this.reviewMessageType = 'error'
      } finally {
        this.reviewLoading = false
      }
    },
    updateReviewItemEditText({ item, value }) {
      if (item) item.edit_text = value
    },
    async saveReviewItem(item) {
      try {
        const resp = await api.updateTranslationItem(item.item_type, item.item_id, {
          action: 'save',
          source_text: item.source_text,
          translated_text: item.edit_text,
        })
        Object.assign(item, resp.data || {}, { edit_text: resp.data?.translated_text || item.edit_text })
        this.reviewMessage = '译文已保存'
        this.reviewMessageType = 'success'
        await Promise.all([this.loadStats(), this.loadTranslationItems(this.reviewPage)])
      } catch (error) {
        console.error('Failed to save translation item:', error)
        this.reviewMessage = error.response?.data?.detail || '保存失败'
        this.reviewMessageType = 'error'
      }
    },
    async markReviewItem(item) {
      try {
        const resp = await api.updateTranslationItem(item.item_type, item.item_id, {
          action: 'proofread',
          source_text: item.source_text,
        })
        Object.assign(item, resp.data || {}, { edit_text: resp.data?.translated_text || item.edit_text })
        this.reviewMessage = '已标记为已校对'
        this.reviewMessageType = 'success'
        await this.loadTranslationItems(this.reviewPage)
      } catch (error) {
        console.error('Failed to review translation item:', error)
        this.reviewMessage = error.response?.data?.detail || '标记失败'
        this.reviewMessageType = 'error'
      }
    },
    async resetReviewItem(item) {
      const confirmed = await requestConfirm({
        title: '重置译文',
        message: `确认清除「${item.source_text || item.item_id}」的译文？`,
        details: '会移除当前正式映射，并回到未翻译状态。',
        confirmText: '重置',
        tone: 'danger',
      })
      if (!confirmed) return
      try {
        const resp = await api.updateTranslationItem(item.item_type, item.item_id, {
          action: 'reset',
          source_text: item.source_text,
          clear_mapping: true,
        })
        Object.assign(item, resp.data || {}, { edit_text: '' })
        this.reviewMessage = '已重置为未翻译'
        this.reviewMessageType = 'success'
        await Promise.all([this.loadStats(), this.loadTranslationItems(this.reviewPage)])
      } catch (error) {
        console.error('Failed to reset translation item:', error)
        this.reviewMessage = error.response?.data?.detail || '重置失败'
        this.reviewMessageType = 'error'
      }
    },
    async showItemHistory(item) {
      this.reviewHistoryItem = item
      this.reviewHistoryLoading = true
      try {
        const resp = await api.getTranslationItemHistory(item.item_type, item.item_id, 50)
        this.reviewHistory = resp.data?.data || []
      } catch (error) {
        console.error('Failed to load translation item history:', error)
        this.reviewHistory = []
        this.reviewMessage = '历史加载失败'
        this.reviewMessageType = 'error'
      } finally {
        this.reviewHistoryLoading = false
      }
    },
    async restoreHistoryItem(history) {
      if (!this.reviewHistoryItem) return
      const confirmed = await requestConfirm({
        title: '恢复历史译文',
        message: '确认用这条历史记录覆盖当前译文？',
        details: history.translated_text || '',
        confirmText: '恢复',
      })
      if (!confirmed) return
      try {
        await api.updateTranslationItem(this.reviewHistoryItem.item_type, this.reviewHistoryItem.item_id, {
          action: 'restore',
          history_id: history.id,
        })
        this.reviewMessage = '已恢复历史版本'
        this.reviewMessageType = 'success'
        await Promise.all([
          this.loadStats(),
          this.loadTranslationItems(this.reviewPage),
          this.showItemHistory(this.reviewHistoryItem),
        ])
      } catch (error) {
        console.error('Failed to restore translation history:', error)
        this.reviewMessage = error.response?.data?.detail || '恢复失败'
        this.reviewMessageType = 'error'
      }
    },
    async retryReviewItems() {
      const confirmed = await requestConfirm({
        title: '重试当前筛选项',
        message: `确认重试「${this.reviewStatus === 'all' ? '全部状态' : this.reviewStatus}」筛选下的翻译项？`,
        details: this.reviewQuery.trim() ? `关键词：${this.reviewQuery.trim()}` : '会按当前类型和状态筛选批量创建重试作业。',
        confirmText: '开始重试',
      })
      if (!confirmed) return
      this.retryingItems = true
      try {
        const payload = {
          type: this.reviewType,
          provider: this.selectedProvider,
        }
        if (this.reviewStatus && this.reviewStatus !== 'all') payload.status = this.reviewStatus
        if (this.reviewQuery.trim()) payload.q = this.reviewQuery.trim()
        const resp = await api.retryTranslationItems(payload)
        const job = resp.data || {}
        this.currentJob = job
        this.selectedJob = job
        this.reviewMessage = `重试作业 #${job.id || ''} 已启动`
        this.reviewMessageType = 'success'
        if (job.id) this.startPolling(job.id)
        await this.loadJobs()
      } catch (error) {
        console.error('Failed to retry translation items:', error)
        this.reviewMessage = error.response?.data?.detail || '重试提交失败'
        this.reviewMessageType = 'error'
      } finally {
        this.retryingItems = false
      }
    },
    providerStatusLabel(key) {
      const state = this.stats.providers?.[key]
      if (!state) return '未检测'
      if (!state.enabled) return '未启用'
      return state.ready ? '可用' : '待配置'
    },
    providerLabel,
    providerOrderLabel,
    normalizeProvider,
    firstNetworkProvider,
    percentValue,
    coveragePercent,
    formatNumber,
    jobTypeLabel,
    statusLabel,
    jobStatusClass,
    durationText,
    jobProgressValue,
    formatTime(value) {
      if (!value) return '—'
      const date = new Date(value)
      if (Number.isNaN(date.getTime())) return String(value)
      return date.toLocaleString('zh-CN', {
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
      })
    },
  },
}
</script>

<style scoped src="../features/translations/translationJobs.css"></style>
