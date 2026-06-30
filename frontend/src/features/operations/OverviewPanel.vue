<template>
  <div class="ops-page">
    <!-- 概览条：系统状态 + 待处理告警 + 全局动作，一行收口，不再用四张高卡复述下方面板 -->
    <header class="ops-summary" :class="summaryTone">
      <button class="ops-summary-status" type="button" @click="onHealthStat">
        <span class="ops-dot" :class="summaryTone"></span>
        <span class="ops-summary-state">{{ healthStatusText }}</span>
        <span class="ops-summary-sub">{{ summaryHeadline }}</span>
      </button>
      <button v-if="hasRecentAlerts" class="ops-summary-alert" type="button" @click="goLogsFiltered">
        近 24h
        <strong v-if="recentErrorCount" class="is-bad">{{ recentErrorCount }} 错误</strong>
        <strong v-if="recentWarningCount" class="is-warn">{{ recentWarningCount }} 警告</strong>
      </button>
      <div class="ops-summary-actions">
        <button class="btn btn-ghost btn-sm" type="button" @click="goLogs">运行日志</button>
        <button class="btn btn-ghost btn-sm" type="button" @click="$router.push('/settings')">配置中心</button>
      </div>
    </header>

    <!-- 系统健康：扁平状态清单，绿点保持安静，黄/红跳出，点开直达配置 -->
    <section ref="healthPanel" class="ops-panel" aria-label="系统健康">
      <div class="ops-panel-head">
        <div>
          <h2>系统健康</h2>
          <p>{{ healthError || '各子系统就绪状态，异常项可点开直达配置。' }}</p>
        </div>
      </div>
      <div class="ops-statuslist">
        <component
          :is="row.jump ? 'button' : 'div'"
          v-for="row in healthRows"
          :key="row.key"
          class="ops-statusrow"
          :class="`is-${row.tone}`"
          :type="row.jump ? 'button' : undefined"
          @click="row.jump && confirmJumpSettings(row)"
        >
          <span class="ops-dot" :class="`is-${row.tone}`"></span>
          <span class="ops-statusrow-label">{{ row.label }}</span>
          <span class="ops-statusrow-value">
            <span class="ops-statusrow-state">{{ row.status }}</span>
            <span v-if="row.detail" class="ops-statusrow-detail">{{ row.detail }}</span>
          </span>
          <span v-if="row.jump" class="ops-chevron" aria-hidden="true">›</span>
        </component>
      </div>
    </section>

    <!-- 运营：候选 / 调度 / 缓存 合并为一卡三段，数据走内联指标条而非高卡 -->
    <section class="ops-panel ops-ops" aria-label="运营指标">
      <div class="ops-block">
        <div class="ops-block-head">
          <h3>候选自动化</h3>
          <button class="ops-link" type="button" @click="goCandidates()">候选队列 →</button>
        </div>
        <div class="ops-statbar">
          <button class="ops-stat-item" type="button" @click="goCandidates()">
            <strong>{{ candidate.candidate || 0 }}</strong><span>待确认</span>
          </button>
          <button class="ops-stat-item" type="button" @click="goCandidates({ needs_magnet: '0' })">
            <strong>{{ candidate.ready || 0 }}</strong><span>可批准</span>
          </button>
          <button
            class="ops-stat-item"
            :class="{ 'is-warn': (candidate.needs_magnet || 0) > 0 }"
            type="button"
            @click="goCandidates({ needs_magnet: '1' })"
          >
            <strong>{{ candidate.needs_magnet || 0 }}</strong><span>待补磁力</span>
          </button>
          <div class="ops-stat-item ops-stat-item--text">
            <strong :class="{ 'is-ok': schedulerEnabled }">{{ schedulerEnabled ? '已调度' : '未调度' }}</strong>
            <span>{{ candidateNextRunText }}</span>
          </div>
        </div>
      </div>

      <div class="ops-block">
        <div class="ops-block-head">
          <h3>调度管道</h3>
          <button class="ops-link" type="button" @click="goSchedulerConsole">系统作业 →</button>
        </div>
        <div v-if="schedulerJobs.length" class="ops-statuslist ops-statuslist--compact">
          <button
            v-for="job in schedulerJobs"
            :key="job.id"
            class="ops-statusrow"
            :class="`is-${jobTone(job.last_status)}`"
            type="button"
            @click="confirmRunJob(job)"
          >
            <span class="ops-dot" :class="`is-${jobTone(job.last_status)}`"></span>
            <span class="ops-statusrow-label">{{ job.name || job.id }}</span>
            <span class="ops-statusrow-value">
              <span class="ops-statusrow-state">{{ pillText(job.last_status) }}</span>
              <span class="ops-statusrow-detail">下次 {{ formatTime(job.next_run_time) || '未计划' }}</span>
            </span>
            <span class="ops-chevron" aria-hidden="true">›</span>
          </button>
        </div>
        <p v-else class="ops-empty">调度未启用，或暂无调度作业。</p>
      </div>

      <div class="ops-block">
        <div class="ops-block-head">
          <h3>缓存</h3>
          <button class="ops-link" type="button" @click="goCachePurge">清理 →</button>
        </div>
        <div class="ops-statbar">
          <div class="ops-stat-item"><strong>{{ cacheHitRate }}</strong><span>命中率</span></div>
          <div class="ops-stat-item"><strong>{{ cacheActiveEntries }}</strong><span>活跃条目</span></div>
          <div class="ops-stat-item"><strong>{{ cacheStats?.total_entries ?? 0 }}</strong><span>总条目</span></div>
          <div class="ops-stat-item ops-stat-item--text"><strong>{{ cacheBackend }}</strong><span>后端</span></div>
        </div>
        <p v-if="cacheError" class="ops-block-error">{{ cacheError }}</p>
      </div>
    </section>
  </div>
</template>

<script>
import api from '../../api'
import { requestConfirm } from '../../utils/confirmDialog'

export default {
  name: 'OverviewPanel',
  emits: ['summary'],
  data() {
    return {
      health: null,
      candidate: {},
      schedulerJobs: [],
      cacheStats: null,
      logCounts: { error: 0, warning: 0, info: 0 },
      healthError: '',
      cacheError: '',
      logSummaryError: '',
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
      // 每行拆成「状态词(tone+status) + 次要细节(detail，冗余则隐去)」，颜色一眼区分健康/需检查。
      const rows = [
        {
          key: 'config', label: '配置',
          ...(h.config?.loaded
            ? { tone: 'ok', status: '已加载', detail: '' }
            : { tone: 'bad', status: '未加载', detail: h.config?.error || '' }),
        },
        {
          key: 'database', label: '数据库', jump: true,
          ...(db.connectable
            ? { tone: 'ok', status: '正常', detail: db.backend || 'postgres' }
            : { tone: 'bad', status: '不可连接', detail: db.error || '' }),
        },
        { key: 'javinfo', label: 'JavInfo', jump: true, ...this.javinfoStatus(jav) },
        {
          key: 'cache', label: '缓存',
          ...(cache.error
            ? { tone: 'bad', status: '异常', detail: cache.error }
            : { tone: 'ok', status: '正常', detail: `${cache.backend || 'unknown'} · ${cache.active_entries || 0}/${cache.total_entries || 0}` }),
        },
        {
          key: 'downloaders', label: '默认下载器', jump: true,
          ...(dl.error
            ? { tone: 'bad', status: '异常', detail: dl.error }
            : {
                tone: dl.default_available === false ? 'warn' : 'ok',
                status: dl.default_available === false ? '默认离线' : '在线',
                detail: `${dl.default_id || '未设置'} · ${dl.available || 0}/${dl.registered || 0} 在线`,
              }),
        },
        {
          key: 'sources', label: '磁力源', jump: true,
          ...(src.error
            ? { tone: 'bad', status: '异常', detail: src.error }
            : {
                tone: (src.available === false || src.latest_attempt_error) ? 'warn' : 'ok',
                status: `${src.available || 0}/${src.registered || 0} 可用`,
                detail: src.latest_attempt_error ? '最近探测有误' : '',
              }),
        },
        {
          key: 'scheduler', label: '调度有效性',
          ...(sch.effective_enabled
            ? { tone: 'ok', status: '已启用', detail: '' }
            : { tone: 'warn', status: '未启用', detail: sch.disabled_reason || '' }),
        },
      ]
      return rows.map(r => ({ ...r, jump: r.jump || false, warning: r.tone !== 'ok' }))
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
    // 概览条主色：错误/异常→红，需检查/警告→黄，全绿→绿，未加载→中性
    healthWorstTone() {
      if (this.healthError) return 'bad'
      if (!this.health) return 'neutral'
      if (this.recentErrorCount > 0 || this.healthRows.some(r => r.tone === 'bad')) return 'bad'
      if (this.healthDegraded || this.recentWarningCount > 0) return 'warn'
      return 'ok'
    },
    summaryTone() {
      return `is-${this.healthWorstTone}`
    },
    summaryHeadline() {
      if (this.healthError) return '健康检查不可用'
      if (!this.health) return '加载中…'
      if (this.healthWarningCount) return `${this.healthWarningCount} 项需关注`
      return '所有子系统就绪'
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
    recentErrorCount() {
      return Number(this.logCounts?.error || 0)
    },
    recentWarningCount() {
      return Number(this.logCounts?.warning || 0)
    },
    hasRecentAlerts() {
      return this.recentErrorCount > 0 || this.recentWarningCount > 0
    },
  },
  mounted() {
    this.loadAll()
  },
  methods: {
    async loadAll() {
      const [healthResp, candResp, jobsResp, cacheResp, summaryResp] = await Promise.allSettled([
        api.readiness(),
        api.getDownloadCandidateSummary(),
        api.getSchedulerJobs(),
        api.getCacheStats(),
        api.getLogSummary(1440),
      ])
      if (healthResp.status === 'fulfilled') this.health = healthResp.value.data
      else this.healthError = this.errText(healthResp.reason)
      if (candResp.status === 'fulfilled') this.candidate = candResp.value.data || {}
      if (jobsResp.status === 'fulfilled') this.schedulerJobs = Array.isArray(jobsResp.value.data) ? jobsResp.value.data : []
      if (cacheResp.status === 'fulfilled') this.cacheStats = cacheResp.value.data
      else this.cacheError = this.errText(cacheResp.reason)
      if (summaryResp.status === 'fulfilled') this.logCounts = summaryResp.value.data?.counts || { error: 0, warning: 0, info: 0 }
      else this.logSummaryError = this.errText(summaryResp.reason)
      this.$emit('summary', {
        status: this.healthStatusText,
        degraded: this.healthDegraded || this.recentErrorCount > 0,
        errorCount: this.recentErrorCount,
      })
    },
    javinfoStatus(jav) {
      if (!jav.api_url_configured) return { tone: 'warn', status: '未配置', detail: '' }
      if (jav.legacy) return { tone: 'warn', status: '旧端口', detail: '建议迁移端口' }
      if (jav.reachable === false) return { tone: 'bad', status: '不可达', detail: '' }
      return { tone: 'ok', status: '已配置', detail: '' }
    },
    jobTone(status) {
      if (status === 'success') return 'ok'
      if (status === 'failed') return 'bad'
      return 'neutral'
    },
    pillText(status) {
      if (status === 'success') return '成功'
      if (status === 'failed') return '失败'
      return '未运行'
    },
    async confirmJumpSettings(row) {
      const detail = row.detail ? `（${row.detail}）` : ''
      const ok = await requestConfirm({
        title: '前往配置中心',
        message: `「${row.label}」当前为：${row.status}${detail}。是否前往配置中心处理？`,
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
    goLogs() {
      this.$router.push({ path: '/operations', query: { tab: 'logs' } })
    },
    goLogsFiltered() {
      const level = this.recentErrorCount > 0 ? 'ERROR' : this.recentWarningCount > 0 ? 'WARNING' : ''
      const query = { tab: 'logs' }
      if (level) query.level = level
      this.$router.push({ path: '/operations', query })
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

<style scoped src="./operationsPanel.css"></style>
