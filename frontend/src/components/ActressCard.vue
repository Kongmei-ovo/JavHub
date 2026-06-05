<template>
  <article
    class="actress-card"
    role="button"
    tabindex="0"
    :aria-label="`打开演员 ${name}`"
    @click="$emit('click')"
    @keydown.enter.prevent="$emit('click')"
    @keydown.space.prevent="$emit('click')"
  >
    <!-- Cover -->
    <div class="card-cover">
      <img
        :src="coverUrl"
        :alt="name"
        @error="handleImgError"
        loading="lazy"
        class="cover-img"
      />
      <div class="cover-fade"></div>
      <!-- Count badge top-left -->
      <span v-if="totalCount != null" class="cover-badge">
        <svg viewBox="0 0 24 24" fill="currentColor" width="10" height="10"><path d="M4 6.47L5.76 10H20v8H4V6.47M22 4h-4l2 4h-3l-2-4h-2l2 4h-3l-2-4H8l2 4H7L5 4H4c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V4z"/></svg>
        {{ totalCount }}
      </span>
      <!-- Heart top-right -->
      <span v-if="subscribed" class="cover-heart">
        <svg viewBox="0 0 24 24" width="14" height="14"><path d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z" fill="currentColor"/></svg>
      </span>
      <span v-if="candidateCount > 0" class="candidate-badge">{{ candidateCount }}</span>
    </div>
    <!-- Info -->
    <div class="card-info">
      <div class="info-name">{{ name }}</div>
      <div v-if="originalName && originalName !== name" class="info-sub">{{ originalName }}</div>
      <div class="info-meta">
        <span v-if="totalCount != null" class="meta-item">
          <svg viewBox="0 0 24 24" fill="currentColor" width="11" height="11"><path d="M4 6.47L5.76 10H20v8H4V6.47M22 4h-4l2 4h-3l-2-4h-2l2 4h-3l-2-4H8l2 4H7L5 4H4c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V4z"/></svg>
          {{ totalCount }} 部
        </span>
        <span v-if="subscribed" class="meta-item meta-subscribed">
          <svg viewBox="0 0 24 24" fill="currentColor" width="11" height="11"><path d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z"/></svg>
          已订阅
        </span>
        <span v-if="candidateCount > 0" class="meta-item meta-candidate">
          {{ candidateCount }} 候选
        </span>
      </div>
    </div>
  </article>
</template>

<script setup>
import { applyImageFallback } from '../utils/imageFallback.js'

const props = defineProps({
  coverUrl: { type: String, default: '' },
  name: { type: String, default: '未知' },
  originalName: { type: String, default: '' },
  totalCount: { type: Number, default: null },
  subscribed: { type: Boolean, default: false },
  candidateCount: { type: Number, default: 0 }
})

defineEmits(['click'])

const handleImgError = (e) => {
  applyImageFallback(e, { label: props.name?.slice(0, 1) || '?' })
}
</script>

<style scoped>
.actress-card {
  background: var(--surface-specular-edge), var(--surface-noise), var(--material-glass-control);
  backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
  -webkit-backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
  border: 1px solid var(--glass-control-border);
  border-radius: var(--radius-card);
  box-shadow: var(--glass-control-shadow);
  overflow: hidden;
  cursor: pointer;
  color: var(--text-primary);
  outline: none;
  transition: transform var(--motion-standard), background var(--motion-standard), border-color var(--motion-standard), box-shadow var(--motion-standard);
}

.actress-card:hover {
  transform: translateY(-5px);
  background: var(--surface-specular-edge-strong), var(--surface-noise), var(--material-glass-control-hover);
  border-color: var(--glass-control-border-hover);
  box-shadow: var(--glass-control-shadow-hover);
}

.actress-card:focus-visible {
  border-color: var(--glass-control-border-hover);
  background: var(--surface-specular-edge-strong), var(--surface-noise), var(--material-glass-control-hover);
  box-shadow:
    var(--glass-control-shadow-hover),
    0 0 0 4px rgba(var(--accent-rgb), 0.12),
    var(--glass-inner-shadow);
}

.actress-card:active {
  transform: translateY(-2px) scale(0.99);
}

/* ===== Cover ===== */
.card-cover {
  position: relative;
  width: 100%;
  aspect-ratio: 3/4;
  overflow: hidden;
  background:
    var(--surface-specular-edge),
    var(--surface-noise),
    var(--material-glass-subtle);
  box-shadow: var(--glass-inner-shadow);
}

.cover-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  object-position: center top;
  transition: transform var(--motion-emphasized);
}

.actress-card:hover .cover-img {
  transform: scale(1.06);
}

.actress-card:focus-visible .cover-img {
  transform: scale(1.06);
}

.cover-fade {
  position: absolute;
  bottom: 0; left: 0; right: 0;
  height: 50%;
  background: linear-gradient(to top, var(--surface-scrim) 0%, rgba(var(--accent-rgb), 0.18) 48%, transparent 100%);
  pointer-events: none;
}

/* Count badge */
.cover-badge {
  position: absolute;
  top: 8px; left: 8px;
  display: inline-flex; align-items: center; gap: 3px;
  height: 22px; padding: 0 8px;
  border-radius: var(--radius-sm);
  background: var(--surface-specular-edge), var(--surface-noise), var(--material-glass-control);
  backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
  -webkit-backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
  border: 1px solid var(--glass-control-border);
  box-shadow: var(--glass-control-shadow);
  color: var(--text-primary);
  font-size: var(--type-micro);
  font-weight: 600;
  pointer-events: none;
}

/* Heart */
.cover-heart {
  position: absolute;
  top: 8px; right: 8px;
  width: 24px; height: 24px;
  border-radius: var(--radius-control);
  background: var(--surface-specular-edge), var(--surface-noise), var(--material-glass-control);
  backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
  -webkit-backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
  border: 1px solid var(--glass-control-border);
  box-shadow: var(--glass-control-shadow);
  color: var(--badge-error-text);
  display: flex; align-items: center; justify-content: center;
  pointer-events: none;
}

.candidate-badge {
  position: absolute;
  right: 8px;
  bottom: 8px;
  min-width: 24px;
  height: 24px;
  padding: 0 8px;
  border-radius: 999px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: var(--surface-specular-edge), var(--surface-noise), var(--badge-warning-bg);
  border: 1px solid var(--badge-warning-border);
  color: var(--badge-warning-text);
  font-size: var(--type-caption);
  font-weight: 800;
  box-shadow: var(--glass-control-shadow);
  backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
  -webkit-backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
}

/* ===== Info ===== */
.card-info {
  padding: 10px 12px 14px;
}

.info-name {
  font-size: var(--type-body);
  font-weight: 600;
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  line-height: 1.3;
}

.info-sub {
  font-size: var(--type-micro);
  color: var(--text-muted);
  margin-top: 2px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.info-meta {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 8px;
}

.meta-item {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  font-weight: 500;
  color: var(--text-muted);
}

.meta-subscribed {
  color: var(--badge-error-text);
}

.meta-candidate {
  color: var(--badge-warning-text);
}
</style>
