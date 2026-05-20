<template>
  <div :class="['apple-skeleton', `apple-skeleton--${variant}`]" :style="styleVars" aria-hidden="true">
    <template v-if="variant === 'card'">
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
  aspectRatio: { type: String, default: '3 / 4' },
})

const styleVars = computed(() => ({ '--skeleton-aspect-ratio': props.aspectRatio }))
</script>

<style scoped>
.apple-skeleton--card {
  border-radius: var(--radius-card);
  overflow: hidden;
  background: var(--surface-card);
  border: 1px solid var(--border);
  box-shadow: var(--glass-surface-shadow);
  backdrop-filter: blur(var(--glass-blur-surface)) saturate(var(--glass-saturate-surface));
  -webkit-backdrop-filter: blur(var(--glass-blur-surface)) saturate(var(--glass-saturate-surface));
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
