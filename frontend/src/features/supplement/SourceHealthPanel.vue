<template>
  <section class="workspace-panel apple-surface">
    <div class="panel-header">
      <div>
        <p class="eyebrow">Health</p>
        <h2>来源状态</h2>
      </div>
      <div class="source-health-toolbar">
        <button class="btn btn-ghost btn-sm" type="button" @click="$emit('refresh-health')">刷新</button>
        <button class="btn btn-primary btn-sm" type="button" :disabled="providerSmokeLoading" @click="$emit('run-smoke')">
          {{ providerSmokeLoading ? '诊断中...' : '运行诊断' }}
        </button>
      </div>
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
        placeholder="source_movie_id"
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
          <p>{{ report.source }} · {{ report.source_movie_id }} · {{ report.duration_ms || 0 }}ms</p>
          <small>字段分 {{ report.quality?.score ?? 0 }} / {{ report.quality?.max_score ?? 0 }}</small>
          <small v-if="report.quality?.missing?.length">缺失 {{ report.quality.missing.join(', ') }}</small>
          <small v-if="report.quality?.warnings?.length">警告 {{ report.quality.warnings.join(', ') }}</small>
          <small v-if="report.error">{{ report.error_type || 'error' }} · {{ report.error }}</small>
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
      <small v-else class="empty-inline">暂无诊断历史</small>
    </div>
    <div v-if="sourceHealthLoading" class="loading-wrap"><div class="spinner-large"></div></div>
    <div v-else class="source-health-grid">
      <article v-for="source in sourceHealthRows" :key="source.source" class="source-health-card">
        <div>
          <strong>{{ source.display_name || source.source }}</strong>
          <span>{{ source.source }}</span>
        </div>
        <span class="status-pill" :class="`health-${source.runtime_status}`">{{ sourceHealthLabel(source.runtime_status) }}</span>
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
            v-if="source.runtime_status === 'paused'"
            class="btn btn-primary btn-xs"
            type="button"
            :disabled="sourceActionLoading === source.source"
            @click="$emit('resume-source', source.source)"
          >恢复</button>
          <button
            v-else
            class="btn btn-ghost btn-xs"
            type="button"
            :disabled="sourceActionLoading === source.source"
            @click="$emit('pause-source', source.source)"
          >暂停 24h</button>
        </div>
      </article>
    </div>
  </section>
</template>

<script>
import GlassSelect from '../../components/GlassSelect.vue'

export default {
  name: 'SourceHealthPanel',
  components: { GlassSelect },
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
  methods: {
    updateProviderSmokeForm(patch) {
      this.$emit('update:providerSmokeForm', { ...this.providerSmokeForm, ...patch })
    },
  },
}
</script>
