<template>
  <div class="actress-card" @click="$emit('click')">
    <div class="card-cover">
      <img
        :src="coverUrl"
        :alt="name"
        @error="handleImgError"
        loading="lazy"
        class="cover-img"
      />
      <div class="card-overlay">
        <div class="overlay-name">{{ name }}</div>
        <div v-if="totalCount != null" class="overlay-meta">
          {{ totalCount }} 部<span v-if="missingCount > 0"> · {{ missingCount }} 缺失</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  coverUrl: { type: String, default: '' },
  name: { type: String, default: '未知' },
  totalCount: { type: Number, default: null },
  missingCount: { type: Number, default: 0 }
})

defineEmits(['click'])

const handleImgError = (e) => {
  e.target.style.display = 'none'
}
</script>

<style scoped>
.actress-card {
  background: rgba(255, 255, 255, 0.04);
  backdrop-filter: blur(40px) saturate(200%);
  -webkit-backdrop-filter: blur(40px) saturate(200%);
  border-radius: 14px;
  overflow: hidden;
  cursor: pointer;
  transition: all 0.35s cubic-bezier(0.23, 1, 0.32, 1);
  border: 1px solid rgba(255, 255, 255, 0.08);
}

.actress-card:hover {
  transform: translateY(-6px);
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.4), 0 0 0 1px rgba(255, 255, 255, 0.12);
  border-color: rgba(255, 255, 255, 0.15);
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
  object-position: center top;
  transition: transform 0.5s cubic-bezier(0.23, 1, 0.32, 1);
}

.actress-card:hover .cover-img {
  transform: scale(1.06);
}

.card-overlay {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  padding: 32px 12px 12px;
  background: linear-gradient(to top, rgba(0, 0, 0, 0.8) 0%, transparent 100%);
}

.overlay-name {
  font-size: 13px;
  font-weight: 600;
  color: #fff;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  text-shadow: 0 1px 4px rgba(0, 0, 0, 0.5);
}

.overlay-meta {
  font-size: 11px;
  color: rgba(255, 255, 255, 0.65);
  margin-top: 2px;
}
</style>
