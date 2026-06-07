<template>
  <TransitionGroup name="toast-slide" tag="div" class="toast-island-stack">
    <div
      v-for="item in renderedStackItems"
      :key="item.id"
      :class="['toast-capsule', { 'toast-capsule--stacked': item.index > 0 }]"
      :style="stackItemStyle(item)"
      role="status"
      :aria-hidden="item.index > 0 ? 'true' : undefined"
    >
      <div class="toast-content">
        <span class="toast-message">{{ item.message }}</span>
        <button
          v-if="item.index === 0 && showOrganize"
          class="toast-action"
          @click="$emit('organize')"
        >
          整理
        </button>
      </div>
      <button v-if="item.index === 0" class="toast-close" @click="$emit('close')">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
          <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
        </svg>
      </button>
    </div>
  </TransitionGroup>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { MESSAGE_EVENT } from '../utils/message.js'

const MAX_TOAST_STACK = 5
const STACK_STEP = 12
const STACK_SCALE_STEP = 0.08
const STACK_OPACITY_STEP = 0.3

const props = defineProps({
  visible: { type: Boolean, default: false },
  message: { type: String, default: '' },
  showOrganize: { type: Boolean, default: false }
})

defineEmits(['close', 'organize'])

const stackItems = ref([])
let nextToastId = 0
let pendingMessageBusEcho = null

const renderedStackItems = computed(() =>
  stackItems.value.map((item, index) => ({ ...item, index }))
)

function pushToast(message, showOrganize) {
  nextToastId += 1
  stackItems.value = [
    { id: `toast-${nextToastId}`, message, showOrganize },
    ...stackItems.value
  ].slice(0, MAX_TOAST_STACK)
}

function stackItemStyle(item) {
  return {
    '--toast-stack-y': `${8 + item.index * STACK_STEP}px`,
    '--toast-stack-scale': String(Math.max(0.76, 1 - item.index * STACK_SCALE_STEP)),
    '--toast-stack-opacity': String(Math.max(0.4, 1 - item.index * STACK_OPACITY_STEP)),
    '--toast-stack-z': String(MAX_TOAST_STACK - item.index)
  }
}

function normalizeToastMessage(input) {
  if (typeof input === 'string') return input
  if (input && typeof input === 'object') return input.message || String(input)
  return String(input ?? '')
}

function shouldSkipMessageBusEcho(message, showOrganize) {
  if (!pendingMessageBusEcho) return false
  const freshEcho = Date.now() - pendingMessageBusEcho.time < 250
  const matchingEcho =
    pendingMessageBusEcho.message === message &&
    pendingMessageBusEcho.showOrganize === showOrganize
  if (freshEcho && matchingEcho) {
    pendingMessageBusEcho = null
    return true
  }
  return false
}

function handleMessageEvent(event) {
  const message = normalizeToastMessage(event?.detail?.message)
  if (!message) return
  pendingMessageBusEcho = { message, showOrganize: false, time: Date.now() }
  pushToast(message, false)
}

watch(
  () => [props.visible, props.message, props.showOrganize],
  ([visible, message, showOrganize], previous = []) => {
    if (!visible) {
      stackItems.value = []
      return
    }

    const [wasVisible, previousMessage, previousShowOrganize] = previous
    if (!wasVisible || message !== previousMessage || showOrganize !== previousShowOrganize) {
      if (shouldSkipMessageBusEcho(message, showOrganize)) return
      pushToast(message, showOrganize)
    }
  },
  { immediate: true }
)

onMounted(() => {
  window.addEventListener(MESSAGE_EVENT, handleMessageEvent)
})

onUnmounted(() => {
  window.removeEventListener(MESSAGE_EVENT, handleMessageEvent)
})
</script>

<style scoped>
:global(:root) {
  --b4-local-specular-edge: var(--surface-specular-edge, none);
  --b4-local-specular-edge-strong: var(--surface-specular-edge-strong, none);
  --b4-local-surface-noise: var(--surface-noise, none);
  --b4-local-sheet-bg: var(--material-glass-sheet, var(--glass-sheet-material, none));
  --b4-local-sheet-border: var(--glass-control-border, var(--border-light, currentColor));
  --b4-local-control-bg: var(--material-glass-control, var(--glass-control-material, none));
  --b4-local-control-bg-hover: var(--material-glass-control-hover, var(--glass-control-material-hover, none));
  --b4-local-control-border: var(--glass-control-border, var(--border-light, currentColor));
  --b4-local-control-border-hover: var(--glass-control-border-hover, var(--border-light, currentColor));
  --b4-local-control-shadow: var(--glass-control-shadow, none);
  --b4-local-control-shadow-hover: var(--glass-control-shadow-hover, none);
  --b4-local-action-bg: var(--glass-active-material, var(--material-glass-control, none));
  --b4-local-action-bg-hover: var(--material-glass-control-hover, var(--glass-control-material-hover, none));
  --b4-local-action-border: var(--glass-active-border, var(--glass-control-border, currentColor));
  --b4-local-action-border-hover: var(--glass-control-border-hover, var(--glass-control-border, currentColor));
  --b4-local-action-shadow: var(--glass-active-shadow, none);
  --b4-local-action-text: var(--text-primary, currentColor);
  --b4-local-muted-text: var(--text-muted, currentColor);
  --b4-local-focus-ring: var(--focus-ring-wide, var(--focus-ring, none));
  --b4-local-radius-control: var(--radius-control, 999px);
  --b4-local-sheet-shadow: var(--shadow-sheet, none);
  --b4-local-blur-sheet: var(--glass-blur-sheet, 24px);
  --b4-local-blur-control: var(--glass-blur-control, 12px);
  --b4-local-saturate-surface: var(--glass-saturate-surface, 160%);
  --b4-local-saturate-control: var(--glass-saturate-control, 160%);
}

.toast-island-stack {
  pointer-events: none;
}

.toast-capsule {
  --toast-sheet-bg: var(--b4-local-sheet-bg);
  --toast-sheet-border: var(--b4-local-sheet-border);
  --toast-control-bg: var(--b4-local-control-bg);
  --toast-control-bg-hover: var(--b4-local-control-bg-hover);
  --toast-control-border: var(--b4-local-control-border);
  --toast-control-border-hover: var(--b4-local-control-border-hover);
  --toast-control-shadow: var(--b4-local-control-shadow);
  --toast-control-shadow-hover: var(--b4-local-control-shadow-hover);
  --toast-action-bg: var(--b4-local-action-bg);
  --toast-action-bg-hover: var(--b4-local-action-bg-hover);
  --toast-action-border: var(--b4-local-action-border);
  --toast-action-border-hover: var(--b4-local-action-border-hover);
  --toast-action-shadow: var(--b4-local-action-shadow);
  --toast-action-text: var(--b4-local-action-text);
  position: fixed;
  top: max(env(safe-area-inset-top, 0px), 0px);
  bottom: auto;
  left: 50%;
  transform: translate3d(-50%, var(--toast-stack-y, 8px), 0) scale(var(--toast-stack-scale, 1));
  transform-origin: top center;
  z-index: calc(var(--z-toast, 1000) + var(--toast-stack-z, 0));
  display: flex;
  align-items: center;
  gap: var(--space-3, 12px);
  padding: 10px 10px 10px 20px;
  width: min(calc(100vw - var(--space-6, 24px)), 480px);
  min-width: 240px;
  max-width: 480px;
  opacity: var(--toast-stack-opacity, 1);
  pointer-events: auto;
  background:
    var(--b4-local-specular-edge-strong),
    var(--b4-local-surface-noise),
    var(--toast-sheet-bg);
  backdrop-filter: blur(var(--b4-local-blur-sheet)) saturate(var(--b4-local-saturate-surface));
  -webkit-backdrop-filter: blur(var(--b4-local-blur-sheet)) saturate(var(--b4-local-saturate-surface));
  border: 1px solid var(--toast-sheet-border);
  border-radius: var(--b4-local-radius-control);
  box-shadow: var(--b4-local-sheet-shadow);
}

.toast-content {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.toast-message {
  font-size: 14px;
  font-weight: 500;
  color: var(--b4-local-action-text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.toast-action {
  background:
    var(--b4-local-specular-edge-strong),
    var(--b4-local-surface-noise),
    var(--toast-action-bg);
  color: var(--toast-action-text);
  border: 1px solid var(--toast-action-border);
  padding: 6px 14px;
  border-radius: var(--b4-local-radius-control);
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
  box-shadow: var(--toast-action-shadow);
  backdrop-filter: blur(var(--b4-local-blur-control)) saturate(var(--b4-local-saturate-control));
  -webkit-backdrop-filter: blur(var(--b4-local-blur-control)) saturate(var(--b4-local-saturate-control));
  transition: transform var(--motion-spring, 280ms cubic-bezier(0.34, 1.56, 0.64, 1)), opacity var(--motion-fast, 140ms cubic-bezier(0.16, 1, 0.3, 1));
}

.toast-action:hover {
  background:
    var(--b4-local-specular-edge),
    var(--b4-local-surface-noise),
    var(--toast-action-bg-hover);
  border-color: var(--toast-action-border-hover);
  box-shadow: var(--toast-control-shadow-hover);
  transform: translateY(-1px);
}

.toast-action:focus-visible {
  outline: none;
  box-shadow: var(--toast-control-shadow-hover), var(--b4-local-focus-ring);
}

.toast-action:active {
  transform: translateY(0) scale(0.97);
}

.toast-close {
  width: 28px;
  height: 28px;
  border-radius: var(--b4-local-radius-control);
  background:
    var(--b4-local-specular-edge),
    var(--b4-local-surface-noise),
    var(--toast-control-bg);
  border: 1px solid var(--toast-control-border);
  color: var(--b4-local-muted-text);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: transform var(--motion-spring, 280ms cubic-bezier(0.34, 1.56, 0.64, 1)), opacity var(--motion-fast, 140ms cubic-bezier(0.16, 1, 0.3, 1));
  box-shadow: var(--toast-control-shadow);
  backdrop-filter: blur(var(--b4-local-blur-control)) saturate(var(--b4-local-saturate-control));
  -webkit-backdrop-filter: blur(var(--b4-local-blur-control)) saturate(var(--b4-local-saturate-control));
}

.toast-close:hover {
  background:
    var(--b4-local-specular-edge),
    var(--b4-local-surface-noise),
    var(--toast-control-bg-hover);
  border-color: var(--toast-control-border-hover);
  color: var(--b4-local-action-text);
  box-shadow: var(--toast-control-shadow-hover);
  transform: translateY(-1px);
}

.toast-close:focus-visible {
  outline: none;
  box-shadow: var(--toast-control-shadow-hover), var(--b4-local-focus-ring);
}

.toast-close:active {
  transform: translateY(0) scale(0.97);
}

/* Animations */
.toast-slide-enter-active {
  transition: opacity var(--motion-spring, 280ms cubic-bezier(0.34, 1.56, 0.64, 1)), transform var(--motion-spring-emphasized, 420ms cubic-bezier(0.5, 1.7, 0.6, 1));
}
.toast-slide-leave-active {
  transition: opacity var(--motion-spring, 280ms cubic-bezier(0.34, 1.56, 0.64, 1)), transform var(--motion-spring-emphasized, 420ms cubic-bezier(0.5, 1.7, 0.6, 1));
}
.toast-slide-enter-from {
  opacity: 0;
  transform: translate3d(-50%, -100%, 0) scale(0.96);
}
.toast-slide-enter-to {
  transform: translate3d(-50%, 8px, 0) scale(1);
}
.toast-slide-leave-to {
  opacity: 0;
  transform: translate3d(-50%, -100%, 0) scale(0.96);
}

.toast-capsule--stacked {
  pointer-events: none;
}

@media (max-width: 768px) {
  .toast-close {
    width: 40px;
    height: 40px;
  }
}
</style>
