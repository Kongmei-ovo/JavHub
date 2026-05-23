<template>
  <div class="operations-page page-shell page-shell--workspace">
    <header class="operations-header operations-hero">
      <div class="header-copy">
        <span class="hero-eyebrow">系统工作台</span>
        <h1>运营总览</h1>
        <p>{{ operationsSummary }}</p>
      </div>
      <div class="hero-stat-grid" aria-label="首要运营指标">
        <button
          v-for="metric in statusMetrics"
          :key="metric.key"
          class="hero-stat"
          type="button"
          @click="openStatusMetric(metric.key)"
        >
          <strong>{{ metric.value }}</strong>
          <span>{{ metric.label }}</span>
        </button>
      </div>
      <div class="header-actions">
        <button class="btn btn-ghost btn-sm" type="button" @click="$router.push('/settings')">策略设置</button>
        <button class="btn btn-primary btn-sm" type="button" :disabled="loading" @click="loadOverview">
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
      <nav class="operations-segments apple-surface" aria-label="运营总览视图">
        <button
          v-for="segment in operationsSegments"
          :key="segment.key"
          type="button"
          :class="{ active: activeSegment === segment.key }"
          @click="setActiveSegment(segment.key)"
        >
          <span>{{ segment.label }}</span>
          <small>{{ segment.hint }}</small>
        </button>
      </nav>

      <section v-if="activeSegment === 'workbench'" class="operations-workbench priority-board" aria-label="处理">
        <article class="workbench-panel workbench-primary">
          <div class="panel-head">
            <div>
              <h2>待处理队列</h2>
              <p>候选、缺口和可执行动作放在首屏处理。</p>
            </div>
            <div class="panel-actions">
              <button class="btn btn-ghost btn-sm" type="button" @click="goCandidates({ status: 'candidate' })">候选队列</button>
              <button class="btn btn-primary btn-sm" type="button" :disabled="processingNow" @click="runCandidateProcessingNow">
                {{ processingNow ? '处理中...' : '立即运行' }}
              </button>
            </div>
          </div>

          <div class="queue-overview">
            <button class="queue-focus" type="button" @click="goCandidates({ status: 'candidate' })">
              <span>待确认候选</span>
              <strong>{{ overview.candidates?.candidate || 0 }}</strong>
              <small>可批准 {{ overview.candidates?.ready || 0 }} · 待补磁力 {{ overview.candidates?.needs_magnet || 0 }}</small>
            </button>
            <div class="quick-actions">
              <button class="btn btn-ghost btn-sm" type="button" @click="goCandidates({ status: 'candidate', needs_magnet: true })">处理待补磁力</button>
              <button class="btn btn-primary btn-sm" type="button" @click="goCandidates({ status: 'candidate', needs_magnet: false })">处理可批准</button>
            </div>
          </div>

          <div class="queue-grid">
            <div class="list-block">
              <div class="block-head">
                <h3>候选来源</h3>
                <span>{{ sourceListLabel(overview.automation?.candidate_sources) }}</span>
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
        </article>

        <aside class="workbench-side" aria-label="处理摘要">
          <article class="workbench-panel automation-summary">
            <div class="panel-head">
              <div>
                <h2>自动化摘要</h2>
                <p>{{ candidateSchedule.disabled_reason || '策略、调度和映射保护。' }}</p>
              </div>
              <button class="btn btn-ghost btn-sm" type="button" @click="setActiveSegment('system')">系统状态</button>
            </div>
            <div class="state-grid compact-state-grid">
              <button class="state-item" type="button" @click="$router.push('/settings')">
                <span>当前策略</span>
                <strong>{{ policyLabel(overview.automation?.download_policy) }}</strong>
              </button>
              <div class="state-item">
                <span>调度</span>
                <strong>{{ scheduleStatusLabel }}</strong>
              </div>
              <button class="state-item" type="button" @click="goLibraryOrganize('mapping')">
                <span>自动匹配</span>
                <strong>{{ overview.mapping?.auto_match?.auto_match_after_collect ? '采集后自动匹配' : '手动匹配' }}</strong>
              </button>
              <div class="state-item">
                <span>下一次</span>
                <strong>{{ formatTime(candidateSchedule.next_run_time) || '未计划' }}</strong>
              </div>
            </div>
          </article>
        </aside>

        <article class="workbench-panel action-map-panel diagnostic-wide" aria-label="自动化工作台">
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
            <button
              v-for="action in workbenchActions"
              :key="action.key"
              class="action-card"
              type="button"
              @click="goWorkbenchAction(action)"
            >
              <span>{{ action.label }}</span>
              <strong>{{ action.title }}</strong>
              <small>{{ action.hint }}</small>
            </button>
          </div>
        </article>
      </section>

      <section v-else-if="activeSegment === 'system'" class="system-layout" aria-label="系统状态">
          <article class="workbench-panel health-panel" aria-label="初始化与健康检查">
            <div class="panel-head">
              <div>
                <h2>初始化与健康检查</h2>
                <p>{{ healthStatusLabel }} · {{ healthConfigSummary }}</p>
              </div>
              <div class="panel-actions">
                <button class="btn btn-ghost btn-sm" type="button" @click="goSettings">设置</button>
                <button class="btn btn-ghost btn-sm" type="button" @click="goJavInfoImport">导入数据库</button>
                <button class="btn btn-ghost btn-sm" type="button" @click="goLogs">日志</button>
              </div>
            </div>
            <div class="health-grid">
              <div class="state-item" :class="{ warning: !health?.config?.loaded }">
                <span>配置已加载</span>
                <strong>{{ health?.config?.loaded ? '是' : '否' }}</strong>
              </div>
              <div class="state-item" :class="{ warning: health?.database && !health.database.connectable }">
                <span>数据库</span>
                <strong>{{ healthDatabaseSummary }}</strong>
              </div>
              <div class="state-item" :class="{ warning: health?.javinfo && (!health.javinfo.api_url_configured || health.javinfo.legacy) }">
                <span>JavInfo</span>
                <strong>{{ healthJavInfoSummary }}</strong>
              </div>
              <div class="state-item" :class="{ warning: !!health?.cache?.error }">
                <span>缓存</span>
                <strong>{{ healthCacheSummary }}</strong>
              </div>
              <div class="state-item" :class="{ warning: health?.downloaders && !health.downloaders.default_available }">
                <span>默认下载器</span>
                <strong>{{ healthDownloaderSummary }}</strong>
              </div>
              <div class="state-item" :class="{ warning: health?.sources && (!health.sources.available || health.sources.latest_attempt_error) }">
                <span>磁力源</span>
                <strong>{{ healthSourceSummary }}</strong>
                <small v-if="healthSourceAttemptSummary">{{ healthSourceAttemptSummary }}</small>
              </div>
              <div class="state-item" :class="{ warning: health?.scheduler && !health.scheduler.effective_enabled }">
                <span>调度有效性</span>
                <strong>{{ healthSchedulerSummary }}</strong>
              </div>
              <div class="state-item" :class="{ warning: health?.javinfo?.legacy || health?.javinfo?.error }">
                <span>JavInfo 地址</span>
                <strong>{{ healthJavInfoUrlSummary }}</strong>
              </div>
            </div>
          </article>

          <article class="workbench-panel automation-panel">
            <div class="panel-head">
              <div>
                <h2>自动化状态</h2>
                <p>{{ candidateSchedule.disabled_reason || '策略、调度和映射保护。' }}</p>
              </div>
              <button class="btn btn-ghost btn-sm" type="button" @click="$router.push('/settings')">策略设置</button>
            </div>
            <div class="state-grid">
              <button class="state-item" type="button" @click="$router.push('/settings')">
                <span>当前策略</span>
                <strong>{{ policyLabel(overview.automation?.download_policy) }}</strong>
              </button>
              <div class="state-item">
                <span>自动处理间隔</span>
                <strong>{{ overview.automation?.auto_process_interval_minutes || 0 }} 分钟</strong>
              </div>
              <div class="state-item">
                <span>调度</span>
                <strong>{{ scheduleStatusLabel }}</strong>
              </div>
              <div class="state-item">
                <span>下一次</span>
                <strong>{{ formatTime(candidateSchedule.next_run_time) || '未计划' }}</strong>
              </div>
              <button class="state-item" type="button" @click="goLibraryOrganize('mapping')">
                <span>自动匹配</span>
                <strong>{{ overview.mapping?.auto_match?.auto_match_after_collect ? '采集后自动匹配' : '手动匹配' }}</strong>
              </button>
              <div class="state-item">
                <span>确认策略</span>
                <strong>保守唯一</strong>
              </div>
            </div>
          </article>
      </section>

      <section v-else-if="activeSegment === 'diagnostics'" class="diagnostic-grid" aria-label="诊断与记录">
        <article class="workbench-panel">
            <div class="panel-head">
              <div>
                <h2>补全状态</h2>
                <p>{{ overview.supplement?.available ? '队列状态正常返回。' : '服务当前不可用。' }}</p>
              </div>
              <button class="btn btn-ghost btn-sm" type="button" @click="$router.push('/supplement')">补全管理</button>
            </div>
            <div v-if="overview.supplement?.available" class="mini-stats">
              <div><strong>{{ overview.supplement.queued || 0 }}</strong><span>排队</span></div>
              <div><strong>{{ overview.supplement.running || 0 }}</strong><span>运行</span></div>
              <div><strong>{{ overview.supplement.failed || 0 }}</strong><span>失败</span></div>
            </div>
            <p v-else class="muted">补全服务暂不可用：{{ overview.supplement?.error || '未连接' }}</p>
        </article>

        <article class="workbench-panel cache-panel diagnostic-wide">
            <div class="panel-head">
              <div>
                <h2>缓存诊断</h2>
                <p>{{ cacheStatsSummary }}</p>
              </div>
              <span class="backend-pill">{{ cacheStats?.backend || 'unknown' }}</span>
            </div>
            <div class="mini-stats cache-entry-stats">
              <div><strong>{{ cacheStats?.total_entries || 0 }}</strong><span>总条目</span></div>
              <div><strong>{{ cacheStats?.active_entries || 0 }}</strong><span>有效</span></div>
              <div><strong>{{ cacheStats?.expired_entries || 0 }}</strong><span>过期</span></div>
            </div>
            <div class="cache-rate-grid">
              <div class="state-item">
                <span>响应命中率</span>
                <strong>{{ responseHitRate }}</strong>
              </div>
              <div class="state-item">
                <span>搜索命中率</span>
                <strong>{{ searchHitRate }}</strong>
              </div>
              <div class="state-item">
                <span>合并等待</span>
                <strong>{{ cacheStats?.metrics?.singleflight_waits || 0 }}</strong>
              </div>
            </div>
            <div class="cache-namespaces">
              <div class="block-head">
                <h3>热门响应命名空间</h3>
              </div>
              <div class="compact-list">
                <div v-for="item in topResponseNamespaces" :key="item.name" class="compact-row static-row">
                  <span>{{ item.name }}</span>
                  <strong>{{ item.count }}</strong>
                </div>
                <small v-if="!topResponseNamespaces.length" class="empty-line">暂无响应缓存</small>
              </div>
            </div>
            <div class="cache-cleanup">
              <div class="block-head">
                <h3>缓存清理</h3>
                <span>{{ selectedCachePurgeLabel }}</span>
              </div>
              <div class="cache-scope-group" role="group" aria-label="缓存清理范围">
                <button
                  v-for="scope in cachePurgeScopes"
                  :key="scope.value"
                  class="scope-chip"
                  type="button"
                  :class="{ active: selectedCachePurgeScope === scope.value }"
                  @click="selectedCachePurgeScope = scope.value"
                >
                  {{ scope.label }}
                </button>
              </div>
              <button class="btn btn-ghost btn-sm cache-purge-btn" type="button" :disabled="purgingCache" @click="purgeSelectedCache">
                {{ purgingCache ? '清理中...' : '清理缓存' }}
              </button>
            </div>
            <p v-if="cacheStatsError" class="muted cache-error">{{ cacheStatsError }}</p>
        </article>

        <article class="workbench-panel">
            <div class="panel-head">
              <div>
                <h2>库存任务</h2>
                <p>运行中 {{ overview.inventory_jobs?.running || 0 }} · 失败 {{ overview.inventory_jobs?.failed || 0 }}</p>
              </div>
              <button class="btn btn-ghost btn-sm" type="button" @click="goLibraryOrganize('inventory')">片库整理</button>
            </div>
            <div class="compact-list">
              <div v-for="job in recentJobs" :key="job.id" class="compact-row static-row">
                <strong>{{ job.job_type }}</strong>
                <span>{{ job.status }} · {{ formatTime(job.created_at) }}</span>
              </div>
              <small v-if="!recentJobs.length" class="empty-line">暂无作业记录</small>
            </div>
        </article>

        <article class="workbench-panel history-panel diagnostic-wide">
        <div class="panel-head">
          <div>
            <h2>最近候选处理</h2>
            <p>调度 {{ scheduleStatusLabel }} · 下一次 {{ formatTime(candidateSchedule.next_run_time) || '未计划' }}</p>
          </div>
          <div class="panel-actions">
            <button class="btn btn-ghost btn-sm" type="button" @click="goCandidates({ status: 'candidate' })">候选队列</button>
            <button class="btn btn-primary btn-sm" type="button" :disabled="processingNow" @click="runCandidateProcessingNow">
              {{ processingNow ? '处理中...' : '立即运行' }}
            </button>
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
      </section>
    </template>
  </div>
</template>

<script>
import api from '../api'
import { requestConfirm } from '../utils/confirmDialog'

export default {
  name: 'Operations',
  data() {
    return {
      overview: null,
      cacheStats: null,
      health: null,
      cacheStatsError: '',
      healthError: '',
      loading: false,
      processingNow: false,
      refreshingMissing: false,
      purgingCache: false,
      selectedCachePurgeScope: 'video',
      activeSegment: 'workbench',
      cachePurgeScopes: [
        { value: 'video', label: '影片/搜索' },
        { value: 'response', label: '响应缓存' },
        { value: 'enum', label: '枚举目录' },
        { value: 'all', label: '全部' },
      ],
      error: '',
    }
  },
  computed: {
    coverageText() {
      return `${Math.round((this.overview?.mapping?.coverage || 0) * 100)}%`
    },
    operationsSummary() {
      if (!this.overview) return '库存、映射、补全和下载候选的闭环状态。'
      return `候选 ${this.overview.candidates?.candidate || 0} · 缺口 ${this.overview.missing?.total || 0} · 调度 ${this.scheduleStatusLabel}`
    },
    operationsSegments() {
      return [
        { key: 'workbench', label: '处理', hint: `${this.overview?.candidates?.candidate || 0} 个候选` },
        { key: 'system', label: '系统状态', hint: this.healthStatusLabel },
        { key: 'diagnostics', label: '诊断记录', hint: `${this.recentRuns.length} 次运行` },
      ]
    },
    statusMetrics() {
      const candidates = this.overview?.candidates || {}
      const missing = this.overview?.missing || {}
      const mapping = this.overview?.mapping || {}
      const supplement = this.overview?.supplement || {}
      return [
        {
          key: 'candidate',
          label: '待确认候选',
          value: candidates.candidate || 0,
          hint: '打开队列',
          urgent: (candidates.candidate || 0) > 0,
        },
        {
          key: 'ready',
          label: '可批准',
          value: candidates.ready || 0,
          hint: '已有磁力',
          urgent: (candidates.ready || 0) > 0,
        },
        {
          key: 'needs_magnet',
          label: '待补磁力',
          value: candidates.needs_magnet || 0,
          hint: '需要补全',
          urgent: (candidates.needs_magnet || 0) > 0,
        },
        {
          key: 'missing',
          label: '库存缺口',
          value: missing.total || 0,
          hint: '片库整理',
          urgent: (missing.total || 0) > 0,
        },
        {
          key: 'mapping',
          label: '映射待审核',
          value: mapping.candidate || 0,
          hint: `${this.coverageText} 覆盖`,
          urgent: (mapping.candidate || 0) > 0,
        },
        {
          key: 'supplement_failed',
          label: '补全失败',
          value: supplement.failed || 0,
          hint: supplement.available ? '补全管理' : '服务不可用',
          urgent: !supplement.available || (supplement.failed || 0) > 0,
        },
      ]
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
    cacheStatsSummary() {
      if (this.cacheStatsError) return '缓存统计暂不可用。'
      if (!this.cacheStats) return '加载缓存指标中。'
      return `${this.cacheStats.backend || 'unknown'} · ${this.cacheStats.active_entries || 0}/${this.cacheStats.total_entries || 0} active`
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
      const url = String(javinfo.api_url)
      return url.replace(/^https?:\/\//, '').replace(/\/$/, '')
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
    responseHitRate() {
      return this.formatHitRate(this.cacheStats?.metrics?.response)
    },
    searchHitRate() {
      return this.formatHitRate(this.cacheStats?.metrics?.search)
    },
    topResponseNamespaces() {
      const namespaces = this.cacheStats?.response_namespaces || {}
      return Object.entries(namespaces)
        .map(([name, count]) => ({ name, count: Number(count || 0) }))
        .sort((a, b) => b.count - a.count || a.name.localeCompare(b.name))
        .slice(0, 5)
    },
    scheduleStatusLabel() {
      if (this.candidateSchedule.running) return '运行中'
      if (this.candidateSchedule.effective_enabled) return '已启用'
      if (this.candidateSchedule.disabled_reason === 'manual_policy') return '手动策略'
      if (this.candidateSchedule.enabled) return '已配置未生效'
      return '未启用'
    },
    selectedCachePurgeLabel() {
      return this.cachePurgeScopes.find(scope => scope.value === this.selectedCachePurgeScope)?.label || this.selectedCachePurgeScope
    },
    workbenchActions() {
      return [
        { key: 'collect', label: '1', title: '采集 Emby', hint: '拉取本地库快照', path: '/library-organize', query: { tab: 'inventory' } },
        { key: 'compare', label: '2', title: '全量对比', hint: '生成缺失与候选', path: '/library-organize', query: { tab: 'check' } },
        { key: 'mapping', label: '3', title: '映射审核', hint: `${this.overview?.mapping?.candidate || 0} 个待审`, path: '/library-organize', query: { tab: 'mapping' } },
        { key: 'sources', label: '4', title: '补全来源诊断', hint: 'Provider smoke 与预算', path: '/supplement', query: { tab: 'sources' } },
        { key: 'candidates', label: '5', title: '下载候选', hint: `${this.overview?.candidates?.candidate || 0} 个候选`, path: '/downloads', query: { tab: 'candidates', status: 'candidate' } },
        { key: 'downloaders', label: '6', title: '下载源', hint: '默认下载器与连通性', path: '/downloads', query: { tab: 'downloaders' } },
        { key: 'activity', label: '7', title: '运行日志', hint: '日志与通知记录', path: '/logs' },
        { key: 'settings', label: '8', title: '初始化设置', hint: 'JavInfo/配置导入', path: '/settings', query: { tab: 'javinfo-import' } },
      ]
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
    topMissingActors() {
      return (this.overview?.missing?.top_actresses || []).slice(0, 6)
    },
  },
  mounted() {
    this.activeSegment = this.segmentFromRoute()
    this.loadOverview()
  },
  watch: {
    '$route.query.tab'() {
      this.activeSegment = this.segmentFromRoute()
    },
  },
  methods: {
    segmentFromRoute() {
      const tab = this.$route.query.tab
      return ['workbench', 'system', 'diagnostics'].includes(tab) ? tab : 'workbench'
    },
    setActiveSegment(segment) {
      if (!['workbench', 'system', 'diagnostics'].includes(segment)) return
      this.activeSegment = segment
      this.$router.replace({ query: { ...this.$route.query, tab: segment } })
    },
    async loadOverview() {
      this.loading = true
      this.error = ''
      this.cacheStatsError = ''
      this.healthError = ''
      try {
        const [overviewResp, cacheStatsResp, healthResp] = await Promise.allSettled([
          api.getOperationsOverview(),
          api.getCacheStats(),
          api.readiness(),
        ])
        if (overviewResp.status === 'rejected') {
          throw overviewResp.reason
        }
        this.overview = overviewResp.value.data
        if (cacheStatsResp.status === 'fulfilled') {
          this.cacheStats = cacheStatsResp.value.data
        } else {
          this.cacheStatsError = cacheStatsResp.reason?.response?.data?.detail || cacheStatsResp.reason?.message || '加载失败'
        }
        if (healthResp.status === 'fulfilled') {
          this.health = healthResp.value.data
        } else {
          this.healthError = healthResp.reason?.response?.data?.detail || healthResp.reason?.message || '加载失败'
        }
      } catch (e) {
        this.error = e.response?.data?.detail || e.message || '加载失败'
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
    sourceListLabel(sources = []) {
      if (!sources.length) return '全部'
      const labels = { subscription: '订阅', inventory: '库存', supplement: '补全', manual: '手动' }
      return sources.map(source => labels[source] || source).join(' / ')
    },
    formatHitRate(metrics = {}) {
      const hits = Number(metrics.hits || 0)
      const misses = Number(metrics.misses || 0)
      const total = hits + misses
      if (!total) return '0%'
      return `${Math.round((hits / total) * 100)}%`
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
    async purgeSelectedCache() {
      if (this.purgingCache) return
      const confirmed = await requestConfirm({
        title: '缓存清理',
        message: `确认清理${this.selectedCachePurgeLabel}？`,
        details: '清理后会重新拉取相关数据，短时间内接口可能变慢。',
        confirmText: '清理',
        tone: this.selectedCachePurgeScope === 'all' ? 'danger' : 'default',
      })
      if (!confirmed) return
      this.purgingCache = true
      try {
        await api.purgeCache(this.selectedCachePurgeScope)
        this.$message?.success?.('缓存已清理')
        await this.loadCacheStats()
      } catch (e) {
        console.error('Purge cache failed:', e)
      } finally {
        this.purgingCache = false
      }
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
    goJavInfoImport() {
      this.$router.push({ path: '/settings', query: { tab: 'javinfo-import' } })
    },
    goSettings() {
      this.$router.push('/settings')
    },
    goLogs() {
      this.$router.push('/logs')
    },
    goLibraryOrganize(tab = 'inventory') {
      this.$router.push({ path: '/library-organize', query: { tab } })
    },
    goInventoryActor(actorId) {
      this.$router.push({ path: '/library-organize', query: { tab: 'inventory', actor_id: actorId } })
    },
    openStatusMetric(key) {
      const actions = {
        candidate: () => this.goCandidates({ status: 'candidate' }),
        ready: () => this.goCandidates({ status: 'candidate', needs_magnet: false }),
        needs_magnet: () => this.goCandidates({ status: 'candidate', needs_magnet: true }),
        missing: () => this.goLibraryOrganize('inventory'),
        mapping: () => this.goLibraryOrganize('mapping'),
        supplement_failed: () => this.$router.push('/supplement'),
      }
      actions[key]?.()
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
  --operations-line: var(--border-light);
}

.operations-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  min-height: 52px;
  margin-bottom: 10px;
  padding-bottom: 10px;
  border-bottom: 1px solid var(--operations-line);
}

.header-copy {
  min-width: 0;
}

.operations-header h1 {
  margin: 0;
  font-size: var(--type-workbench-title);
  line-height: 1.1;
  font-weight: 650;
  letter-spacing: 0;
}

.operations-header p {
  margin: 4px 0 0;
  color: var(--text-secondary);
  font-size: var(--type-caption);
  line-height: 1.3;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.header-actions {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.btn-sm {
  min-height: 34px;
  padding: 7px 12px;
  font-size: 12px;
}

.health-panel {
  margin-bottom: 12px;
}

.health-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 8px;
}

.state-item.warning {
  border-color: var(--badge-warning-border);
  background: var(--badge-warning-bg);
}

.action-map-panel {
  margin-bottom: 12px;
}

.action-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 8px;
}

.action-card {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  gap: 2px 8px;
  align-items: center;
  min-height: 58px;
  padding: 9px 10px;
  border: 1px solid var(--operations-line);
  border-radius: var(--radius-md);
  background: var(--surface-control);
  color: var(--text-primary);
  text-align: left;
  cursor: pointer;
}

.action-card:hover {
  border-color: var(--border);
  background: var(--surface-card-hover);
}

.action-card span {
  display: inline-flex;
  grid-row: 1 / span 2;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border-radius: 999px;
  background: var(--glass-active-material);
  color: var(--text-primary);
  font-family: var(--font-mono);
  font-size: 11px;
}

.action-card strong,
.action-card small {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.action-card strong {
  font-size: 12px;
}

.action-card small {
  color: var(--text-secondary);
  font-size: 11px;
}

.operations-workbench {
  display: grid;
  grid-template-columns: minmax(0, 1.55fr) minmax(320px, 0.85fr);
  gap: 12px;
  align-items: start;
}

.workbench-panel,
.loading-panel,
.empty-panel {
  border: 1px solid var(--operations-line);
  border-radius: var(--radius-lg);
  background: var(--surface-card);
  box-shadow: var(--shadow-card);
}

.workbench-panel {
  min-width: 0;
  padding: 12px;
}

.workbench-primary {
  min-height: 100%;
}

.panel-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 10px;
}

.panel-head > div {
  min-width: 0;
}

.panel-head h2 {
  margin: 0;
  font-size: var(--type-card-title);
  line-height: 1.2;
  font-weight: 650;
  letter-spacing: 0;
}

.panel-head p {
  margin: 3px 0 0;
  color: var(--text-secondary);
  font-size: 12px;
  line-height: 1.3;
}

.panel-actions {
  display: flex;
  gap: 8px;
  flex: 0 0 auto;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.queue-overview {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 10px;
  align-items: stretch;
  margin-bottom: 12px;
}

.queue-focus {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: center;
  min-height: 58px;
  padding: 9px 12px;
  border: 1px solid var(--operations-line);
  border-radius: var(--radius-md);
  background: var(--surface-control);
  color: var(--text-primary);
  text-align: left;
  cursor: pointer;
  transition: background var(--motion-fast), border-color var(--motion-fast);
}

.queue-focus:hover,
.compact-row:hover,
.state-item:is(button):hover,
.block-head button:hover {
  border-color: var(--border);
  background: var(--surface-card-hover);
}

.queue-focus span,
.queue-focus small {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.queue-focus span {
  font-size: 12px;
  font-weight: 600;
}

.queue-focus strong {
  grid-row: 1 / span 2;
  grid-column: 2;
  font-family: var(--font-mono);
  font-size: var(--type-workbench-title);
  line-height: 1;
}

.queue-focus small {
  margin-top: 2px;
  color: var(--text-secondary);
  font-size: 11px;
}

.quick-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  align-content: center;
  justify-content: flex-end;
}

.queue-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.list-block {
  min-width: 0;
}

.block-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  min-height: 28px;
  margin-bottom: 6px;
}

.block-head h3 {
  margin: 0;
  font-size: 12px;
  font-weight: 650;
  letter-spacing: 0;
}

.block-head span,
.block-head button {
  color: var(--text-secondary);
  font-size: 11px;
}

.block-head button {
  padding: 4px 8px;
  border: 1px solid transparent;
  border-radius: var(--radius-sm);
  background: transparent;
  cursor: pointer;
  transition: background var(--motion-fast), border-color var(--motion-fast), color var(--motion-fast);
}

.compact-list,
.run-list {
  display: grid;
  gap: 0;
  overflow: hidden;
  border: 1px solid var(--operations-line);
  border-radius: var(--radius-md);
  background: var(--surface-card);
}

.compact-row,
.run-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  width: 100%;
  min-height: 36px;
  padding: 8px 10px;
  border: 0;
  border-bottom: 1px solid var(--operations-line);
  background: transparent;
  color: var(--text-primary);
  font-family: inherit;
  text-align: left;
}

.compact-row:last-child,
.run-row:last-child {
  border-bottom: 0;
}

.compact-row {
  cursor: pointer;
  transition: background var(--motion-fast);
}

.static-row {
  cursor: default;
}

.compact-row span,
.compact-row strong,
.run-row span,
.run-row strong,
.run-row small {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.compact-row span {
  color: var(--text-primary);
  font-size: 12px;
  font-weight: 500;
}

.compact-row strong {
  font-family: var(--font-mono);
  font-size: 13px;
  font-weight: 650;
}

.static-row strong {
  font-family: var(--font-body);
  font-size: 12px;
}

.static-row span {
  color: var(--text-secondary);
}

.state-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
}

.state-item {
  min-width: 0;
  min-height: 52px;
  padding: 8px 10px;
  border: 1px solid var(--operations-line);
  border-radius: var(--radius-md);
  background: var(--surface-control);
  color: var(--text-primary);
  font-family: inherit;
  text-align: left;
}

button.state-item {
  cursor: pointer;
  transition: background var(--motion-fast), border-color var(--motion-fast);
}

.state-item span {
  display: block;
  overflow: hidden;
  color: var(--text-secondary);
  font-size: 11px;
  line-height: 1.2;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.state-item strong {
  display: block;
  margin-top: 4px;
  overflow: hidden;
  color: var(--text-primary);
  font-size: 12px;
  font-weight: 650;
  line-height: 1.2;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.mini-stats {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
}

.mini-stats > div {
  min-width: 0;
  padding: 8px 10px;
  border: 1px solid var(--operations-line);
  border-radius: var(--radius-md);
  background: var(--surface-control);
}

.mini-stats strong {
  display: block;
  font-family: var(--font-mono);
  font-size: 18px;
  line-height: 1;
}

.mini-stats span,
.muted,
.empty-line,
.run-row span,
.run-row small {
  color: var(--text-secondary);
  font-size: 11px;
}

.mini-stats span {
  display: block;
  margin-top: 4px;
}

.backend-pill {
  flex: 0 0 auto;
  max-width: 110px;
  overflow: hidden;
  padding: 4px 8px;
  border: 1px solid var(--operations-line);
  border-radius: var(--radius-sm);
  background: var(--surface-control);
  color: var(--text-secondary);
  font-family: var(--font-mono);
  font-size: 11px;
  line-height: 1.2;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.cache-entry-stats {
  grid-template-columns: repeat(3, minmax(0, 1fr));
  margin-bottom: 8px;
}

.cache-rate-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
  margin-bottom: 10px;
}

.cache-rate-grid .state-item {
  min-height: 48px;
}

.cache-namespaces {
  min-width: 0;
}

.cache-cleanup {
  margin-top: 10px;
}

.cache-scope-group {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 8px;
}

.scope-chip {
  min-height: 30px;
  padding: 5px 9px;
  border: 1px solid var(--glass-control-border);
  border-radius: var(--radius-control);
  background: var(--material-glass-subtle);
  color: var(--text-secondary);
  font-size: 11px;
  cursor: pointer;
}

.scope-chip.active {
  background: var(--glass-active-material);
  color: var(--text-primary);
  border-color: var(--glass-active-border);
  box-shadow: var(--glass-active-shadow);
}

.cache-purge-btn {
  width: 100%;
  justify-content: center;
}

.cache-error {
  margin-top: 8px;
}

.muted {
  margin: 0;
  line-height: 1.5;
}

.history-panel {
  margin-top: 12px;
}

.run-row {
  align-items: flex-start;
}

.run-row > div {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.run-row strong {
  font-size: 12px;
  font-weight: 650;
}

.run-row small {
  flex: 0 1 auto;
  text-align: right;
}

.empty-line {
  display: block;
  padding: 10px;
  line-height: 1.4;
}

.loading-panel,
.empty-panel {
  padding: 28px;
  text-align: center;
}

.empty-panel h2 {
  margin: 0 0 6px;
  font-size: var(--type-panel-title);
}

.empty-panel p {
  margin: 0 0 14px;
  color: var(--text-secondary);
  font-size: 13px;
}

.operations-page {
  --operations-line: color-mix(in srgb, var(--border-light) 68%, transparent);
  --operations-soft-line: color-mix(in srgb, var(--border-light) 42%, transparent);
  --operations-panel-gap: clamp(12px, 1.4vw, 18px);
  --operations-panel-pad: clamp(14px, 1.45vw, 20px);
}

.operations-hero {
  display: grid;
  grid-template-columns: minmax(260px, 0.8fr) minmax(520px, 1.1fr) auto;
  align-items: start;
  gap: var(--operations-panel-gap);
  min-height: unset;
  margin-bottom: var(--operations-panel-gap);
  padding: var(--operations-panel-pad);
  border: 1px solid var(--operations-line);
  border-radius: var(--radius-xl);
  background: var(--material-glass-sheet);
  box-shadow: var(--glass-surface-shadow);
  backdrop-filter: blur(var(--glass-blur-surface)) saturate(var(--glass-saturate-surface));
  -webkit-backdrop-filter: blur(var(--glass-blur-surface)) saturate(var(--glass-saturate-surface));
}

.hero-eyebrow {
  display: block;
  margin-bottom: 8px;
  color: var(--text-muted);
  font-size: var(--type-micro);
  font-weight: 650;
}

.operations-header h1 {
  font-size: var(--type-page-title);
}

.operations-header p {
  max-width: 58ch;
  white-space: normal;
}

.hero-stat-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(132px, 1fr));
  gap: 8px;
  min-width: 0;
}

.operations-segments {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 4px;
  margin-bottom: var(--operations-panel-gap);
  padding: 4px;
  border: 1px solid var(--operations-soft-line);
  border-radius: var(--radius-lg);
  background: var(--material-glass-control);
  box-shadow: none;
}

.operations-segments button {
  min-width: 0;
  min-height: 46px;
  padding: 8px 12px;
  border: 1px solid transparent;
  border-radius: var(--radius-md);
  background: transparent;
  color: var(--text-secondary);
  font-family: inherit;
  text-align: left;
  cursor: pointer;
  transition: background var(--motion-fast), border-color var(--motion-fast), color var(--motion-fast), box-shadow var(--motion-fast);
}

.operations-segments button:hover {
  border-color: var(--glass-control-border-hover);
  background: var(--material-glass-control-hover);
  color: var(--text-primary);
}

.operations-segments button.active {
  border-color: var(--glass-active-border);
  background: var(--glass-active-material);
  color: var(--text-primary);
  box-shadow: var(--glass-active-shadow);
}

.operations-segments span,
.operations-segments small {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.operations-segments span {
  font-size: 12px;
  font-weight: 650;
  line-height: 1.2;
}

.operations-segments small {
  margin-top: 3px;
  color: var(--text-secondary);
  font-size: 11px;
  line-height: 1.2;
}

.hero-stat {
  min-width: 0;
  min-height: 70px;
  padding: 12px;
  border: 1px solid var(--operations-soft-line);
  border-radius: var(--radius-lg);
  background: var(--material-glass-subtle);
  color: var(--text-primary);
  font-family: inherit;
  text-align: left;
  cursor: pointer;
  transition: background var(--motion-fast), border-color var(--motion-fast), transform var(--motion-fast);
}

.hero-stat:hover {
  border-color: var(--glass-control-border-hover);
  background: var(--material-glass-control-hover);
  transform: translateY(-1px);
}

.hero-stat strong {
  display: block;
  font-family: var(--font-mono);
  font-size: clamp(22px, 2.2vw, 32px);
  line-height: 1;
  font-weight: 650;
}

.hero-stat span {
  display: block;
  margin-top: 8px;
  overflow: hidden;
  color: var(--text-secondary);
  font-size: var(--type-caption);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.priority-board {
  grid-template-columns: minmax(0, 1.45fr) minmax(360px, 0.95fr);
  gap: var(--operations-panel-gap);
  margin-bottom: var(--operations-panel-gap);
}

.workbench-side,
.system-layout,
.diagnostic-grid {
  display: grid;
  gap: var(--operations-panel-gap);
  min-width: 0;
}

.system-layout {
  grid-template-columns: minmax(0, 1.25fr) minmax(360px, 0.75fr);
  align-items: start;
}

.workbench-side {
  align-self: start;
}

.workbench-panel,
.loading-panel,
.empty-panel {
  border-color: var(--operations-line);
  border-radius: var(--radius-xl);
  background: var(--material-glass-sheet);
  box-shadow: var(--glass-surface-shadow);
  backdrop-filter: blur(var(--glass-blur-surface)) saturate(var(--glass-saturate-surface));
  -webkit-backdrop-filter: blur(var(--glass-blur-surface)) saturate(var(--glass-saturate-surface));
}

.workbench-panel {
  padding: var(--operations-panel-pad);
}

.workbench-primary {
  min-height: 0;
}

.panel-head {
  margin-bottom: 14px;
}

.panel-head h2 {
  font-size: var(--type-panel-title);
}

.panel-head p {
  max-width: 56ch;
  line-height: 1.45;
}

.health-panel,
.action-map-panel,
.history-panel {
  margin: 0;
}

.health-grid {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.state-item,
.mini-stats > div,
.queue-focus,
.action-card,
.compact-list,
.run-list {
  border-color: var(--operations-soft-line);
  background: var(--material-glass-control);
  box-shadow: none;
}

.state-item.warning {
  border-color: color-mix(in srgb, var(--badge-warning-border) 72%, transparent);
  background: linear-gradient(145deg, var(--badge-warning-bg), rgba(255,255,255,0.28));
}

.queue-overview {
  grid-template-columns: minmax(0, 1fr);
  margin-bottom: 16px;
}

.queue-focus {
  min-height: 84px;
  padding: 14px 16px;
}

.queue-focus strong {
  font-size: clamp(28px, 3vw, 40px);
}

.quick-actions {
  justify-content: flex-start;
}

.queue-grid,
.diagnostic-grid {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.compact-state-grid {
  grid-template-columns: 1fr;
}

.diagnostic-wide {
  grid-column: span 2;
}

.action-grid {
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
}

.action-card {
  min-height: 66px;
  padding: 12px;
}

.action-card span {
  background: var(--material-glass-subtle);
}

.compact-row,
.run-row {
  min-height: 40px;
}

.cache-panel {
  align-self: start;
}

.cache-rate-grid {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.scope-chip {
  background: var(--material-glass-control);
  transition: background var(--motion-fast), border-color var(--motion-fast), color var(--motion-fast);
}

.scope-chip:hover {
  border-color: var(--glass-control-border-hover);
  background: var(--material-glass-control-hover);
}

@media (max-width: 900px) {
  .operations-header {
    align-items: flex-start;
    flex-direction: column;
  }

  .operations-header p {
    white-space: normal;
  }

  .operations-hero {
    grid-template-columns: 1fr;
  }

  .hero-stat-grid {
    width: 100%;
  }

  .operations-segments {
    grid-template-columns: 1fr;
  }

  .header-actions,
  .panel-actions {
    justify-content: flex-start;
  }

  .operations-workbench,
  .action-grid,
  .diagnostic-grid,
  .system-layout,
  .queue-overview,
  .queue-grid {
    grid-template-columns: 1fr;
  }

  .diagnostic-wide {
    grid-column: auto;
  }

  .quick-actions {
    justify-content: flex-start;
  }
}

@media (max-width: 560px) {
  .operations-header .btn,
  .panel-actions .btn,
  .quick-actions .btn {
    min-height: 40px;
    min-width: 0;
  }

  .header-actions,
  .panel-actions,
  .quick-actions {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    width: 100%;
  }

  .empty-panel .btn {
    min-height: 40px;
    width: 100%;
  }

  .panel-head {
    flex-direction: column;
  }

  .state-grid,
  .action-grid,
  .health-grid,
  .mini-stats,
  .cache-rate-grid {
    grid-template-columns: 1fr;
  }

  .run-row {
    flex-direction: column;
    gap: 4px;
  }

  .run-row small {
    text-align: left;
  }
}
</style>
