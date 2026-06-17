<template>
  <transition name="confirm-fade">
    <div v-if="state.open" class="confirm-overlay" @click.self="cancel">
      <section
        class="confirm-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="global-confirm-title"
      >
        <div class="confirm-head">
          <div class="confirm-icon" :class="state.tone">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
              <path d="M12 9v4" />
              <path d="M12 17h.01" />
              <path d="M10.3 3.7 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.7a2 2 0 0 0-3.4 0Z" />
            </svg>
          </div>
          <div class="confirm-copy">
            <h2 id="global-confirm-title">{{ state.title }}</h2>
            <p>{{ state.message }}</p>
            <p v-if="state.details" class="confirm-details">{{ state.details }}</p>
          </div>
        </div>

        <div class="confirm-actions">
          <button class="confirm-btn confirm-cancel" type="button" @click="cancel">
            {{ state.cancelText }}
          </button>
          <button class="confirm-btn confirm-primary" :class="state.tone" type="button" @click="confirm">
            {{ state.confirmText }}
          </button>
        </div>
      </section>
    </div>
  </transition>
</template>

<script setup>
import { confirmDialogState as state, resolveConfirm } from '../utils/confirmDialog'

const cancel = () => resolveConfirm(false)
const confirm = () => resolveConfirm(true)
</script>

<style scoped>
.confirm-overlay {
  --confirm-overlay-bg: var(--surface-scrim, var(--scrim));
  --confirm-sheet-bg: var(--material-glass-sheet);
  --confirm-sheet-border: var(--glass-control-border);
  --confirm-control-bg: var(--material-glass-control);
  --confirm-control-bg-hover: var(--material-glass-control-hover);
  --confirm-control-border: var(--glass-control-border);
  --confirm-control-border-hover: var(--glass-control-border-hover);
  --confirm-control-shadow: var(--glass-control-shadow);
  --confirm-control-shadow-hover: var(--glass-control-shadow-hover);
  --confirm-primary-bg: var(--glass-active-material);
  --confirm-primary-border: var(--glass-active-border);
  --confirm-primary-text: var(--text-primary);
  --confirm-danger-bg: var(--badge-error-bg);
  --confirm-danger-border: var(--badge-error-border);
  --confirm-danger-text: var(--badge-error-text);
  position: fixed;
  inset: 0;
  z-index: var(--z-confirm);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
  background: var(--confirm-overlay-bg);
  backdrop-filter: blur(var(--glass-blur-sheet)) saturate(var(--glass-saturate-surface));
  -webkit-backdrop-filter: blur(var(--glass-blur-sheet)) saturate(var(--glass-saturate-surface));
}

.confirm-dialog {
  width: min(430px, 100%);
  border: 1px solid var(--confirm-sheet-border);
  border-radius: var(--radius-sheet);
  background:
    var(--surface-specular-edge-strong),
    var(--surface-noise),
    var(--confirm-sheet-bg);
  box-shadow: var(--shadow-sheet);
  backdrop-filter: blur(var(--glass-blur-sheet)) saturate(var(--glass-saturate-surface));
  -webkit-backdrop-filter: blur(var(--glass-blur-sheet)) saturate(var(--glass-saturate-surface));
  padding: 18px;
  color: var(--text-primary);
}

.confirm-head {
  display: flex;
  gap: 14px;
  align-items: flex-start;
}

.confirm-icon {
  width: 42px;
  height: 42px;
  flex: 0 0 auto;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 14px;
  border: 1px solid var(--confirm-control-border);
  color: var(--text-secondary);
  background:
    var(--surface-specular-edge),
    var(--surface-noise),
    var(--confirm-control-bg);
  box-shadow: var(--confirm-control-shadow);
  backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
  -webkit-backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
}

.confirm-icon.danger {
  color: var(--confirm-danger-text);
  border-color: var(--confirm-danger-border);
  background:
    var(--surface-specular-edge),
    var(--surface-noise),
    var(--confirm-danger-bg);
}

.confirm-icon svg {
  width: 22px;
  height: 22px;
}

.confirm-copy {
  min-width: 0;
}

.confirm-copy h2 {
  margin: 0;
  font-size: var(--type-panel-title);
  line-height: 1.3;
}

.confirm-copy p {
  margin: 6px 0 0;
  color: var(--text-secondary);
  font-size: var(--type-body);
  line-height: 1.6;
}

.confirm-details {
  color: var(--text-muted) !important;
  overflow-wrap: anywhere;
}

.confirm-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 18px;
}

.confirm-btn {
  min-height: 44px;
  border: 1px solid var(--confirm-control-border);
  border-radius: var(--radius-control);
  padding: 0 18px;
  font: inherit;
  font-size: var(--type-body);
  font-weight: 700;
  cursor: pointer;
  transition: transform var(--motion-standard), opacity var(--motion-fast);
}

.confirm-btn:focus-visible {
  outline: none;
  box-shadow: var(--confirm-control-shadow-hover), var(--focus-ring-wide);
}

.confirm-btn:active {
  transform: translateY(0) scale(0.97);
}

.confirm-cancel {
  background:
    var(--surface-specular-edge),
    var(--surface-noise),
    var(--confirm-control-bg);
  color: var(--text-secondary);
  box-shadow: var(--confirm-control-shadow);
  backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
  -webkit-backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
}

.confirm-cancel:hover {
  background:
    var(--surface-specular-edge),
    var(--surface-noise),
    var(--confirm-control-bg-hover);
  border-color: var(--confirm-control-border-hover);
  color: var(--text-primary);
  box-shadow: var(--confirm-control-shadow-hover);
}

.confirm-primary {
  border-color: var(--confirm-primary-border);
  background:
    var(--surface-specular-edge-strong),
    var(--surface-noise),
    var(--confirm-primary-bg);
  color: var(--confirm-primary-text);
  box-shadow: var(--glass-active-shadow);
  backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
  -webkit-backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
}

.confirm-primary.danger {
  background:
    var(--surface-specular-edge),
    var(--surface-noise),
    var(--confirm-danger-bg);
  border-color: var(--confirm-danger-border);
  color: var(--confirm-danger-text);
}

.confirm-fade-enter-active,
.confirm-fade-leave-active {
  transition: opacity var(--motion-fast);
}

.confirm-fade-enter-active .confirm-dialog,
.confirm-fade-leave-active .confirm-dialog {
  /* WAVE-4 E2: spring entry for a more iOS-26-feeling pop. */
  transition: transform var(--motion-spring, 280ms cubic-bezier(0.34, 1.56, 0.64, 1));
}

.confirm-fade-enter-from,
.confirm-fade-leave-to {
  opacity: 0;
}

.confirm-fade-enter-from .confirm-dialog,
.confirm-fade-leave-to .confirm-dialog {
  transform: translateY(12px) scale(0.98);
}

/* WAVE-4 E2: mobile breakpoints push the dialog to the bottom of the
   viewport as a system-style sheet (drag handle + thumb-reach actions). */
@media (max-width: 640px) {
  .confirm-overlay {
    align-items: flex-end;
    padding: 0;
  }
  .confirm-dialog {
    width: 100%;
    max-width: 100%;
    border-radius: 24px 24px 0 0;
    padding: 14px 18px calc(18px + env(safe-area-inset-bottom, 0px));
    border-left: 0;
    border-right: 0;
    border-bottom: 0;
    position: relative;
  }
  .confirm-dialog::before {
    content: "";
    display: block;
    width: 36px;
    height: 4px;
    margin: 0 auto var(--space-3, 12px);
    border-radius: 999px;
    background: var(--text-muted);
    opacity: 0.35;
  }
  .confirm-fade-enter-from .confirm-dialog,
  .confirm-fade-leave-to .confirm-dialog {
    transform: translateY(100%) scale(1);
  }
}

@media (max-width: 768px) {
  .confirm-overlay {
    align-items: flex-end;
    padding: 12px 12px calc(82px + env(safe-area-inset-bottom, 0px));
  }

  .confirm-dialog {
    border-radius: 22px;
  }

  .confirm-actions {
    flex-direction: column-reverse;
  }

  .confirm-btn {
    width: 100%;
  }
}
</style>
