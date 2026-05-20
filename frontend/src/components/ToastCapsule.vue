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
  position: fixed;
  bottom: 40px;
  left: 50%;
  transform: translateX(-50%);
  z-index: var(--z-toast);
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 10px 10px 20px;
  background: var(--material-glass-sheet);
  backdrop-filter: blur(var(--glass-blur-sheet)) saturate(var(--glass-saturate-surface));
  -webkit-backdrop-filter: blur(var(--glass-blur-sheet)) saturate(var(--glass-saturate-surface));
  border: 1px solid var(--border-light);
  border-radius: 100px;
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
  background: var(--accent);
  color: var(--text-on-accent);
  border: none;
  padding: 6px 14px;
  border-radius: 100px;
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
  transition: var(--transition-pro);
}

.toast-action:hover {
  background: var(--accent-light);
  transform: scale(1.05);
}

.toast-close {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: var(--surface-control);
  border: 1px solid var(--glass-control-border);
  color: var(--text-muted);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: var(--transition-pro);
  box-shadow: var(--glass-control-shadow);
  backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
  -webkit-backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
}

.toast-close:hover {
  background: var(--surface-control-hover);
  border-color: var(--glass-control-border-hover);
  color: var(--text-primary);
  box-shadow: var(--glass-control-shadow-hover);
}

/* Animations */
.toast-slide-enter-active {
  transition: all 0.6s cubic-bezier(0.23, 1, 0.32, 1);
}
.toast-slide-leave-active {
  transition: all 0.4s cubic-bezier(0.23, 1, 0.32, 1);
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
