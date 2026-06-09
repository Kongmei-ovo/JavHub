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
        :class="['vp-source-btn', `vp-source-${s.status}`, { active: current === s.source }]"
        :disabled="s.status !== 'ok'"
        :title="s.status === 'ok' ? s.title : s.detail"
        @click="$emit('switch', s.source)"
      >
        <span class="vp-source-name">{{ s.source }}</span>
        <span class="vp-source-meta">
          <span v-if="s.status === 'ok'">✓</span>
          <span v-else-if="s.status === 'no_result'">空</span>
          <span v-else>×</span>
          · {{ (s.elapsed_ms / 1000).toFixed(1) }}s
        </span>
      </button>
    </div>
  </div>
</template>

<script>
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
}
</script>

<style scoped>
/* 浮层模式: 平级于 HlsPlayerOverlay 时贴在视口底部居中。 */
.vp-sources.vp-sources-floating {
  position: fixed;
  bottom: max(var(--space-5), env(safe-area-inset-bottom, 0px));
  left: 50%;
  transform: translateX(-50%);
  z-index: calc(var(--z-modal) + 1);
  width: min(720px, calc(100vw - var(--space-6)));
}
.vp-sources {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  padding: var(--space-4);
  border-radius: var(--radius-lg);
  background: var(--surface-specular-edge), var(--surface-noise), var(--material-glass-control);
  border: var(--stroke-pro) solid var(--glass-control-border);
  box-shadow: var(--glass-control-shadow);
  backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
  -webkit-backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
}
.vp-sources-head {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-size: var(--type-caption);
  color: var(--text-secondary);
}
.vp-sources-label { font-weight: 700; color: var(--text-primary); }
.vp-sources-hint { color: var(--text-muted); }
.vp-sources-spinner {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  border: 2px solid var(--glass-control-border);
  border-top-color: var(--accent);
  animation: vp-pickerspin 0.7s linear infinite;
}
@keyframes vp-pickerspin { to { transform: rotate(360deg); } }
.vp-sources-list { display: flex; flex-wrap: wrap; gap: var(--space-2); }
.vp-source-btn {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-4);
  border-radius: var(--radius-control);
  background: var(--surface-specular-edge), var(--surface-noise), var(--material-glass-control);
  border: var(--stroke-pro) solid var(--glass-control-border);
  color: var(--text-secondary);
  font-size: var(--type-caption);
  cursor: pointer;
  transition: transform var(--motion-standard), opacity var(--motion-fast);
}
.vp-source-btn:disabled { opacity: 0.5; cursor: not-allowed; }
.vp-source-name { font-weight: 700; font-family: var(--font-mono); }
.vp-source-meta { font-size: var(--type-micro); color: var(--text-muted); }
.vp-source-ok { color: var(--text-primary); }
.vp-source-no_result { opacity: 0.55; }
.vp-source-error { opacity: 0.55; color: var(--text-muted); }
.vp-source-btn:not(:disabled):hover {
  background: var(--surface-specular-edge-strong), var(--surface-noise), var(--material-glass-control-hover);
  border-color: var(--glass-control-border-hover);
  box-shadow: var(--glass-control-shadow-hover);
}
.vp-source-btn.active {
  background: var(--surface-specular-edge-strong), var(--surface-noise), var(--glass-active-material);
  border-color: var(--glass-active-border);
  box-shadow: var(--glass-active-shadow);
  color: var(--text-primary);
}
</style>
