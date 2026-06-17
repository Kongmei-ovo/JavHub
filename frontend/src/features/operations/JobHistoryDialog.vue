<template>
  <div v-if="open" class="jh-overlay" @click.self="$emit('close')">
    <div class="jh-dialog" role="dialog" aria-modal="true" :aria-label="title">
      <div class="jh-head">
        <h3>{{ title }}</h3>
        <button class="jh-close" type="button" aria-label="关闭" @click="$emit('close')">✕</button>
      </div>
      <div class="jh-body">
        <ul v-if="rows.length" class="jh-list">
          <li v-for="row in rows" :key="row.id" class="jh-row">
            <span class="jh-status" :class="`jh-status--${row.tone || 'idle'}`">{{ row.statusText }}</span>
            <div class="jh-row-main">
              <strong class="jh-time">{{ row.time || `#${row.id}` }}</strong>
              <small v-if="row.meta" class="jh-meta">{{ row.meta }}</small>
            </div>
          </li>
        </ul>
        <p v-else class="jh-empty">{{ emptyText }}</p>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'JobHistoryDialog',
  props: {
    open: { type: Boolean, default: false },
    title: { type: String, default: '作业历史' },
    rows: { type: Array, default: () => [] },
    emptyText: { type: String, default: '暂无记录' },
  },
  emits: ['close'],
}
</script>

<style scoped>
.jh-overlay {
  position: fixed;
  inset: 0;
  z-index: var(--z-confirm);
  background: var(--surface-scrim, var(--scrim));
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
}

.jh-dialog {
  width: 100%;
  max-width: 460px;
  max-height: 80vh;
  display: flex;
  flex-direction: column;
  background: var(--card);
  border: 1px solid var(--hairline);
  border-radius: var(--radius-card);
  box-shadow: var(--shadow-modal, var(--shadow-card));
  overflow: hidden;
}

.jh-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 16px 20px;
  border-bottom: 1px solid var(--hairline);
}

.jh-head h3 {
  margin: 0;
  font-size: var(--type-panel-title);
  font-weight: 650;
  color: var(--text-primary);
}

.jh-close {
  flex-shrink: 0;
  width: 28px;
  height: 28px;
  border: none;
  border-radius: 999px;
  background: var(--card-2);
  color: var(--text-muted);
  cursor: pointer;
  font-size: var(--type-caption);
}

.jh-close:hover { color: var(--text-primary); }

.jh-body {
  padding: 12px 20px 20px;
  overflow-y: auto;
}

.jh-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.jh-row {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 12px;
  border-radius: var(--radius-md, 12px);
  background: var(--card-2);
  border: 1px solid var(--hairline);
}

.jh-status {
  flex-shrink: 0;
  min-width: 44px;
  padding: 2px 8px;
  border-radius: 999px;
  font-size: var(--type-badge);
  font-weight: 700;
  text-align: center;
  background: var(--surface);
  color: var(--text-muted);
}

.jh-status--ok { color: var(--ok); }
.jh-status--bad { color: var(--bad); }
.jh-status--run { color: var(--accent); }

.jh-row-main {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}

.jh-time {
  font-size: var(--type-control);
  font-weight: 600;
  color: var(--text-primary);
  font-variant-numeric: tabular-nums;
}

.jh-meta {
  font-size: var(--type-micro);
  color: var(--text-secondary);
  font-variant-numeric: tabular-nums;
}

.jh-empty {
  padding: 24px;
  text-align: center;
  color: var(--text-muted);
  font-size: var(--type-caption);
}
</style>
