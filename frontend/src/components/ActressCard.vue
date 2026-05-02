<template>
  <div class="actress-card" @click="$emit('click')">
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
        <svg viewBox="0 0 24 24" width="14" height="14"><path d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z" fill="#FF375F"/></svg>
      </span>
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
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  coverUrl: { type: String, default: '' },
  name: { type: String, default: '未知' },
  originalName: { type: String, default: '' },
  totalCount: { type: Number, default: null },
  subscribed: { type: Boolean, default: false }
})

defineEmits(['click'])

const handleImgError = (e) => {
  e.target.src = 'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" width="200" height="280" viewBox="0 0 200 280"><rect fill="%231a1a2e" width="200" height="280"/><text x="50%" y="50%" text-anchor="middle" dy=".3em" fill="%23555" font-size="36">?</text></svg>'
}
</script>

<style scoped>
.actress-card {
  background: rgba(255, 255, 255, 0.04);
  backdrop-filter: blur(80px) saturate(200%);
  -webkit-backdrop-filter: blur(80px) saturate(200%);
  border-radius: 16px;
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

/* ===== Cover ===== */
.card-cover {
  position: relative;
  width: 100%;
  aspect-ratio: 3/4;
  overflow: hidden;
  background: rgba(255, 255, 255, 0.03);
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

.cover-fade {
  position: absolute;
  bottom: 0; left: 0; right: 0;
  height: 50%;
  background: linear-gradient(to top, rgba(10, 10, 12, 0.95) 0%, rgba(10, 10, 12, 0.4) 50%, transparent 100%);
  pointer-events: none;
}

/* Count badge */
.cover-badge {
  position: absolute;
  top: 8px; left: 8px;
  display: inline-flex; align-items: center; gap: 3px;
  height: 22px; padding: 0 8px;
  border-radius: 7px;
  background: rgba(0, 0, 0, 0.55);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border: 0.5px solid rgba(255, 255, 255, 0.12);
  color: rgba(255, 255, 255, 0.85);
  font-size: 11px;
  font-weight: 600;
  pointer-events: none;
}

/* Heart */
.cover-heart {
  position: absolute;
  top: 8px; right: 8px;
  width: 24px; height: 24px;
  border-radius: 50%;
  background: rgba(0, 0, 0, 0.45);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border: 0.5px solid rgba(255, 255, 255, 0.1);
  display: flex; align-items: center; justify-content: center;
  pointer-events: none;
}

/* ===== Info ===== */
.card-info {
  padding: 10px 12px 14px;
}

.info-name {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  line-height: 1.3;
}

.info-sub {
  font-size: 11px;
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
  color: #FF375F;
}
</style>
