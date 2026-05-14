<template>
  <div class="apple-empty-state apple-surface">
    <div class="empty-orb"></div>
    <h3>{{ title }}</h3>
    <p>{{ description }}</p>
    <button v-if="actionLabel" class="empty-action" type="button" @click="$emit('action')">{{ actionLabel }}</button>
  </div>
</template>

<script setup>
defineProps({
  title: { type: String, default: '暂无内容' },
  description: { type: String, default: '换个条件再试试。' },
  actionLabel: { type: String, default: '' },
})

defineEmits(['action'])
</script>

<style scoped>
.apple-empty-state {
  max-width: 460px;
  margin: 48px auto;
  padding: 38px 32px;
  text-align: center;
  color: var(--text-secondary);
}

.empty-orb {
  width: 56px;
  height: 56px;
  margin: 0 auto 18px;
  border-radius: 20px;
  background:
    radial-gradient(circle at 30% 20%, rgba(var(--accent-rgb), 0.18), transparent 42%),
    var(--surface-control);
  border: 1px solid var(--border-light);
  box-shadow: none;
}

h3 {
  margin: 0 0 8px;
  color: var(--text-primary);
  font-size: var(--type-panel-title);
  letter-spacing: 0;
}

p {
  margin: 0;
  line-height: 1.7;
}

.empty-action {
  margin-top: 20px;
  min-height: var(--touch-target);
  padding: 0 18px;
  border-radius: var(--radius-control);
  border: 1px solid transparent;
  background: var(--accent);
  color: var(--text-on-accent);
  cursor: pointer;
  transition: transform var(--motion-fast), background var(--motion-fast);
}

.empty-action:hover {
  transform: translateY(-1px);
  background: var(--accent-light);
}
</style>
