<template>
  <div class="candidate-run-panel">
    <div class="candidate-run-head">
      <div>
        <strong>最近处理</strong>
        <span>复用批处理筛选，快速回收失败项</span>
      </div>
      <button class="link-btn" type="button" :disabled="loading" @click="$emit('refresh')">
        {{ loading ? '刷新中...' : '刷新记录' }}
      </button>
    </div>
    <div v-if="runs.length" class="candidate-run-list">
      <div v-for="run in runs" :key="run.id" class="candidate-run-row">
        <div class="candidate-run-main">
          <strong>{{ policyLabel(run.policy) }}</strong>
          <span>{{ triggerLabel(run.trigger_source) }} · {{ formatTime(run.created_at) }}</span>
        </div>
        <div class="candidate-run-stats">
          <span>处理 {{ run.total || 0 }}</span>
          <span>下发 {{ run.sent || 0 }}</span>
          <span>失败 {{ run.failed || 0 }}</span>
          <span>跳过 {{ run.skipped || 0 }}</span>
        </div>
        <div class="candidate-run-actions">
          <button class="link-btn" type="button" @click="$emit('apply', run)">套用筛选</button>
          <button v-if="run.failed" class="link-btn danger" type="button" @click="$emit('apply-failed', run)">失败队列</button>
          <button
            v-if="run.failed"
            class="link-btn danger"
            type="button"
            :disabled="processing"
            @click="$emit('retry-failed', run)"
          >
            重试失败
          </button>
        </div>
      </div>
    </div>
    <small v-else class="candidate-run-empty">暂无处理记录</small>
  </div>
</template>

<script>
export default {
  name: 'CandidateRunPanel',
  props: {
    runs: { type: Array, default: () => [] },
    loading: { type: Boolean, default: false },
    processing: { type: [Boolean, String], default: false },
  },
  emits: ['refresh', 'apply', 'apply-failed', 'retry-failed'],
  methods: {
    formatTime(time) {
      if (!time) return '—'
      return new Date(time).toLocaleString()
    },
    policyLabel(policy) {
      const map = { manual: '人工批准', rules: '规则自动', auto: '全自动' }
      return map[policy] || '人工批准'
    },
    triggerLabel(trigger) {
      const map = { manual: '人工触发', system: '系统触发' }
      return map[trigger] || trigger || '未知触发'
    },
  },
}
</script>

<style scoped>
.candidate-run-panel {
  border: 1px solid var(--glass-edge);
  border-radius: var(--radius-card);
  padding: 16px;
  background: var(--surface-specular-edge-strong), var(--surface-noise), var(--material-glass-sheet);
  box-shadow: var(--glass-surface-shadow);
  backdrop-filter: blur(var(--glass-blur-surface)) saturate(var(--glass-saturate-surface));
  -webkit-backdrop-filter: blur(var(--glass-blur-surface)) saturate(var(--glass-saturate-surface));
}
.candidate-run-head,
.candidate-run-row,
.candidate-run-stats,
.candidate-run-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}
.candidate-run-head {
  justify-content: space-between;
  margin-bottom: 12px;
}
.candidate-run-head strong,
.candidate-run-main strong {
  display: block;
  color: var(--text-primary);
}
.candidate-run-head span,
.candidate-run-main span,
.candidate-run-stats span,
.candidate-run-empty {
  color: var(--text-secondary);
  font-size: 12px;
}
.candidate-run-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.candidate-run-row {
  justify-content: space-between;
  padding: 12px;
  border-radius: var(--radius-md);
  border: 1px solid var(--glass-control-border);
  background: var(--surface-specular-edge), var(--surface-noise), var(--material-glass-control);
  box-shadow: var(--glass-control-shadow);
}
.candidate-run-main {
  min-width: 170px;
}
.candidate-run-stats {
  flex-wrap: wrap;
}
.candidate-run-stats span {
  display: inline-flex;
  align-items: center;
  min-height: 26px;
  padding: 3px 9px;
  border: 1px solid var(--glass-control-border);
  border-radius: 999px;
  background: var(--surface-specular-edge), var(--surface-noise), var(--material-glass-subtle);
  box-shadow: var(--glass-inner-shadow);
}
.candidate-run-actions {
  margin-left: auto;
}
</style>
