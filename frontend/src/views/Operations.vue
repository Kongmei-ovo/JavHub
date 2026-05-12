<template>
  <div class="operations-page">
    <header class="operations-header">
      <div>
        <p class="eyebrow">Operations</p>
        <h1>运营总览</h1>
        <p>库存、映射、补全和下载候选的闭环状态。</p>
      </div>
      <div class="header-actions">
        <button class="btn btn-ghost" type="button" @click="$router.push('/settings')">策略设置</button>
        <button class="btn btn-primary" type="button" :disabled="loading" @click="loadOverview">
          {{ loading ? '刷新中...' : '刷新' }}
        </button>
      </div>
    </header>

    <div v-if="loading && !overview" class="loading-panel">加载中...</div>
    <div v-else-if="error" class="empty-panel">
      <h2>总览加载失败</h2>
      <p>{{ error }}</p>
      <button class="btn btn-primary" type="button" @click="loadOverview">重试</button>
    </div>

    <template v-else-if="overview">
      <section class="policy-strip">
        <div>
          <span>当前策略</span>
          <strong>{{ policyLabel(overview.automation?.download_policy) }}</strong>
        </div>
        <div>
          <span>允许来源</span>
          <strong>{{ sourceListLabel(overview.automation?.candidate_sources) }}</strong>
        </div>
        <div>
          <span>自动处理间隔</span>
          <strong>{{ overview.automation?.auto_process_interval_minutes || 0 }} 分钟</strong>
        </div>
      </section>

      <section class="metric-grid">
        <button class="metric-card" type="button" @click="$router.push('/inventory')">
          <span>{{ overview.snapshot?.actor_count || 0 }}</span>
          <strong>快照演员</strong>
          <small>{{ overview.snapshot?.snapshot_key || '尚未采集' }}</small>
        </button>
        <button class="metric-card" type="button" @click="$router.push('/normalize')">
          <span>{{ coverageText }}</span>
          <strong>映射覆盖率</strong>
          <small>
            未映射 {{ overview.mapping?.unmapped || 0 }} · 待审核 {{ overview.mapping?.candidate || 0 }}
            · {{ overview.mapping?.auto_match?.auto_match_after_collect ? '采集后自动匹配' : '手动匹配' }}
          </small>
        </button>
        <button class="metric-card urgent" type="button" @click="$router.push('/inventory')">
          <span>{{ overview.missing?.total || 0 }}</span>
          <strong>库存缺口</strong>
          <small>由库存对比确认</small>
        </button>
        <button class="metric-card" type="button" @click="goCandidates({ status: 'candidate' })">
          <span>{{ overview.candidates?.candidate || 0 }}</span>
          <strong>待确认候选</strong>
          <small>可批准 {{ overview.candidates?.ready || 0 }} · 待补磁力 {{ overview.candidates?.needs_magnet || 0 }}</small>
        </button>
      </section>

      <section class="workflow-grid">
        <article class="workflow-panel">
          <div class="panel-head">
            <div>
              <p class="eyebrow">Queue</p>
              <h2>下载候选</h2>
            </div>
            <button class="btn btn-ghost btn-sm" type="button" @click="goCandidates({ status: 'candidate' })">打开队列</button>
          </div>
          <div class="source-bars">
            <button
              v-for="source in candidateSources"
              :key="source.key"
              class="source-row"
              type="button"
              @click="goCandidates({ status: 'candidate', source: source.key })"
            >
              <span>{{ source.label }}</span>
              <strong>{{ source.count }}</strong>
            </button>
          </div>
          <div class="quick-actions">
            <button class="btn btn-ghost" type="button" @click="goCandidates({ status: 'candidate', needs_magnet: true })">处理待补磁力</button>
            <button class="btn btn-primary" type="button" @click="goCandidates({ status: 'candidate', needs_magnet: false })">处理可批准</button>
          </div>
        </article>

        <article class="workflow-panel">
          <div class="panel-head">
            <div>
              <p class="eyebrow">Inventory</p>
              <h2>库存任务</h2>
            </div>
            <button class="btn btn-ghost btn-sm" type="button" @click="$router.push('/inventory')">库存对比</button>
          </div>
          <div class="job-summary">
            <span>运行中 {{ overview.inventory_jobs?.running || 0 }}</span>
            <span>失败 {{ overview.inventory_jobs?.failed || 0 }}</span>
          </div>
          <div class="job-list">
            <div v-for="job in recentJobs" :key="job.id" class="job-row">
              <strong>{{ job.job_type }}</strong>
              <span>{{ job.status }} · {{ formatTime(job.created_at) }}</span>
            </div>
            <small v-if="!recentJobs.length">暂无作业记录</small>
          </div>
        </article>

        <article class="workflow-panel">
          <div class="panel-head">
            <div>
              <p class="eyebrow">Mapping</p>
              <h2>演员映射</h2>
            </div>
            <button class="btn btn-ghost btn-sm" type="button" @click="$router.push('/normalize')">打开映射</button>
          </div>
          <div class="automation-status">
            <div>
              <span>自动匹配</span>
              <strong>{{ overview.mapping?.auto_match?.auto_match_after_collect ? '采集后执行' : '手动执行' }}</strong>
            </div>
            <div>
              <span>确认策略</span>
              <strong>保守唯一</strong>
            </div>
          </div>
          <div class="mapping-actions">
            <button class="source-row" type="button" @click="$router.push('/normalize')">
              <span>待审核候选</span>
              <strong>{{ overview.mapping?.candidate || 0 }}</strong>
            </button>
            <button class="source-row" type="button" @click="$router.push('/normalize')">
              <span>未映射演员</span>
              <strong>{{ overview.mapping?.unmapped || 0 }}</strong>
            </button>
          </div>
        </article>

        <article class="workflow-panel">
          <div class="panel-head">
            <div>
              <p class="eyebrow">Supplement</p>
              <h2>补全状态</h2>
            </div>
            <button class="btn btn-ghost btn-sm" type="button" @click="$router.push('/supplement')">补全管理</button>
          </div>
          <div v-if="overview.supplement?.available" class="supplement-stats">
            <div><strong>{{ overview.supplement.queued || 0 }}</strong><span>排队</span></div>
            <div><strong>{{ overview.supplement.running || 0 }}</strong><span>运行</span></div>
            <div><strong>{{ overview.supplement.failed || 0 }}</strong><span>失败</span></div>
          </div>
          <p v-else class="muted">补全服务暂不可用：{{ overview.supplement?.error || '未连接' }}</p>
        </article>

        <article class="workflow-panel">
          <div class="panel-head">
            <div>
              <p class="eyebrow">Missing</p>
              <h2>缺口演员</h2>
            </div>
          </div>
          <div class="missing-list">
            <button
              v-for="actor in overview.missing?.top_actresses || []"
              :key="actor.actress_id"
              class="missing-row"
              type="button"
              @click="$router.push(`/inventory/actors/${actor.actress_id}`)"
            >
              <span>{{ actor.actress_name || `ID ${actor.actress_id}` }}</span>
              <strong>{{ actor.missing_count }}</strong>
            </button>
            <small v-if="!(overview.missing?.top_actresses || []).length">暂无缺口记录</small>
          </div>
        </article>

        <article class="workflow-panel">
          <div class="panel-head">
            <div>
              <p class="eyebrow">Automation</p>
              <h2>最近候选处理</h2>
            </div>
            <div class="panel-actions">
              <button class="btn btn-ghost btn-sm" type="button" @click="goCandidates({ status: 'candidate' })">候选队列</button>
              <button class="btn btn-primary btn-sm" type="button" :disabled="processingNow" @click="runCandidateProcessingNow">
                {{ processingNow ? '处理中...' : '立即运行' }}
              </button>
            </div>
          </div>
          <div class="automation-status">
            <div>
              <span>调度</span>
              <strong>{{ scheduleStatusLabel }}</strong>
            </div>
            <div>
              <span>下一次</span>
              <strong>{{ formatTime(candidateSchedule.next_run_time) || '未计划' }}</strong>
            </div>
          </div>
          <div class="run-list">
            <div v-for="run in recentRuns" :key="run.id" class="run-row">
              <div>
                <strong>{{ policyLabel(run.policy) }}</strong>
                <span>{{ run.trigger_source }} · {{ formatTime(run.created_at) }}</span>
              </div>
              <small>处理 {{ run.total || 0 }} · 下发 {{ run.sent || 0 }} · 失败 {{ run.failed || 0 }} · 跳过 {{ run.skipped || 0 }}</small>
            </div>
            <small v-if="!recentRuns.length">暂无候选处理记录</small>
          </div>
        </article>
      </section>
    </template>
  </div>
</template>

<script>
import api from '../api'

export default {
  name: 'Operations',
  data() {
    return {
      overview: null,
      loading: false,
      processingNow: false,
      error: '',
    }
  },
  computed: {
    coverageText() {
      return `${Math.round((this.overview?.mapping?.coverage || 0) * 100)}%`
    },
    recentJobs() {
      return this.overview?.inventory_jobs?.recent || []
    },
    recentRuns() {
      return this.overview?.candidate_runs?.recent || []
    },
    candidateSchedule() {
      return this.overview?.candidate_runs?.schedule || {}
    },
    scheduleStatusLabel() {
      if (this.candidateSchedule.running) return '运行中'
      if (this.candidateSchedule.enabled) return '已启用'
      return '未启用'
    },
    candidateSources() {
      const counts = this.overview?.candidates?.candidate_by_source || {}
      return [
        { key: 'subscription', label: '订阅发现', count: counts.subscription || 0 },
        { key: 'inventory', label: '库存发现', count: counts.inventory || 0 },
        { key: 'supplement', label: '补全发现', count: counts.supplement || 0 },
        { key: 'manual', label: '手动加入', count: counts.manual || 0 },
      ]
    },
  },
  mounted() {
    this.loadOverview()
  },
  methods: {
    async loadOverview() {
      this.loading = true
      this.error = ''
      try {
        const resp = await api.getOperationsOverview()
        this.overview = resp.data
      } catch (e) {
        this.error = e.response?.data?.detail || e.message || '加载失败'
      } finally {
        this.loading = false
      }
    },
    policyLabel(policy) {
      const map = { manual: '人工批准', rules: '规则自动', auto: '全自动' }
      return map[policy] || '人工批准'
    },
    sourceListLabel(sources = []) {
      if (!sources.length) return '全部'
      const labels = { subscription: '订阅', inventory: '库存', supplement: '补全', manual: '手动' }
      return sources.map(source => labels[source] || source).join(' / ')
    },
    async runCandidateProcessingNow() {
      if (this.processingNow) return
      this.processingNow = true
      try {
        const resp = await api.runCandidateProcessingNow()
        if (resp.data?.status === 'busy') {
          this.$message?.info?.('候选处理正在运行')
        } else {
          const counts = resp.data?.counts || {}
          this.$message?.success?.(`处理 ${resp.data?.total || 0} 个：下发 ${counts.sent || 0}，失败 ${counts.failed_downloader || 0}`)
        }
        await this.loadOverview()
      } catch (e) {
        console.error('Run candidate processing failed:', e)
      } finally {
        this.processingNow = false
      }
    },
    goCandidates({ status = 'candidate', source = '', needs_magnet = null } = {}) {
      const query = { tab: 'candidates' }
      if (status) query.status = status
      if (source) query.source = source
      if (needs_magnet === true) query.needs_magnet = '1'
      if (needs_magnet === false) query.needs_magnet = '0'
      this.$router.push({ path: '/downloads', query })
    },
    formatTime(value) {
      if (!value) return ''
      const date = new Date(value)
      if (Number.isNaN(date.getTime())) return value
      return `${date.getMonth() + 1}/${date.getDate()} ${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`
    },
  },
}
</script>

<style scoped>
.operations-page {
  max-width: 1360px;
  margin: 0 auto;
  padding: 28px;
}
.operations-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 20px;
}
.operations-header h1 {
  margin: 0;
  font-size: 30px;
}
.operations-header p {
  margin: 6px 0 0;
  color: var(--text-secondary);
}
.header-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
.policy-strip {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
  margin-bottom: 18px;
}
.policy-strip > div,
.metric-card,
.workflow-panel,
.loading-panel,
.empty-panel {
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  background: var(--bg-card);
}
.policy-strip > div {
  padding: 12px 14px;
}
.policy-strip span,
.metric-card small,
.muted {
  color: var(--text-secondary);
  font-size: 12px;
}
.policy-strip strong {
  display: block;
  margin-top: 3px;
  color: var(--text-primary);
}
.metric-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 18px;
}
.metric-card {
  padding: 18px;
  text-align: left;
  color: var(--text-primary);
  cursor: pointer;
}
.metric-card:hover {
  border-color: var(--accent);
}
.metric-card span {
  display: block;
  font-family: var(--font-mono);
  font-size: 30px;
  font-weight: 700;
}
.metric-card strong {
  display: block;
  margin: 6px 0;
}
.metric-card.urgent span {
  color: #fa8c16;
}
.workflow-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}
.workflow-panel {
  padding: 16px;
}
.panel-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}
.panel-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  justify-content: flex-end;
}
.panel-head h2 {
  margin: 0;
  font-size: 18px;
}
.source-bars,
.mapping-actions,
.job-list,
.missing-list,
.run-list {
  display: grid;
  gap: 8px;
}
.source-row,
.missing-row,
.job-row,
.run-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 10px 12px;
  min-height: 44px;
  background: var(--bg-secondary);
  color: var(--text-primary);
}
.source-row,
.missing-row {
  cursor: pointer;
}
.source-row:hover,
.missing-row:hover {
  border-color: var(--accent);
}
.quick-actions,
.job-summary,
.automation-status,
.supplement-stats {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-top: 12px;
}
.automation-status {
  margin: 0 0 12px;
}
.automation-status > div {
  flex: 1;
  min-width: 120px;
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 10px;
  background: var(--bg-secondary);
}
.automation-status span {
  display: block;
  color: var(--text-secondary);
  font-size: 11px;
}
.automation-status strong {
  display: block;
  margin-top: 4px;
  color: var(--text-primary);
  font-size: 13px;
}
.supplement-stats > div {
  flex: 1;
  min-width: 90px;
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 10px;
  background: var(--bg-secondary);
}
.supplement-stats strong {
  display: block;
  font-size: 22px;
}
.supplement-stats span,
.job-row span,
.run-row span,
.run-row small {
  color: var(--text-secondary);
  font-size: 12px;
}
.run-row {
  align-items: flex-start;
}
.run-row > div {
  display: flex;
  flex-direction: column;
  gap: 3px;
}
.loading-panel,
.empty-panel {
  padding: 30px;
  text-align: center;
}
.eyebrow {
  margin: 0 0 4px;
  color: var(--accent);
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.08em;
}
@media (max-width: 900px) {
  .operations-page { padding: 18px; }
  .operations-header,
  .panel-head { flex-direction: column; }
  .panel-actions {
    justify-content: flex-start;
  }
  .operations-header .btn,
  .empty-panel .btn {
    min-height: 44px;
  }
  .policy-strip,
  .metric-grid,
  .workflow-grid { grid-template-columns: 1fr; }
}
</style>
