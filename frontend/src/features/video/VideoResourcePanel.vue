<template>
  <div class="resource-panel">
    <div class="resource-heading">
      <strong>115 播放资源</strong>
      <span>默认资源优先播放，也可临时选择其他文件</span>
    </div>
    <div class="resource-list">
      <div v-for="resource in resources" :key="resource.id" class="resource-row"
        :class="{ 'is-default': resource.is_default }">
        <button class="resource-main" type="button" @click="$emit('play', resource.id)">
          <span class="resource-name">{{ resource.name }}</span>
          <span class="resource-meta">
            {{ String(resource.extension || '').toUpperCase() }} · {{ formatSize(resource.size) }}
          </span>
        </button>
        <span v-if="resource.is_default" class="resource-default">默认</span>
        <button v-else class="resource-default-action" type="button"
          @click="$emit('make-default', resource)">设为默认</button>
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({ resources: { type: Array, default: () => [] } })
defineEmits(['play', 'make-default'])

function formatSize(size) {
  const value = Number(size || 0)
  if (value <= 0) return '未知大小'
  const units = ['B', 'KB', 'MB', 'GB', 'TB']
  const index = Math.min(Math.floor(Math.log(value) / Math.log(1024)), units.length - 1)
  return `${(value / (1024 ** index)).toFixed(index >= 3 ? 2 : 0)} ${units[index]}`
}
</script>

<style scoped>
.resource-panel {
  margin-top: var(--space-5);
  padding: var(--space-4);
  border: 1px solid var(--modal-panel-border);
  border-radius: var(--radius-lg);
  background: var(--surface-specular-edge), var(--surface-noise), var(--modal-panel-bg);
}
.resource-heading {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: var(--space-3);
  margin-bottom: var(--space-3);
}
.resource-heading strong { color: var(--modal-text-primary); font-size: var(--type-body); }
.resource-heading span, .resource-meta { color: var(--modal-text-muted); font-size: var(--type-caption-1); }
.resource-list { display: grid; gap: var(--space-2); }
.resource-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: center;
  gap: var(--space-3);
  min-width: 0;
  padding: var(--space-2) var(--space-3);
  border: 1px solid transparent;
  border-radius: var(--radius-md);
  background: var(--modal-panel-bg);
}
.resource-row.is-default { border-color: var(--accent); }
.resource-main, .resource-default-action {
  border: 0;
  background: transparent;
  color: inherit;
  cursor: pointer;
}
.resource-main { display: grid; min-width: 0; gap: 2px; padding: 0; text-align: left; }
.resource-name {
  overflow: hidden;
  color: var(--modal-text-primary);
  font-size: var(--type-subheadline);
  font-weight: 600;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.resource-default, .resource-default-action { font-size: var(--type-caption-1); }
.resource-default { color: var(--accent); font-weight: 700; }
.resource-default-action { padding: var(--space-1) var(--space-2); color: var(--modal-text-muted); }
.resource-default-action:hover { color: var(--accent); }
@media (max-width: 640px) {
  .resource-heading { align-items: flex-start; flex-direction: column; }
}
</style>
