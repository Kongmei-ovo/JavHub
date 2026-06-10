<template>
  <div class="vp-sources">
    <div class="vp-sources-head">
      <span class="vp-sources-label">播放源</span>
      <span v-if="!scanDone" class="vp-sources-spinner" />
      <span class="vp-sources-hint">{{ scanDone ? '扫描完成' : '搜索中…' }}</span>
    </div>
    <div class="vp-sources-list">
      <button
        v-for="s in visibleSources"
        :key="s.source"
        type="button"
        :class="[
          'vp-source-btn',
          `vp-source--${s.status}`,
          { 'vp-source--active': current === s.source },
        ]"
        :disabled="s.status !== 'ok'"
        :title="s.status === 'ok' ? s.title : s.detail"
        @click="$emit('switch', s.source)"
      >
        <span :class="['vp-source-dot', `vp-source-dot--${s.status}`]" />
        <span class="vp-source-name">{{ sourceLabel(s.source) }}</span>
        <span class="vp-source-time">{{ (s.elapsed_ms / 1000).toFixed(1) }}s</span>
      </button>
    </div>
  </div>
</template>

<script>
const LABELS = {
  jable: 'Jable',
  missav: 'MissAV',
  kanav: 'KanAV',
  hohoj: 'HohoJ',
}

export default {
  name: 'StreamSourcePicker',
  emits: ['switch'],
  props: {
    sources: { type: Array, default: () => [] },
    current: { type: String, default: '' },
    scanDone: { type: Boolean, default: false },
  },
  computed: {
    visibleSources() {
      return this.sources.filter(s => s.source !== '_done')
    },
  },
  methods: {
    sourceLabel(name) { return LABELS[name] || name },
  },
}
</script>

<style scoped>
/* picker 嵌在 vp-container 内,自己不再叠一层玻璃,只做轻量胶囊条 */
.vp-sources {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}
.vp-sources-head {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-size: var(--type-caption);
  font-weight: 550;
  color: var(--text-muted);
}
.vp-sources-label {
  color: var(--text-secondary);
  font-weight: 700;
}
.vp-sources-hint { color: var(--text-muted); }
.vp-sources-spinner {
  width: 11px;
  height: 11px;
  border-radius: 50%;
  border: 2px solid var(--hairline-strong);
  border-top-color: var(--accent);
  animation: vp-pickerspin 0.7s linear infinite;
}
@keyframes vp-pickerspin { to { transform: rotate(360deg); } }

.vp-sources-list {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}

.vp-source-btn {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-3);
  border-radius: var(--radius-control);
  background: var(--surface-specular-edge), var(--surface-noise), var(--material-glass-control);
  border: 1px solid var(--glass-control-border);
  box-shadow: var(--glass-control-shadow);
  backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
  -webkit-backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
  color: var(--text-secondary);
  font-size: var(--type-caption);
  font-weight: 550;
  cursor: pointer;
  transition: transform var(--motion-standard), opacity var(--motion-fast);
  pointer-events: auto;
}
.vp-source-btn:disabled {
  opacity: 0.42;
  cursor: not-allowed;
}
.vp-source-btn:not(:disabled):hover {
  background: var(--surface-specular-edge-strong), var(--surface-noise), var(--material-glass-control-hover);
  border-color: var(--glass-control-border-hover);
  box-shadow: var(--glass-control-shadow-hover);
  color: var(--text-primary);
}
.vp-source-btn:focus-visible {
  outline: none;
  box-shadow: var(--glass-control-shadow-hover), var(--focus-ring-wide);
}

.vp-source-name {
  font-weight: 700;
}
.vp-source-time {
  font-family: var(--font-mono);
  font-size: var(--type-micro);
  color: var(--text-muted);
  font-variant-numeric: tabular-nums;
}

.vp-source-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--text-muted);
  flex-shrink: 0;
}
.vp-source-dot--ok { background: var(--ok); }
.vp-source-dot--no_result { background: var(--hairline-strong); }
.vp-source-dot--error { background: var(--bad); }

/* Active = 实心 accent 胶囊,呼应设计文档 accent 用于"主按钮/激活态/关键数字" */
.vp-source--active {
  background: var(--surface-specular-edge-strong), var(--surface-noise), var(--glass-active-material);
  border-color: var(--glass-active-border);
  box-shadow: var(--glass-active-shadow);
  color: var(--text-primary);
  font-weight: 700;
}
.vp-source--active:not(:disabled):hover {
  background: var(--surface-specular-edge-strong), var(--surface-noise), var(--glass-active-material);
  border-color: var(--glass-active-border);
  box-shadow: var(--glass-active-shadow);
  color: var(--text-primary);
}
.vp-source--active .vp-source-time { color: var(--text-muted); }
</style>
