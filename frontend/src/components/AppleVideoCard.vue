<template>
  <article
    class="apple-video-card apple-surface"
    role="button"
    tabindex="0"
    @click="openCard"
    @keydown="handleKeydown"
  >
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
})

const emit = defineEmits(['open'])

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

function openCard() {
  emit('open', normalized.value)
}

function handleKeydown(event) {
  if (event.repeat) return
  if (event.key !== 'Enter' && event.key !== ' ') return
  event.preventDefault()
  openCard()
}
</script>

<style scoped>
.apple-video-card {
  cursor: pointer;
  overflow: hidden;
  container-type: inline-size;
  transition: transform var(--motion-standard), border-color var(--motion-standard), box-shadow var(--motion-standard), background var(--motion-standard);
}

.apple-video-card:hover {
  transform: translateY(-3px);
  border-color: var(--border-light);
  background: var(--surface-card-hover);
  box-shadow: var(--shadow-floating), var(--glass-surface-shadow);
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
  min-width: 0;
  flex-wrap: wrap;
}

@container (max-width: 180px) {
  .apple-video-card {
    border-radius: var(--video-card-radius-mobile);
  }

  .apple-video-card__body {
    padding: var(--video-card-body-padding-mobile);
  }

  .apple-video-card__meta-row {
    gap: 5px;
    margin-bottom: 5px;
  }

  .apple-video-card__code {
    font-size: 11px;
  }

  .apple-video-card__badge {
    padding: 1px 5px;
    font-size: 9px;
  }

  .apple-video-card__title {
    margin-bottom: 6px;
    font-size: 12px;
    line-height: 1.35;
  }

  .apple-video-card__subline {
    gap: 4px 6px;
    font-size: 10px;
    line-height: 1.25;
  }

}
</style>
