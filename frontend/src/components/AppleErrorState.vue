<template>
  <div class="apple-error-state apple-surface" role="alert" aria-live="assertive">
    <div class="error-mark" aria-hidden="true">!</div>
    <div class="apple-state-copy">
      <h3>{{ title }}</h3>
      <p>{{ description }}</p>
      <p v-if="nextStep" class="error-next-step">{{ nextStep }}</p>
      <small v-if="sourceLabel || details">
        <span v-if="sourceLabel">{{ sourceLabel }}</span>
        <span v-if="sourceLabel && details"> · </span>
        <span v-if="details">{{ details }}</span>
      </small>
    </div>
    <div v-if="hasActions" class="apple-state-actions">
      <button v-if="retryLabel" class="error-action error-action--primary" type="button" :disabled="retrying" @click="$emit('retry')">
        {{ retrying ? '重试中...' : retryLabel }}
      </button>
      <button v-if="secondaryActionLabel" class="error-action error-action--secondary" type="button" :disabled="retrying" @click="$emit('secondary-action')">
        {{ secondaryActionLabel }}
      </button>
      <slot name="actions"></slot>
    </div>
  </div>
</template>

<script setup>
import { computed, useSlots } from 'vue'

const props = defineProps({
  title: { type: String, default: '加载失败' },
  description: { type: String, default: '请稍后重试。' },
  nextStep: { type: String, default: '请重试，或检查相关服务后再刷新。' },
  retryLabel: { type: String, default: '重试' },
  secondaryActionLabel: { type: String, default: '' },
  sourceLabel: { type: String, default: '' },
  details: { type: String, default: '' },
  retrying: { type: Boolean, default: false },
})

const slots = useSlots()
const hasActions = computed(() => Boolean(props.retryLabel || props.secondaryActionLabel || slots.actions))

defineEmits(['retry', 'secondary-action'])
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
  align-items: flex-start;
  gap: 18px;
  max-width: 720px;
  margin: 24px auto;
  padding: 18px 20px;
}

.apple-state-copy {
  flex: 1;
  min-width: 0;
}

.error-mark {
  flex: 0 0 auto;
  display: grid;
  place-items: center;
  width: 38px;
  height: 38px;
  border-radius: 14px;
  border: 1px solid var(--badge-error-border);
  background:
    var(--surface-specular-edge),
    var(--surface-noise),
    var(--badge-error-bg);
  color: var(--badge-error-text);
  font-weight: 800;
  box-shadow: var(--glass-control-shadow);
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

.error-next-step {
  margin-top: 6px;
  color: var(--text-muted);
}

small {
  display: block;
  margin-top: 6px;
  color: var(--text-muted);
  font-size: var(--type-caption);
}

.apple-state-actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 8px;
  flex: 0 0 auto;
}

button,
.error-action {
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
  transition: transform var(--motion-standard), opacity var(--motion-fast);
}

button:hover,
.error-action:hover {
  transform: translateY(-1px);
  background:
    var(--surface-specular-edge),
    var(--surface-noise),
    var(--apple-state-action-bg-hover);
  border-color: var(--apple-state-action-border-hover);
  box-shadow: var(--apple-state-action-shadow-hover);
}

button:focus-visible,
.error-action:focus-visible {
  outline: none;
  transform: translateY(-1px);
  background:
    var(--surface-specular-edge),
    var(--surface-noise),
    var(--apple-state-action-bg-hover);
  border-color: var(--apple-state-action-border-hover);
  box-shadow: var(--apple-state-action-shadow-hover), var(--focus-ring);
}

button:disabled,
.error-action:disabled {
  opacity: 0.55;
  cursor: not-allowed;
  transform: none;
}

.error-action--secondary {
  --apple-state-action-bg: var(--material-glass-control);
  --apple-state-action-bg-hover: var(--material-glass-control-hover);
  --apple-state-action-border: var(--glass-control-border);
  --apple-state-action-border-hover: var(--glass-control-border-hover);
  --apple-state-action-shadow: var(--glass-control-shadow);
  --apple-state-action-shadow-hover: var(--glass-control-shadow-hover);
  color: var(--text-secondary);
}

@media (max-width: 640px) {
  .apple-error-state {
    flex-direction: column;
  }

  .apple-state-actions {
    justify-content: flex-start;
  }
}
</style>
