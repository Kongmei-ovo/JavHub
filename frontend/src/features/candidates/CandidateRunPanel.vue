<template>
  <div class="candidate-run-panel" :class="{ bare }">
    <div class="candidate-run-head">
      <div class="candidate-run-title">
        <strong v-if="!bare">最近处理</strong>
        <span v-if="!runs.length" class="candidate-run-empty">暂无处理记录</span>
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
  </div>
</template>

<script>
export default {
  name: 'CandidateRunPanel',
  props: {
    runs: { type: Array, default: () => [] },
    loading: { type: Boolean, default: false },
    processing: { type: [Boolean, String], default: false },
    // 嵌进「最近处理」弹窗时去掉自身卡片外壳与重复标题，避免卡中卡。
    bare: { type: Boolean, default: false },
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
  background: var(--card);
  box-shadow: var(--shadow-card);
}
.candidate-run-panel.bare {
  border: 0;
  border-radius: 0;
  padding: 0;
  background: none;
  box-shadow: none;
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
/* 空态「暂无处理记录」与标题同一行(虚化小字,不再独占大块) */
.candidate-run-title { display: inline-flex; align-items: baseline; gap: 8px; }
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
  font-size: var(--type-caption);
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
  border: 1px solid var(--hairline);
  background: var(--card-2);
  box-shadow: none;
  transition: transform var(--motion-standard);
}
.candidate-run-row:hover {
  border-color: var(--hairline-strong);
  background: var(--card-hover);
  box-shadow: var(--shadow-card);
  transform: translateY(-1px);
}
.candidate-run-row:focus-within {
  border-color: var(--hairline-strong);
  background: var(--card-hover);
  box-shadow: var(--shadow-card), var(--focus-ring);
  transform: translateY(-1px);
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
  border: 1px solid var(--hairline);
  border-radius: 999px;
  background: var(--card);
  box-shadow: none;
}
.candidate-run-actions {
  margin-left: auto;
}

/* 这些按钮原来依赖父组件 scoped 的 .link-btn,本组件作用域里取不到 → 之前没样式。 */
.link-btn {
  background: none;
  border: 0;
  padding: 2px 0;
  font-family: inherit;
  font-size: var(--type-control);
  font-weight: 600;
  color: var(--accent);
  cursor: pointer;
  transition: opacity var(--motion-fast);
}
.link-btn:hover:not(:disabled) { opacity: 0.7; }
.link-btn:disabled { opacity: 0.45; cursor: not-allowed; }
.link-btn.danger { color: var(--bad); }
</style>
