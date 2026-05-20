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
  border: 1px solid transparent;
  background: var(--accent);
  color: var(--text-on-accent);
  cursor: pointer;
  transition: transform var(--motion-fast), background var(--motion-fast);
}

button:hover {
  transform: translateY(-1px);
  background: var(--accent-light);
}

button:disabled {
  opacity: 0.55;
  cursor: not-allowed;
  transform: none;
}
</style>
