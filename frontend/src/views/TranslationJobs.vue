<template>
  <div class="translation-page page-shell page-shell--workspace">
    <header class="translation-header">
      <div>
        <h1>翻译作业</h1>
      </div>
      <div class="header-actions">
        <button class="btn btn-ghost" type="button" :disabled="loading" @click="reloadAll">
          {{ loading ? '刷新中...' : '刷新' }}
        </button>
        <button class="btn btn-primary" type="button" @click="activeSegment = 'create'">创建作业</button>
      </div>
    </header>

    <section class="summary-strip apple-surface" aria-label="翻译统计">
      <div class="summary-item">
        <span>{{ stats.title || 0 }}</span>
        <strong>有效标题译文</strong>
        <small>只统计真实标题映射</small>
      </div>
      <div class="summary-item">
        <span>{{ metadataTotal }}</span>
        <strong>元数据名称</strong>
        <small>{{ metadataSummary }}</small>
      </div>
      <div class="summary-item">
        <span>{{ stats.ai_cache || 0 }}</span>
        <strong>实时缓存</strong>
        <small>简介和兜底翻译</small>
      </div>
      <div class="summary-item">
        <span>{{ recentJobLabel }}</span>
        <strong>最近作业</strong>
        <small>{{ recentJobDetail }}</small>
      </div>
    </section>

    <nav class="segmented-control apple-surface" aria-label="翻译作业视图">
      <button
        v-for="segment in segments"
        :key="segment.key"
        type="button"
        :class="{ active: activeSegment === segment.key }"
        @click="activeSegment = segment.key"
      >{{ segment.label }}</button>
    </nav>

    <section v-if="activeSegment === 'overview'" class="workspace-panel apple-surface">
      <div class="panel-header">
        <div>
          <h2>总览</h2>
        </div>
        <span class="status-pill" :class="jobStatusClass(currentJob?.status)">{{ statusLabel(currentJob?.status) }}</span>
      </div>

      <div class="overview-grid">
        <div class="progress-block">
          <template v-if="currentJob">
            <div class="progress-topline">
              <strong>#{{ currentJob.id }} · {{ jobTypeLabel(currentJob.job_type) }}</strong>
              <span>{{ currentJob.progress_percent || 0 }}%</span>
            </div>
            <div class="progress-track" aria-label="翻译作业进度">
              <div class="progress-fill" :style="{ width: `${currentJob.progress_percent || 0}%` }"></div>
            </div>
            <div class="counter-grid">
              <div><strong>{{ currentJob.total || 0 }}</strong><span>总数</span></div>
              <div><strong>{{ currentJob.processed || 0 }}</strong><span>已处理</span></div>
              <div><strong>{{ currentJob.translated || 0 }}</strong><span>已翻译</span></div>
              <div><strong>{{ currentJob.skipped || 0 }}</strong><span>跳过</span></div>
              <div><strong>{{ currentJob.failed || 0 }}</strong><span>失败</span></div>
              <div><strong>{{ durationText(currentJob.duration_seconds) }}</strong><span>耗时</span></div>
            </div>
            <div class="job-meta">
              <span>开始 {{ formatTime(currentJob.started_at || currentJob.created_at) }}</span>
              <span v-if="currentJob.finished_at">结束 {{ formatTime(currentJob.finished_at) }}</span>
              <span>源 {{ providerOrderLabel(currentJob.provider_order) }}</span>
            </div>
            <div v-if="currentJob.error_msg" class="message-line error">{{ currentJob.error_msg }}</div>
          </template>
          <div v-else class="empty-panel compact">暂无运行中的翻译作业</div>
        </div>

        <aside class="recent-panel">
          <div class="recent-head">
            <strong>最近作业</strong>
            <button class="btn btn-ghost btn-sm" type="button" @click="activeSegment = 'history'">查看历史</button>
          </div>
          <button
            v-for="job in jobs.slice(0, 4)"
            :key="job.id"
            class="compact-job-row"
            type="button"
            @click="selectJob(job)"
          >
            <span>#{{ job.id }} · {{ jobTypeLabel(job.job_type) }}</span>
            <small>{{ statusLabel(job.status) }} · {{ job.progress_percent || 0 }}%</small>
          </button>
          <small v-if="!jobs.length" class="muted">暂无作业记录</small>
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
        <span>默认先查缓存和映射，再走低成本翻译源；简介仍由实时链路处理。</span>
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
          <span>数量上限</span>
          <input v-model.number="jobForm.limit" class="input" type="number" min="1" max="10000" />
        </label>
      </div>

      <label class="check-row standalone">
        <input v-model="jobForm.force" type="checkbox" />
        <span>强制重翻，忽略已有缓存</span>
      </label>

      <div class="provider-list">
        <label
          v-for="(provider, index) in batchProviders"
          :key="provider.key"
          class="provider-row"
          :class="{ enabled: provider.enabled }"
        >
          <input v-model="provider.enabled" type="checkbox" @change="syncBatchOrderFromProviders" />
          <div>
            <strong>{{ provider.label }}</strong>
            <small>{{ provider.hint }}</small>
          </div>
          <span class="provider-status">{{ providerStatusLabel(provider.key) }}</span>
          <span class="order-actions">
            <button class="icon-btn" type="button" :disabled="index === 0" title="上移" @click.prevent="moveProvider(index, -1)">
              <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 19V5"/><path d="M5 12l7-7 7 7"/></svg>
            </button>
            <button class="icon-btn" type="button" :disabled="index === batchProviders.length - 1" title="下移" @click.prevent="moveProvider(index, 1)">
              <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 5v14"/><path d="M19 12l-7 7-7-7"/></svg>
            </button>
          </span>
        </label>
      </div>

      <div class="panel-footer-actions">
        <button class="btn btn-primary" type="button" :disabled="startingJob || selectedProviderOrder.length <= 2" @click="startJob">
          {{ startingJob ? '启动中...' : '开始翻译作业' }}
        </button>
      </div>
      <div v-if="jobMessage" class="message-line" :class="jobMessageType">{{ jobMessage }}</div>
    </section>

    <section v-else-if="activeSegment === 'sources'" class="workspace-panel apple-surface">
      <div class="panel-header">
        <div>
          <h2>翻译源</h2>
        </div>
        <div class="panel-actions">
          <label class="mini-toggle">
            <input v-model="translationConfig.enabled" type="checkbox" />
            <span>启用翻译</span>
          </label>
          <button class="btn btn-primary btn-sm" type="button" :disabled="savingConfig" @click="saveTranslationConfig">
            {{ savingConfig ? '保存中...' : '保存翻译源' }}
          </button>
        </div>
      </div>

      <div class="source-layout">
        <section class="source-section">
          <div class="source-section-head">
            <div>
              <strong>低成本批量源</strong>
              <span>用于标题、演员、题材、系列和厂商名。</span>
            </div>
          </div>
          <div class="form-grid">
            <label class="field">
              <span>目标语言</span>
              <input v-model="translationConfig.target_language" class="input" placeholder="zh-CN" />
            </label>
            <label class="field">
              <span>实时模式</span>
              <input v-model="translationConfig.realtime_mode" class="input" disabled />
            </label>
          </div>
          <div class="source-settings">
            <label class="check-row boxed">
              <input v-model="translationConfig.google_free.enabled" type="checkbox" />
              <span>Google 免费接口</span>
            </label>
            <input v-model="translationConfig.google_free.base_url" class="input" placeholder="https://translate.googleapis.com/translate_a/single" />
            <div class="form-grid">
              <label class="check-row boxed">
                <input v-model="translationConfig.deepl.enabled" type="checkbox" />
                <span>启用 DeepL</span>
              </label>
              <label class="check-row boxed">
                <input v-model="translationConfig.deepl.free_api" type="checkbox" />
                <span>免费接口</span>
              </label>
            </div>
            <input v-model="translationConfig.deepl.api_key" class="input" :type="showDeeplKey ? 'text' : 'password'" placeholder="DeepL 密钥，可选" autocomplete="off" />
            <div class="form-grid">
              <label class="check-row boxed">
                <input v-model="translationConfig.microsoft.enabled" type="checkbox" />
                <span>启用 Microsoft</span>
              </label>
              <input v-model="translationConfig.microsoft.region" class="input" placeholder="Azure 区域，例如 eastasia" />
            </div>
            <input v-model="translationConfig.microsoft.api_key" class="input" :type="showMicrosoftKey ? 'text' : 'password'" placeholder="Microsoft 密钥，可选" autocomplete="off" />
          </div>
          <div class="key-actions left">
            <button class="btn btn-ghost btn-sm" type="button" @click="showDeeplKey = !showDeeplKey">{{ showDeeplKey ? '隐藏 DeepL 密钥' : '显示 DeepL 密钥' }}</button>
            <button class="btn btn-ghost btn-sm" type="button" @click="showMicrosoftKey = !showMicrosoftKey">{{ showMicrosoftKey ? '隐藏 Microsoft 密钥' : '显示 Microsoft 密钥' }}</button>
          </div>
        </section>

        <section class="source-section">
          <div class="source-section-head">
            <div>
              <strong>实时兜底</strong>
              <span>公共智能翻译参数在设置页维护，这里只用于状态检测和手动测试。</span>
            </div>
            <span class="provider-status">{{ providerStatusLabel('openai_compatible') }}</span>
          </div>
          <div class="source-settings">
            <textarea v-model="translationTestText" class="input test-textarea" rows="3" placeholder="输入一小段文本测试实时翻译"></textarea>
            <div class="key-actions left">
              <button class="btn btn-primary btn-sm" type="button" :disabled="testingTranslation || !translationTestText.trim()" @click="testTranslation">
                {{ testingTranslation ? '测试中...' : '测试实时翻译' }}
              </button>
            </div>
            <div v-if="translationTestMsg" class="message-line" :class="translationTestType">{{ translationTestMsg }}</div>
          </div>
        </section>
      </div>
    </section>

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
          <strong>{{ stats[translationType] || 0 }}</strong>
          <span>当前 {{ translationTypeLabels[translationType] }} 已翻译</span>
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
import { ElMessage } from 'element-plus'
import api from '../api'
import GlassSelect from '../components/GlassSelect.vue'
import { DEFAULT_CONFIG, TRANSLATION_TYPE_LABELS } from '../features/config/configDefaults.js'

const BASE_BATCH_ORDER = ['cache', 'mapping']
const JOB_TYPE_OPTIONS = [
  { value: 'library_titles', label: '库内影片标题', hint: '独立处理片库标题，默认走低成本源。' },
  { value: 'metadata_categories', label: '题材名称', hint: '只翻译题材名称。' },
  { value: 'metadata_series', label: '系列名称', hint: '只翻译系列名称。' },
  { value: 'metadata_makers', label: '厂商名称', hint: '只翻译厂商名称。' },
  { value: 'metadata_labels', label: '厂牌名称', hint: '只翻译厂牌名称。' },
  { value: 'metadata_actresses', label: '演员名称', hint: '只翻译演员名称，可用数量上限控制范围。' },
  { value: 'metadata_names', label: '全部元数据名称', hint: '题材、系列、厂商、厂牌、演员一起处理。' },
]
const TRANSLATION_TYPE_OPTIONS = Object.entries(TRANSLATION_TYPE_LABELS)
  .map(([value, label]) => ({ value, label }))
const PROVIDER_META = {
  google_free: { label: 'Google 免费接口', hint: '无密钥，适合标题和短名称批量翻译。' },
  deepl: { label: 'DeepL', hint: '质量更高，需要配置密钥。' },
  microsoft: { label: 'Microsoft 翻译', hint: 'Azure 翻译接口，需要密钥和可选区域。' },
}

function cloneTranslationConfig() {
  return JSON.parse(JSON.stringify(DEFAULT_CONFIG.translation))
}

export default {
  name: 'TranslationJobs',
  components: { GlassSelect },
  data() {
    return {
      activeSegment: 'overview',
      segments: [
        { key: 'overview', label: '总览' },
        { key: 'create', label: '创建作业' },
        { key: 'sources', label: '翻译源' },
        { key: 'mappings', label: '映射导入' },
        { key: 'history', label: '历史记录' },
      ],
      loading: false,
      savingConfig: false,
      startingJob: false,
      testingTranslation: false,
      stats: {},
      jobs: [],
      currentJob: null,
      selectedJob: null,
      jobTypeOptions: JOB_TYPE_OPTIONS,
      pollTimer: null,
      translationConfig: cloneTranslationConfig(),
      translationType: 'title',
      translationTypeLabels: TRANSLATION_TYPE_LABELS,
      translationTypeOptions: TRANSLATION_TYPE_OPTIONS,
      translationTestText: 'これは翻訳テストです。',
      translationTestMsg: '',
      translationTestType: 'info',
      mappingMessage: '',
      mappingMessageType: 'info',
      jobMessage: '',
      jobMessageType: 'info',
      showDeeplKey: false,
      showMicrosoftKey: false,
      batchProviders: [
        { key: 'google_free', ...PROVIDER_META.google_free, enabled: true },
        { key: 'deepl', ...PROVIDER_META.deepl, enabled: true },
        { key: 'microsoft', ...PROVIDER_META.microsoft, enabled: true },
      ],
      jobForm: {
        job_type: 'library_titles',
        limit: 1000,
        force: false,
      },
    }
  },
  computed: {
    metadataTotal() {
      return (this.stats.actress || 0) + (this.stats.category || 0) + (this.stats.series || 0)
        + (this.stats.maker || 0) + (this.stats.label || 0)
    },
    metadataSummary() {
      return [
        `演员 ${this.stats.actress || 0}`,
        `题材 ${this.stats.category || 0}`,
        `系列 ${this.stats.series || 0}`,
        `厂商 ${this.stats.maker || 0}`,
        `厂牌 ${this.stats.label || 0}`,
      ].join(' · ')
    },
    recentJob() {
      return this.jobs[0] || null
    },
    recentJobLabel() {
      if (!this.recentJob) return '无'
      return this.statusLabel(this.recentJob.status)
    },
    recentJobDetail() {
      if (!this.recentJob) return '尚未启动作业'
      return `#${this.recentJob.id} · ${this.jobTypeLabel(this.recentJob.job_type)} · ${this.recentJob.progress_percent || 0}%`
    },
    selectedProviderOrder() {
      return [
        ...BASE_BATCH_ORDER,
        ...this.batchProviders.filter(provider => provider.enabled).map(provider => provider.key),
      ]
    },
    selectedProviderOrderLabel() {
      return this.providerOrderLabel(this.selectedProviderOrder)
    },
  },
  watch: {
    'jobForm.job_type'(value) {
      this.jobForm.limit = String(value || '').startsWith('metadata_') ? 10000 : 1000
    },
  },
  async mounted() {
    await this.reloadAll()
  },
  beforeUnmount() {
    this.stopPolling()
  },
  methods: {
    async reloadAll() {
      this.loading = true
      try {
        await Promise.all([this.loadConfig(), this.loadStats(), this.loadJobs()])
        this.pickCurrentJob()
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
    mergeTranslationConfig(remote = {}) {
      const base = cloneTranslationConfig()
      const merged = { ...base, ...remote }
      for (const key of ['google_free', 'deepl', 'microsoft']) {
        merged[key] = { ...(base[key] || {}), ...((remote && remote[key]) || {}) }
      }
      delete merged.openai_compatible
      if (!Array.isArray(merged.provider_order)) merged.provider_order = [...base.provider_order]
      if (!Array.isArray(merged.batch_provider_order)) merged.batch_provider_order = [...base.batch_provider_order]
      return merged
    },
    async loadStats() {
      try {
        const resp = await api.getTranslationStats()
        this.stats = resp.data || {}
      } catch (error) {
        console.error('Failed to load translation stats:', error)
        this.stats = {}
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
      const configured = Array.isArray(this.translationConfig.batch_provider_order)
        ? this.translationConfig.batch_provider_order
        : []
      const configuredLowCost = configured.filter(key => PROVIDER_META[key])
      const orderedKeys = [
        ...configuredLowCost,
        ...Object.keys(PROVIDER_META).filter(key => !configuredLowCost.includes(key)),
      ]
      this.batchProviders = orderedKeys.map(key => ({
        key,
        ...PROVIDER_META[key],
        enabled: configured.length ? configured.includes(key) : true,
      }))
      this.syncBatchOrderFromProviders()
    },
    syncBatchOrderFromProviders() {
      this.translationConfig.batch_provider_order = this.selectedProviderOrder
    },
    moveProvider(index, direction) {
      const nextIndex = index + direction
      if (nextIndex < 0 || nextIndex >= this.batchProviders.length) return
      const providers = [...this.batchProviders]
      const [item] = providers.splice(index, 1)
      providers.splice(nextIndex, 0, item)
      this.batchProviders = providers
      this.syncBatchOrderFromProviders()
    },
    async saveTranslationConfig() {
      this.savingConfig = true
      this.syncBatchOrderFromProviders()
      const realtimeOrder = Array.from(new Set([
        'cache',
        'mapping',
        ...this.selectedProviderOrder.filter(key => !BASE_BATCH_ORDER.includes(key)),
        'openai_compatible',
      ]))
      const payload = {
        translation: {
          ...this.translationConfig,
          provider_order: realtimeOrder,
          batch_provider_order: this.selectedProviderOrder,
          realtime_mode: 'sync',
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
      this.startingJob = true
      this.jobMessage = ''
      this.jobMessageType = 'info'
      try {
        const resp = await api.startTranslationJob({
          job_type: this.jobForm.job_type,
          provider_order: this.selectedProviderOrder,
          limit: this.jobForm.limit,
          force: this.jobForm.force,
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
    async refreshCurrentJob(jobId) {
      try {
        const resp = await api.getTranslationJob(jobId)
        const job = resp.data || null
        if (!job) return
        this.currentJob = job
        this.jobs = [job, ...this.jobs.filter(item => item.id !== job.id)]
        if (this.selectedJob?.id === job.id) this.selectedJob = job
        if (['completed', 'failed'].includes(job.status)) {
          this.stopPolling()
          await Promise.all([this.loadStats(), this.loadJobs()])
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
    async testTranslation() {
      this.testingTranslation = true
      this.translationTestMsg = ''
      this.translationTestType = 'info'
      try {
        const resp = await api.testTranslation(this.translationTestText.trim())
        const translated = resp.data?.translated_text || ''
        this.translationTestMsg = translated ? `译文：${translated}` : '测试完成，但没有返回译文'
        this.translationTestType = translated ? 'success' : 'error'
      } catch (error) {
        console.error('Failed to test translation:', error)
        this.translationTestMsg = error.response?.data?.detail || '实时翻译测试失败，请检查兜底配置'
        this.translationTestType = 'error'
      } finally {
        this.testingTranslation = false
      }
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
    providerStatusLabel(key) {
      const state = this.stats.providers?.[key]
      if (!state) return '未检测'
      if (!state.enabled) return '未启用'
      return state.ready ? '可用' : '待配置'
    },
    providerLabel(key) {
      return {
        cache: '缓存',
        mapping: '映射',
        google_free: 'Google 免费接口',
        deepl: 'DeepL',
        microsoft: 'Microsoft 翻译',
        openai_compatible: '智能兜底',
      }[key] || key || ''
    },
    providerOrderLabel(order) {
      const labels = (order || []).map(key => this.providerLabel(key)).filter(Boolean)
      return labels.length ? labels.join(' -> ') : '未记录'
    },
    jobTypeLabel(type) {
      return {
        library_titles: '库内影片标题',
        metadata_names: '全部元数据名称',
        metadata_categories: '题材名称',
        metadata_series: '系列名称',
        metadata_makers: '厂商名称',
        metadata_labels: '厂牌名称',
        metadata_actresses: '演员名称',
      }[type] || type || '未知作业'
    },
    statusLabel(status) {
      return {
        pending: '等待中',
        running: '运行中',
        completed: '已完成',
        failed: '失败',
        idle: '空闲',
      }[status] || '空闲'
    },
    jobStatusClass(status) {
      return `status-${status || 'idle'}`
    },
    durationText(value) {
      if (value === null || value === undefined) return '—'
      const seconds = Math.max(0, Number(value) || 0)
      if (seconds < 60) return `${seconds}s`
      const minutes = Math.floor(seconds / 60)
      const rest = seconds % 60
      if (minutes < 60) return rest ? `${minutes}m ${rest}s` : `${minutes}m`
      const hours = Math.floor(minutes / 60)
      const minuteRest = minutes % 60
      return minuteRest ? `${hours}h ${minuteRest}m` : `${hours}h`
    },
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

<style scoped>
.translation-page {
  display: flex;
  flex-direction: column;
  gap: 10px;
  letter-spacing: 0;
}

.translation-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  padding: 2px 0 8px;
}

.translation-header h1,
.panel-header h2 {
  margin: 0;
  color: var(--text-primary);
  letter-spacing: 0;
}

.translation-header h1 {
  font-size: 40px;
  line-height: 1.05;
  font-weight: 600;
}

.eyebrow {
  margin: 0 0 4px;
  color: var(--text-muted);
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}

.header-actions,
.panel-actions,
.panel-footer-actions,
.key-actions,
.mapping-actions,
.recent-head,
.progress-topline,
.job-meta {
  display: flex;
  align-items: center;
  gap: 10px;
}

.header-actions,
.panel-actions {
  flex-wrap: wrap;
  justify-content: flex-end;
}

.btn-sm {
  min-height: 36px;
  padding: 7px 12px;
  font-size: 12px;
}

.summary-strip {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 0;
  overflow: hidden;
}

.summary-item {
  min-height: 62px;
  padding: 10px 14px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  background: rgba(255, 255, 255, 0.025);
  border-right: 1px solid var(--border);
}

.summary-item:last-child {
  border-right: 0;
}

.summary-item span {
  color: var(--text-primary);
  font-size: 15px;
  font-weight: 600;
  line-height: 1;
}

.summary-item strong {
  margin-top: 6px;
  color: var(--text-primary);
  font-size: 12px;
  font-weight: 500;
}

.summary-item small {
  display: block;
  margin-top: 3px;
  font-size: 11px;
  line-height: 1.35;
}

.summary-item small,
.muted,
.provider-row small,
.source-section-head span,
.history-row span,
.result-summary span,
.job-meta,
.notice-row span {
  color: var(--text-secondary);
}

.segmented-control {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 3px;
  padding: 3px;
  border-radius: var(--radius-md);
  background: rgba(255, 255, 255, 0.045);
}

.segmented-control button {
  min-height: 32px;
  border: 0;
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--text-secondary);
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  transition: background var(--motion-fast), color var(--motion-fast), box-shadow var(--motion-fast);
}

.segmented-control button:hover {
  background: var(--accent-bg);
  color: var(--text-primary);
}

.segmented-control button.active {
  background: rgba(255, 255, 255, 0.12);
  color: var(--text-primary);
  box-shadow: inset 0 0 0 1px var(--border-light), 0 4px 12px var(--black-20);
}

.workspace-panel {
  padding: 14px;
}

.panel-header {
  min-height: 36px;
  margin-bottom: 12px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
}

.panel-header h2 {
  font-size: 14px;
  line-height: 1.25;
  font-weight: 600;
}

.overview-grid,
.source-layout,
.history-layout {
  display: grid;
  grid-template-columns: minmax(0, 1.5fr) minmax(280px, 0.85fr);
  gap: 16px;
}

.progress-block,
.recent-panel,
.source-section,
.result-summary {
  min-width: 0;
}

.recent-panel,
.result-summary {
  padding-left: 16px;
  border-left: 1px solid var(--border);
}

.progress-topline {
  justify-content: space-between;
  color: var(--text-primary);
  font-size: 13px;
}

.progress-topline strong,
.recent-head strong,
.history-row strong,
.result-summary strong {
  font-weight: 500;
}

.progress-track {
  height: 6px;
  margin: 14px 0;
  overflow: hidden;
  border-radius: var(--radius-control);
  background: rgba(255, 255, 255, 0.08);
}

.progress-fill {
  height: 100%;
  border-radius: inherit;
  background: var(--accent);
  transition: width 0.25s ease;
}

.counter-grid {
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  gap: 6px;
}

.counter-grid div {
  min-height: 52px;
  padding: 9px;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  background: rgba(255, 255, 255, 0.035);
}

.counter-grid strong {
  display: block;
  color: var(--text-primary);
  font-size: 14px;
  font-weight: 500;
}

.counter-grid span {
  display: block;
  margin-top: 3px;
  color: var(--text-secondary);
  font-size: 11px;
}

.job-meta {
  margin-top: 12px;
  flex-wrap: wrap;
  font-size: 12px;
}

.compact-job-row,
.history-row {
  width: 100%;
  border: 0;
  border-bottom: 1px solid var(--border);
  background: transparent;
  color: var(--text-primary);
  cursor: pointer;
  text-align: left;
}

.compact-job-row {
  min-height: 52px;
  padding: 10px 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.compact-job-row small,
.history-row small {
  color: var(--text-secondary);
}

.history-row {
  min-height: 58px;
  padding: 10px 0;
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: center;
  gap: 12px;
}

.history-row div {
  display: grid;
  gap: 4px;
}

.history-row.active strong {
  color: var(--text-primary);
}

.notice-row {
  margin-bottom: 12px;
  padding: 10px 12px;
  display: grid;
  gap: 3px;
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: var(--radius-md);
  background: rgba(255, 255, 255, 0.035);
}

.notice-row strong {
  color: var(--text-primary);
  font-weight: 500;
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.field {
  display: grid;
  gap: 6px;
}

.field span {
  color: var(--text-secondary);
  font-size: 12px;
  font-weight: 500;
}

.input {
  width: 100%;
  min-height: 40px;
  padding: 8px 11px;
  border: 1px solid transparent;
  border-radius: var(--radius-md);
  background: rgba(255, 255, 255, 0.05);
  color: var(--text-primary);
  outline: none;
  font: inherit;
  transition: border-color 0.18s ease, background 0.18s ease;
}

.input:focus {
  border-color: var(--accent);
  background: rgba(255, 255, 255, 0.08);
}

.input:disabled {
  opacity: 0.72;
  cursor: not-allowed;
}

.check-row,
.mini-toggle {
  display: inline-flex;
  align-items: center;
  gap: 9px;
  color: var(--text-primary);
  font-weight: 500;
}

.check-row input,
.mini-toggle input,
.provider-row input {
  width: 16px;
  height: 16px;
  accent-color: var(--accent);
}

.standalone {
  margin-top: 12px;
}

.boxed {
  min-height: 40px;
  padding: 8px 11px;
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  background: rgba(255, 255, 255, 0.035);
}

.provider-list {
  margin-top: 14px;
  border-top: 1px solid var(--border);
}

.provider-row {
  min-height: 56px;
  padding: 10px 0;
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto auto;
  align-items: center;
  gap: 12px;
  border-bottom: 1px solid var(--border);
}

.provider-row strong {
  display: block;
  margin-bottom: 3px;
  color: var(--text-primary);
  font-size: 13px;
  font-weight: 500;
}

.provider-row:not(.enabled) {
  opacity: 0.62;
}

.provider-status,
.chain-pill,
.status-pill {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 26px;
  padding: 4px 9px;
  border-radius: var(--radius-control);
  border: 1px solid var(--border);
  background: rgba(255, 255, 255, 0.05);
  color: var(--text-secondary);
  font-size: 11px;
  font-weight: 600;
  white-space: nowrap;
}

.chain-pill {
  max-width: min(520px, 100%);
  overflow: hidden;
  color: var(--text-primary);
  text-overflow: ellipsis;
}

.status-running,
.status-pending {
  color: var(--badge-warning-text);
  background: var(--badge-warning-bg);
  border-color: rgba(245, 181, 80, 0.28);
}

.status-completed {
  color: var(--badge-success-text);
  background: var(--badge-success-bg);
  border-color: rgba(90, 200, 150, 0.28);
}

.status-failed {
  color: #ff6b78;
  background: rgba(255, 80, 90, 0.12);
  border-color: rgba(255, 80, 90, 0.22);
}

.order-actions {
  display: inline-flex;
  gap: 6px;
}

.icon-btn {
  width: 32px;
  height: 32px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  background: rgba(255, 255, 255, 0.04);
  color: var(--text-primary);
  cursor: pointer;
}

.icon-btn:disabled {
  opacity: 0.36;
  cursor: not-allowed;
}

.icon-btn svg {
  width: 16px;
  height: 16px;
  fill: none;
  stroke: currentColor;
  stroke-width: 2;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.panel-footer-actions {
  margin-top: 16px;
  justify-content: flex-end;
}

.source-section + .source-section {
  padding-left: 16px;
  border-left: 1px solid var(--border);
}

.source-section-head {
  margin-bottom: 12px;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.source-section-head strong {
  display: block;
  margin-bottom: 4px;
  color: var(--text-primary);
  font-size: 13px;
  font-weight: 500;
}

.source-section-head span {
  display: block;
  font-size: 12px;
}

.source-settings {
  display: grid;
  gap: 10px;
}

.source-section {
  min-width: 0;
}

.test-textarea {
  min-height: 84px;
  resize: vertical;
}

.left {
  margin-top: 10px;
  justify-content: flex-start;
  flex-wrap: wrap;
}

.mapping-layout {
  display: grid;
  grid-template-columns: minmax(220px, 0.8fr) minmax(220px, 1fr) auto;
  align-items: end;
  gap: 14px;
}

.mapping-stat {
  min-height: 52px;
  display: grid;
  align-content: center;
  gap: 3px;
}

.mapping-stat strong {
  color: var(--text-primary);
  font-size: 16px;
  font-weight: 500;
}

.mapping-stat span {
  color: var(--text-secondary);
  font-size: 12px;
}

.import-button {
  position: relative;
  overflow: hidden;
}

.import-button input {
  position: absolute;
  inset: 0;
  opacity: 0;
  cursor: pointer;
}

.history-list {
  min-width: 0;
}

.result-summary {
  display: grid;
  align-content: start;
  gap: 8px;
}

.result-summary strong {
  color: var(--text-primary);
  font-size: 14px;
  font-weight: 500;
}

.empty-panel {
  min-height: 120px;
  display: grid;
  place-items: center;
  color: var(--text-secondary);
  border: 1px dashed var(--border);
  border-radius: var(--radius-lg);
}

.empty-panel.compact {
  min-height: 136px;
}

.message-line {
  margin-top: 12px;
  padding: 10px 12px;
  border-radius: var(--radius-md);
  border: 1px solid var(--border);
  background: rgba(255, 255, 255, 0.04);
  color: var(--text-secondary);
  font-size: 12px;
}

.message-line.success {
  color: var(--badge-success-text);
  background: var(--badge-success-bg);
}

.message-line.error,
.error-text {
  color: #ff6b78;
}

@media (max-width: 920px) {
  .translation-header,
  .panel-header {
    align-items: flex-start;
    flex-direction: column;
  }

  .header-actions,
  .panel-actions {
    width: 100%;
    justify-content: flex-start;
  }

  .summary-strip {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .summary-item:nth-child(2n) {
    border-right: 0;
  }

  .segmented-control {
    grid-template-columns: repeat(5, max-content);
    overflow-x: auto;
    scrollbar-width: none;
  }

  .segmented-control::-webkit-scrollbar {
    display: none;
  }

  .segmented-control button {
    min-width: 88px;
    min-height: 38px;
  }

  .overview-grid,
  .source-layout,
  .history-layout,
  .form-grid,
  .mapping-layout {
    grid-template-columns: 1fr;
  }

  .recent-panel,
  .result-summary,
  .source-section + .source-section {
    padding-left: 0;
    border-left: 0;
    padding-top: 14px;
    border-top: 1px solid var(--border);
  }

  .counter-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

@media (max-width: 560px) {
  .translation-page {
    gap: 10px;
  }

  .workspace-panel {
    padding: 12px;
  }

  .translation-header h1 {
    font-size: 30px;
    line-height: 1.1;
  }

  .summary-strip {
    grid-template-columns: 1fr;
  }

  .summary-item {
    min-height: 62px;
    border-right: 0;
    border-bottom: 1px solid var(--border);
  }

  .summary-item:last-child {
    border-bottom: 0;
  }

  .counter-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .provider-row {
    grid-template-columns: auto minmax(0, 1fr);
    min-height: 70px;
  }

  .provider-status,
  .order-actions {
    grid-column: 2;
    justify-self: start;
  }

  .history-row,
  .compact-job-row {
    grid-template-columns: 1fr;
    align-items: start;
  }

  .header-actions,
  .panel-actions,
  .panel-footer-actions,
  .key-actions,
  .mapping-actions {
    align-items: stretch;
  }

  .header-actions .btn,
  .panel-actions .btn,
  .panel-footer-actions .btn,
  .key-actions .btn,
  .mapping-actions .btn,
  .mapping-actions .import-button {
    width: 100%;
    justify-content: center;
  }
}
</style>
