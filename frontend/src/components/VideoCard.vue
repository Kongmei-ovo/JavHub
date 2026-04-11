<template>
  <div class="video-card" @click="$emit('click')">
    <div class="video-cover">
      <img :src="coverUrl" :alt="contentId" @error="handleImageError" />
    </div>
    <div class="video-info">
      <div class="video-code">{{ contentId }}</div>
      <div class="video-actresses">{{ actressNames }}</div>
      <div class="video-date">{{ releaseDate }}</div>
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
  background: #fff;
  border-radius: 8px;
  overflow: hidden;
  cursor: pointer;
  transition: transform 0.2s;
}
.video-card:hover {
  transform: translateY(-2px);
}
.video-cover img {
  width: 100%;
  aspect-ratio: 3/4;
  object-fit: cover;
}
.video-info {
  padding: 8px;
}
.video-code {
  font-weight: bold;
  margin-bottom: 4px;
}
.video-actresses {
  font-size: 12px;
  color: #666;
  margin-bottom: 4px;
}
.video-date {
  font-size: 12px;
  color: #999;
}
</style>
