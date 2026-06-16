<template>
  <section class="workspace-panel">
    <div class="panel-header">
      <div>
        <h2>来源健康</h2>
        <p class="panel-subtitle">汇总 → 来源行 → 隔离 runbook · 来源抽检在下方</p>
      </div>
      <div class="source-health-toolbar">
        <button class="btn btn-ghost btn-sm" type="button" @click="$emit('refresh-health')">刷新</button>
        <button class="btn btn-primary btn-sm" type="button" :disabled="providerSmokeLoading" @click="$emit('run-smoke')">
          {{ providerSmokeLoading ? '抽检中...' : '运行抽检' }}
        </button>
      </div>
    </div>

    <!-- Layer 1 — summary -->
    <div class="src-summary">
      <div v-for="card in sourceHealthSummary" :key="card.label" class="ss-card" :class="`ss-card-${card.tone}`">
        <strong>{{ card.value }}</strong>
        <span>{{ card.label }}</span>
      </div>
    </div>

    <!-- Layer 2 — source rows -->
    <AppleSkeleton
      v-if="sourceHealthLoading"
      class="source-health-state"
      variant="list"
      :items="4"
      label="来源状态加载中"
    />
    <AppleEmptyState
      v-else-if="!sourceHealthRows.length"
      class="source-health-empty"
      title="暂无来源状态"
      description="来源池还没有可展示的健康记录。"
      next-step="先刷新来源状态，或运行诊断样本建立第一批质量记录。"
      action-label="刷新来源"
      secondary-action-label="运行诊断"
      density="compact"
      @action="$emit('refresh-health')"
      @secondary-action="$emit('run-smoke')"
    />
    <div v-else class="src-rows">
      <article v-for="source in sourceHealthRows" :key="source.source" class="source-card">
        <span class="sc-dot" :class="`sc-dot-${sourceDotTone(source)}`"></span>
        <div class="sc-main">
          <div class="sc-name">
            {{ source.display_name || source.source }}
            <small>{{ source.source }}</small>
          </div>
          <div class="sc-state">{{ sourceHealthLabel(source.runtime_status) }} · {{ sourceBudgetLabel(source.budget) }}</div>
        </div>
        <div class="sc-stat">
          <b :class="(source.consecutive_failures || 0) >= 2 ? 'err' : ''">{{ source.consecutive_failures || 0 }}</b>
          <span>连续失败</span>
        </div>
        <div class="sc-stat sc-stat-error">
          <b class="err">{{ source.last_error_type || '—' }}</b>
          <span>最近错误</span>
        </div>
        <div class="sc-next">
          <span>下一步</span>
          {{ sourceNextStep(source) }}
        </div>
        <div class="sc-act">
          <button
            :class="['btn', sourceHealthPrimaryAction(source).tone, 'btn-sm']"
            type="button"
            :disabled="sourceActionLoading === source.source"
            @click="$emit(sourceHealthPrimaryAction(source).event, source.source)"
          >{{ sourceActionLoading === source.source ? '执行中…' : sourceHealthPrimaryAction(source).label }}</button>
        </div>
      </article>
    </div>

    <!-- Layer 3 — runbook -->
    <div class="src-runbook">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16" aria-hidden="true">
        <circle cx="12" cy="12" r="10"/>
        <line x1="12" y1="8" x2="12" y2="12"/>
        <line x1="12" y1="16" x2="12.01" y2="16"/>
      </svg>
      <div>
        <b>隔离 runbook</b>
        连续失败或预算异常的来源先暂停 24h，避免污染字段补全；窗口结束后自动恢复并重新参与诊断。
      </div>
    </div>

    <!-- Source sampling (un-folded; this is how source quality is scored) -->
    <div class="src-advanced-body">
        <section class="provider-smoke-panel">
          <div class="provider-smoke-head">
            <h3>来源抽检 / 采样</h3>
            <small>样本字段分 · 当前预算 · 字段缺失</small>
          </div>
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
          <div v-if="providerSmokeReport" class="provider-smoke-result">
            <div class="psr-head">
              <strong>{{ providerSmokeReport.ok }} / {{ providerSmokeReport.total }}</strong>
              <span>诊断通过 · {{ providerSmokeReport.failed }} 失败</span>
              <small>{{ formatActionTime(providerSmokeReport.generated_at) }}</small>
            </div>
            <ul class="psr-list">
              <li v-for="report in providerSmokeReport.reports || []" :key="`${report.source}:${report.source_movie_id}`" :class="{ failed: !report.ok }">
                <strong>{{ report.name || report.source_movie_id }}</strong>
                <span class="status-pill" :class="report.ok ? 'health-healthy' : 'health-degraded'">{{ report.ok ? '通过' : '异常' }}</span>
                <small>{{ report.source }} · {{ report.duration_ms || 0 }} ms · 字段分 {{ report.quality?.score ?? 0 }}/{{ report.quality?.max_score ?? 0 }}</small>
                <small v-if="report.quality?.missing?.length">缺失 {{ report.quality.missing.join(', ') }}</small>
              </li>
            </ul>
          </div>
          <div class="provider-smoke-history">
            <div class="psh-head">
              <strong>最近诊断</strong>
              <button class="btn btn-ghost btn-xs" type="button" @click="$emit('load-smoke-runs')">刷新历史</button>
            </div>
            <ul v-if="providerSmokeRuns.length" class="psh-list">
              <li v-for="run in providerSmokeRuns" :key="run.id">
                <button type="button" @click="$emit('update:providerSmokeReport', run.response)">
                  <span>{{ formatActionTime(run.generated_at || run.created_at) }}</span>
                  <strong>{{ run.ok }} / {{ run.total }}</strong>
                  <small>{{ smokeRunLabel(run) }}</small>
                </button>
              </li>
            </ul>
            <small v-else class="psh-empty">运行诊断后会在这里保留最近样本</small>
          </div>
        </section>
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
    'load-smoke-runs',
    'pause-source',
    'resume-source',
  ],
  computed: {
    healthyRows() {
      return this.sourceHealthRows.filter(s => s.runtime_status === 'healthy')
    },
    degradedRows() {
      return this.sourceHealthRows.filter(s => ['degraded', 'cooling_down'].includes(s.runtime_status))
    },
    pausedRows() {
      return this.sourceHealthRows.filter(s => s.runtime_status === 'paused')
    },
    sourceHealthSummary() {
      return [
        { label: '接入来源', value: this.sourceHealthRows.length, tone: 'info' },
        { label: '可参与补全', value: this.healthyRows.length, tone: 'ok' },
        { label: '降级 / 冷却', value: this.degradedRows.length, tone: 'warn' },
        { label: '隔离 / 暂停', value: this.pausedRows.length, tone: 'bad' },
      ]
    },
  },
  methods: {
    sourceDotTone(source) {
      if (source.runtime_status === 'paused') return 'bad'
      if (['degraded', 'cooling_down'].includes(source.runtime_status)) return 'warn'
      if (source.runtime_status === 'healthy') return 'ok'
      return 'info'
    },
    sourceNextStep(source) {
      if (source.runtime_status === 'paused') return '恢复后复采'
      if (source.runtime_status === 'cooling_down') return '解除冷却'
      if (source.runtime_status === 'degraded' || (source.consecutive_failures || 0) >= 2) return '暂停 24h 隔离'
      if (source.runtime_status === 'healthy') return '保持采样'
      return '运行诊断采样'
    },
    sourceHealthPrimaryAction(source) {
      if (source.runtime_status === 'paused') return { event: 'resume-source', label: '恢复', tone: 'btn-primary' }
      if (source.runtime_status === 'cooling_down') return { event: 'resume-source', label: '解除冷却', tone: 'btn-primary' }
      return { event: 'pause-source', label: '暂停 24h', tone: 'btn-ghost' }
    },
    updateProviderSmokeForm(patch) {
      this.$emit('update:providerSmokeForm', { ...this.providerSmokeForm, ...patch })
    },
  },
}
</script>

<style scoped src="./supplementPanel.css"></style>
<style scoped src="./sourceHealthPanel.css"></style>
