<template>
  <!-- 全站统一的刷新控件:裸 ⟳ 图标(C 级 18px)、幽灵态(不抢主色)、固定放在动作组最右。 -->
  <button
    class="refresh-btn"
    type="button"
    :class="{ 'is-loading': loading }"
    :disabled="disabled || loading"
    :aria-label="label"
    :title="label"
    @click="$emit('click', $event)"
  >
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" width="18" height="18" aria-hidden="true">
      <polyline points="23 4 23 10 17 10" />
      <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10" />
    </svg>
  </button>
</template>

<script>
export default {
  name: 'RefreshButton',
  props: {
    loading: { type: Boolean, default: false },
    disabled: { type: Boolean, default: false },
    label: { type: String, default: '刷新' },
  },
  emits: ['click'],
}
</script>

<style scoped>
.refresh-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex: 0 0 auto;
  width: 34px;
  height: 34px;
  padding: 0;
  border: 1px solid transparent;
  border-radius: var(--radius-control);
  background: transparent;
  color: var(--text-secondary);
  cursor: pointer;
  transition: transform var(--motion-standard), opacity var(--motion-fast);
}
.refresh-btn:hover:not(:disabled) {
  color: var(--text-primary);
  background: color-mix(in srgb, var(--text-primary) 8%, transparent);
}
.refresh-btn:focus-visible {
  outline: none;
  color: var(--text-primary);
  box-shadow: var(--focus-ring);
}
.refresh-btn:active:not(:disabled) { transform: scale(0.96); }
.refresh-btn:disabled { opacity: 0.55; cursor: not-allowed; }
.refresh-btn.is-loading svg { animation: refresh-spin 0.9s linear infinite; }

@keyframes refresh-spin { to { transform: rotate(360deg); } }

@media (prefers-reduced-motion: reduce) {
  .refresh-btn.is-loading svg { animation-duration: 0.01ms; animation-iteration-count: 1; }
}
</style>
