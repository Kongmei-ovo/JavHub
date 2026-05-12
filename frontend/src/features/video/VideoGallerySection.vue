<template>
  <div v-if="thumbs.length" class="modal-section">
    <h4 class="section-title">剧照</h4>
    <div class="gallery-grid">
      <div v-for="(thumb, idx) in thumbs" :key="idx" class="gallery-item" @click="$emit('open', idx)">
        <img :src="formatGalleryUrl(thumb)" :alt="'剧照 ' + (idx + 1)" loading="lazy" @error="onGalleryError" />
      </div>
    </div>
  </div>
  <div v-else-if="!videoLoaded" class="modal-section">
    <h4 class="section-title">剧照</h4>
    <div class="gallery-grid">
      <div v-for="n in 6" :key="n" class="gallery-item skeleton"></div>
    </div>
  </div>
</template>

<script>
import { galleryFullUrl, galleryThumbUrl } from '../../utils/imageUrl.js'

export default {
  name: 'VideoGallerySection',
  props: {
    thumbs: { type: Array, default: () => [] },
    videoLoaded: { type: Boolean, default: false },
  },
  emits: ['open'],
  methods: {
    formatGalleryUrl(path) {
      return galleryFullUrl(path) || galleryThumbUrl(path) || null
    },
    onGalleryError(e) {
      e.target.style.display = 'none'
    },
  },
}
</script>

<style scoped>
.modal-section { margin-top: 0; }
.section-title { font-size: 12px; font-weight: 700; margin-bottom: 20px; color: rgba(255, 255, 255, 0.5); text-transform: uppercase; letter-spacing: 0.12em; }
.gallery-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 16px; }
.gallery-item { aspect-ratio: 16/9; overflow: hidden; border-radius: var(--radius-md); background: rgba(255, 255, 255, 0.05); cursor: pointer; border: 1px solid rgba(255, 255, 255, 0.05); transition: var(--transition-pro); }
.gallery-item:hover { border-color: rgba(255, 255, 255, 0.3); transform: scale(1.02); box-shadow: 0 10px 20px rgba(0,0,0,0.3); }
.gallery-item img { width: 100%; height: 100%; object-fit: cover; transition: var(--transition-pro); }
.gallery-item:hover img { filter: saturate(1.2); }
.skeleton { background: rgba(255, 255, 255, 0.05); position: relative; overflow: hidden; border-radius: 8px; }
.skeleton::after { content: ""; position: absolute; inset: 0; background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.05), transparent); transform: translateX(-100%); animation: shimmer 2s infinite; }
@keyframes shimmer { 100% { transform: translateX(100%); } }
</style>
