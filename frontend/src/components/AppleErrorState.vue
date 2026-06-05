<template>
  <div class="apple-error-state apple-surface">
    <div>
      <h3>{{ title }}</h3>
      <p>{{ description }}</p>
      <small v-if="sourceLabel || details">
        <span v-if="sourceLabel">{{ sourceLabel }}</span>
        <span v-if="sourceLabel && details"> · </span>
        <span v-if="details">{{ details }}</span>
      </small>
    </div>
    <button v-if="retryLabel" type="button" :disabled="retrying" @click="$emit('retry')">
      {{ retrying ? '重试中...' : retryLabel }}
    </button>
  </div>
</template>

<script setup>
defineProps({
  title: { type: String, default: '加载失败' },
  description: { type: String, default: '请稍后重试。' },
  retryLabel: { type: String, default: '重试' },
  sourceLabel: { type: String, default: '' },
  details: { type: String, default: '' },
  retrying: { type: Boolean, default: false },
})

defineEmits(['retry'])
</script>

<style scoped>
.apple-error-state {
  --apple-state-action-bg: var(--glass-active-material);
  --apple-state-action-bg-hover: var(--material-glass-control-hover);
  --apple-state-action-border: var(--glass-active-border);
  --apple-state-action-border-hover: var(--glass-control-border-hover);
  --apple-state-action-shadow: var(--glass-active-shadow);
  --apple-state-action-shadow-hover: var(--glass-control-shadow-hover);
  --apple-state-action-text: var(--text-primary);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  max-width: 720px;
  margin: 24px auto;
  padding: 18px 20px;
}

h3 {
  margin: 0 0 4px;
  color: var(--text-primary);
  font-size: var(--type-card-title);
  letter-spacing: 0;
}

p {
  margin: 0;
  color: var(--text-secondary);
  font-size: var(--type-control);
}

small {
  display: block;
  margin-top: 6px;
  color: var(--text-muted);
  font-size: var(--type-caption);
}

button {
  min-height: var(--touch-target);
  padding: 0 14px;
  border-radius: var(--radius-control);
  border: 1px solid var(--apple-state-action-border);
  background:
    var(--surface-specular-edge-strong),
    var(--surface-noise),
    var(--apple-state-action-bg);
  color: var(--apple-state-action-text);
  box-shadow: var(--apple-state-action-shadow);
  backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
  -webkit-backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
  cursor: pointer;
  transition: transform var(--motion-standard), background var(--motion-standard), border-color var(--motion-standard), box-shadow var(--motion-standard), opacity var(--motion-fast);
}

button:hover {
  transform: translateY(-1px);
  background:
    var(--surface-specular-edge),
    var(--surface-noise),
    var(--apple-state-action-bg-hover);
  border-color: var(--apple-state-action-border-hover);
  box-shadow: var(--apple-state-action-shadow-hover);
}

button:disabled {
  opacity: 0.55;
  cursor: not-allowed;
  transform: none;
}
</style>
