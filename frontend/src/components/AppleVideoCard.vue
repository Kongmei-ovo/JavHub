<template>
  <article
    class="apple-video-card"
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
        decoding="async"
        class="apple-video-card__image"
        @error="onImageError"
        @load="onImageLoad"
      />
      <div v-else class="apple-video-card__fallback">
        <span>{{ fallbackText }}</span>
      </div>

      <div class="apple-video-card__scrim" aria-hidden="true"></div>

      <div class="apple-video-card__overlay-top">
        <span v-if="displayCode" class="apple-video-card__code">{{ displayCode }}</span>
        <div
          v-if="variantLabels.length"
          class="apple-video-card__variant-stack"
          :title="variantTooltip"
        >
          <span
            v-for="label in variantLabels"
            :key="label.key || label.label"
            class="apple-video-card__variant-pill"
          >
            {{ label.short_label || label.label }}
          </span>
        </div>
      </div>

      <span v-if="serviceLabel" class="apple-video-card__badge">{{ serviceLabel }}</span>
    </div>

    <div class="apple-video-card__meta">
      <h3 class="apple-video-card__title" :title="titleText">{{ titleText }}</h3>
      <div v-if="sublineParts.length" class="apple-video-card__subline" :title="sublineTooltip">
        <template v-for="(part, index) in sublineParts" :key="part.key">
          <span v-if="index > 0" class="apple-video-card__dot" aria-hidden="true"></span>
          <span :class="part.className">{{ part.text }}</span>
        </template>
      </div>
    </div>
  </article>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { normalizeVideo, videoCoverCandidates } from '../utils/videoNormalize.js'

const props = defineProps({
  video: { type: Object, required: true },
  coverUrl: { type: String, default: '' },
})

const emit = defineEmits(['open'])

const imageError = ref(false)
const wideImage = ref(false)
const coverIndex = ref(0)
const normalized = computed(() => normalizeVideo(props.video))
const coverCandidates = computed(() => videoCoverCandidates(normalized.value, props.coverUrl))
const coverUrl = computed(() => imageError.value ? '' : (coverCandidates.value[coverIndex.value] || ''))
const titleText = computed(() => normalized.value.title_ja || normalized.value.title_en || normalized.value.title || 'Untitled')
const displayCode = computed(() => normalized.value.display_code || normalized.value.dvd_id || normalized.value.content_id || '')
const fallbackText = computed(() => (displayCode.value || '?').slice(0, 12))
const serviceLabel = computed(() => {
  const map = { mono: 'DVD', digital: '数字', rental: '租赁', ebook: '写真', download: '下载', streaming: '流媒体', subscription: '订阅' }
  return map[normalized.value.service_code] || normalized.value.service_code || ''
})
const variantLabels = computed(() => {
  const labels = Array.isArray(normalized.value.variant_labels) ? normalized.value.variant_labels : []
  return labels
    .filter(label => label && (label.short_label || label.label))
    .slice(0, 2)
})
const actressNames = computed(() => {
  const list = Array.isArray(normalized.value.actresses) ? normalized.value.actresses : []
  return list
    .map(item => item?.name_kanji || item?.name_translated || item?.name_romaji || item?.name)
    .filter(name => typeof name === 'string' && name.trim())
})
const actressLine = computed(() => {
  const top = actressNames.value.slice(0, 2).join(' / ')
  const extra = actressNames.value.length - 2
  return extra > 0 ? `${top} +${extra}` : top
})
const sublineParts = computed(() => {
  const parts = []
  if (actressLine.value) {
    parts.push({ key: 'actress', text: actressLine.value, className: 'apple-video-card__subline-actress' })
  }
  if (normalized.value.runtime_mins) {
    parts.push({ key: 'runtime', text: `${normalized.value.runtime_mins} 分钟`, className: 'apple-video-card__subline-runtime' })
  }
  if (normalized.value.release_date) {
    parts.push({ key: 'date', text: normalized.value.release_date, className: 'apple-video-card__subline-date' })
  }
  return parts
})
const sublineTooltip = computed(() => sublineParts.value.map(part => part.text).join(' · '))

const variantTooltip = computed(() => {
  const explanations = Array.isArray(normalized.value.variant_explanations)
    ? normalized.value.variant_explanations
    : []
  if (explanations.length) {
    return explanations
      .map(item => {
        const label = item.label || item.raw || '版本'
        const meaning = item.meaning || item.evidence || ''
        return meaning ? `${label}：${meaning}` : label
      })
      .join('\n')
  }
  const labels = Array.isArray(normalized.value.variant_labels) ? normalized.value.variant_labels : []
  return labels.map(label => label.label || label.short_label).filter(Boolean).join(' / ')
})

watch(coverCandidates, () => {
  coverIndex.value = 0
  imageError.value = false
  wideImage.value = false
})

function onImageError() {
  const nextIndex = coverIndex.value + 1
  if (nextIndex < coverCandidates.value.length) {
    coverIndex.value = nextIndex
    wideImage.value = false
    return
  }
  imageError.value = true
}

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
/* Poster-first card (Wave B redesign). Card root is structural only — the
   cover element carries the surface, shadow and lift so the poster reads as
   the hero, with glass reserved for the small chrome overlays. */
.apple-video-card {
  cursor: pointer;
  container-type: inline-size;
  display: flex;
  flex-direction: column;
  gap: 12px;
  background: transparent;
  border: 0;
  border-radius: 0;
  outline: none;
}

.apple-video-card__cover {
  position: relative;
  aspect-ratio: var(--movie-card-cover-aspect, 3 / 4);
  overflow: hidden;
  border-radius: var(--radius-lg);
  background: var(--card-2);
  box-shadow: var(--shadow-card);
  /* Project render-containment guard restricts transition to transform/opacity;
     box-shadow updates snap on hover/focus instead of being animated. */
  transition: transform var(--motion-standard);
}

.apple-video-card:hover .apple-video-card__cover,
.apple-video-card:focus-visible .apple-video-card__cover {
  /* Prototype calls for -4px; project lift guard caps interactive translateY
     at 2px, so we stay light and lean on shadow + image zoom for emphasis. */
  transform: translateY(-2px);
  box-shadow: var(--shadow-hover);
}

.apple-video-card:focus-visible .apple-video-card__cover {
  box-shadow: var(--shadow-hover), var(--focus-ring-wide-strong);
}

.apple-video-card:active .apple-video-card__cover {
  /* WAVE-3 E3: card depth on press — sink 0.5px and scale tight, image
     pulls back from hover scale for a synchronised tactile push. */
  transform: translateY(-1px) scale(0.99);
}
.apple-video-card:active .apple-video-card__image {
  transform: scale(1.01);
}

.apple-video-card__image,
.apple-video-card__fallback {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
}

.apple-video-card__image {
  object-fit: cover;
  object-position: center;
  transition: transform var(--motion-standard);
}

.apple-video-card:hover .apple-video-card__image,
.apple-video-card:focus-visible .apple-video-card__image {
  transform: scale(1.03);
  filter: saturate(1.08);
}

.apple-video-card__image.is-wide {
  object-fit: none;
  object-position: right center;
  clip-path: inset(0 0 0 50%);
}

.apple-video-card__scrim {
  position: absolute;
  inset: 0;
  pointer-events: none;
  background:
    linear-gradient(180deg, var(--black-40) 0%, var(--black-00) 22%, var(--black-00) 70%, var(--black-40) 100%);
}

.apple-video-card__overlay-top {
  position: absolute;
  top: 10px;
  left: 10px;
  z-index: 2;
  display: flex;
  flex-direction: column;
  gap: 5px;
  max-width: calc(100% - 88px);
  pointer-events: auto;
}

.apple-video-card__code {
  align-self: flex-start;
  padding: 3px 8px;
  border-radius: var(--radius-sm);
  background: var(--black-40);
  color: var(--media-caption-text);
  font-family: var(--font-mono);
  font-size: var(--type-micro);
  font-weight: 650;
  letter-spacing: 0.4px;
  line-height: 1.25;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 100%;
  backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
  -webkit-backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
}

.apple-video-card__variant-stack {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.apple-video-card__variant-pill {
  max-width: 72px;
  padding: 3px 7px;
  border-radius: var(--radius-control);
  background: var(--card);
  border: 1px solid var(--glass-edge);
  color: var(--text-primary);
  font-size: var(--type-badge);
  font-weight: 650;
  line-height: 1.15;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  box-shadow: none;
}

.apple-video-card__badge {
  position: absolute;
  top: 10px;
  right: 10px;
  z-index: 2;
  padding: 3px 8px;
  border-radius: var(--radius-control);
  background: var(--surface-specular-edge), var(--surface-noise), var(--badge-info-bg);
  border: 1px solid var(--badge-info-border);
  color: var(--badge-info-text);
  font-size: var(--type-badge);
  font-weight: 650;
  line-height: 1.2;
  box-shadow: var(--glass-control-shadow);
  backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
  -webkit-backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
}

.apple-video-card__fallback {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 18px;
  background: var(--card-2);
  color: var(--text-muted);
  text-align: center;
  font-family: var(--font-mono);
  font-size: var(--type-caption);
}

.apple-video-card__meta {
  padding: 0 2px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.apple-video-card__title {
  margin: 0;
  color: var(--text-primary);
  font-size: var(--type-callout);
  font-weight: 600;
  line-height: 1.35;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  text-wrap: pretty;
}

.apple-video-card__subline {
  display: flex;
  align-items: center;
  gap: 6px;
  color: var(--text-muted);
  font-size: var(--type-caption);
  font-variant-numeric: tabular-nums;
  min-width: 0;
}

.apple-video-card__subline > span {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.apple-video-card__subline-actress {
  color: var(--text-secondary);
  font-weight: 550;
  flex: 0 1 auto;
}

.apple-video-card__dot {
  flex: 0 0 auto;
  width: 3px;
  height: 3px;
  border-radius: var(--radius-control);
  background: var(--text-muted);
}

@container (max-width: 180px) {
  .apple-video-card {
    gap: 8px;
  }

  .apple-video-card__cover {
    border-radius: var(--video-card-radius-mobile);
  }

  .apple-video-card__overlay-top {
    top: 7px;
    left: 7px;
    gap: 4px;
    max-width: calc(100% - 70px);
  }

  .apple-video-card__code {
    font-size: 10px;
    padding: 2px 6px;
  }

  .apple-video-card__badge {
    top: 7px;
    right: 7px;
    padding: 2px 6px;
    font-size: 9px;
  }

  .apple-video-card__variant-pill {
    max-width: 58px;
    padding: 2px 5px;
    font-size: 9px;
  }

  .apple-video-card__meta {
    padding: var(--video-card-body-padding-mobile);
  }

  .apple-video-card__title {
    font-size: 12px;
    line-height: 1.3;
  }

  .apple-video-card__subline {
    font-size: 10px;
    line-height: 1.25;
  }
}
</style>
