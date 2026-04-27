<template>
  <div class="video-card av-card" @click="$emit('click')">
    <div class="video-cover">
      <img :src="coverUrl" :alt="contentId" @error="handleImageError" />
      <div class="cover-overlay">
        <span class="cover-code">{{ contentId }}</span>
      </div>
      <div v-if="!coverUrl || imageError" class="cover-placeholder">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="32" height="32">
          <rect x="2" y="2" width="20" height="20" rx="2.18" ry="2.18"/>
          <circle cx="8.5" cy="8.5" r="1.5"/>
          <path d="M21 15l-5-5L5 21"/>
        </svg>
      </div>
    </div>
    <div class="video-info">
      <div class="video-code">{{ contentId }}</div>
      <div v-if="actressNames" class="video-actresses">{{ actressNames }}</div>
      <div v-if="releaseDate" class="video-date">{{ releaseDate }}</div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'

const props = defineProps({
  contentId: { type: String, required: true },
  title: { type: String, default: '' },
  coverUrl: { type: String, default: '' },
  actressNames: { type: String, default: '' },
  releaseDate: { type: String, default: '' }
})

defineEmits(['click'])

const imageError = ref(false)
const handleImageError = () => {
  imageError.value = true
}
</script>

<style scoped>
.video-card {
  cursor: pointer;
  overflow: hidden;
}

.video-cover {
  position: relative;
  aspect-ratio: 3/4;
  overflow: hidden;
  background: var(--bg-secondary);
}

.video-cover img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 0.4s cubic-bezier(0.4, 0, 0.2, 1);
}

.video-card:hover .video-cover img {
}

.cover-placeholder {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg-card);
  color: var(--text-muted);
}

.cover-overlay {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  padding: 8px 10px;
  background: rgba(0, 0, 0, 0.4);
  backdrop-filter: blur(4px);
  -webkit-backdrop-filter: blur(4px);
}

.cover-code {
  font-size: 12px;
  font-weight: 600;
  color: white;
  letter-spacing: 0.02em;
}

.video-info {
  padding: 10px 12px 12px;
}

.video-code {
  font-weight: 600;
  font-size: 13px;
  color: var(--text-primary);
  margin-bottom: 4px;
}

.video-actresses {
  font-size: 12px;
  color: var(--text-secondary);
  margin-bottom: 4px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.video-date {
  font-size: 11px;
  color: var(--text-muted);
}
</style>
