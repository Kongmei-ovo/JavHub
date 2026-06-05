<template>
  <article
    class="actor-portrait-card"
    :class="[`actor-portrait-card--${density}`, { 'is-favorited': favorited, 'is-subscribed': subscribed }]"
    role="button"
    tabindex="0"
    :aria-label="`打开演员 ${displayNameText}`"
    @click="emitOpen"
    @keydown.enter.prevent="emitOpen"
    @keydown.space.prevent="emitOpen"
  >
    <div class="actor-portrait-card__media">
      <img
        v-if="displayAvatar && !imageErrored"
        :src="displayAvatar"
        :alt="displayNameText"
        loading="lazy"
        @error="handleImageError"
      />
      <div v-else class="actor-portrait-card__fallback">{{ displayInitial }}</div>
      <button
        v-if="showFavorite"
        class="actor-portrait-card__favorite"
        type="button"
        :aria-label="favorited ? '取消收藏演员' : '收藏演员'"
        @click.stop="emitFavorite"
        @keydown.enter.stop.prevent="emitFavorite"
        @keydown.space.stop.prevent="emitFavorite"
      >
        <svg viewBox="0 0 24 24" width="15" height="15" aria-hidden="true">
          <path
            d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"
            :fill="favorited ? 'currentColor' : 'none'"
            stroke="currentColor"
            stroke-width="1.8"
            stroke-linecap="round"
            stroke-linejoin="round"
          />
        </svg>
      </button>
      <button
        v-if="showSubscribe"
        class="actor-portrait-card__subscribe"
        type="button"
        :aria-label="subscribeAriaLabel"
        :title="subscribeButtonTitle"
        :disabled="subscribeDisabled"
        @click.stop="emitSubscribe"
        @keydown.enter.stop.prevent="emitSubscribe"
        @keydown.space.stop.prevent="emitSubscribe"
      >
        <svg viewBox="0 0 24 24" width="15" height="15" aria-hidden="true">
          <path
            d="M19 3H5a2 2 0 0 0-2 2v16l9-4 9 4V5a2 2 0 0 0-2-2zm-2 11H7v-2h10v2zm0-4H7V8h10v2z"
            fill="currentColor"
          />
        </svg>
      </button>
    </div>

    <div class="actor-portrait-card__body">
      <strong class="actor-portrait-card__name">{{ displayNameText }}</strong>
      <span v-if="displaySubtitle" class="actor-portrait-card__subtitle">{{ displaySubtitle }}</span>
      <span v-if="displayMeta" class="actor-portrait-card__meta">{{ displayMeta }}</span>
      <div v-if="normalizedBadges.length" class="actor-portrait-card__badges">
        <span
          v-for="badge in normalizedBadges"
          :key="`${badge.tone}-${badge.label}`"
          class="actor-portrait-card__badge"
          :class="`actor-portrait-card__badge--${badge.tone}`"
        >{{ badge.label }}</span>
      </div>
      <span v-if="actionLabel" class="actor-portrait-card__action">{{ actionLabel }}</span>
    </div>
  </article>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { actorAvatar, actorInitial, actorName, actorOriginalName } from '../utils/actorDisplay.js'

const props = defineProps({
  actor: { type: Object, default: null },
  name: { type: String, default: '' },
  subtitle: { type: String, default: '' },
  meta: { type: String, default: '' },
  avatarUrl: { type: String, default: '' },
  badges: { type: Array, default: () => [] },
  density: {
    type: String,
    default: 'standard',
    validator: (value) => ['standard', 'compact'].includes(value),
  },
  actionLabel: { type: String, default: '' },
  showFavorite: { type: Boolean, default: false },
  favorited: { type: Boolean, default: false },
  showSubscribe: { type: Boolean, default: false },
  subscribed: { type: Boolean, default: false },
  subscribeDisabled: { type: Boolean, default: false },
  subscribeTitle: { type: String, default: '' },
})

const emit = defineEmits(['open', 'favorite', 'subscribe'])
const imageErrored = ref(false)

const displayNameText = computed(() => props.name || actorName(props.actor, '未知演员') || '未知演员')
const rawSubtitle = computed(() => props.subtitle || actorOriginalName(props.actor))
const displaySubtitle = computed(() => (
  rawSubtitle.value && rawSubtitle.value !== displayNameText.value ? rawSubtitle.value : ''
))
const displayMeta = computed(() => props.meta || '')
const displayAvatar = computed(() => props.avatarUrl || actorAvatar(props.actor))
const displayInitial = computed(() => actorInitial(props.actor, displayNameText.value))
const normalizedBadges = computed(() => props.badges
  .filter(badge => badge && badge.label)
  .map(badge => ({ label: badge.label, tone: badge.tone || 'neutral' })))
const subscribeAriaLabel = computed(() => (props.subscribed ? '取消订阅演员' : '订阅演员'))
const subscribeButtonTitle = computed(() => (
  props.subscribeTitle || (props.subscribed ? '取消订阅演员' : '订阅演员')
))

watch(displayAvatar, () => {
  imageErrored.value = false
})

function handleImageError() {
  imageErrored.value = true
}

function emitOpen() {
  emit('open', props.actor)
}

function emitFavorite() {
  emit('favorite', props.actor)
}

function emitSubscribe() {
  emit('subscribe', props.actor)
}
</script>

<style scoped>
.actor-portrait-card {
  position: relative;
  display: grid;
  gap: 12px;
  width: 100%;
  padding: 10px;
  border: 1px solid var(--glass-control-border);
  border-radius: var(--radius-card);
  background: var(--surface-specular-edge), var(--surface-noise), var(--material-glass-control);
  box-shadow: var(--glass-control-shadow);
  color: var(--text-primary);
  cursor: pointer;
  text-align: left;
  transition:
    transform var(--motion-standard),
    border-color var(--motion-standard),
    background var(--motion-standard),
    box-shadow var(--motion-standard);
  outline: none;
  backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
  -webkit-backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
}

.actor-portrait-card:hover {
  transform: translateY(-5px);
  border-color: var(--glass-control-border-hover);
  background: var(--surface-specular-edge-strong), var(--surface-noise), var(--material-glass-control-hover);
  box-shadow: var(--glass-control-shadow-hover);
}

.actor-portrait-card:focus-visible {
  border-color: var(--glass-control-border-hover);
  background: var(--surface-specular-edge-strong), var(--surface-noise), var(--material-glass-control-hover);
  box-shadow:
    var(--glass-control-shadow-hover),
    0 0 0 4px rgba(var(--accent-rgb), 0.12),
    var(--glass-active-shadow);
}

.actor-portrait-card:active {
  transform: translateY(-2px) scale(0.99);
}

.actor-portrait-card__media {
  position: relative;
  overflow: hidden;
  aspect-ratio: 3 / 4;
  border: 1px solid var(--glass-control-border);
  border-radius: calc(var(--radius-card) - 8px);
  background:
    var(--surface-specular-edge),
    var(--surface-noise),
    var(--material-glass-subtle);
  box-shadow: var(--glass-inner-shadow);
}

.actor-portrait-card__media img,
.actor-portrait-card__fallback {
  width: 100%;
  height: 100%;
}

.actor-portrait-card__media img {
  display: block;
  object-fit: cover;
  object-position: top center;
  transition: transform var(--motion-emphasized);
}

.actor-portrait-card:hover .actor-portrait-card__media img {
  transform: scale(1.045);
}

.actor-portrait-card:focus-visible .actor-portrait-card__media img {
  transform: scale(1.045);
}

.actor-portrait-card__fallback {
  display: grid;
  place-items: center;
  color: var(--text-secondary);
  font-size: 42px;
  font-weight: 700;
}

.actor-portrait-card__favorite,
.actor-portrait-card__subscribe {
  position: absolute;
  top: 9px;
  display: grid;
  place-items: center;
  width: 32px;
  height: 32px;
  padding: 0;
  border: 1px solid var(--glass-edge);
  border-radius: 50%;
  background: var(--surface-specular-edge), var(--surface-noise), var(--material-glass-sheet);
  color: var(--text-muted);
  box-shadow: var(--glass-control-shadow);
  backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
  -webkit-backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
  cursor: pointer;
  transition: transform var(--motion-fast), background var(--motion-fast), border-color var(--motion-fast), box-shadow var(--motion-fast), color var(--motion-fast), opacity var(--motion-fast);
}

.actor-portrait-card__favorite {
  right: 9px;
  color: var(--text-muted);
}

.actor-portrait-card__subscribe {
  left: 9px;
  color: var(--text-muted);
}

.actor-portrait-card__favorite:hover,
.actor-portrait-card__subscribe:hover {
  transform: scale(1.07);
  background: var(--surface-specular-edge-strong), var(--surface-noise), var(--material-glass-control-hover);
  border-color: var(--glass-control-border-hover);
  box-shadow: var(--glass-control-shadow-hover);
}

.actor-portrait-card__favorite:focus-visible,
.actor-portrait-card__subscribe:focus-visible {
  outline: none;
  background: var(--surface-specular-edge-strong), var(--surface-noise), var(--material-glass-control-hover);
  border-color: var(--glass-control-border-hover);
  box-shadow:
    var(--glass-control-shadow-hover),
    0 0 0 3px rgba(var(--accent-rgb), 0.16);
}

.actor-portrait-card__favorite:active,
.actor-portrait-card__subscribe:active {
  transform: scale(0.96);
}

.actor-portrait-card__subscribe:disabled {
  cursor: not-allowed;
  opacity: 0.48;
}

.actor-portrait-card.is-subscribed .actor-portrait-card__subscribe {
  background: var(--badge-success-bg);
  border-color: var(--badge-success-border);
  color: var(--badge-success-text);
  box-shadow: var(--glass-control-shadow);
}

.actor-portrait-card.is-favorited .actor-portrait-card__favorite {
  background: var(--badge-error-bg);
  border-color: var(--badge-error-border);
  color: var(--badge-error-text);
  box-shadow: var(--glass-control-shadow);
}

.actor-portrait-card__body {
  display: grid;
  gap: 5px;
  min-width: 0;
  padding: 0 3px 4px;
}

.actor-portrait-card__name,
.actor-portrait-card__subtitle,
.actor-portrait-card__meta {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.actor-portrait-card__name {
  font-size: var(--type-card-title);
  font-weight: 650;
  line-height: 1.25;
  color: var(--text-primary);
}

.actor-portrait-card__subtitle,
.actor-portrait-card__meta {
  color: var(--text-muted);
  font-size: var(--type-caption);
  line-height: 1.25;
}

.actor-portrait-card__badges {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 2px;
}

.actor-portrait-card__badge,
.actor-portrait-card__action {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 22px;
  width: fit-content;
  padding: 0 8px;
  border: 1px solid var(--glass-control-border);
  border-radius: 999px;
  font-size: var(--type-badge);
  font-weight: 700;
  white-space: nowrap;
}

.actor-portrait-card__badge--neutral {
  background: var(--surface-specular-edge), var(--surface-noise), var(--material-glass-control);
  border-color: var(--glass-control-border);
  color: var(--text-secondary);
}

.actor-portrait-card__badge--favorite {
  background: var(--badge-error-bg);
  border-color: var(--badge-error-border);
  color: var(--badge-error-text);
}

.actor-portrait-card__badge--subscribed,
.actor-portrait-card__badge--success {
  background: var(--badge-success-bg);
  border-color: var(--badge-success-border);
  color: var(--badge-success-text);
}

.actor-portrait-card__badge--warning {
  background: var(--badge-warning-bg);
  border-color: var(--badge-warning-border);
  color: var(--badge-warning-text);
}

.actor-portrait-card__action {
  margin-top: 4px;
  background: var(--surface-specular-edge-strong), var(--surface-noise), var(--glass-active-material);
  color: var(--text-primary);
  border: 1px solid var(--glass-active-border);
  box-shadow: var(--glass-active-shadow);
  backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
  -webkit-backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
}

.actor-portrait-card--compact {
  gap: 10px;
  padding: 9px;
  border-radius: 22px;
}

.actor-portrait-card--compact .actor-portrait-card__media {
  border-radius: 16px;
}

.actor-portrait-card--compact .actor-portrait-card__fallback {
  font-size: 32px;
}

.actor-portrait-card--compact .actor-portrait-card__name {
  font-size: var(--type-body);
}

.actor-portrait-card--compact .actor-portrait-card__subtitle,
.actor-portrait-card--compact .actor-portrait-card__meta {
  font-size: var(--type-micro);
}

</style>
