<template>
  <div :class="['apple-empty-state apple-surface', `apple-empty-state--${density}`]">
    <div class="empty-orb" aria-hidden="true">
      <slot name="icon"></slot>
    </div>
    <div class="apple-state-copy">
      <h3>{{ title }}</h3>
      <p>{{ description }}</p>
      <p v-if="nextStep" class="empty-next-step">{{ nextStep }}</p>
    </div>
    <div v-if="hasActions" class="apple-state-actions">
      <button v-if="actionLabel" class="empty-action empty-action--primary" type="button" @click="$emit('action')">{{ actionLabel }}</button>
      <button v-if="secondaryActionLabel" class="empty-action empty-action--secondary" type="button" @click="$emit('secondary-action')">{{ secondaryActionLabel }}</button>
      <slot name="actions"></slot>
    </div>
  </div>
</template>

<script setup>
import { computed, useSlots } from 'vue'

const props = defineProps({
  title: { type: String, default: '暂无内容' },
  description: { type: String, default: '换个条件再试试。' },
  nextStep: { type: String, default: '' },
  actionLabel: { type: String, default: '' },
  secondaryActionLabel: { type: String, default: '' },
  density: { type: String, default: 'regular' },
})

const slots = useSlots()
const hasActions = computed(() => Boolean(props.actionLabel || props.secondaryActionLabel || slots.actions))

defineEmits(['action', 'secondary-action'])
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

.apple-empty-state--compact {
  max-width: 420px;
  margin: 24px auto;
  padding: 24px;
}

.empty-orb {
  display: grid;
  place-items: center;
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

.empty-orb :slotted(*) {
  width: 26px;
  height: 26px;
  color: var(--text-secondary);
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

.empty-next-step {
  margin-top: 10px;
  color: var(--text-muted);
  font-size: var(--type-control);
}

.apple-state-actions {
  display: flex;
  justify-content: center;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 20px;
}

.empty-action {
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
  transition: transform var(--motion-standard), opacity var(--motion-fast);
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

.empty-action:focus-visible {
  outline: none;
  transform: translateY(-1px);
  background:
    var(--surface-specular-edge),
    var(--surface-noise),
    var(--apple-state-action-bg-hover);
  border-color: var(--apple-state-action-border-hover);
  box-shadow: var(--apple-state-action-shadow-hover), var(--focus-ring);
}

.empty-action:active {
  transform: translateY(0);
}

.empty-action--secondary {
  --apple-state-action-bg: var(--material-glass-control);
  --apple-state-action-bg-hover: var(--material-glass-control-hover);
  --apple-state-action-border: var(--glass-control-border);
  --apple-state-action-border-hover: var(--glass-control-border-hover);
  --apple-state-action-shadow: var(--glass-control-shadow);
  --apple-state-action-shadow-hover: var(--glass-control-shadow-hover);
  color: var(--text-secondary);
}
</style>
