<template>
  <div class="operations-page page-shell page-shell--workspace ops-page">
    <header class="ops-hero">
      <div class="ops-hero-copy">
        <span class="ops-eyebrow">系统工作台</span>
        <h1>运营总览</h1>
        <p>一眼看获取闭环是否健康。需要动手时，点指标直接跳到对应操作。</p>
      </div>
      <div class="ops-hero-stats" aria-label="首要运营指标">
        <button class="ops-stat" :class="{ urgent: candidate.candidate > 0 }" type="button" @click="goCandidates()">
          <strong>{{ candidate.candidate ?? '—' }}</strong>
          <span>待确认候选</span>
          <small>可批准 {{ candidate.ready || 0 }} · 待补磁力 {{ candidate.needs_magnet || 0 }}</small>
        </button>
        <button class="ops-stat" type="button" @click="goSchedulerConsole">
          <strong>{{ schedulerJobs.length || '—' }}</strong>
          <span>调度作业</span>
          <small>{{ schedulerEnabled ? '调度已启用' : '调度未启用' }}</small>
        </button>
        <button class="ops-stat" :class="{ urgent: healthDegraded }" type="button" @click="onHealthStat">
          <strong>{{ healthStatusText }}</strong>
          <span>系统健康</span>
          <small>{{ healthWarningCount ? `${healthWarningCount} 项需检查` : '全部正常' }}</small>
        </button>
        <button class="ops-stat" type="button" @click="goCachePurge">
          <strong>{{ cacheHitRate }}</strong>
          <span>缓存命中率</span>
          <small>活跃 {{ cacheActiveEntries }} · {{ cacheBackend }}</small>
        </button>
      </div>
    </header>

    <!-- 系统健康 -->
    <section ref="healthPanel" class="ops-panel" aria-label="系统健康">
      <div class="ops-panel-head">
        <div>
          <h2>系统健康</h2>
          <p>{{ healthError ? healthError : '初始化、数据库、来源与调度的就绪状态。异常项可点开直达配置。' }}</p>
        </div>
        <div class="ops-panel-actions">
          <button class="btn btn-ghost btn-sm" type="button" @click="$router.push('/settings')">配置中心</button>
          <button class="btn btn-ghost btn-sm" type="button" @click="$router.push('/logs')">运行日志</button>
        </div>
      </div>
      <div class="ops-grid">
        <component
          :is="row.jump ? 'button' : 'div'"
          v-for="row in healthRows"
          :key="row.key"
          class="ops-cell"
          :class="{ warning: row.warning }"
          :type="row.jump ? 'button' : undefined"
          @click="row.jump && confirmJumpSettings(row)"
        >
          <span>{{ row.label }}</span>
          <strong>{{ row.value }}</strong>
          <small v-if="row.hint">{{ row.hint }}</small>
        </component>
      </div>
    </section>

    <!-- 候选自动化 -->
    <section class="ops-panel" aria-label="候选自动化">
      <div class="ops-panel-head">
        <div>
          <h2>候选自动化</h2>
          <p>{{ candidateSummaryText }}</p>
        </div>
        <div class="ops-panel-actions">
          <button class="btn btn-ghost btn-sm" type="button" @click="goCandidates()">候选队列</button>
        </div>
      </div>
      <div class="ops-grid">
        <button class="ops-cell" type="button" @click="goCandidates">
          <span>待确认候选</span><strong>{{ candidate.candidate || 0 }}</strong>
        </button>
        <button class="ops-cell" type="button" @click="goCandidates({ needs_magnet: '0' })">
          <span>可批准</span><strong>{{ candidate.ready || 0 }}</strong>
        </button>
        <button class="ops-cell" type="button" @click="goCandidates({ needs_magnet: '1' })">
          <span>待补磁力</span><strong>{{ candidate.needs_magnet || 0 }}</strong>
        </button>
        <div class="ops-cell">
          <span>自动处理</span>
          <strong>{{ schedulerEnabled ? '已调度' : '未调度' }}</strong>
          <small>{{ candidateNextRunText }}</small>
        </div>
      </div>
    </section>

    <!-- 调度管道（只读，点跳系统作业） -->
    <section class="ops-panel" aria-label="调度管道">
      <div class="ops-panel-head">
        <div>
          <h2>调度管道</h2>
          <p>各定时作业的下次运行与上次结果。需要立即运行请进入系统作业。</p>
        </div>
        <div class="ops-panel-actions">
          <button class="btn btn-primary btn-sm" type="button" @click="goSchedulerConsole">去系统作业 →</button>
        </div>
      </div>
      <div v-if="schedulerJobs.length" class="ops-grid">
        <button
          v-for="job in schedulerJobs"
          :key="job.id"
          class="ops-cell"
          type="button"
          @click="confirmRunJob(job)"
        >
          <span>{{ job.name || job.id }}</span>
          <strong>
            <span class="ops-pill" :class="pillClass(job.last_status)">{{ pillText(job.last_status) }}</span>
          </strong>
          <small>下次 {{ formatTime(job.next_run_time) || '未计划' }}</small>
        </button>
      </div>
      <p v-else class="ops-empty">调度未启用，或暂无调度作业。</p>
    </section>

    <!-- 缓存诊断（只读） -->
    <section class="ops-panel" aria-label="缓存诊断">
      <div class="ops-panel-head">
        <div>
          <h2>缓存诊断</h2>
          <p>{{ cacheError ? cacheError : '响应缓存命中率与条目。清理操作在系统作业。' }}</p>
        </div>
        <div class="ops-panel-actions">
          <button class="btn btn-ghost btn-sm" type="button" @click="goCachePurge">前往清理 →</button>
        </div>
      </div>
      <div class="ops-grid">
        <div class="ops-cell"><span>响应命中率</span><strong>{{ cacheHitRate }}</strong></div>
        <div class="ops-cell"><span>活跃条目</span><strong>{{ cacheActiveEntries }}</strong></div>
        <div class="ops-cell"><span>总条目</span><strong>{{ cacheStats?.total_entries ?? 0 }}</strong></div>
        <div class="ops-cell"><span>后端</span><strong>{{ cacheBackend }}</strong></div>
      </div>
    </section>
  </div>
</template>

<script>
import api from '../api'
import { requestConfirm } from '../utils/confirmDialog'

export default {
  name: 'Operations',
  data() {
    return {
      health: null,
      candidate: {},
      schedulerJobs: [],
      cacheStats: null,
      healthError: '',
      cacheError: '',
    }
  },
  computed: {
    schedulerEnabled() {
      return Boolean(this.health?.scheduler?.effective_enabled)
    },
    healthRows() {
      const h = this.health || {}
      const dl = h.downloaders || {}
      const src = h.sources || {}
      const jav = h.javinfo || {}
      const db = h.database || {}
      const cache = h.cache || {}
      const sch = h.scheduler || {}
      return [
        { key: 'config', label: '配置', value: h.config?.loaded ? '已加载' : (h.config?.error || '未加载'), warning: !h.config?.loaded },
        { key: 'database', label: '数据库', value: db.connectable ? (db.backend || 'postgres') : (db.error || '不可连接'), warning: db.connectable === false, jump: true },
        { key: 'javinfo', label: 'JavInfo', value: this.javinfoText(jav), warning: !jav.api_url_configured || jav.legacy || jav.reachable === false, jump: true },
        { key: 'cache', label: '缓存', value: cache.error ? cache.error : `${cache.backend || 'unknown'} · ${cache.active_entries || 0}/${cache.total_entries || 0}`, warning: Boolean(cache.error) },
        { key: 'downloaders', label: '默认下载器', value: dl.error ? dl.error : `${dl.default_id || '未设置'} · ${dl.available || 0}/${dl.registered || 0}`, warning: dl.default_available === false, jump: true },
        { key: 'sources', label: '磁力源', value: src.error ? src.error : `${src.available || 0}/${src.registered || 0} 可用`, warning: src.available === false || Boolean(src.latest_attempt_error), jump: true },
        { key: 'scheduler', label: '调度有效性', value: sch.effective_enabled ? '已启用' : (sch.disabled_reason || '未启用'), warning: sch.effective_enabled === false },
      ]
    },
    healthWarningCount() {
      return this.healthRows.filter(r => r.warning).length
    },
    healthDegraded() {
      return this.health ? (this.health.status !== 'ok' || this.healthWarningCount > 0) : false
    },
    healthStatusText() {
      if (this.healthError) return '不可用'
      if (!this.health) return '—'
      return this.healthDegraded ? '需检查' : '正常'
    },
    candidateSummaryText() {
      return `候选 ${this.candidate.candidate || 0} · 可批准 ${this.candidate.ready || 0} · 待补磁力 ${this.candidate.needs_magnet || 0}`
    },
    candidateNextRunText() {
      const job = this.schedulerJobs.find(j => j.id === 'candidate_auto_process')
      return job ? `下次 ${this.formatTime(job.next_run_time) || '未计划'}` : '手动策略'
    },
    cacheHitRate() {
      const m = this.cacheStats?.response || this.cacheStats || {}
      const hits = Number(m.hits || 0)
      const total = hits + Number(m.misses || 0)
      if (!total) return '—'
      return `${Math.round((hits / total) * 100)}%`
    },
    cacheActiveEntries() {
      return this.cacheStats?.active_entries ?? this.cacheStats?.response?.active_entries ?? 0
    },
    cacheBackend() {
      return this.cacheStats?.backend || this.cacheStats?.response?.backend || 'unknown'
    },
  },
  mounted() {
    this.loadAll()
  },
  methods: {
    async loadAll() {
      const [healthResp, candResp, jobsResp, cacheResp] = await Promise.allSettled([
        api.readiness(),
        api.getDownloadCandidateSummary(),
        api.getSchedulerJobs(),
        api.getCacheStats(),
      ])
      if (healthResp.status === 'fulfilled') this.health = healthResp.value.data
      else this.healthError = this.errText(healthResp.reason)
      if (candResp.status === 'fulfilled') this.candidate = candResp.value.data || {}
      if (jobsResp.status === 'fulfilled') this.schedulerJobs = Array.isArray(jobsResp.value.data) ? jobsResp.value.data : []
      if (cacheResp.status === 'fulfilled') this.cacheStats = cacheResp.value.data
      else this.cacheError = this.errText(cacheResp.reason)
    },
    javinfoText(jav) {
      if (!jav.api_url_configured) return '未配置'
      if (jav.legacy) return '旧端口配置'
      if (jav.reachable === false) return '不可达'
      return '已配置'
    },
    pillClass(status) {
      return { 'is-success': status === 'success', 'is-failed': status === 'failed', 'is-idle': !status }
    },
    pillText(status) {
      if (status === 'success') return '成功'
      if (status === 'failed') return '失败'
      return '未运行'
    },
    async confirmJumpSettings(row) {
      const ok = await requestConfirm({
        title: '前往配置中心',
        message: `「${row.label}」当前为：${row.value}。是否前往配置中心处理？`,
        confirmText: '前往配置',
        cancelText: '取消',
      })
      if (ok) this.$router.push('/settings')
    },
    async confirmRunJob(job) {
      const failed = job.last_status === 'failed'
      const ok = await requestConfirm({
        title: '系统作业',
        message: failed
          ? `「${job.name || job.id}」上次运行失败，是否前往系统作业立即重跑？`
          : `是否前往系统作业立即运行「${job.name || job.id}」？`,
        confirmText: '前往系统作业',
        cancelText: '取消',
        tone: failed ? 'warning' : 'default',
      })
      if (ok) this.$router.push({ path: '/system-jobs', query: { job: job.id } })
    },
    async goCachePurge() {
      const ok = await requestConfirm({
        title: '缓存清理',
        message: '是否前往系统作业清理缓存？',
        confirmText: '前往清理',
        cancelText: '取消',
      })
      if (ok) this.$router.push({ path: '/system-jobs', query: { job: 'cache' } })
    },
    async onHealthStat() {
      if (this.healthDegraded) {
        const ok = await requestConfirm({
          title: '系统状态',
          message: `检测到 ${this.healthWarningCount} 项需检查，是否前往配置中心？`,
          confirmText: '前往配置',
          cancelText: '稍后',
          tone: 'warning',
        })
        if (ok) this.$router.push('/settings')
        return
      }
      this.$refs.healthPanel?.scrollIntoView({ behavior: 'smooth', block: 'start' })
    },
    goSchedulerConsole() {
      this.$router.push('/system-jobs')
    },
    goCandidates(query = {}) {
      const extra = query && !(query instanceof Event) ? query : {}
      this.$router.push({ path: '/candidates', query: { status: 'candidate', ...extra } })
    },
    formatTime(value) {
      if (!value) return ''
      const date = new Date(value)
      if (Number.isNaN(date.getTime())) return value
      return `${date.getMonth() + 1}/${date.getDate()} ${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`
    },
    errText(reason) {
      return reason?.response?.data?.detail || reason?.message || '加载失败'
    },
  },
}
</script>

<style scoped src="../features/operations/operationsPanel.css"></style>
