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
  position: fixed;
  inset: 0;
  z-index: 2000;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
  background: rgba(0, 0, 0, 0.58);
  backdrop-filter: blur(18px);
  -webkit-backdrop-filter: blur(18px);
}

.confirm-dialog {
  width: min(430px, 100%);
  border: 1px solid var(--border-light);
  border-radius: 22px;
  background: var(--material-glass-sheet);
  box-shadow: var(--shadow-sheet);
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
  border: 1px solid var(--border);
  color: var(--accent);
  background: var(--white-06);
}

.confirm-icon.danger {
  color: #ff6b6b;
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
  font-size: 18px;
  line-height: 1.3;
}

.confirm-copy p {
  margin: 6px 0 0;
  color: var(--text-secondary);
  font-size: 14px;
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
  border: 1px solid var(--border);
  border-radius: 999px;
  padding: 0 18px;
  font: inherit;
  font-size: 14px;
  font-weight: 700;
  cursor: pointer;
}

.confirm-cancel {
  background: var(--white-06);
  color: var(--text-secondary);
}

.confirm-primary {
  border-color: transparent;
  background: var(--accent);
  color: var(--bg-primary);
}

.confirm-primary.danger {
  background: #ff6b6b;
  color: #160b0b;
}

.confirm-fade-enter-active,
.confirm-fade-leave-active {
  transition: opacity 180ms var(--ease-pro);
}

.confirm-fade-enter-active .confirm-dialog,
.confirm-fade-leave-active .confirm-dialog {
  transition: transform 220ms var(--ease-pro);
}

.confirm-fade-enter-from,
.confirm-fade-leave-to {
  opacity: 0;
}

.confirm-fade-enter-from .confirm-dialog,
.confirm-fade-leave-to .confirm-dialog {
  transform: translateY(12px) scale(0.98);
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
