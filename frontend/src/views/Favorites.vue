<template>
  <div class="favorites-page">
    <div class="curate-header">
      <h1 class="curate-title">私人策展</h1>
      <div class="curate-stats">
        共 {{ state.count }} 个收藏项
      </div>
      
      <!-- iOS 风格的分段选择器 -->
      <div class="segmented-control">
        <button 
          v-for="tab in tabs" 
          :key="tab.id"
          class="segment-item"
          :class="{ active: activeTab === tab.id }"
          @click="activeTab = tab.id"
        >
          {{ tab.label }}
        </button>
      </div>
    </div>

    <!-- 收藏网格 -->
    <div class="curate-content">
      <div v-if="filteredItems.length > 0" class="favorites-grid">
        <VideoCard 
          v-for="item in filteredItems" 
          :key="item.entity_id"
          :content-id="item.entity_id"
          :cover-url="item.metadata?.jacket_thumb_url"
          :actress="item.metadata?.actress_name"
          @click="openVideo(item)"
        />
      </div>

      <!-- 空状态：Apple 风格 -->
      <div v-else class="curate-empty">
        <div class="empty-icon">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="48" height="48">
            <path d="M20.84 4.61a5.5 5.5 0 00-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 00-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 000-7.78z"/>
          </svg>
        </div>
        <h3>开始你的策展</h3>
        <p>在探索过程中点击心形图标，将喜欢的项目收入此处。</p>
        <button class="btn-explore" @click="$router.push('/search')">去探索</button>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed } from 'vue'
import { state } from '../utils/favoriteState'
import { openVideoModal } from '../utils/modalState'
import VideoCard from '../components/VideoCard.vue'

export default {
  name: 'Favorites',
  components: { VideoCard },
  setup() {
    const activeTab = ref('all')
    const tabs = [
      { id: 'all', label: '全部' },
      { id: 'video', label: '影片' },
      { id: 'actress', label: '演员' },
      { id: 'maker', label: '工作室' }
    ]

    const filteredItems = computed(() => {
      if (activeTab.value === 'all') return state.items
      return state.items.filter(i => i.entity_type === activeTab.value)
    })

    const openVideo = (item) => {
      if (item.entity_type === 'video') {
        openVideoModal(item.metadata || { content_id: item.entity_id })
      }
    }

    return {
      state,
      activeTab,
      tabs,
      filteredItems,
      openVideo
    }
  }
}
</script>

<style scoped>
.favorites-page {
  padding: 60px 40px;
  max-width: 1600px;
  margin: 0 auto;
  min-height: 100vh;
}

.curate-header {
  text-align: center;
  margin-bottom: 50px;
}

.curate-title {
  font-size: 42px;
  font-weight: 800;
  letter-spacing: -0.03em;
  margin-bottom: 8px;
}

.curate-stats {
  font-size: 14px;
  color: var(--text-muted);
  margin-bottom: 32px;
}

/* Segmented Control - Apple Look */
.segmented-control {
  display: inline-flex;
  background: var(--white-06);
  padding: 3px;
  border-radius: 12px;
  backdrop-filter: blur(20px);
}

.segment-item {
  border: none;
  background: transparent;
  color: var(--text-secondary);
  padding: 8px 24px;
  font-size: 14px;
  font-weight: 600;
  border-radius: 9px;
  cursor: pointer;
  transition: all 0.2s var(--ease-pro);
}

.segment-item.active {
  background: var(--white-10);
  color: var(--text-primary);
  box-shadow: 0 2px 8px rgba(0,0,0,0.2);
}

.curate-content {
  margin-top: 20px;
}

.favorites-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 32px;
}

.curate-empty {
  padding: 100px 20px;
  text-align: center;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.empty-icon {
  color: var(--text-muted);
  margin-bottom: 20px;
  opacity: 0.5;
}

.curate-empty h3 {
  font-size: 20px;
  margin-bottom: 8px;
}

.curate-empty p {
  color: var(--text-muted);
  margin-bottom: 32px;
}

.btn-explore {
  background: var(--text-primary);
  color: var(--bg-primary);
  border: none;
  padding: 12px 40px;
  border-radius: 20px;
  font-weight: 700;
  cursor: pointer;
  transition: var(--transition-pro);
}

.btn-explore:hover {
  transform: scale(1.05);
}

@media (max-width: 768px) {
  .favorites-page { padding: 40px 20px; }
  .curate-title { font-size: 32px; }
  .favorites-grid { grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: 20px; }
}
</style>

<script>
import api from '../api'

export default {
  name: 'Favorites',
  data() {
    return {
      favorites: [],
      loading: false,
      selectedMovie: null,
      mainGalleryImg: '',
      loadingMagnets: false
    }
  },
  computed: {
    galleryImages() {
      if (!this.selectedMovie) return []
      return this.selectedMovie.samples || this.selectedMovie.images || []
    },
    filteredMagnets() {
      if (!this.selectedMovie?.magnets) return []
      return this.selectedMovie.magnets
    }
  },
  mounted() {
    this.loadFavorites()
  },
  methods: {
    loadFavorites() {
      try {
        const fav = localStorage.getItem('movieFavorites')
        if (fav) {
          this.favorites = JSON.parse(fav)
        }
      } catch (e) {
        console.error('Load favorites failed:', e)
      }
    },
    saveFavorites() {
      try {
        localStorage.setItem('movieFavorites', JSON.stringify(this.favorites))
      } catch (e) {
        console.error('Save favorites failed:', e)
      }
    },
    removeFavorite(code) {
      this.favorites = this.favorites.filter(f => f.code !== code)
      this.saveFavorites()
      this.$message.success('已取消收藏')
    },
    clearAll() {
      this.favorites = []
      this.saveFavorites()
      this.$message.success('已清空全部收藏')
    },
    proxyImg(url) {
      if (!url) return ''
      if (url.includes('javbus.com') || url.includes('javcdn')) return api.proxyImage(url)
      return url
    },
    async openModal(movie) {
      this.selectedMovie = movie
      this.mainGalleryImg = movie.cover_url || ''
      this.loadingMagnets = true

      try {
        const resp = await api.getMovieFull(movie.code)
        if (resp.data && !resp.data.error) {
          this.selectedMovie = { ...movie, ...resp.data }
        }
      } catch (e) {
        console.error('Load magnets failed:', e)
      }
      this.loadingMagnets = false
    },
    closeModal() {
      this.selectedMovie = null
      this.mainGalleryImg = ''
    },
    async download(movie, mag) {
      try {
        await api.createDownload({
          code: movie.code,
          title: movie.title,
          magnet: mag.magnet
        })
        this.$message.success('已添加到下载队列')
      } catch (e) {
        console.error('Download failed:', e)
        this.$message.error('添加失败')
      }
    },
    handleImgError(e) {
      e.target.src = 'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" width="200" height="280" viewBox="0 0 200 280"><rect fill="%231a1a2e" width="200" height="280"/><text x="50%" y="50%" text-anchor="middle" dy=".3em" fill="%236B6B8A" font-size="14">暂无封面</text></svg>'
    }
  }
}
</script>

<style scoped>
.favorites-page {
  padding-bottom: 40px;
}

/* Hero */
.favorites-hero {
  text-align: center;
  padding: 60px 20px 40px;
  background: var(--bg-primary);
}

.hero-title {
  font-size: 40px;
  font-weight: 700;
  color: var(--text-primary);
  margin-bottom: 8px;
  letter-spacing: -0.03em;
}

.hero-subtitle {
  font-size: 14px;
  color: var(--text-muted);
}

/* Loading */
.loading-wrap {
  text-align: center;
  padding: 80px;
  color: var(--text-secondary);
}

.spinner-large {
  width: 40px;
  height: 40px;
  border: 3px solid rgba(255,255,255,0.1);
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  margin: 0 auto 16px;
}

/* Favorites Content */
.favorites-content {
  padding: 20px 40px;
  max-width: 1600px;
  margin: 0 auto;
}

.favorites-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--border);
}

.favorites-count {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
}

.favorites-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 20px;
}

/* Movie Card */
.movie-card {
  cursor: pointer;
}

.card-cover {
  position: relative;
  aspect-ratio: 3/4;
  overflow: hidden;
  background: var(--bg-secondary);
}

.cover-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 0.4s ease;
}

.movie-card:hover .cover-img {
  transform: translateY(-4px);
}

.card-overlay {
  position: absolute;
  inset: 0;
  background: rgba(0, 0, 0, 0.4);
  backdrop-filter: blur(4px);
  -webkit-backdrop-filter: blur(4px);
  display: flex;
  flex-direction: column;
  justify-content: flex-end;
  padding: 12px;
  opacity: 0;
  transition: opacity 0.3s ease;
}

.movie-card:hover .card-overlay {
  opacity: 1;
}

.overlay-code {
  color: white;
  font-size: 14px;
  font-weight: 700;
  font-family: var(--font-mono);
}

.unfavorite-btn {
  position: absolute;
  top: 8px;
  right: 8px;
  background: rgba(0, 0, 0, 0.5);
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 50%;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  color: white;
  transition: var(--transition);
}

.unfavorite-btn:hover {
  background: #EF4444;
  border-color: #EF4444;
}

.card-info {
  padding: 12px;
}

.card-title {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-primary);
  margin-bottom: 6px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  line-height: 1.4;
}

.card-meta {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.meta-item {
  font-size: 11px;
  color: var(--text-secondary);
}

/* Empty State */
.empty-state {
  text-align: center;
  padding: 80px;
  color: var(--text-secondary);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
}

.empty-state svg {
  width: 64px;
  height: 64px;
  opacity: 0.5;
}

/* Modal */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.8);
  backdrop-filter: blur(8px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 20px;
}

.modal-container {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  width: 100%;
  max-width: 960px;
  max-height: 90vh;
  overflow: hidden;
  position: relative;
  box-shadow: 0 25px 80px rgba(0,0,0,0.6);
}

.modal-close {
  position: absolute;
  top: 14px;
  right: 14px;
  background: rgba(255,255,255,0.08);
  border: none;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  color: var(--text-secondary);
  z-index: 10;
  transition: var(--transition);
}

.modal-close:hover {
  background: rgba(255,255,255,0.15);
  color: white;
  transform: rotate(90deg);
}

.modal-body {
  display: flex;
  max-height: 90vh;
  overflow: hidden;
}

.modal-gallery {
  width: 380px;
  min-width: 380px;
  background: var(--bg-secondary);
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 12px;
  overflow-y: auto;
}

.gallery-main {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  border-radius: var(--radius-sm);
  background: #000;
  min-height: 300px;
}

.gallery-main img {
  width: 100%;
  height: 100%;
  object-fit: contain;
}

.gallery-thumbs {
  display: flex;
  gap: 6px;
  overflow-x: auto;
}

.gallery-thumb {
  width: 56px;
  height: 40px;
  object-fit: cover;
  border-radius: 4px;
  cursor: pointer;
  opacity: 0.5;
  border: 2px solid transparent;
  transition: var(--transition);
  flex-shrink: 0;
}

.gallery-thumb:hover {
  opacity: 0.8;
}

.gallery-thumb.active {
  opacity: 1;
  border-color: var(--accent);
}

.modal-content {
  flex: 1;
  padding: 24px;
  overflow-y: auto;
}

.modal-header {
  margin-bottom: 12px;
}

.modal-header-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.modal-title {
  font-size: 20px;
  font-weight: 700;
  color: var(--text-primary);
  margin-bottom: 8px;
  line-height: 1.3;
}

.modal-code-badge {
  display: inline-block;
  background: var(--accent);
  color: white;
  font-size: 12px;
  font-weight: 600;
  padding: 4px 10px;
  border-radius: 4px;
}

.favorite-btn {
  background: none;
  border: none;
  padding: 6px;
  cursor: pointer;
  color: var(--text-muted);
  border-radius: 50%;
  transition: var(--transition);
  display: flex;
  align-items: center;
  justify-content: center;
}

.favorite-btn:hover {
  background: rgba(244, 67, 54, 0.1);
  color: #F44336;
}

.favorite-btn.active {
  color: #F44336;
}

.favorite-btn svg {
  width: 20px;
  height: 20px;
}

.modal-meta {
  display: flex;
  gap: 16px;
  margin-bottom: 12px;
  flex-wrap: wrap;
}

.modal-meta-item {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 13px;
  color: var(--text-secondary);
}

.modal-genres {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  margin-bottom: 16px;
}

.genre-tag {
  font-size: 12px;
  padding: 4px 10px;
  background: var(--bg-secondary);
  border: 1px solid var(--border);
  border-radius: 20px;
  color: var(--text-secondary);
}

.modal-magnets {
  border-top: 1px solid var(--border);
  padding-top: 14px;
}

.magnets-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
}

.magnets-loading,
.magnets-empty {
  text-align: center;
  padding: 20px;
  color: var(--text-muted);
  font-size: 13px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.magnets-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
  max-height: 300px;
  overflow-y: auto;
}

.magnet-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 12px;
  background: var(--bg-secondary);
  border-radius: var(--radius-sm);
  gap: 12px;
  transition: var(--transition);
}

.magnet-row:hover {
  background: var(--bg-card-hover);
}

.magnet-left {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
  flex: 1;
}

.magnet-right {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
}

.badge {
  font-size: 10px;
  padding: 2px 6px;
  border-radius: 4px;
  font-weight: 600;
}

.badge-hd {
  background: rgba(76, 175, 80, 0.2);
  color: var(--accent-light);
}

.badge-resolution {
  background: rgba(33, 150, 243, 0.2);
  color: #42A5F5;
}

.mag-title {
  font-size: 12px;
  color: var(--text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.mag-size {
  font-size: 11px;
  color: var(--text-muted);
}

.download-btn {
  font-size: 12px;
  padding: 5px 10px;
}

/* Transitions */
.modal-fade-enter-active .modal-container {
  animation: modalIn 0.4s cubic-bezier(0.32, 0.72, 0, 1.2);
}

.modal-fade-leave-active .modal-container {
  animation: modalOut 0.25s ease;
}

.modal-fade-enter-active {
  animation: fadeIn 0.3s ease;
}

.modal-fade-leave-active {
  animation: fadeIn 0.2s ease reverse;
}

@keyframes modalIn {
  from { transform: scale(0.88); opacity: 0; }
  to { transform: scale(1); opacity: 1; }
}

@keyframes modalOut {
  from { transform: scale(1); opacity: 1; }
  to { transform: scale(0.92); opacity: 0; }
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* Responsive */
@media (max-width: 768px) {
  .favorites-content {
    padding: 16px;
  }

  .favorites-grid {
    grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
    gap: 12px;
  }

  .modal-body {
    flex-direction: column;
    overflow-y: auto;
    max-height: 85vh;
  }

  .modal-gallery {
    width: 100%;
    min-width: unset;
  }

  .gallery-main {
    min-height: 200px;
  }
}
</style>
