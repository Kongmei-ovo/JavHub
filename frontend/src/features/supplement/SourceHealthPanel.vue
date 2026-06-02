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
  computed: {
    avatarJobRunning() {
      const status = this.gfriendsAvatarJob?.status
      return status === 'queued' || status === 'running'
    },
  },
  methods: {
    avatarJobStatusLabel(status) {
      const map = { queued: '排队中', running: '同步中', succeeded: '已完成', failed: '失败', idle: '待开始' }
      return map[status] || status || '待开始'
    },
    updateProviderSmokeForm(patch) {
      this.$emit('update:providerSmokeForm', { ...this.providerSmokeForm, ...patch })
    },
  },
}
</script>

<style scoped>
.workspace-panel {
  padding: 18px;
  border-radius: var(--radius-card);
}

.workspace-panel h2,
.workspace-panel p {
  margin: 0;
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  margin-bottom: 14px;
}

.panel-header h2 {
  color: var(--text-primary);
  font-size: 20px;
}

.source-health-toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: flex-end;
}

.provider-smoke-controls {
  display: grid;
  grid-template-columns: minmax(150px, 220px) minmax(180px, 1fr) auto;
  gap: 10px;
  margin-bottom: 14px;
}

.provider-smoke-controls .glass-select {
  width: 100%;
}

.filter-input {
  min-height: 44px;
  padding: 0 14px;
  color: var(--text-primary);
  background: var(--material-glass-control);
  border: 1px solid var(--glass-control-border);
  border-radius: 999px;
  box-shadow: var(--glass-control-shadow);
  backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
  -webkit-backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
  outline: none;
  font-size: 13px;
  transition: background var(--motion-standard), border-color var(--motion-standard), box-shadow var(--motion-standard);
}

.filter-input:focus {
  border-color: var(--glass-active-border);
  background: var(--glass-active-material);
  box-shadow: var(--glass-active-shadow);
}

.avatar-sync-panel {
  display: grid;
  gap: 12px;
  margin-bottom: 14px;
  padding: 14px;
  border: 1px solid var(--glass-control-border);
  border-radius: 16px;
  background: var(--material-glass-sheet);
  box-shadow: var(--glass-surface-shadow);
  backdrop-filter: blur(var(--glass-blur-surface)) saturate(var(--glass-saturate-surface));
  -webkit-backdrop-filter: blur(var(--glass-blur-surface)) saturate(var(--glass-saturate-surface));
}

.avatar-sync-head,
.avatar-sync-actions,
.avatar-sync-steps {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.avatar-sync-head {
  justify-content: space-between;
}

.avatar-sync-head h3 {
  color: var(--text-primary);
  font-size: 16px;
}

.avatar-sync-head p,
.avatar-sync-footnote,
.avatar-sync-error {
  margin-top: 4px;
  color: var(--text-muted);
  font-size: 12px;
  line-height: 1.5;
}

.avatar-sync-error {
  color: var(--badge-error-text);
  overflow-wrap: anywhere;
}

.avatar-sync-metrics {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 8px;
}

.avatar-sync-metrics div {
  padding: 10px 12px;
  border: 1px solid var(--glass-control-border);
  border-radius: 12px;
  background: var(--material-glass-control);
  box-shadow: var(--glass-control-shadow);
  backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
  -webkit-backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
}

.avatar-sync-metrics strong {
  display: block;
  color: var(--text-primary);
  font-size: 18px;
}

.avatar-sync-metrics span,
.avatar-sync-steps span {
  color: var(--text-muted);
  font-size: 12px;
}

.avatar-sync-steps.active span {
  color: var(--text-secondary);
}

.mini-spinner {
  width: 16px;
  height: 16px;
  border: 2px solid var(--glass-control-border);
  border-top-color: var(--badge-info-text);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

.provider-smoke-panel {
  display: grid;
  gap: 12px;
  margin-bottom: 14px;
}

.provider-smoke-summary {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 14px;
  padding: 12px 14px;
  border: 1px solid var(--glass-control-border);
  border-radius: 14px;
  background: var(--material-glass-sheet);
  box-shadow: var(--glass-surface-shadow);
  backdrop-filter: blur(var(--glass-blur-surface)) saturate(var(--glass-saturate-surface));
  -webkit-backdrop-filter: blur(var(--glass-blur-surface)) saturate(var(--glass-saturate-surface));
}

.provider-smoke-summary div {
  display: grid;
  gap: 2px;
}

.provider-smoke-summary strong {
  color: var(--text-primary);
  font-size: 18px;
}

.provider-smoke-summary span,
.provider-smoke-summary small {
  color: var(--text-muted);
  font-size: 12px;
}

.provider-smoke-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 12px;
}

.provider-smoke-card {
  display: grid;
  gap: 7px;
  min-width: 0;
  padding: 12px;
  border: 1px solid var(--glass-control-border);
  border-radius: 14px;
  background: var(--material-glass-control);
  box-shadow: var(--glass-control-shadow);
  backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
  -webkit-backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
}

.provider-smoke-card.failed {
  border-color: var(--badge-error-border);
}

.provider-smoke-card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.provider-smoke-card strong {
  min-width: 0;
  overflow-wrap: anywhere;
  color: var(--text-primary);
}

.provider-smoke-card p,
.provider-smoke-card small {
  color: var(--text-muted);
  font-size: 12px;
  overflow-wrap: anywhere;
}

.provider-smoke-detail {
  display: grid;
  gap: 3px;
  padding-top: 4px;
}

.provider-smoke-detail span {
  color: var(--text-muted);
  font-size: 11px;
}

.provider-smoke-history {
  display: grid;
  gap: 10px;
  margin-bottom: 14px;
  padding: 12px;
  border: 1px solid var(--glass-control-border);
  border-radius: 14px;
  background: var(--material-glass-sheet);
  box-shadow: var(--glass-surface-shadow);
  backdrop-filter: blur(var(--glass-blur-surface)) saturate(var(--glass-saturate-surface));
  -webkit-backdrop-filter: blur(var(--glass-blur-surface)) saturate(var(--glass-saturate-surface));
}

.provider-smoke-history-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.provider-smoke-history-head strong {
  color: var(--text-primary);
}

.provider-smoke-run-list {
  display: grid;
  gap: 8px;
}

.provider-smoke-run {
  display: grid;
  grid-template-columns: minmax(140px, 1fr) auto minmax(120px, 1fr);
  gap: 10px;
  align-items: center;
  min-width: 0;
  padding: 9px 10px;
  border: 1px solid var(--glass-control-border);
  border-radius: 12px;
  background: var(--material-glass-control);
  box-shadow: var(--glass-control-shadow);
  backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
  -webkit-backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
  color: inherit;
  cursor: pointer;
  text-align: left;
  transition: transform var(--motion-fast), background var(--motion-standard), border-color var(--motion-standard), box-shadow var(--motion-standard);
}

.provider-smoke-run:hover {
  transform: translateY(-1px);
  border-color: var(--glass-control-border-hover);
  background: var(--material-glass-control-hover);
  box-shadow: var(--glass-control-shadow-hover);
}

.provider-smoke-run span,
.provider-smoke-run small {
  color: var(--text-muted);
  font-size: 12px;
  overflow-wrap: anywhere;
}

.provider-smoke-run strong {
  color: var(--text-primary);
}

.source-health-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 12px;
}

.source-health-card {
  display: grid;
  gap: 10px;
  padding: 14px;
  border: 1px solid var(--glass-control-border);
  border-radius: 16px;
  background: var(--material-glass-sheet);
  box-shadow: var(--glass-surface-shadow);
  backdrop-filter: blur(var(--glass-blur-surface)) saturate(var(--glass-saturate-surface));
  -webkit-backdrop-filter: blur(var(--glass-blur-surface)) saturate(var(--glass-saturate-surface));
}

.source-health-card strong {
  display: block;
  color: var(--text-primary);
  font-size: 15px;
}

.source-health-card span,
.source-health-card p,
.source-health-card small {
  color: var(--text-muted);
  font-size: 12px;
}

.source-budget-meter {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 12px;
  border: 1px solid var(--glass-control-border);
  border-radius: 12px;
  background: var(--material-glass-control);
  box-shadow: var(--glass-control-shadow);
  backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
  -webkit-backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
}

.source-budget-meter strong {
  font-size: 18px;
}

.source-budget-meter span,
.source-budget-meter small {
  color: var(--text-muted);
  font-size: 11px;
}

.source-budget-meter small {
  text-align: right;
}

.source-health-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

.status-pill {
  display: inline-flex;
  align-items: center;
  min-height: 26px;
  padding: 3px 9px;
  border: 1px solid var(--badge-info-border);
  border-radius: 999px;
  color: var(--badge-info-text);
  background: var(--badge-info-bg);
  font-size: 12px;
  font-weight: 700;
  white-space: nowrap;
}

.status-succeeded {
  color: var(--badge-success-text);
  background: var(--badge-success-bg);
  border-color: var(--badge-success-border);
}

.status-running,
.status-queued {
  color: var(--badge-warning-text);
  background: var(--badge-warning-bg);
  border-color: var(--badge-warning-border);
}

.status-failed {
  color: var(--badge-error-text);
  background: var(--badge-error-bg);
  border-color: var(--badge-error-border);
}

.status-idle {
  color: var(--badge-pending-text);
  background: var(--badge-pending-bg);
  border-color: var(--badge-pending-border);
}

.health-healthy {
  color: var(--badge-success-text);
  background: var(--badge-success-bg);
  border-color: var(--badge-success-border);
}

.health-degraded {
  color: var(--badge-warning-text);
  background: var(--badge-warning-bg);
  border-color: var(--badge-warning-border);
}

.health-cooling_down {
  color: var(--badge-error-text);
  background: var(--badge-error-bg);
  border-color: var(--badge-error-border);
}

.health-paused {
  color: var(--badge-pending-text);
  background: var(--badge-pending-bg);
  border-color: var(--badge-pending-border);
}

.health-unknown {
  color: var(--text-muted);
}

.loading-wrap {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 140px;
}

.spinner-large {
  width: 28px;
  height: 28px;
  border: 2px solid var(--glass-control-border);
  border-top-color: var(--badge-info-text);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

.empty-inline {
  padding: 20px;
  color: var(--text-muted);
  text-align: center;
}

.btn-xs {
  min-height: 28px;
  padding: 5px 9px;
  font-size: 11px;
}

.btn-sm {
  min-height: 36px;
  padding: 8px 12px;
  font-size: 12px;
}

@media (max-width: 860px) {
  .panel-header {
    align-items: flex-start;
    flex-direction: column;
  }

  .source-health-toolbar {
    justify-content: flex-start;
  }

  .provider-smoke-controls,
  .provider-smoke-run,
  .avatar-sync-metrics {
    grid-template-columns: 1fr;
  }
}
</style>
