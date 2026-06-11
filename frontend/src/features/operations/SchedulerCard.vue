<template>
  <article class="workbench-panel health-panel" aria-label="初始化与健康检查">
    <div class="panel-head">
      <div>
        <h2>初始化与健康检查</h2>
        <p>{{ healthStatusLabel }} · {{ healthConfigSummary }}</p>
      </div>
      <div class="panel-actions">
        <button class="btn btn-ghost btn-sm" type="button" @click="$router.push('/settings')">设置</button>
        <button class="btn btn-ghost btn-sm" type="button" @click="goJavInfoImport">导入数据库</button>
        <button class="btn btn-ghost btn-sm" type="button" @click="$router.push('/logs')">日志</button>
      </div>
    </div>

    <AppleSkeleton v-if="loading && !health" class="loading-panel console-state" variant="list" :items="5" label="系统状态加载中" />
    <AppleErrorState v-else-if="healthError && !health" class="empty-panel console-state" title="健康检查暂不可用" :description="healthError" next-step="可以重试健康检查，或打开运行日志查看后端状态。" retry-label="重试" secondary-action-label="运行日志" source-label="Readiness API" @retry="loadOverview" @secondary-action="$router.push('/logs')" />
    <AppleEmptyState v-else-if="!health" class="empty-panel console-state" title="暂无系统状态" description="后端还没有返回健康检查数据。" next-step="可以重试健康检查，或打开设置确认初始化配置。" action-label="重试" secondary-action-label="设置" density="compact" @action="loadOverview" @secondary-action="$router.push('/settings')" />
    <template v-else>
    <div class="health-grid">
      <div class="state-item" :class="{ warning: !health?.config?.loaded }"><span>配置已加载</span><strong>{{ health?.config?.loaded ? '是' : '否' }}</strong></div>
      <div class="state-item" :class="{ warning: health?.database && !health.database.connectable }"><span>数据库</span><strong>{{ healthDatabaseSummary }}</strong></div>
      <div class="state-item" :class="{ warning: health?.javinfo && (!health.javinfo.api_url_configured || health.javinfo.legacy) }"><span>JavInfo</span><strong>{{ healthJavInfoSummary }}</strong></div>
      <div class="state-item" :class="{ warning: !!health?.cache?.error }"><span>缓存</span><strong>{{ healthCacheSummary }}</strong></div>
      <div class="state-item" :class="{ warning: health?.downloaders && !health.downloaders.default_available }"><span>默认下载器</span><strong>{{ healthDownloaderSummary }}</strong></div>
      <div class="state-item" :class="{ warning: health?.sources && (!health.sources.available || health.sources.latest_attempt_error) }">
        <span>磁力源</span>
        <strong>{{ healthSourceSummary }}</strong>
        <small v-if="healthSourceAttemptSummary">{{ healthSourceAttemptSummary }}</small>
      </div>
      <div class="state-item" :class="{ warning: health?.scheduler && !health.scheduler.effective_enabled }"><span>调度有效性</span><strong>{{ healthSchedulerSummary }}</strong></div>
      <div class="state-item" :class="{ warning: health?.javinfo?.legacy || health?.javinfo?.error }"><span>JavInfo 地址</span><strong>{{ healthJavInfoUrlSummary }}</strong></div>
    </div>

    <div class="state-grid">
      <button class="state-item" type="button" @click="$router.push('/settings')"><span>当前策略</span><strong>{{ policyLabel(overview?.automation?.download_policy) }}</strong></button>
      <div class="state-item"><span>自动处理间隔</span><strong>{{ overview?.automation?.auto_process_interval_minutes || 0 }} 分钟</strong></div>
      <div class="state-item"><span>调度</span><strong>{{ scheduleStatusLabel }}</strong></div>
      <div class="state-item"><span>下一次</span><strong>{{ formatTime(candidateSchedule.next_run_time) || '未计划' }}</strong></div>
      <button class="state-item" type="button" @click="goLibraryOrganize('mapping')">
        <span>自动匹配</span>
        <strong>{{ overview?.mapping?.auto_match?.auto_match_after_collect ? '采集后自动匹配' : '手动匹配' }}</strong>
      </button>
      <div class="state-item"><span>确认策略</span><strong>保守唯一</strong></div>
    </div>

    <p v-if="healthError || cacheStatsError" class="muted cache-error">{{ healthError || cacheStatsError }}</p>
    </template>
  </article>
</template>

<script>
import api from '../../api'
import AppleSkeleton from '../../components/AppleSkeleton.vue'
import AppleEmptyState from '../../components/AppleEmptyState.vue'
import AppleErrorState from '../../components/AppleErrorState.vue'

export default {
  name: 'SchedulerCard',
  components: { AppleSkeleton, AppleEmptyState, AppleErrorState },
  data() {
    return {
      overview: null,
      cacheStats: null,
      health: null,
      cacheStatsError: '',
      healthError: '',
      loading: false,
    }
  },
  computed: {
    candidateSchedule() {
      return this.overview?.candidate_runs?.schedule || {}
    },
    healthStatusLabel() {
      if (this.healthError) return '健康检查暂不可用'
      if (!this.health) return '健康检查加载中'
      return this.health.status === 'ok' ? '运行正常' : '需要检查'
    },
    healthConfigSummary() {
      if (this.healthError) return this.healthError
      const cfg = this.health?.config
      if (!cfg) return '等待后端返回配置状态'
      return cfg.loaded ? '配置已加载' : (cfg.error || '配置未加载')
    },
    healthDatabaseSummary() {
      const database = this.health?.database
      if (!database) return '未知'
      return database.connectable ? database.backend || 'postgres' : database.error || '不可连接'
    },
    healthJavInfoSummary() {
      const javinfo = this.health?.javinfo
      if (!javinfo) return '未知'
      if (!javinfo.api_url_configured) return '未配置'
      if (javinfo.legacy) return '旧端口配置'
      if (javinfo.reachable === false) return '不可达'
      return '已配置'
    },
    healthJavInfoUrlSummary() {
      const javinfo = this.health?.javinfo
      if (!javinfo?.api_url) return '未配置'
      return String(javinfo.api_url).replace(/^https?:\/\//, '').replace(/\/$/, '')
    },
    healthCacheSummary() {
      const cache = this.health?.cache
      if (!cache) return '未知'
      if (cache.error) return cache.error
      return `${cache.backend || 'unknown'} · ${cache.active_entries || 0}/${cache.total_entries || 0}`
    },
    healthDownloaderSummary() {
      const downloaders = this.health?.downloaders
      if (!downloaders) return '未知'
      if (downloaders.error) return downloaders.error
      return `${downloaders.default_id || '未设置'} · ${downloaders.available || 0}/${downloaders.registered || 0}`
    },
    healthSourceSummary() {
      const sources = this.health?.sources
      if (!sources) return '未知'
      if (sources.error) return sources.error
      return `${sources.available || 0}/${sources.registered || 0} 可用`
    },
    healthSourceAttemptSummary() {
      const sources = this.health?.sources || {}
      const count = Number(sources.recent_attempt_count || 0)
      const latestError = String(sources.latest_attempt_error || '').trim()
      if (!count) return ''
      if (!latestError) return `最近源检索 ${count} 次无错误`
      const source = String(sources.latest_attempt_source || '未知源').trim()
      const keyword = String(sources.latest_attempt_keyword || '').trim()
      return `最近源检索 ${count} 次 · ${source}${keyword ? ` · ${keyword}` : ''}：${latestError}`
    },
    healthSchedulerSummary() {
      const scheduler = this.health?.scheduler
      if (!scheduler) return '未知'
      if (scheduler.effective_enabled) return '已启用'
      return scheduler.disabled_reason || '未启用'
    },
    scheduleStatusLabel() {
      if (this.candidateSchedule.running) return '运行中'
      if (this.candidateSchedule.effective_enabled) return '已启用'
      if (this.candidateSchedule.disabled_reason === 'manual_policy') return '手动策略'
      if (this.candidateSchedule.enabled) return '已配置未生效'
      return '未启用'
    },
  },
  mounted() {
    this.loadOverview()
  },
  methods: {
    async loadOverview() {
      this.loading = true
      this.cacheStatsError = ''
      this.healthError = ''
      try {
        const [cacheStatsResp, healthResp, configResp] = await Promise.allSettled([
          api.getCacheStats(),
          api.readiness(),
          api.getConfig(),
        ])
        if (cacheStatsResp.status === 'fulfilled') this.cacheStats = cacheStatsResp.value.data
        else this.cacheStatsError = cacheStatsResp.reason?.response?.data?.detail || cacheStatsResp.reason?.message || '加载失败'
        if (healthResp.status === 'fulfilled') this.health = healthResp.value.data
        else this.healthError = healthResp.reason?.response?.data?.detail || healthResp.reason?.message || '加载失败'
        const cfg = configResp.status === 'fulfilled' ? configResp.value.data : {}
        this.overview = {
          automation: cfg.automation || {},
          candidate_runs: { schedule: this.health?.scheduler || {} },
          mapping: { auto_match: cfg.actor_mapping || {} },
        }
      } finally {
        this.loading = false
      }
    },
    async loadCacheStats() {
      this.cacheStatsError = ''
      try {
        const resp = await api.getCacheStats()
        this.cacheStats = resp.data
      } catch (e) {
        this.cacheStatsError = e.response?.data?.detail || e.message || '加载失败'
      }
    },
    policyLabel(policy) {
      const map = { manual: '人工批准', rules: '规则自动', auto: '全自动' }
      return map[policy] || '人工批准'
    },
    formatTime(value) {
      if (!value) return ''
      const date = new Date(value)
      if (Number.isNaN(date.getTime())) return value
      return `${date.getMonth() + 1}/${date.getDate()} ${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`
    },
    goJavInfoImport() {
      this.$router.push({ path: '/settings', query: { tab: 'javinfo-import' } })
    },
    goLibraryOrganize(tab = 'inventory') {
      this.$router.push({ path: '/library-organize', query: { tab } })
    },
  },
}
</script>

<style scoped src="./operations.css"></style>
