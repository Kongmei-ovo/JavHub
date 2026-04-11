<template>
  <div class="genres-page">
    <!-- Hero -->
    <div class="genres-hero">
      <h1 class="hero-title">影片分类</h1>
      <p class="hero-subtitle">按类型浏览所有影片</p>
    </div>

    <!-- 加载状态 -->
    <div v-if="loading && !genres.length" class="loading-wrap">
      <div class="spinner-large"></div>
      <p>加载分类中...</p>
    </div>

    <!-- 分类网格 -->
    <div v-else class="genres-grid">
      <div
        v-for="genre in genres"
        :key="genre.name"
        class="genre-card"
        :class="{ active: selectedGenre === genre.name }"
        @click="selectGenre(genre)"
      >
        <div class="genre-icon">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M4 19.5A2.5 2.5 0 016.5 17H20"/>
            <path d="M6.5 2H20v20H6.5A2.5 2.5 0 014 19.5v-15A2.5 2.5 0 016.5 2z"/>
          </svg>
        </div>
        <div class="genre-info">
          <h3 class="genre-name">{{ genre.name }}</h3>
          <span class="genre-count">{{ genre.count }} 部</span>
        </div>
      </div>
    </div>

    <!-- 选中分类的结果 -->
    <div v-if="selectedGenre" class="genre-results">
      <div class="results-header">
        <button class="back-btn" @click="selectedGenre = null; genreMovies = []">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16">
            <polyline points="15 18 9 12 15 6"/>
          </svg>
          返回分类
        </button>
        <h2>{{ selectedGenre }}</h2>
        <span class="results-count">{{ genreMovies.length }} 部影片</span>
      </div>

      <!-- 加载骨架屏 -->
      <div v-if="loadingMovies" class="skeleton-grid">
        <div v-for="n in 12" :key="n" class="skeleton-card av-card">
          <div class="skeleton-cover"></div>
          <div class="skeleton-info">
            <div class="skeleton-line w-60"></div>
            <div class="skeleton-line w-80"></div>
          </div>
        </div>
      </div>

      <!-- 结果网格 -->
      <div v-else-if="genreMovies.length" class="results-grid">
        <div
          v-for="item in genreMovies"
          :key="item.code || item.id"
          class="movie-card av-card"
          @click="openModal(item)"
        >
          <div class="card-cover">
            <img
              :src="proxyImg(item.cover_url || item.img)"
              :alt="item.code || item.id"
              class="cover-img"
              @error="handleImgError"
              loading="lazy"
            />
            <div class="card-overlay">
              <span class="overlay-code">{{ item.code || item.id }}</span>
            </div>
          </div>
          <div class="card-info">
            <h3 class="card-title" :title="item.title">{{ item.title }}</h3>
            <div class="card-meta">
              <span v-if="item.actor" class="meta-item">{{ item.actor }}</span>
              <span v-if="item.date" class="meta-item">{{ item.date }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 空结果 -->
      <div v-else class="empty-state">
        <p>该分类下暂无影片</p>
      </div>
    </div>

    <!-- 详情弹窗 -->
    <transition name="modal-fade">
      <div v-if="selectedMovie" class="modal-overlay" @click.self="closeModal">
        <div class="modal-container">
          <button class="modal-close" @click="closeModal">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="20" height="20">
              <line x1="18" y1="6" x2="6" y2="18"/>
              <line x1="6" y1="6" x2="18" y2="18"/>
            </svg>
          </button>
          <div class="modal-body">
            <!-- 左侧: 封面 + 剧照 -->
            <div class="modal-gallery">
              <div class="gallery-main">
                <img
                  v-if="mainGalleryImg"
                  :src="proxyImg(mainGalleryImg)"
                  :alt="selectedMovie?.code"
                  @error="handleImgError"
                />
              </div>
              <div v-if="galleryImages.length > 0" class="gallery-thumbs">
                <img
                  v-for="(img, idx) in galleryImages"
                  :key="idx"
                  :src="proxyImg(img)"
                  :alt="'sample-' + idx"
                  class="gallery-thumb"
                  :class="{ active: mainGalleryImg === img }"
                  @click="mainGalleryImg = img"
                />
              </div>
            </div>

            <!-- 右侧: 详情 -->
            <div class="modal-content">
              <div class="modal-header">
                <h2 class="modal-title">{{ selectedMovie?.title }}</h2>
                <span class="modal-code-badge">{{ selectedMovie?.code || selectedMovie?.id }}</span>
              </div>

              <div class="modal-meta">
                <span v-if="selectedMovie?.actor" class="modal-meta-item">
                  <svg viewBox="0 0 24 24" fill="currentColor" width="14" height="14">
                    <path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"/>
                  </svg>
                  {{ selectedMovie.actor }}
                </span>
                <span v-if="selectedMovie?.date" class="modal-meta-item">
                  <svg viewBox="0 0 24 24" fill="currentColor" width="14" height="14">
                    <path d="M19 3h-1V1h-2v2H8V1H6v2H5c-1.11 0-2 .9-2 2v14c0 1.1.89 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm0 16H5V8h14v11z"/>
                  </svg>
                  {{ selectedMovie.date }}
                </span>
              </div>

              <!-- 标签 -->
              <div v-if="selectedMovie?.genres?.length || selectedMovie?.tags?.length" class="modal-genres">
                <span v-for="(g, i) in (selectedMovie.genres || selectedMovie.tags || [])" :key="i" class="genre-tag">{{ g }}</span>
              </div>

              <!-- 磁力列表 -->
              <div class="modal-magnets">
                <div class="magnets-header">
                  <span>磁力链接</span>
                </div>
                <div v-if="loadingMagnets" class="magnets-loading">
                  <span class="spinner"></span>
                  <span>加载中...</span>
                </div>
                <div v-else-if="filteredMagnets.length > 0" class="magnets-list">
                  <div v-for="(mag, idx) in filteredMagnets" :key="idx" class="magnet-row">
                    <div class="magnet-left">
                      <span v-if="mag.hd" class="badge badge-hd">HD</span>
                      <span v-if="mag.resolution" class="badge badge-resolution">{{ mag.resolution }}</span>
                      <span class="mag-title">{{ mag.title }}</span>
                    </div>
                    <div class="magnet-right">
                      <span class="mag-size">{{ mag.size }}</span>
                      <button class="btn btn-primary download-btn" @click="download(item, mag)">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
                          <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/>
                          <polyline points="7 10 12 15 17 10"/>
                          <line x1="12" y1="15" x2="12" y2="3"/>
                        </svg>
                        下载
                      </button>
                    </div>
                  </div>
                </div>
                <div v-else class="magnets-empty">
                  <span>暂无可用磁力</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </transition>
  </div>
</template>

<script>
import api from '../api'

export default {
  name: 'Genres',
  data() {
    return {
      genres: [],
      loading: false,
      selectedGenre: null,
      genreMovies: [],
      loadingMovies: false,
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
    },
    item() {
      return this.selectedMovie
    }
  },
  mounted() {
    this.loadGenres()
  },
  methods: {
    proxyImg(url) {
      if (!url) return ''
      if (url.includes('javbus.com') || url.includes('javcdn')) return api.proxyImage(url)
      return url
    },
    async loadGenres() {
      this.loading = true
      try {
        // 直接从 R18 数据库获取类别列表
        const resp = await api.getGenres()
        this.genres = resp.data || []
      } catch (e) {
        console.error('Load genres failed:', e)
        this.genres = []
      } finally {
        this.loading = false
      }
    },
    async selectGenre(genre) {
      this.selectedGenre = genre.name
      this.loadingMovies = true
      this.genreMovies = []
      this.selectedMovie = null

      try {
        // 从 R18 数据库按类别获取影片
        const resp = await api.searchMovies('', 1, genre.id)
        this.genreMovies = resp.data.movies || []
      } catch (e) {
        console.error('Load genre movies failed:', e)
      } finally {
        this.loadingMovies = false
      }
    },
    async openModal(movie) {
      this.selectedMovie = movie
      this.mainGalleryImg = movie.cover_url || movie.img || ''
      this.loadingMagnets = true

      try {
        const resp = await api.getMovieFull(movie.code || movie.id)
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
    async download(item, mag) {
      try {
        await api.createDownload({
          code: item.code || item.id,
          title: item.title,
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
.genres-page {
  padding-bottom: 40px;
}

/* Hero */
.genres-hero {
  text-align: center;
  padding: 60px 20px 40px;
  background: linear-gradient(180deg, var(--bg-secondary) 0%, var(--bg-primary) 100%);
}

.hero-title {
  font-size: 40px;
  font-weight: 700;
  color: var(--text-primary);
  margin-bottom: 8px;
}

.hero-subtitle {
  font-size: 14px;
  color: var(--text-muted);
}

/* Loading */
.loading-wrap {
  text-align: center;
  padding: 60px;
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

/* Genres Grid */
.genres-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 16px;
  padding: 20px;
  max-width: 1200px;
  margin: 0 auto;
}

.genre-card {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  padding: 20px;
  cursor: pointer;
  transition: var(--transition);
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
}

.genre-card:hover {
  border-color: var(--accent);
  transform: translateY(-2px);
}

.genre-card.active {
  border-color: var(--accent);
  background: rgba(76, 175, 80, 0.1);
}

.genre-icon {
  width: 48px;
  height: 48px;
  background: var(--bg-secondary);
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 12px;
}

.genre-icon svg {
  width: 24px;
  height: 24px;
  color: var(--accent);
}

.genre-info {
  flex: 1;
}

.genre-name {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 4px;
}

.genre-count {
  font-size: 12px;
  color: var(--text-muted);
}

/* Results */
.genre-results {
  padding: 0 20px;
  max-width: 1400px;
  margin: 0 auto;
}

.results-header {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 20px;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--border);
}

.back-btn {
  display: flex;
  align-items: center;
  gap: 4px;
  background: none;
  border: none;
  color: var(--accent);
  font-size: 13px;
  cursor: pointer;
  padding: 6px 12px;
  border-radius: var(--radius-sm);
  transition: var(--transition);
}

.back-btn:hover {
  background: rgba(76, 175, 80, 0.1);
}

.results-header h2 {
  font-size: 20px;
  font-weight: 600;
  color: var(--text-primary);
  flex: 1;
}

.results-count {
  font-size: 13px;
  color: var(--text-secondary);
}

/* Skeleton */
.skeleton-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 20px;
}

.skeleton-card {
  overflow: hidden;
}

.skeleton-cover {
  aspect-ratio: 3/4;
  background: linear-gradient(90deg, var(--bg-card) 25%, var(--bg-card-hover) 50%, var(--bg-card) 75%);
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
}

.skeleton-info {
  padding: 12px;
}

.skeleton-line {
  height: 12px;
  background: var(--bg-card-hover);
  border-radius: 6px;
  margin-bottom: 8px;
}

.skeleton-line.w-60 { width: 60%; }
.skeleton-line.w-80 { width: 80%; }

@keyframes shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

/* Results Grid */
.results-grid {
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
  transform: scale(1.05);
}

.card-overlay {
  position: absolute;
  inset: 0;
  background: linear-gradient(transparent 40%, rgba(0,0,0,0.85) 100%);
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

/* Empty */
.empty-state {
  text-align: center;
  padding: 60px;
  color: var(--text-muted);
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
  .genres-grid {
    grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
    gap: 12px;
  }

  .genre-card {
    padding: 16px;
  }

  .results-grid {
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
