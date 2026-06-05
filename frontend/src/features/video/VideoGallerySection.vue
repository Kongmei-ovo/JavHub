<template>
  <div v-if="thumbs.length" class="modal-section">
    <h4 class="section-title">剧照</h4>
    <div class="gallery-grid">
      <button
        v-for="(thumb, idx) in thumbs"
        :key="idx"
        class="gallery-item"
        type="button"
        @click="$emit('open', idx)"
      >
        <img :src="formatGalleryUrl(thumb)" :alt="'剧照 ' + (idx + 1)" loading="lazy" @error="onGalleryError" />
      </button>
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
.section-title { font-size: var(--type-caption); font-weight: 650; line-height: 1.3; margin-bottom: 14px; color: var(--modal-text-muted, var(--text-muted)); letter-spacing: 0; }
.gallery-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(clamp(152px, 22vw, 220px), 1fr)); gap: 12px; }
.gallery-item {
  display: block;
  width: 100%;
  padding: 0;
  aspect-ratio: 16/9;
  overflow: hidden;
  border-radius: var(--radius-lg);
  appearance: none;
  background: var(--surface-specular-edge), var(--surface-noise), var(--material-glass-control);
  cursor: pointer;
  border: 1px solid var(--glass-control-border);
  transition: transform var(--motion-standard), background var(--motion-standard), border-color var(--motion-standard), box-shadow var(--motion-standard);
  box-shadow: var(--glass-control-shadow);
  backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
  -webkit-backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
}
.gallery-item:hover {
  background: var(--surface-specular-edge-strong), var(--surface-noise), var(--material-glass-control-hover);
  border-color: var(--glass-control-border-hover);
  transform: translateY(-2px) scale(1.01);
  box-shadow: var(--glass-control-shadow-hover);
}
.gallery-item:focus-visible {
  outline: none;
  background: var(--surface-specular-edge-strong), var(--surface-noise), var(--material-glass-control-hover);
  border-color: var(--glass-control-border-hover);
  transform: translateY(-2px) scale(1.01);
  box-shadow: var(--glass-control-shadow-hover), 0 0 0 3px rgba(var(--accent-rgb), 0.12);
}
.gallery-item:active { transform: translateY(0) scale(0.99); }
.gallery-item img { width: 100%; height: 100%; object-fit: cover; transition: transform var(--motion-standard), filter var(--motion-standard), opacity var(--motion-fast); }
.gallery-item:hover img { filter: saturate(1.08); transform: scale(1.015); }
.gallery-item:focus-visible img { filter: saturate(1.08); transform: scale(1.015); }
.skeleton { background: var(--skeleton-base); position: relative; overflow: hidden; border-radius: var(--radius-lg); cursor: default; pointer-events: none; }
.skeleton::after { content: ""; position: absolute; inset: 0; background: linear-gradient(90deg, transparent, var(--skeleton-highlight), transparent); transform: translateX(-100%); animation: shimmer 2s infinite; opacity: 0.42; }
@keyframes shimmer { 100% { transform: translateX(100%); } }

@media (max-width: 768px) {
  .section-title { margin-bottom: 12px; }
  .gallery-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 8px;
  }
  .gallery-item,
  .skeleton {
    border-radius: var(--radius-md);
  }
}
</style>
