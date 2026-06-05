<template>
  <transition name="toast-slide">
    <div v-if="visible" class="toast-capsule">
      <div class="toast-content">
        <span class="toast-message">{{ message }}</span>
        <button v-if="showOrganize" class="toast-action" @click="$emit('organize')">
          整理
        </button>
      </div>
      <button class="toast-close" @click="$emit('close')">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
          <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
        </svg>
      </button>
    </div>
  </transition>
</template>

<script setup>
defineProps({
  visible: { type: Boolean, default: false },
  message: { type: String, default: '' },
  showOrganize: { type: Boolean, default: false }
})

defineEmits(['close', 'organize'])
</script>

<style scoped>
.toast-capsule {
  --toast-sheet-bg: var(--material-glass-sheet);
  --toast-sheet-border: var(--glass-control-border);
  --toast-control-bg: var(--material-glass-control);
  --toast-control-bg-hover: var(--material-glass-control-hover);
  --toast-control-border: var(--glass-control-border);
  --toast-control-border-hover: var(--glass-control-border-hover);
  --toast-control-shadow: var(--glass-control-shadow);
  --toast-control-shadow-hover: var(--glass-control-shadow-hover);
  --toast-action-bg: var(--glass-active-material);
  --toast-action-bg-hover: var(--material-glass-control-hover);
  --toast-action-border: var(--glass-active-border);
  --toast-action-border-hover: var(--glass-control-border-hover);
  --toast-action-shadow: var(--glass-active-shadow);
  --toast-action-text: var(--text-primary);
  position: fixed;
  bottom: 40px;
  left: 50%;
  transform: translateX(-50%);
  z-index: var(--z-toast);
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 10px 10px 20px;
  background:
    var(--surface-specular-edge-strong),
    var(--surface-noise),
    var(--toast-sheet-bg);
  backdrop-filter: blur(var(--glass-blur-sheet)) saturate(var(--glass-saturate-surface));
  -webkit-backdrop-filter: blur(var(--glass-blur-sheet)) saturate(var(--glass-saturate-surface));
  border: 1px solid var(--toast-sheet-border);
  border-radius: var(--radius-control);
  box-shadow: var(--shadow-sheet);
  min-width: 240px;
  max-width: 90vw;
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
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.toast-action {
  background:
    var(--surface-specular-edge-strong),
    var(--surface-noise),
    var(--toast-action-bg);
  color: var(--toast-action-text);
  border: 1px solid var(--toast-action-border);
  padding: 6px 14px;
  border-radius: var(--radius-control);
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
  box-shadow: var(--toast-action-shadow);
  backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
  -webkit-backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
  transition: transform var(--motion-standard), background var(--motion-standard), border-color var(--motion-standard), box-shadow var(--motion-standard), opacity var(--motion-fast);
}

.toast-action:hover {
  background:
    var(--surface-specular-edge),
    var(--surface-noise),
    var(--toast-action-bg-hover);
  border-color: var(--toast-action-border-hover);
  box-shadow: var(--toast-control-shadow-hover);
  transform: translateY(-1px);
}

.toast-action:focus-visible {
  outline: none;
  box-shadow: var(--toast-control-shadow-hover), var(--focus-ring-wide);
}

.toast-action:active {
  transform: translateY(0) scale(0.97);
}

.toast-close {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background:
    var(--surface-specular-edge),
    var(--surface-noise),
    var(--toast-control-bg);
  border: 1px solid var(--toast-control-border);
  color: var(--text-muted);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: transform var(--motion-standard), background var(--motion-standard), border-color var(--motion-standard), box-shadow var(--motion-standard), opacity var(--motion-fast);
  box-shadow: var(--toast-control-shadow);
  backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
  -webkit-backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
}

.toast-close:hover {
  background:
    var(--surface-specular-edge),
    var(--surface-noise),
    var(--toast-control-bg-hover);
  border-color: var(--toast-control-border-hover);
  color: var(--text-primary);
  box-shadow: var(--toast-control-shadow-hover);
  transform: translateY(-1px);
}

.toast-close:focus-visible {
  outline: none;
  box-shadow: var(--toast-control-shadow-hover), var(--focus-ring-wide);
}

.toast-close:active {
  transform: translateY(0) scale(0.94);
}

/* Animations */
.toast-slide-enter-active {
  transition: opacity var(--motion-standard), transform var(--motion-standard);
}
.toast-slide-leave-active {
  transition: opacity var(--motion-standard), transform var(--motion-standard);
}
.toast-slide-enter-from {
  opacity: 0;
  transform: translate(-50%, 40px) scale(0.9);
}
.toast-slide-leave-to {
  opacity: 0;
  transform: translate(-50%, 20px) scale(0.95);
}
</style>
