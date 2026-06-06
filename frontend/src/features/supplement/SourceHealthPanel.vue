<template>
  <section class="workspace-panel apple-surface">
    <div class="panel-header">
      <div>
        <h2>来源状态</h2>
      </div>
      <div class="source-health-toolbar">
        <button class="btn btn-ghost btn-sm" type="button" @click="$emit('refresh-health')">刷新</button>
        <button class="btn btn-ghost btn-sm" type="button" @click="$emit('view-avatar-jobs')">查看头像任务</button>
        <button class="btn btn-primary btn-sm" type="button" :disabled="providerSmokeLoading" @click="$emit('run-smoke')">
          {{ providerSmokeLoading ? '诊断中...' : '运行诊断' }}
        </button>
      </div>
    </div>
    <div class="source-health-modebar">
      <button
        v-for="mode in sourceHealthModes"
        :key="mode.key"
        type="button"
        :class="{ active: sourceHealthMode === mode.key }"
        @click="sourceHealthMode = mode.key"
      >
        <strong>{{ mode.label }}</strong>
        <em class="mode-count">{{ sourceHealthModeCount(mode.key) }}</em>
        <span>{{ mode.description }}</span>
      </button>
    </div>
    <div class="source-health-summary-grid">
      <div v-for="card in sourceHealthSummary" :key="card.label" class="health-summary-card">
        <strong>{{ card.value }}</strong>
        <span>{{ card.label }}</span>
      </div>
    </div>
    <div class="source-next-actions">
      <article
        v-for="action in sourceHealthActionQueue"
        :key="action.mode"
        class="source-next-action-card"
        :class="sourceNextActionCardClass(action)"
      >
        <div>
          <strong>{{ action.label }}</strong>
          <em v-if="action.primary">当前模式</em>
        </div>
        <span class="source-next-action-value">{{ action.count }}</span>
        <small>{{ action.detail }}</small>
        <button
          :class="['btn', action.tone, 'btn-xs']"
          type="button"
          :disabled="action.loading"
          @click="action.event ? $emit(action.event) : sourceHealthMode = action.mode"
        >{{ action.cta }}</button>
      </article>
    </div>
    <div class="source-runbook">
      <strong>{{ activeRunbook.title }}</strong>
      <span>{{ activeRunbook.detail }}</span>
    </div>
    <section class="avatar-sync-panel">
      <div class="avatar-sync-head">
        <div>
          <h3>头像覆盖作业</h3>
          <p>gfriends Filetree 匹配本地演员头像，并校验图片健康。</p>
        </div>
        <span class="status-pill" :class="`status-${gfriendsAvatarJob?.status || 'idle'}`">
          {{ avatarJobStatusLabel(gfriendsAvatarJob?.status) }}
        </span>
      </div>
      <div class="avatar-sync-actions">
        <button
          class="btn btn-primary btn-sm"
          type="button"
          :disabled="gfriendsAvatarSyncing || avatarJobRunning"
          @click="$emit('sync-gfriends-avatars')"
        >{{ gfriendsAvatarSyncing || avatarJobRunning ? '同步中...' : '同步演员头像' }}</button>
        <button class="btn btn-ghost btn-sm" type="button" @click="$emit('view-avatar-jobs')">查看头像任务</button>
      </div>
      <div class="avatar-sync-steps" :class="{ active: avatarJobRunning }">
        <span v-if="avatarJobRunning" class="mini-spinner" aria-hidden="true"></span>
        <span>拉取 gfriends Filetree</span>
        <span>匹配本地演员</span>
        <span>写入头像覆盖</span>
        <span>校验图片健康</span>
      </div>
      <div class="avatar-sync-metrics">
        <div>
          <strong>{{ gfriendsAvatarJob?.total_found ?? 0 }}</strong>
          <span>匹配头像</span>
        </div>
        <div>
          <strong>{{ gfriendsAvatarJob?.inserted_count ?? 0 }}</strong>
          <span>写入覆盖</span>
        </div>
        <div>
          <strong>{{ gfriendsAvatarJob?.updated_count ?? 0 }}</strong>
          <span>已校验</span>
        </div>
        <div>
          <strong>{{ gfriendsAvatarJob?.matched_r18 ?? 0 }}</strong>
          <span>有效头像</span>
        </div>
      </div>
      <p v-if="gfriendsAvatarJob?.last_error" class="avatar-sync-error">{{ gfriendsAvatarJob.last_error }}</p>
      <p v-else class="avatar-sync-footnote">
        {{ gfriendsAvatarJob?.created_at ? `最近任务 #${gfriendsAvatarJob.id} · ${formatActionTime(gfriendsAvatarJob.finished_at || gfriendsAvatarJob.started_at || gfriendsAvatarJob.created_at)}` : '暂无头像同步任务' }}
      </p>
    </section>
    <div class="provider-smoke-controls">
      <GlassSelect
        :model-value="providerSmokeForm.source"
        :options="providerSourceOptions"
        size="compact"
        aria-label="诊断来源"
        @update:model-value="updateProviderSmokeForm({ source: $event })"
        @change="$emit('load-smoke-runs')"
      />
      <input
        :value="providerSmokeForm.sourceMovieId"
        class="filter-input"
        placeholder="源影片编号"
        @input="updateProviderSmokeForm({ sourceMovieId: $event.target.value })"
        @keyup.enter="$emit('run-smoke')"
      />
      <button
        v-if="providerSmokeReport"
        class="btn btn-ghost btn-sm"
        type="button"
        @click="$emit('update:providerSmokeReport', null)"
      >清除结果</button>
    </div>
    <div v-if="providerSmokeReport" class="provider-smoke-panel">
      <div class="provider-smoke-summary">
        <div>
          <strong>{{ providerSmokeReport.ok }} / {{ providerSmokeReport.total }}</strong>
          <span>诊断通过</span>
        </div>
        <div>
          <strong>{{ providerSmokeReport.failed }}</strong>
          <span>失败样本</span>
        </div>
        <small>{{ formatActionTime(providerSmokeReport.generated_at) }}</small>
      </div>
      <div class="provider-smoke-grid">
        <article
          v-for="report in providerSmokeReport.reports || []"
          :key="`${report.source}:${report.source_movie_id}`"
          class="provider-smoke-card"
          :class="{ failed: !report.ok }"
        >
          <div class="provider-smoke-card-head">
            <strong>{{ report.name || report.source_movie_id }}</strong>
            <span class="status-pill" :class="report.ok ? 'health-healthy' : 'health-degraded'">
              {{ report.ok ? '通过' : '异常' }}
            </span>
          </div>
          <p>{{ report.source }} · {{ report.source_movie_id }} · {{ report.duration_ms || 0 }} 毫秒</p>
          <small>字段分 {{ report.quality?.score ?? 0 }} / {{ report.quality?.max_score ?? 0 }}</small>
          <small v-if="report.quality?.missing?.length">缺失 {{ report.quality.missing.join(', ') }}</small>
          <small v-if="report.quality?.warnings?.length">警告 {{ report.quality.warnings.join(', ') }}</small>
          <small v-if="report.error">{{ report.error_type || '错误' }} · {{ report.error }}</small>
          <div v-if="report.detail?.title" class="provider-smoke-detail">
            <span>{{ report.detail.display_number || report.detail.normalized_number }}</span>
            <strong>{{ report.detail.title }}</strong>
          </div>
        </article>
      </div>
    </div>
    <div class="provider-smoke-history">
      <div class="provider-smoke-history-head">
        <strong>最近诊断</strong>
        <button class="btn btn-ghost btn-xs" type="button" @click="$emit('load-smoke-runs')">刷新历史</button>
      </div>
      <div v-if="providerSmokeRuns.length" class="provider-smoke-run-list">
        <button
          v-for="run in providerSmokeRuns"
          :key="run.id"
          type="button"
          class="provider-smoke-run"
          @click="$emit('update:providerSmokeReport', run.response)"
        >
          <span>{{ formatActionTime(run.generated_at || run.created_at) }}</span>
          <strong>{{ run.ok }} / {{ run.total }}</strong>
          <small>{{ smokeRunLabel(run) }}</small>
        </button>
      </div>
      <small v-else class="empty-inline">运行诊断后会在这里保留最近样本</small>
    </div>
    <AppleSkeleton
      v-if="sourceHealthLoading"
      class="source-health-state"
      variant="list"
      :items="5"
      label="来源状态加载中"
    />
    <div v-else class="source-health-grid">
      <div class="source-health-queue-head">
        <div>
          <strong>{{ sourceHealthQueueTitle }}</strong>
          <span>{{ sourceHealthQueueHint }}</span>
        </div>
        <small>{{ sourceHealthVisibleRows.length }} / {{ sourceHealthRows.length }}</small>
      </div>
      <AppleEmptyState
        v-if="!sourceHealthVisibleRows.length"
        class="source-health-empty"
        :title="sourceHealthEmptyState.title"
        :description="sourceHealthEmptyState.description"
        :next-step="sourceHealthEmptyState.nextStep"
        action-label="刷新来源"
        secondary-action-label="运行诊断"
        density="compact"
        @action="$emit('refresh-health')"
        @secondary-action="$emit('run-smoke')"
      />
      <article v-for="source in sourceHealthVisibleRows" :key="source.source" class="source-health-card">
        <div>
          <strong>{{ source.display_name || source.source }}</strong>
          <span>{{ source.source }}</span>
        </div>
        <span class="status-pill" :class="`health-${source.runtime_status}`">{{ sourceHealthLabel(source.runtime_status) }}</span>
        <div class="source-risk-row">
          <span v-for="item in sourceHealthRiskItems(source)" :key="item.label">
            <b>{{ item.value }}</b>
            <em>{{ item.label }}</em>
          </span>
        </div>
        <div class="source-budget-meter">
          <div>
            <strong>{{ source.budget?.local_active ?? 0 }} / {{ source.budget?.local_limit ?? '—' }}</strong>
            <span>当前预算</span>
          </div>
          <small>{{ sourceBudgetLabel(source.budget) }}</small>
        </div>
        <p>{{ source.last_error_type || '暂无错误' }}</p>
        <small>{{ sourceHealthDetail(source) }}</small>
        <div class="source-health-actions">
          <button
            :class="['btn', sourceHealthPrimaryAction(source).tone, 'btn-xs']"
            type="button"
            :disabled="sourceActionLoading === source.source"
            @click="$emit(sourceHealthPrimaryAction(source).event, source.source)"
          >{{ sourceHealthActionLabel(sourceHealthPrimaryAction(source)) }}</button>
        </div>
      </article>
    </div>
  </section>
</template>

<script>
import GlassSelect from '../../components/GlassSelect.vue'
import AppleEmptyState from '../../components/AppleEmptyState.vue'
import AppleSkeleton from '../../components/AppleSkeleton.vue'

export default {
  name: 'SourceHealthPanel',
  components: { GlassSelect, AppleEmptyState, AppleSkeleton },
  props: {
    providerSmokeForm: { type: Object, required: true },
    providerSourceOptions: { type: Array, default: () => [] },
    providerSmokeLoading: { type: Boolean, default: false },
    providerSmokeReport: { type: Object, default: null },
    providerSmokeRuns: { type: Array, default: () => [] },
    sourceHealthLoading: { type: Boolean, default: false },
    sourceHealthRows: { type: Array, default: () => [] },
    sourceActionLoading: { type: String, default: '' },
    gfriendsAvatarJob: { type: Object, default: null },
    gfriendsAvatarSyncing: { type: Boolean, default: false },
    formatActionTime: { type: Function, required: true },
    smokeRunLabel: { type: Function, required: true },
    sourceHealthLabel: { type: Function, required: true },
    sourceBudgetLabel: { type: Function, required: true },
    sourceHealthDetail: { type: Function, required: true },
  },
  emits: [
    'update:providerSmokeForm',
    'update:providerSmokeReport',
    'refresh-health',
    'run-smoke',
    'sync-gfriends-avatars',
    'view-avatar-jobs',
    'load-smoke-runs',
    'pause-source',
    'resume-source',
  ],
  data() {
    return {
      sourceHealthMode: 'diagnose',
    }
  },
  computed: {
    sourceHealthModes() {
      return [
        { key: 'diagnose', label: '诊断模式', description: '跑样本、看字段分' },
        { key: 'recover', label: '恢复模式', description: '清冷却、看预算' },
        { key: 'isolate', label: '隔离模式', description: '暂停异常来源' },
      ]
    },
    degradedSources() {
      return this.sourceHealthRows.filter(source => ['degraded', 'cooling_down'].includes(source.runtime_status))
    },
    pausedSources() {
      return this.sourceHealthRows.filter(source => source.runtime_status === 'paused')
    },
    diagnoseQueueRows() {
      return this.sourceHealthRows.filter(source => ['unknown', 'healthy', 'degraded'].includes(source.runtime_status))
    },
    recoverQueueRows() {
      return this.sourceHealthRows.filter(source => source.runtime_status === 'cooling_down' || source.runtime_status === 'paused')
    },
    isolateQueueRows() {
      return this.sourceHealthRows.filter(source => (
        ['degraded', 'cooling_down', 'paused'].includes(source.runtime_status)
        || (source.consecutive_failures || 0) >= 2
      ))
    },
    sourceHealthSummary() {
      return [
        { label: '来源总数', value: this.sourceHealthRows.length },
        { label: '异常来源', value: this.degradedSources.length },
        { label: '已暂停', value: this.pausedSources.length },
        { label: '头像任务', value: this.avatarJobRunning ? '运行中' : '待命' },
      ]
    },
    sourceHealthActionQueue() {
      return [
        {
          mode: 'diagnose',
          label: '运行诊断',
          count: this.diagnoseQueueRows.length,
          detail: '样本字段分与最近错误',
          cta: this.providerSmokeLoading ? '诊断中...' : '运行诊断',
          event: 'run-smoke',
          tone: 'btn-primary',
          loading: this.providerSmokeLoading,
          primary: this.sourceHealthMode === 'diagnose',
        },
        {
          mode: 'recover',
          label: '恢复来源',
          count: this.recoverQueueRows.length,
          detail: '冷却与人工暂停入口',
          cta: '查看恢复',
          tone: 'btn-ghost',
          primary: this.sourceHealthMode === 'recover',
        },
        {
          mode: 'isolate',
          label: '隔离风险',
          count: this.isolateQueueRows.length,
          detail: '连续失败与异常来源',
          cta: '查看隔离',
          tone: 'btn-ghost',
          primary: this.sourceHealthMode === 'isolate',
        },
      ]
    },
    activeRunbook() {
      if (this.sourceHealthMode === 'recover') {
        return { title: '恢复模式', detail: '优先恢复人工暂停或冷却结束的来源，再回看最近诊断样本。' }
      }
      if (this.sourceHealthMode === 'isolate') {
        return { title: '隔离模式', detail: '连续失败或预算异常的来源先暂停 24h，避免污染字段补全。' }
      }
      return { title: '诊断模式', detail: '先运行默认样本，确认字段分、缺失字段和详情来源是否稳定。' }
    },
    avatarJobRunning() {
      const status = this.gfriendsAvatarJob?.status
      return status === 'queued' || status === 'running'
    },
    sourceHealthVisibleRows() {
      if (this.sourceHealthMode === 'recover') {
        return this.sourceHealthRows.filter(source => source.runtime_status === 'cooling_down' || source.runtime_status === 'paused')
      }
      if (this.sourceHealthMode === 'isolate') {
        return this.sourceHealthRows.filter(source => ['degraded', 'cooling_down', 'paused'].includes(source.runtime_status))
      }
      return this.sourceHealthRows
    },
    sourceHealthQueueTitle() {
      if (this.sourceHealthMode === 'recover') return '恢复队列'
      if (this.sourceHealthMode === 'isolate') return '隔离队列'
      return '来源诊断队列'
    },
    sourceHealthQueueHint() {
      if (this.sourceHealthMode === 'recover') return '只显示冷却中或人工暂停的来源，优先恢复可用入口。'
      if (this.sourceHealthMode === 'isolate') return '只显示异常来源，便于快速暂停高风险来源。'
      return '显示全部来源，按当前运行状态查看字段补全风险。'
    },
    sourceHealthEmptyHint() {
      if (this.sourceHealthMode === 'recover') return '没有冷却中或人工暂停的来源，可以回到诊断模式检查样本质量。'
      if (this.sourceHealthMode === 'isolate') return '没有需要隔离的异常来源，当前来源池可继续观察。'
      return '来源池暂无记录，先刷新来源状态或运行诊断样本。'
    },
    sourceHealthEmptyState() {
      if (this.sourceHealthMode === 'recover') {
        return {
          title: '恢复队列为空',
          description: '当前没有冷却中或人工暂停的来源。',
          nextStep: '刷新来源确认最新预算，或运行诊断样本检查是否有新异常。',
        }
      }
      if (this.sourceHealthMode === 'isolate') {
        return {
          title: '隔离队列为空',
          description: '当前没有需要隔离的异常来源。',
          nextStep: '运行诊断可以重新采样来源质量；刷新来源会同步最新暂停和冷却状态。',
        }
      }
      return {
        title: '暂无来源状态',
        description: '来源池还没有可展示的健康记录。',
        nextStep: '先刷新来源状态，或运行诊断样本建立第一批质量记录。',
      }
    },
    sourceHealthPrimaryAction() {
      return source => {
        if (source.runtime_status === 'paused') {
          return { event: 'resume-source', label: '恢复', tone: 'btn-primary' }
        }
        if (this.sourceHealthMode === 'recover' && source.runtime_status === 'cooling_down') {
          return { event: 'resume-source', label: '解除冷却', tone: 'btn-primary' }
        }
        return { event: 'pause-source', label: '暂停 24h', tone: 'btn-ghost' }
      }
    },
  },
  methods: {
    sourceHealthModeCount(mode) {
      if (mode === 'recover') {
        return this.recoverQueueRows.length
      }
      if (mode === 'isolate') {
        return this.isolateQueueRows.length
      }
      return this.sourceHealthRows.length
    },
    sourceNextActionCardClass(action) {
      return { active: action.primary }
    },
    sourceHealthRiskItems(source) {
      const budget = source.budget || {}
      return [
        { label: '连续失败', value: source.consecutive_failures || 0 },
        { label: '预算占用', value: budget.local_active ?? 0 },
        { label: '最近错误', value: source.last_error_type || '无' },
      ]
    },
    avatarJobStatusLabel(status) {
      const map = { queued: '排队中', running: '同步中', succeeded: '已完成', failed: '失败', idle: '待开始' }
      return map[status] || status || '待开始'
    },
    updateProviderSmokeForm(patch) {
      this.$emit('update:providerSmokeForm', { ...this.providerSmokeForm, ...patch })
    },
    sourceHealthActionLabel(action) {
      if (action.event === 'resume-source') return action.label
      return action.label
    },
  },
}
</script>

<style scoped src="./sourceHealthPanel.css"></style>
