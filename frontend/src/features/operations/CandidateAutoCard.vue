<template>
  <article class="workbench-panel candidate-auto-card" aria-label="候选自动化">
    <div class="panel-head">
      <div>
        <h2>待处理队列</h2>
        <p>{{ loading ? '候选状态加载中。' : candidateSummary }}</p>
      </div>
      <div class="panel-actions">
        <button class="btn btn-ghost btn-sm" type="button" @click="goCandidates({ status: 'candidate' })">候选队列</button>
        <button class="btn btn-primary btn-sm" type="button" :disabled="processingNow" @click="runCandidateProcessingNow">
          {{ processingNow ? '处理中...' : '立即运行' }}
        </button>
      </div>
    </div>

    <AppleSkeleton v-if="loading && !overview" class="loading-panel console-state" variant="list" :items="5" label="候选自动化加载中" />
    <AppleErrorState v-else-if="error && !overview" class="empty-panel console-state" title="候选自动化加载失败" :description="error" next-step="可以刷新候选自动化卡片，或直接打开下载候选队列。" retry-label="重试" secondary-action-label="候选队列" source-label="Download Candidates API" @retry="loadOverview" @secondary-action="goCandidates({ status: 'candidate' })" />
    <AppleEmptyState v-else-if="!overview" class="empty-panel console-state" title="暂无候选自动化状态" description="后端还没有返回候选、缺口和调度状态。" next-step="可以打开下载候选队列，或稍后刷新运营卡片。" action-label="候选队列" density="compact" @action="goCandidates({ status: 'candidate' })" />
    <template v-else>
      <div class="queue-overview">
        <button class="queue-focus" type="button" @click="goCandidates({ status: 'candidate' })">
          <span>待确认候选</span>
          <strong>{{ candidates.candidate || 0 }}</strong>
          <small>可批准 {{ candidates.ready || 0 }} · 待补磁力 {{ candidates.needs_magnet || 0 }}</small>
        </button>
        <div class="quick-actions">
          <button class="btn btn-ghost btn-sm" type="button" @click="goCandidates({ status: 'candidate', needs_magnet: true })">处理待补磁力</button>
          <button class="btn btn-primary btn-sm" type="button" @click="goCandidates({ status: 'candidate', needs_magnet: false })">处理可批准</button>
        </div>
        <p v-if="error" class="muted cache-error">{{ error }}</p>
      </div>

      <div class="queue-grid">
        <div class="list-block">
          <div class="block-head">
            <h3>候选来源</h3>
            <span>{{ sourceListLabel(overview?.automation?.candidate_sources) }}</span>
          </div>
          <div class="compact-list">
            <button
              v-for="source in candidateSources"
              :key="source.key"
              class="compact-row"
              type="button"
              @click="goCandidates({ status: 'candidate', source: source.key })"
            >
              <span>{{ source.label }}</span>
              <strong>{{ source.count }}</strong>
            </button>
          </div>
        </div>

        <div class="list-block">
          <div class="block-head">
            <h3>缺口演员</h3>
            <button type="button" @click="goLibraryOrganize('inventory')">片库整理</button>
          </div>
          <div class="compact-list">
            <button
              v-for="actor in topMissingActors"
              :key="actor.actress_id"
              class="compact-row"
              type="button"
              @click="goInventoryActor(actor.actress_id)"
            >
              <span>{{ actor.actress_name || `编号 ${actor.actress_id}` }}</span>
              <strong>{{ actor.missing_count }}</strong>
            </button>
            <small v-if="!topMissingActors.length" class="empty-line">暂无缺口记录</small>
          </div>
        </div>
      </div>

      <article class="workbench-panel automation-summary">
        <div class="panel-head">
          <div>
            <h2>自动化摘要</h2>
            <p>{{ candidateSchedule.disabled_reason || '策略、调度和映射保护。' }}</p>
          </div>
          <button class="btn btn-ghost btn-sm" type="button" @click="$router.push({ path: '/operations', query: { tab: 'system' } })">系统状态</button>
        </div>
        <div class="state-grid compact-state-grid">
          <button class="state-item" type="button" @click="$router.push('/settings')">
            <span>当前策略</span>
            <strong>{{ policyLabel(overview?.automation?.download_policy) }}</strong>
          </button>
          <div class="state-item"><span>调度</span><strong>{{ scheduleStatusLabel }}</strong></div>
          <button class="state-item" type="button" @click="goLibraryOrganize('mapping')">
            <span>自动匹配</span>
            <strong>{{ overview?.mapping?.auto_match?.auto_match_after_collect ? '采集后自动匹配' : '手动匹配' }}</strong>
          </button>
          <div class="state-item"><span>下一次</span><strong>{{ formatTime(candidateSchedule.next_run_time) || '未计划' }}</strong></div>
        </div>
      </article>

      <article class="workbench-panel action-map-panel" aria-label="自动化工作台">
        <div class="panel-head">
          <div>
            <h2>自动化工作台</h2>
            <p>工作台路径把采集、映射、补全、下载和运行日志串起来。</p>
          </div>
          <button class="btn btn-ghost btn-sm" type="button" :disabled="refreshingMissing" @click="refreshMissingCache">
            {{ refreshingMissing ? '刷新中...' : '刷新缺失缓存' }}
          </button>
        </div>
        <div class="action-grid action-grid-compact">
          <button v-for="action in workbenchActions" :key="action.key" class="action-card" type="button" @click="goWorkbenchAction(action)">
            <span>{{ action.label }}</span>
            <strong>{{ action.title }}</strong>
            <small>{{ action.hint }}</small>
          </button>
        </div>
      </article>

      <article class="workbench-panel history-panel">
        <div class="panel-head">
          <div>
            <h2>最近候选处理</h2>
            <p>调度 {{ scheduleStatusLabel }} · 下一次 {{ formatTime(candidateSchedule.next_run_time) || '未计划' }}</p>
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
          <small v-if="!recentRuns.length" class="empty-line">暂无候选处理记录</small>
        </div>
      </article>
    </template>
  </article>
</template>

<script>
import api from '../../api'
import AppleSkeleton from '../../components/AppleSkeleton.vue'
import AppleEmptyState from '../../components/AppleEmptyState.vue'
import AppleErrorState from '../../components/AppleErrorState.vue'

export default {
  name: 'CandidateAutoCard',
  components: { AppleSkeleton, AppleEmptyState, AppleErrorState },
  data() {
    return {
      overview: null,
      loading: false,
      error: '',
      processingNow: false,
      refreshingMissing: false,
    }
  },
  computed: {
    candidates() {
      return this.overview?.candidates || {}
    },
    candidateSummary() {
      return `候选 ${this.candidates.candidate || 0} · 可批准 ${this.candidates.ready || 0} · 待补磁力 ${this.candidates.needs_magnet || 0}`
    },
    candidateSchedule() {
      return this.overview?.candidate_runs?.schedule || {}
    },
    scheduleStatusLabel() {
      if (this.candidateSchedule.running) return '运行中'
      if (this.candidateSchedule.effective_enabled) return '已启用'
      if (this.candidateSchedule.disabled_reason === 'manual_policy') return '手动策略'
      if (this.candidateSchedule.enabled) return '已配置未生效'
      return '未启用'
    },
    candidateSources() {
      const counts = this.candidates.candidate_by_source || {}
      return [
        { key: 'subscription', label: '订阅发现', count: counts.subscription || 0 },
        { key: 'inventory', label: '库存发现', count: counts.inventory || 0 },
        { key: 'supplement', label: '补全发现', count: counts.supplement || 0 },
        { key: 'manual', label: '手动加入', count: counts.manual || 0 },
      ]
    },
    topMissingActors() {
      return (this.overview?.missing?.top_actresses || []).slice(0, 6)
    },
    recentRuns() {
      return this.overview?.candidate_runs?.recent || []
    },
    workbenchActions() {
      return [
        { key: 'collect', label: '1', title: '采集 Emby', hint: '拉取本地库快照', path: '/library-organize', query: { tab: 'inventory' } },
        { key: 'compare', label: '2', title: '全量对比', hint: '生成缺失与候选', path: '/library-organize', query: { tab: 'check' } },
        { key: 'mapping', label: '3', title: '映射审核', hint: `${this.overview?.mapping?.candidate || 0} 个待审`, path: '/library-organize', query: { tab: 'mapping' } },
        { key: 'sources', label: '4', title: '补全来源诊断', hint: 'Provider smoke 与预算', path: '/supplement', query: { tab: 'sources' } },
        { key: 'candidates', label: '5', title: '下载候选', hint: `${this.candidates.candidate || 0} 个候选`, path: '/downloads', query: { tab: 'candidates', status: 'candidate' } },
        { key: 'downloaders', label: '6', title: '下载源', hint: '默认下载器与连通性', path: '/downloads', query: { tab: 'downloaders' } },
        { key: 'activity', label: '7', title: '运行日志', hint: '日志与通知记录', path: '/logs' },
        { key: 'settings', label: '8', title: '初始化设置', hint: 'JavInfo/配置导入', path: '/settings', query: { tab: 'javinfo-import' } },
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
        const [candidateResp, runsResp, missingResp, configResp, mappingResp, healthResp] = await Promise.allSettled([
          api.getDownloadCandidateSummary({ status: 'candidate', include_sources: true }),
          api.listDownloadCandidateRuns(5),
          api.getMissingActresses(),
          api.getConfig(),
          api.getActorMappingSummary(),
          api.readiness(),
        ])
        if (candidateResp.status === 'rejected') {
          throw candidateResp.reason
        }
        const cfg = configResp.status === 'fulfilled' ? configResp.value.data : {}
        const missing = missingResp.status === 'fulfilled' ? missingResp.value.data : {}
        const mapping = mappingResp.status === 'fulfilled' ? mappingResp.value.data : {}
        const health = healthResp.status === 'fulfilled' ? healthResp.value.data : {}
        this.overview = {
          automation: cfg.automation || {},
          mapping: { ...mapping, auto_match: cfg.actor_mapping || {} },
          missing: {
            total: Number(missing.total || 0),
            top_actresses: missing.data || missing.top_actresses || [],
          },
          candidates: candidateResp.value.data || {},
          candidate_runs: {
            recent: runsResp.status === 'fulfilled' ? (runsResp.value.data?.data || []) : [],
            schedule: health.scheduler || {},
          },
        }
        const softErrors = [
          runsResp,
          missingResp,
          configResp,
          mappingResp,
          healthResp,
        ].filter(resp => resp.status === 'rejected').map(resp => resp.reason?.response?.data?.detail || resp.reason?.message || '加载失败')
        this.error = softErrors[0] || ''
      } catch (e) {
        this.error = e.response?.data?.detail || e.message || '加载失败'
      } finally {
        this.loading = false
      }
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
    async refreshMissingCache() {
      if (this.refreshingMissing) return
      this.refreshingMissing = true
      try {
        await api.refreshMissingCache()
        this.$message?.success?.('缺失缓存已刷新')
        await this.loadOverview()
      } catch (e) {
        console.error('Refresh missing cache failed:', e)
      } finally {
        this.refreshingMissing = false
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
    formatTime(value) {
      if (!value) return ''
      const date = new Date(value)
      if (Number.isNaN(date.getTime())) return value
      return `${date.getMonth() + 1}/${date.getDate()} ${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`
    },
    goWorkbenchAction(action) {
      this.$router.push({ path: action.path, query: action.query || {} })
    },
    goCandidates({ status = 'candidate', source = '', needs_magnet = null } = {}) {
      const query = { tab: 'candidates' }
      if (status) query.status = status
      if (source) query.source = source
      if (needs_magnet === true) query.needs_magnet = '1'
      if (needs_magnet === false) query.needs_magnet = '0'
      this.$router.push({ path: '/downloads', query })
    },
    goLibraryOrganize(tab = 'inventory') {
      this.$router.push({ path: '/library-organize', query: { tab } })
    },
    goInventoryActor(actorId) {
      this.$router.push({ path: '/library-organize', query: { tab: 'inventory', actor_id: actorId } })
    },
  },
}
</script>

<style scoped src="./operations.css"></style>
