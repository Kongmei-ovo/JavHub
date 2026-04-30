<template>
  <div class="movie-card" @click="$emit('click')">
    <div class="card-cover">
      <img
        :src="coverUrl"
        :alt="contentId"
        @error="handleImgError"
        @load="onImgLoad($event)"
        loading="lazy"
        class="cover-img"
      />
      <div v-if="sampleUrl" class="card-preview-badge" title="有预览视频">
        <svg viewBox="0 0 24 24" fill="currentColor" width="12" height="12">
          <path d="M8 5v14l11-7z"/>
        </svg>
      </div>
      <button
        class="favorite-toggle"
        :class="{ 'is-active': isFavorited }"
        @click.stop="$emit('toggle-favorite')"
      >
        <svg class="heart-icon" viewBox="0 0 24 24" width="16" height="16">
          <path v-if="isFavorited" d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z" fill="currentColor"/>
          <path v-else d="M16.5 3c-1.74 0-3.41.81-4.5 2.09C10.91 3.81 9.24 3 7.5 3 4.42 3 2 5.42 2 8.5c0 3.78 3.4 6.86 8.55 11.54L12 21.35l1.45-1.32C18.6 15.36 22 12.28 22 8.5 22 5.42 19.58 3 16.5 3zm-4.4 15.55l-.1.1-.1-.1C7.14 14.24 4 11.39 4 8.5 4 6.5 5.5 5 7.5 5c1.54 0 3.04.99 3.57 2.36h1.87C13.46 5.99 14.96 5 16.5 5c2 0 3.5 1.5 3.5 3.5 0 2.89-3.14 5.74-7.9 10.05z" fill="currentColor"/>
        </svg>
      </button>
    </div>
    <div class="card-info">
      <div class="card-code-row">
        <span class="card-code">{{ contentId }}</span>
        <span v-if="serviceCode" class="card-type" :class="'type-' + serviceCode">{{ formatServiceCode(serviceCode) }}</span>
      </div>
      <div class="card-title" :title="title">{{ title }}</div>
      <div class="card-meta">
        <span v-if="releaseDate" class="meta-date">{{ releaseDate }}</span>
        <span v-if="runtimeMins" class="meta-time">{{ runtimeMins }}分钟</span>
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  contentId: { type: String, required: true },
  coverUrl: { type: String, default: '' },
  title: { type: String, default: '' },
  serviceCode: { type: String, default: '' },
  releaseDate: { type: String, default: '' },
  runtimeMins: { type: [String, Number], default: '' },
  sampleUrl: { type: String, default: '' },
  isFavorited: { type: Boolean, default: false }
})

defineEmits(['click', 'toggle-favorite'])

const handleImgError = (e) => {
  e.target.src = 'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" width="200" height="280" viewBox="0 0 200 280"><rect fill="%231a1a2e" width="200" height="280"/><text x="50%" y="50%" text-anchor="middle" dy=".3em" fill="%236B6B8A" font-size="14">暂无封面</text></svg>'
}

const onImgLoad = (e) => {
  const img = e.target
  if (img.naturalWidth > img.naturalHeight) {
    img.classList.add('wide')
  }
}

const formatServiceCode = (code) => {
  const map = {
    'mono': 'DVD',
    'digital': '数字',
    'rental': '租赁',
    'download': '下载',
    'streaming': '流媒体',
    'subscription': '订阅'
  }
  return map[code] || code
}
</script>

<style scoped>
.movie-card {
  background: var(--bg-card);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border-radius: var(--radius-md);
  overflow: hidden;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.2, 0, 0, 1);
  border: 1px solid var(--border);
}

.movie-card:hover {
  transform: translateY(-4px);
  box-shadow: var(--shadow-hover);
  border-color: var(--accent);
}

.card-cover {
  position: relative;
  width: 100%;
  aspect-ratio: 3/4;
  overflow: hidden;
  background: var(--bg-secondary);
}

.cover-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  object-position: center;
  transition: transform 0.4s cubic-bezier(0.4, 0, 0.2, 1);
}

.movie-card:hover .cover-img {
  transform: scale(1.05);
}

.cover-img.wide {
  object-fit: none;
  object-position: right center;
  clip-path: inset(0 0 0 50%);
}

.card-preview-badge {
  position: absolute;
  top: 6px;
  right: 6px;
  background: rgba(0,0,0,0.65);
  border-radius: 4px;
  padding: 3px 5px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  pointer-events: none;
}

.favorite-toggle {
  position: absolute;
  top: 10px;
  left: 10px;
  width: 30px;
  height: 30px;
  border-radius: 50%;
  background: rgba(0, 0, 0, 0.25);
  backdrop-filter: blur(16px) saturate(180%);
  -webkit-backdrop-filter: blur(16px) saturate(180%);
  border: 0.5px solid rgba(255, 255, 255, 0.15);
  display: flex;
  align-items: center;
  justify-content: center;
  color: rgba(255, 255, 255, 0.85);
  cursor: pointer;
  transition: all 0.25s cubic-bezier(0.23, 1, 0.32, 1);
  opacity: 0;
  transform: scale(0.85);
  z-index: 5;
  padding: 0;
}

.movie-card:hover .favorite-toggle {
  opacity: 1;
  transform: scale(1);
}

.favorite-toggle:hover {
  background: rgba(0, 0, 0, 0.4);
  transform: scale(1.08);
  border-color: rgba(255, 255, 255, 0.2);
}

.favorite-toggle:active {
  transform: scale(0.92);
}

.favorite-toggle.is-active {
  opacity: 1;
  transform: scale(1);
  color: #FF375F;
  background: rgba(255, 55, 95, 0.12);
  border-color: rgba(255, 55, 95, 0.25);
}

.favorite-toggle.is-active:hover {
  background: rgba(255, 55, 95, 0.2);
  transform: scale(1.08);
}

.heart-icon {
  transition: transform 0.25s cubic-bezier(0.23, 1, 0.32, 1);
}

.favorite-toggle:active .heart-icon {
  transform: scale(0.85);
}

.favorite-toggle.is-active .heart-icon {
  animation: heartPop 0.35s cubic-bezier(0.23, 1, 0.32, 1);
}

@keyframes heartPop {
  0% { transform: scale(1); }
  30% { transform: scale(1.25); }
  60% { transform: scale(0.95); }
  100% { transform: scale(1); }
}

.card-info {
  padding: 10px;
}

.card-code-row {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 6px;
  margin-bottom: 4px;
}

.card-code {
  font-weight: bold;
  font-size: 13px;
}

.card-type {
  font-size: 10px;
  padding: 2px 6px;
  border-radius: 4px;
  font-weight: 600;
}

.type-mono { background: rgba(76, 175, 80, 0.2); color: #4CAF50; }
.type-digital { background: rgba(33, 150, 243, 0.2); color: #2196F3; }
.type-rental { background: rgba(255, 152, 0, 0.2); color: #FF9800; }
.type-download { background: rgba(156, 39, 176, 0.2); color: #9C27B0; }
.type-streaming, .type-subscription { background: rgba(244, 67, 54, 0.2); color: #F44336; }

.card-title {
  font-size: 12px;
  color: var(--text-secondary);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  margin-bottom: 4px;
}

.card-meta {
  display: flex;
  gap: 8px;
  font-size: 11px;
  color: var(--text-muted);
}
</style>
