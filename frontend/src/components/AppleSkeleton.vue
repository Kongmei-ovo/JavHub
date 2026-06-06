<template>
  <div
    :class="['apple-skeleton', `apple-skeleton--${variant}`]"
    :style="[styleVars, gridVars]"
    role="status"
    aria-live="polite"
    aria-busy="true"
    :aria-label="label"
  >
    <template v-if="variant === 'gallery'">
      <div class="apple-skeleton-grid">
        <div v-for="item in items" :key="item" class="apple-skeleton apple-skeleton--card">
          <div class="apple-skeleton-cover apple-skeleton-block"></div>
          <div class="apple-skeleton-body">
            <div class="apple-skeleton-line apple-skeleton-line--short apple-skeleton-block"></div>
            <div class="apple-skeleton-line apple-skeleton-block"></div>
          </div>
        </div>
      </div>
    </template>
    <template v-else-if="variant === 'list'">
      <div class="apple-skeleton-list">
        <div v-for="item in items" :key="item" class="apple-skeleton-row">
          <div class="apple-skeleton-thumb apple-skeleton-block"></div>
          <div class="apple-skeleton-row-copy">
            <div class="apple-skeleton-line apple-skeleton-line--short apple-skeleton-block"></div>
            <div class="apple-skeleton-line apple-skeleton-block"></div>
          </div>
        </div>
      </div>
    </template>
    <template v-else-if="variant === 'card'">
      <div class="apple-skeleton-cover apple-skeleton-block"></div>
      <div class="apple-skeleton-body">
        <div class="apple-skeleton-line apple-skeleton-line--short apple-skeleton-block"></div>
        <div class="apple-skeleton-line apple-skeleton-block"></div>
      </div>
    </template>
    <template v-else>
      <div v-for="line in lines" :key="line" class="apple-skeleton-line apple-skeleton-block"></div>
    </template>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  variant: { type: String, default: 'text' },
  lines: { type: Number, default: 2 },
  items: { type: Number, default: 6 },
  columns: { type: String, default: 'repeat(auto-fill, minmax(180px, 1fr))' },
  aspectRatio: { type: String, default: '3 / 4' },
  label: { type: String, default: '内容加载中' },
})

const styleVars = computed(() => ({ '--skeleton-aspect-ratio': props.aspectRatio }))
const gridVars = computed(() => ({ '--skeleton-grid-columns': props.columns }))
</script>

<style scoped>
.apple-skeleton--gallery,
.apple-skeleton--list {
  display: block;
}

.apple-skeleton-grid {
  display: grid;
  grid-template-columns: var(--skeleton-grid-columns);
  gap: 16px;
}

.apple-skeleton-list {
  display: grid;
  gap: 10px;
}

.apple-skeleton--card {
  border-radius: var(--radius-card);
  overflow: hidden;
  background:
    var(--surface-specular-edge),
    var(--surface-noise),
    var(--material-glass-subtle);
  border: 1px solid var(--glass-control-border);
  box-shadow: var(--glass-control-shadow);
  backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
  -webkit-backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
}

.apple-skeleton-row {
  display: grid;
  grid-template-columns: 64px minmax(0, 1fr);
  gap: 12px;
  align-items: center;
  padding: 12px;
  border-radius: var(--radius-card);
  background:
    var(--surface-specular-edge),
    var(--surface-noise),
    var(--material-glass-subtle);
  border: 1px solid var(--glass-control-border);
  box-shadow: var(--glass-control-shadow);
  backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
  -webkit-backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
}

.apple-skeleton-thumb {
  width: 64px;
  aspect-ratio: 1;
  border-radius: var(--radius-md);
}

.apple-skeleton-row-copy {
  min-width: 0;
}

.apple-skeleton-cover {
  aspect-ratio: var(--skeleton-aspect-ratio);
}

.apple-skeleton-body {
  padding: 14px;
}

.apple-skeleton-line {
  height: 11px;
  border-radius: 999px;
  margin-bottom: 10px;
}

.apple-skeleton-line:last-child {
  margin-bottom: 0;
}

.apple-skeleton-line--short {
  width: 58%;
}

.apple-skeleton--text .apple-skeleton-line:nth-child(even) {
  width: 78%;
}
</style>
