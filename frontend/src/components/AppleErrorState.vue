<template>
  <div class="apple-error-state apple-surface">
    <div>
      <h3>{{ title }}</h3>
      <p>{{ description }}</p>
    </div>
    <button v-if="retryLabel" type="button" @click="$emit('retry')">{{ retryLabel }}</button>
  </div>
</template>

<script setup>
defineProps({
  title: { type: String, default: '加载失败' },
  description: { type: String, default: '请稍后重试。' },
  retryLabel: { type: String, default: '重试' },
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
  font-size: 15px;
}

p {
  margin: 0;
  color: var(--text-secondary);
  font-size: 13px;
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
</style>
