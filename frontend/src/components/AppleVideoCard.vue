<template>
  <article class="apple-video-card apple-surface" @click="$emit('open', normalized)">
    <div class="apple-video-card__cover">
      <img
        v-if="coverUrl && !imageError"
        :src="coverUrl"
        :alt="displayCode || normalized.title_ja || 'video cover'"
        loading="lazy"
        class="apple-video-card__image"
        @error="imageError = true"
        @load="onImageLoad"
      />
      <div v-else class="apple-video-card__fallback">
        <span>{{ fallbackText }}</span>
      </div>

      <div v-if="normalized.sample_url" class="apple-video-card__preview" title="有预览视频">
        <svg viewBox="0 0 24 24" fill="currentColor" width="12" height="12"><path d="M8 5v14l11-7z"/></svg>
      </div>

      <button
        v-if="showFavorite"
        class="apple-video-card__favorite"
        :class="{ 'is-active': favorited }"
        type="button"
        :aria-label="favorited ? '取消收藏' : '收藏影片'"
        @click.stop="$emit('toggle-favorite', normalized)"
      >
        <svg viewBox="0 0 24 24" width="16" height="16">
          <path v-if="favorited" d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z" fill="currentColor"/>
          <path v-else d="M16.5 3c-1.74 0-3.41.81-4.5 2.09C10.91 3.81 9.24 3 7.5 3 4.42 3 2 5.42 2 8.5c0 3.78 3.4 6.86 8.55 11.54L12 21.35l1.45-1.32C18.6 15.36 22 12.28 22 8.5 22 5.42 19.58 3 16.5 3zm-4.4 15.55l-.1.1-.1-.1C7.14 14.24 4 11.39 4 8.5 4 6.5 5.5 5 7.5 5c1.54 0 3.04.99 3.57 2.36h1.87C13.46 5.99 14.96 5 16.5 5c2 0 3.5 1.5 3.5 3.5 0 2.89-3.14 5.74-7.9 10.05z" fill="currentColor"/>
        </svg>
      </button>
    </div>

    <div class="apple-video-card__body">
      <div class="apple-video-card__meta-row">
        <span class="apple-video-card__code">{{ displayCode }}</span>
        <span v-if="serviceLabel" class="apple-video-card__badge">{{ serviceLabel }}</span>
      </div>
      <h3 class="apple-video-card__title" :title="titleText">{{ titleText }}</h3>
      <div class="apple-video-card__subline">
        <span v-if="normalized.release_date">{{ normalized.release_date }}</span>
        <span v-if="normalized.runtime_mins">{{ normalized.runtime_mins }}分钟</span>
      </div>
    </div>
  </article>
</template>

<script setup>
import { computed, ref } from 'vue'
import { normalizeVideo } from '../utils/videoNormalize.js'

const props = defineProps({
  video: { type: Object, required: true },
  coverUrl: { type: String, default: '' },
  favorited: { type: Boolean, default: false },
  showFavorite: { type: Boolean, default: true },
})

defineEmits(['open', 'toggle-favorite'])

const imageError = ref(false)
const wideImage = ref(false)
const normalized = computed(() => normalizeVideo(props.video))
const coverUrl = computed(() => props.coverUrl || normalized.value.jacket_thumb_url || normalized.value.jacket_full_url || '')
const titleText = computed(() => normalized.value.title_ja || normalized.value.title_en || normalized.value.title || 'Untitled')
const displayCode = computed(() => normalized.value.dvd_id || normalized.value.content_id || '')
const fallbackText = computed(() => (displayCode.value || '?').slice(0, 12))
const serviceLabel = computed(() => {
  const map = { mono: 'DVD', digital: '数字', rental: '租赁', ebook: '写真', download: '下载', streaming: '流媒体', subscription: '订阅' }
  return map[normalized.value.service_code] || normalized.value.service_code || ''
})

function onImageLoad(event) {
  const img = event.target
  wideImage.value = img.naturalWidth > img.naturalHeight
  if (wideImage.value) img.classList.add('is-wide')
}
</script>

<style scoped>
.apple-video-card {
  cursor: pointer;
  overflow: hidden;
  transition: transform var(--motion-standard), border-color var(--motion-standard), box-shadow var(--motion-standard), background var(--motion-standard);
}

.apple-video-card:hover {
  transform: translateY(-3px);
  border-color: var(--border-light);
  background: var(--surface-card-hover);
  box-shadow: var(--shadow-floating);
}

.apple-video-card:active {
  transform: translateY(-1px) scale(0.995);
}

.apple-video-card__cover {
  position: relative;
  aspect-ratio: 3 / 4;
  overflow: hidden;
  background: var(--surface-control);
}

.apple-video-card__image,
.apple-video-card__fallback {
  width: 100%;
  height: 100%;
}

.apple-video-card__image {
  object-fit: cover;
  object-position: center;
  transition: transform var(--motion-emphasized), filter var(--motion-emphasized);
}

.apple-video-card:hover .apple-video-card__image {
  transform: scale(1.045);
  filter: saturate(1.08);
}

.apple-video-card__image.is-wide {
  object-fit: none;
  object-position: right center;
  clip-path: inset(0 0 0 50%);
}

.apple-video-card__fallback {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 18px;
  color: var(--text-muted);
  background:
    radial-gradient(circle at 35% 20%, rgba(var(--accent-rgb), 0.16), transparent 42%),
    var(--surface-control);
  text-align: center;
  font-family: var(--font-mono);
  font-size: var(--type-caption);
}

.apple-video-card__preview,
.apple-video-card__favorite {
  position: absolute;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  backdrop-filter: blur(16px) saturate(180%);
  -webkit-backdrop-filter: blur(16px) saturate(180%);
  border: 1px solid var(--border-light);
}

.apple-video-card__preview {
  right: 10px;
  bottom: 10px;
  width: 28px;
  height: 28px;
  border-radius: var(--radius-control);
  color: var(--text-primary);
  background: var(--material-glass-sheet);
}

.apple-video-card__favorite {
  top: 10px;
  right: 10px;
  width: var(--touch-target);
  height: var(--touch-target);
  border-radius: 50%;
  color: var(--text-primary);
  background: var(--material-glass-sheet);
  cursor: pointer;
  opacity: 0;
  transform: scale(0.86);
  transition: opacity var(--motion-fast), transform var(--motion-fast), background var(--motion-fast), color var(--motion-fast);
}

.apple-video-card:hover .apple-video-card__favorite,
.apple-video-card__favorite.is-active {
  opacity: 1;
  transform: scale(1);
}

.apple-video-card__favorite:hover {
  background: var(--material-glass-elevated);
  transform: scale(1.06);
}

.apple-video-card__favorite.is-active {
  color: #FF375F;
  background: rgba(255, 55, 95, 0.14);
  border-color: rgba(255, 55, 95, 0.32);
}

.apple-video-card__favorite:active svg {
  transform: scale(0.84);
}

.apple-video-card__body {
  padding: 14px 15px 16px;
}

.apple-video-card__meta-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 7px;
}

.apple-video-card__code {
  min-width: 0;
  color: var(--text-primary);
  font-family: var(--font-mono);
  font-size: var(--type-caption);
  font-weight: 650;
  letter-spacing: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.apple-video-card__badge {
  flex-shrink: 0;
  padding: 2px 7px;
  border-radius: 999px;
  background: var(--badge-info-bg);
  border: 1px solid var(--badge-info-border);
  color: var(--badge-info-text);
  font-size: 10px;
  font-weight: 600;
}

.apple-video-card__title {
  margin: 0 0 8px;
  color: var(--text-secondary);
  font-size: var(--type-control);
  font-weight: 500;
  line-height: 1.45;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.apple-video-card__subline {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--text-muted);
  font-size: var(--type-micro);
}

@media (hover: none) {
  .apple-video-card__favorite {
    opacity: 1;
    transform: scale(1);
  }
}
</style>
