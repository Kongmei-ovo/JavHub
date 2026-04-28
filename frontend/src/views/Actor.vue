<template>
  <div class="actor-page">
    <!-- Hero -->
    <div class="actor-hero">
      <div class="hero-content">
        <div class="actor-avatar">
          <img
            :src="avatarUrl"
            :alt="actorName"
            @error="handleAvatarError"
          />
        </div>
        <div class="actor-info">
          <h1 class="actor-name">{{ actorName }}</h1>
          <div class="actor-meta">
            <span class="meta-item">
              <svg viewBox="0 0 24 24" fill="currentColor" width="14" height="14">
                <path d="M4 19.5A2.5 2.5 0 016.5 17H20"/>
                <path d="M6.5 2H20v20H6.5A2.5 2.5 0 014 19.5v-15A2.5 2.5 0 016.5 2z"/>
              </svg>
              {{ movies.length }} 部作品
            </span>
          </div>
        </div>
      </div>
      <button class="btn btn-ghost back-btn" @click="$router.back()">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="16" height="16">
          <polyline points="15 18 9 12 15 6"/>
        </svg>
        返回
      </button>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="loading-wrap">
      <div class="spinner-large"></div>
      <p>加载作品集中...</p>
    </div>

    <!-- Movies Grid -->
    <div v-else-if="movies.length > 0" class="movies-section">
      <div class="section-header">
        <h2>全部作品</h2>
        <span class="movie-count">{{ movies.length }} 部</span>
      </div>
      <div class="movies-grid">
        <div
          v-for="movie in movies"
          :key="movie.code || movie.id"
          class="movie-card av-card"
          @click="openModal(movie)"
        >
          <div class="card-cover">
            <img
              :src="proxyImg(movie.cover_url || movie.img)"
              :alt="movie.code || movie.id"
              class="cover-img"
              @error="handleImgError"
              loading="lazy"
            />
            <div class="card-overlay">
              <span class="overlay-code">{{ movie.code || movie.id }}</span>
            </div>
          </div>
          <div class="card-info">
            <h3 class="card-title" :title="movie.title">{{ movie.title }}</h3>
            <div class="card-meta">
              <span v-if="movie.date" class="meta-item">{{ movie.date }}</span>
              <span v-if="movie.genres?.length" class="meta-item">{{ movie.genres[0] }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Empty State -->
    <div v-else class="empty-state">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
        <path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2"/>
        <circle cx="9" cy="7" r="4"/>
        <path d="M23 21v-2a4 4 0 00-3-3.87"/>
        <path d="M16 3.13a4 4 0 010 7.75"/>
      </svg>
      <p>暂无演员信息</p>
    </div>

    <!-- Movie Modal -->
    <transition name="modal-fade">
      <div v-if="selectedMovie" class="modal-overlay" @click.self="closeModal">
        <div class="modal-container">
          <button class="modal-close" @click="closeModal">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="20" height="20">
              <line x1="18" y1="6" x2="6" y2="18"/>
              <line x1="6" y1="6" x2="18" y2="18"/>
            </svg>
          </button>
          <div class="modal-body">
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

              <div v-if="selectedMovie?.genres?.length" class="modal-genres">
                <span v-for="(g, i) in selectedMovie.genres" :key="i" class="genre-tag">{{ g }}</span>
              </div>

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
                      <button class="btn btn-primary download-btn" @click="download(mag)">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="14" height="14">
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
  name: 'Actor',
  data() {
    return {
      actorName: '',
      movies: [],
      loading: false,
      selectedMovie: null,
      mainGalleryImg: '',
      loadingMagnets: false
    }
  },
  computed: {
    avatarUrl() {
      return `/api/actors/avatar/${encodeURIComponent(this.actorName)}`
    },
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
    // Get actor name from route query
    this.actorName = this.$route.query.name || this.$route.params.name || ''
    if (this.actorName) {
      this.loadActorMovies()
    }
  },
  methods: {
    proxyImg(url) {
      if (!url) return ''
      if (url.includes('javbus.com') || url.includes('javcdn')) return api.proxyImage(url)
      return url
    },
    async loadActorMovies() {
      this.loading = true
      try {
        // Search by actor name
        const resp = await api.searchMovies(this.actorName, 1)
        const data = resp.data
        const allMovies = [...(data.movies || [])]

        // Load more pages if available
        const totalPages = data.pagination?.pages?.length || 1
        for (let page = 2; page <= Math.min(totalPages, 5); page++) {
          const r = await api.searchMovies(this.actorName, page)
          allMovies.push(...(r.data.movies || []))
        }

        // Filter to only include movies with this actor
        this.movies = allMovies.filter(m =>
          m.actor?.toLowerCase().includes(this.actorName.toLowerCase()) ||
          m.stars?.some(s => s.name?.toLowerCase().includes(this.actorName.toLowerCase()))
        )
      } catch (e) {
        console.error('Load actor movies failed:', e)
      } finally {
        this.loading = false
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
    async download(mag) {
      try {
        await api.createDownload({
          code: this.selectedMovie.code || this.selectedMovie.id,
          title: this.selectedMovie.title,
          magnet: mag.magnet
        })
        this.$message.success('已添加到下载队列')
      } catch (e) {
        console.error('Download failed:', e)
        this.$message.error('添加失败')
      }
    },
    handleAvatarError(e) {
      e.target.src = 'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" width="120" height="120" viewBox="0 0 120 120"><rect fill="%23333" width="120" height="120" rx="60"/><text x="50%" y="55%" text-anchor="middle" dy=".3em" fill="%23999" font-size="40">?</text></svg>'
    },
    handleImgError(e) {
      e.target.src = 'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" width="200" height="280" viewBox="0 0 200 280"><rect fill="%231a1a2e" width="200" height="280"/><text x="50%" y="50%" text-anchor="middle" dy=".3em" fill="%236B6B8A" font-size="14">暂无封面</text></svg>'
    }
  }
}
</script>

<style scoped>
.actor-page {
  padding-bottom: 40px;
}

/* Hero */
.actor-hero {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 40px;
  background: linear-gradient(180deg, var(--bg-secondary) 0%, var(--bg-primary) 100%);
  gap: 24px;
}

.hero-content {
  display: flex;
  align-items: center;
  gap: 24px;
}

.actor-avatar {
  width: 100px;
  height: 100px;
  border-radius: 50%;
  overflow: hidden;
  background: var(--bg-card);
  flex-shrink: 0;
  border: 3px solid var(--accent);
}

.actor-avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.actor-info {
  flex: 1;
}

.actor-name {
  font-size: 28px;
  font-weight: 700;
  color: var(--text-primary);
  margin-bottom: 8px;
}

.actor-meta {
  display: flex;
  gap: 16px;
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 14px;
  color: var(--text-secondary);
}

.back-btn {
  flex-shrink: 0;
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

/* Movies Section */
.movies-section {
  padding: 20px 40px;
  max-width: 1600px;
  margin: 0 auto;
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--border);
}

.section-header h2 {
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary);
}

.movie-count {
  font-size: 14px;
  color: var(--text-secondary);
}

.movies-grid {
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

.card-meta .meta-item {
  font-size: 11px;
  color: var(--text-secondary);
}

/* Empty */
.empty-state {
  text-align: center;
  padding: 80px;
  color: var(--text-secondary);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
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
  .actor-hero {
    flex-direction: column;
    text-align: center;
    padding: 24px;
  }

  .hero-content {
    flex-direction: column;
  }

  .movies-section {
    padding: 16px;
  }

  .movies-grid {
    grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
    gap: 12px;
  }

  .modal-body {
    flex-direction: column;
  }

  .modal-gallery {
    width: 100%;
    min-width: unset;
  }
}
</style>
