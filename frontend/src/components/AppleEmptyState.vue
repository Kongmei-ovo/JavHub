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
  --apple-state-orb-bg: var(--material-glass-control);
  --apple-state-orb-border: var(--glass-control-border);
  --apple-state-orb-shadow: var(--glass-control-shadow);
  --apple-state-action-bg: var(--glass-active-material);
  --apple-state-action-bg-hover: var(--material-glass-control-hover);
  --apple-state-action-border: var(--glass-active-border);
  --apple-state-action-border-hover: var(--glass-control-border-hover);
  --apple-state-action-shadow: var(--glass-active-shadow);
  --apple-state-action-shadow-hover: var(--glass-control-shadow-hover);
  --apple-state-action-text: var(--text-primary);
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
    var(--surface-specular-edge),
    var(--surface-noise),
    var(--apple-state-orb-bg);
  border: 1px solid var(--apple-state-orb-border);
  box-shadow: var(--apple-state-orb-shadow);
  backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
  -webkit-backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
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

.empty-action:hover {
  transform: translateY(-1px);
  background:
    var(--surface-specular-edge),
    var(--surface-noise),
    var(--apple-state-action-bg-hover);
  border-color: var(--apple-state-action-border-hover);
  box-shadow: var(--apple-state-action-shadow-hover);
}
</style>
