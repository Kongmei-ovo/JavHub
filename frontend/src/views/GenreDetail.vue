<template>
  <div class="genre-detail-page">
    <!-- 顶部 Tab 栏 -->
    <div class="tab-bar">
      <div class="tab-inner">
        <button
          class="tab-btn"
          :class="{ active: activeTab === 'genres' }"
          @click="activeTab = 'genres'"
        >
          题材
        </button>
        <button
          class="tab-btn"
          :class="{ active: activeTab === 'movies' }"
          @click="activeTab = 'movies'"
        >
          影片
        </button>
      </div>
    </div>

    <!-- 题材 Tab: 气泡云 -->
    <div v-if="activeTab === 'genres'" class="tab-content">
      <div class="tag-cloud-wrap" ref="cloudWrapRef">
        <div class="cloud-header">
          <span class="cloud-hint">共 {{ categories.length }} 个题材</span>
          <button class="shuffle-btn" @click="reshuffleTags" :disabled="loading">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
              <polyline points="23 4 23 10 17 10"/>
              <polyline points="1 20 1 14 7 14"/>
              <path d="M3.51 9a9 9 0 0114.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0020.49 15"/>
            </svg>
            换一批
          </button>
        </div>
        <div v-if="loading" class="loading-wrap">
          <div class="spinner-large"></div>
          <p>加载题材中...</p>
        </div>
        <div v-else ref="tagCloudRef" class="tag-cloud" :style="cloudStyle">
          <div
            v-for="tag in shuffledTags"
            :key="tag.id"
            class="bubble"
            :class="{ active: tag.id === categoryId }"
            :style="bubbleStyle(tag)"
            @click="switchCategory(tag)"
          >
            {{ tag.name_en || tag.name_ja || tag.name }}
          </div>
        </div>
      </div>
    </div>

    <!-- 影片 Tab: 影片卡片 -->
    <div v-if="activeTab === 'movies'" class="tab-content">
      <div class="result-header">
        <button class="back-btn" @click="$router.push('/genres')">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
            <polyline points="15 18 9 12 15 6"/>
          </svg>
          题材发现
        </button>
        <h2 class="category-title">{{ categoryName }}</h2>
        <button class="shuffle-btn" @click="reshuffle" :disabled="loadingMovies">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
            <polyline points="23 4 23 10 17 10"/>
            <polyline points="1 20 1 14 7 14"/>
            <path d="M3.51 9a9 9 0 0114.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0020.49 15"/>
          </svg>
          换一批
        </button>
      </div>

      <div v-if="loadingMovies" class="skeleton-grid">
        <div v-for="n in 12" :key="n" class="skeleton-card">
          <div class="skeleton-cover"></div>
          <div class="skeleton-info">
            <div class="skeleton-line w-60"></div>
            <div class="skeleton-line w-80"></div>
          </div>
        </div>
      </div>

      <div v-else-if="displayMovies.length" class="results-grid">
        <div
          v-for="item in displayMovies"
          :key="item.content_id || item.dvd_id"
          class="movie-card"
          @click="openModal(item)"
        >
          <div class="card-cover">
            <img
              :src="item.jacket_full_url || item.jacket_thumb_url || '/placeholder.png'"
              :alt="item.dvd_id || item.content_id"
              @error="handleImgError"
              loading="lazy"
              class="cover-img"
            />
          </div>
          <div class="card-info">
            <div class="card-code-row">
              <span class="card-code">{{ item.dvd_id || item.content_id }}</span>
            </div>
            <div class="card-title" :title="item.title_en || item.title_ja">{{ item.title_en || item.title_ja }}</div>
            <div class="card-meta">
              <span v-if="item.release_date" class="meta-date">{{ item.release_date }}</span>
              <span v-if="item.runtime_mins" class="meta-time">{{ item.runtime_mins }}分钟</span>
            </div>
          </div>
        </div>
      </div>

      <div v-else-if="!loadingMovies" class="empty-state">
        <p>该题材下暂无影片</p>
      </div>
    </div>

    <!-- 影片详情弹窗 -->
    <VideoModal
      v-if="selectedVideo"
      :visible="!!selectedVideo"
      :video="selectedVideo"
      @close="closeModal"
      @download="handleDownload"
      @search-by-category="searchByCategory"
      @search-by-maker="searchByMaker"
      @search-by-series="searchBySeries"
      @search-by-actress="searchByActress"
    />
  </div>
</template>

<script>
import gsap from 'gsap'
import api from '../api'
import VideoModal from '../components/VideoModal.vue'

const BUBBLE_COLORS = [
  'linear-gradient(135deg, #667eea, #764ba2)',
  'linear-gradient(135deg, #f093fb, #f5576c)',
  'linear-gradient(135deg, #4facfe, #00f2fe)',
  'linear-gradient(135deg, #43e97b, #38f9d7)',
  'linear-gradient(135deg, #fa709a, #fee140)',
  'linear-gradient(135deg, #a18cd1, #fbc2eb)',
  'linear-gradient(135deg, #ff9a9e, #fecfef)',
  'linear-gradient(135deg, #ffecd2, #fcb69f)',
  'linear-gradient(135deg, #84fab0, #8fd3f4)',
  'linear-gradient(135deg, #cfd9df, #e2ebf0)',
  'linear-gradient(135deg, #a1c4fd, #c2e9fb)',
  'linear-gradient(135deg, #d4fc79, #96e6a1)',
]

function hashCode(str) {
  let hash = 0
  for (let i = 0; i < str.length; i++) {
    hash = ((hash << 5) - hash) + str.charCodeAt(i)
    hash |= 0
  }
  return Math.abs(hash)
}

function shuffle(arr) {
  const a = [...arr]
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1))
    ;[a[i], a[j]] = [a[j], a[i]]
  }
  return a
}

const DISPLAY_COUNT = 30

export default {
  name: 'GenreDetail',
  components: { VideoModal },
  data() {
    return {
      categories: [],
      shuffledTags: [],
      loading: false,
      allMovies: [],
      displayMovies: [],
      loadingMovies: false,
      selectedVideo: null,
      activeTab: 'movies',
      cfg: { baseSize: 16, fillPercent: 50, spacing: 16 },
      bubbleRects: new Map(),
    }
  },
  computed: {
    cloudStyle() {
      return { gap: `${this.cfg.spacing}px` }
    },
    categoryId() {
      return parseInt(this.$route.params.categoryId)
    },
    categoryName() {
      const cat = this.categories.find(c => c.id === this.categoryId)
      return cat ? (cat.name_en || cat.name_ja || cat.name) : ''
    }
  },
  async mounted() {
    this.loadCfg()
    await this.loadCategories()
    await this.loadMovies()
  },
  watch: {
    activeTab(newTab) {
      if (newTab === 'genres' && !this.loading) {
        this.$nextTick(() => this.initGsap())
      }
    },
    categoryId() {
      // reinit GSAP when navigating between genre detail pages
      if (this.activeTab === 'genres' && !this.loading) {
        this.$nextTick(() => this.initGsap())
      }
    }
  },
  methods: {
    bubbleStyle(tag) {
      const idx = hashCode(tag.name_en || tag.name_ja || tag.name) % BUBBLE_COLORS.length
      const size = this.cfg.baseSize
      const fill = this.cfg.fillPercent / 100
      return {
        background: BUBBLE_COLORS[idx],
        fontSize: `${size}px`,
        padding: `${Math.round(size * fill * 0.6)}px ${Math.round(size * fill * 1.2)}px`,
      }
    },
    loadCfg() {
      try {
        const saved = localStorage.getItem('genres_bubble_cfg')
        if (saved) this.cfg = JSON.parse(saved)
      } catch {}
    },
    async loadCategories() {
      this.loading = true
      try {
        const resp = await api.listCategories()
        this.categories = Array.isArray(resp.data) ? resp.data : (resp.data.data || [])
        this.shuffledTags = shuffle(this.categories)
      } catch (e) {
        console.error('Load categories failed:', e)
      } finally {
        this.loading = false
        this.$nextTick(() => {
          if (this.activeTab === 'genres' && this.$refs.tagCloudRef) {
            this.initGsap()
          }
        })
      }
    },
    async loadMovies() {
      if (!this.categoryId) return
      this.loadingMovies = true
      this.allMovies = []
      this.displayMovies = []
      try {
        const resp = await api.searchVideos({
          category_id: this.categoryId,
          page: 1,
          page_size: 60
        })
        this.allMovies = resp.data.data || []
        this.displayMovies = shuffle(this.allMovies).slice(0, DISPLAY_COUNT)
      } catch (e) {
        console.error('Load movies failed:', e)
      } finally {
        this.loadingMovies = false
      }
    },
    initGsap() {
      const cloud = this.$refs.tagCloudRef
      if (!cloud) return
      const bubbles = cloud.querySelectorAll('.bubble')

      this.updateBubbleRects(bubbles)

      // entrance: simultaneous pop-in
      gsap.fromTo(bubbles,
        { scale: 0, opacity: 0 },
        {
          scale: 1,
          opacity: 1,
          duration: 0.25,
          stagger: 0.005,
          ease: 'back.out(1.7)',
        }
      )

      // subtle float (y-axis only)
      bubbles.forEach((bubble, i) => {
        gsap.to(bubble, {
          y: -5,
          duration: 1.4 + (i % 4) * 0.2,
          repeat: -1,
          yoyo: true,
          ease: 'sine.inOut',
          delay: i * 0.03,
        })
      })

      cloud.addEventListener('mousemove', this.handleMouseMove)
      cloud.addEventListener('mouseleave', this.handleMouseLeave)
    },
    updateBubbleRects(bubbles) {
      const newRects = new Map()
      bubbles.forEach(b => {
        newRects.set(b, b.getBoundingClientRect())
      })
      this.bubbleRects = newRects
    },
    handleMouseMove(e) {
      const cloud = this.$refs.tagCloudRef
      if (!cloud) return
      const mouseX = e.clientX
      const mouseY = e.clientY
      const bubbles = cloud.querySelectorAll('.bubble')

      // Phase 1: determine scales
      const scales = new Map()
      const hoveredBubbles = []
      bubbles.forEach(bubble => {
        const r = bubble.getBoundingClientRect()
        const cx = r.left + r.width / 2
        const cy = r.top + r.height / 2
        const dist = Math.hypot(mouseX - cx, mouseY - cy)
        const maxDist = 160

        if (dist < maxDist) {
          scales.set(bubble, 1 + (1 - dist / maxDist) * 0.5)
          hoveredBubbles.push(bubble)
        } else {
          scales.set(bubble, 1)
        }
      })

      // Phase 2: collision detection
      const overlapped = new Set()
      for (let i = 0; i < hoveredBubbles.length; i++) {
        for (let j = i + 1; j < hoveredBubbles.length; j++) {
          const a = hoveredBubbles[i]
          const b = hoveredBubbles[j]
          const ra = a.getBoundingClientRect()
          const rb = b.getBoundingClientRect()
          const sa = scales.get(a)
          const sb = scales.get(b)

          // Scaled rect
          const raS = {
            left: ra.left - (sa - 1) * ra.width / 2,
            right: ra.right + (sa - 1) * ra.width / 2,
            top: ra.top - (sa - 1) * ra.height / 2,
            bottom: ra.bottom + (sa - 1) * ra.height / 2,
          }
          const rbS = {
            left: rb.left - (sb - 1) * rb.width / 2,
            right: rb.right + (sb - 1) * rb.width / 2,
            top: rb.top - (sb - 1) * rb.height / 2,
            bottom: rb.bottom + (sb - 1) * rb.height / 2,
          }

          const intersects = !(raS.right < rbS.left || raS.left > rbS.right ||
                               raS.bottom < rbS.top || raS.top > rbS.bottom)
          if (intersects) {
            overlapped.add(a)
            overlapped.add(b)
          }
        }
      }

      // Phase 3: animate with z-index layering
      let maxZ = 100
      bubbles.forEach(bubble => {
        const scale = scales.get(bubble)
        const isOverlapped = overlapped.has(bubble)
        const isActive = bubble.classList.contains('active')

        if (scale > 1) {
          gsap.to(bubble, {
            scale,
            opacity: 1,
            zIndex: isOverlapped ? ++maxZ : 50,
            duration: 0.15,
            ease: 'back.out(1.2)',
            overwrite: 'auto',
          })
        } else {
          gsap.to(bubble, {
            scale: 1,
            opacity: isActive ? 1 : 0.88,
            zIndex: 1,
            duration: 0.2,
            ease: 'power3.out',
            overwrite: 'auto',
          })
        }
      })

      this.updateBubbleRects(bubbles)
    },
    handleMouseLeave() {
      const cloud = this.$refs.tagCloudRef
      if (!cloud) return
      const bubbles = cloud.querySelectorAll('.bubble')
      gsap.to(bubbles, {
        scale: 1,
        opacity: 0.88,
        zIndex: 1,
        duration: 0.3,
        ease: 'back.out(1.2)',
        stagger: 0.004,
      })
    },
    switchCategory(tag) {
      if (tag.id === this.categoryId) return
      const cloud = this.$refs.tagCloudRef
      if (cloud) {
        cloud.removeEventListener('mousemove', this.handleMouseMove)
        cloud.removeEventListener('mouseleave', this.handleMouseLeave)
      }
      this.$router.push({ name: 'GenreDetail', params: { categoryId: tag.id } })
    },
    reshuffle() {
      if (!this.allMovies.length) return
      this.displayMovies = shuffle(this.allMovies).slice(0, DISPLAY_COUNT)
    },
    reshuffleTags() {
      const cloud = this.$refs.tagCloudRef
      if (!cloud) {
        this.shuffledTags = shuffle(this.categories)
        return
      }
      const bubbles = cloud.querySelectorAll('.bubble')
      gsap.to(bubbles, {
        scale: 0,
        opacity: 0,
        duration: 0.08,
        stagger: 0,
        ease: 'power2.in',
      })
      this.shuffledTags = shuffle(this.categories)
      this.$nextTick(() => {
        const newBubbles = this.$refs.tagCloudRef?.querySelectorAll('.bubble')
        if (!newBubbles?.length) return
        gsap.fromTo(newBubbles,
          { scale: 0, opacity: 0 },
          {
            scale: 1,
            opacity: 0.88,
            duration: 0.3,
            stagger: 0.006,
            ease: 'back.out(1.7)',
          }
        )
      })
    },
    async openModal(video) {
      this.selectedVideo = video
      if (!video.magnets && !video.gallery_thumb_first) {
        try {
          const resp = await api.getVideo(video.content_id || video.dvd_id)
          if (resp.data) {
            this.selectedVideo = { ...video, ...resp.data }
          }
        } catch (e) {
          console.error('Load video detail failed:', e)
        }
      }
    },
    closeModal() {
      this.selectedVideo = null
    },
    async handleDownload(magnet) {
      try {
        await api.createDownload({
          content_id: this.selectedVideo.content_id || this.selectedVideo.dvd_id,
          title: this.selectedVideo.title_en,
          magnet: magnet.magnet || magnet
        })
        this.$message.success('已添加到下载队列')
      } catch (e) {
        console.error('Download failed:', e)
        this.$message.error('添加下载失败')
      }
    },
    searchByCategory(categoryName) {
      const cat = this.categories.find(c =>
        (c.name_en || c.name_ja || c.name) === categoryName
      )
      if (cat) {
        this.closeModal()
        this.$router.push({ name: 'GenreDetail', params: { categoryId: cat.id } })
      }
    },
    searchByMaker(makerName) {
      this.$router.push({ path: '/search', query: { maker: makerName } })
    },
    searchBySeries(seriesName) {
      this.$router.push({ path: '/search', query: { series: seriesName } })
    },
    searchByActress(actressName) {
      this.$router.push({ path: '/search', query: { actress: actressName } })
    },
    handleImgError(e) {
      e.target.src = 'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" width="200" height="280" viewBox="0 0 200 280"><rect fill="%231a1a2e" width="200" height="280"/><text x="50%" y="50%" text-anchor="middle" dy=".3em" fill="%236B6B8A" font-size="14">暂无封面</text></svg>'
    }
  },
  beforeUnmount() {
    const cloud = this.$refs.tagCloudRef
    if (cloud) {
      cloud.removeEventListener('mousemove', this.handleMouseMove)
      cloud.removeEventListener('mouseleave', this.handleMouseLeave)
    }
  }
}
</script>

<style scoped>
.genre-detail-page {
  min-height: 100vh;
  background: var(--bg-primary);
}

/* Tab Bar */
.tab-bar {
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--border);
  position: sticky;
  top: 0;
  z-index: 100;
}

.tab-inner {
  display: flex;
  gap: 0;
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 20px;
}

.tab-btn {
  background: none;
  border: none;
  padding: 14px 24px;
  font-size: 15px;
  font-weight: 600;
  color: var(--text-muted);
  cursor: pointer;
  position: relative;
  transition: color 0.2s;
}

.tab-btn:hover {
  color: var(--text-primary);
}

.tab-btn.active {
  color: var(--accent);
}

.tab-btn.active::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 2px;
  background: var(--accent);
}

/* Tab Content */
.tab-content {
  padding-bottom: 40px;
}

.tag-cloud-wrap {
  padding: 20px;
  max-width: 1200px;
  margin: 0 auto;
}

.cloud-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 4px 16px;
}

.cloud-hint {
  font-size: 13px;
  color: var(--text-muted);
}

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

.tag-cloud {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  align-items: center;
  padding: 30px 20px;
  background: var(--bg-primary);
  border-radius: 16px;
}

.bubble {
  padding: 10px 20px;
  border-radius: 50px;
  color: white;
  font-weight: 600;
  cursor: pointer;
  user-select: none;
  white-space: nowrap;
  box-shadow: 0 4px 20px rgba(0,0,0,0.3);
  text-shadow: 0 1px 2px rgba(0,0,0,0.3);
  flex-shrink: 0;
  opacity: 0.88;
  transform-origin: center center;
  position: relative;
}

.bubble.active {
  opacity: 1;
  filter: brightness(1.05);
}

/* Result Header */
.result-header {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 16px 20px;
  max-width: 1400px;
  margin: 0 auto;
  border-bottom: 1px solid var(--border);
}

.back-btn {
  display: flex;
  align-items: center;
  gap: 4px;
  background: none;
  border: 1px solid var(--border);
  color: var(--text-secondary);
  font-size: 13px;
  cursor: pointer;
  padding: 6px 12px;
  border-radius: var(--radius-sm);
  transition: var(--transition);
}

.back-btn:hover {
  border-color: var(--accent);
  color: var(--accent);
}

.category-title {
  flex: 1;
  font-size: 20px;
  font-weight: 700;
  color: var(--text-primary);
}

.shuffle-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  background: var(--bg-card);
  border: 1px solid var(--border);
  color: var(--text-secondary);
  font-size: 13px;
  cursor: pointer;
  padding: 6px 14px;
  border-radius: 20px;
  transition: var(--transition);
}

.shuffle-btn:hover:not(:disabled) {
  border-color: var(--accent);
  color: var(--accent);
}

.shuffle-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Skeleton */
.skeleton-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: 20px;
  padding: 20px;
  max-width: 1400px;
  margin: 0 auto;
}

.skeleton-card {
  background: var(--bg-card);
  border-radius: var(--radius-md);
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

/* Movie Grid */
.results-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: 20px;
  padding: 20px;
  max-width: 1400px;
  margin: 0 auto;
}

.movie-card {
  background: var(--bg-card);
  border-radius: var(--radius-md);
  overflow: hidden;
  cursor: pointer;
  transition: transform 0.2s;
}

.movie-card:hover {
  transform: translateY(-4px);
}

.card-cover {
  width: 100%;
  aspect-ratio: 3/4;
  overflow: hidden;
}

.cover-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  object-position: top center;
}

.card-info {
  padding: 10px;
}

.card-code-row {
  display: flex;
  justify-content: center;
  margin-bottom: 4px;
}

.card-code {
  font-weight: bold;
  font-size: 13px;
  color: var(--text-primary);
}

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

.empty-state {
  text-align: center;
  padding: 60px;
  color: var(--text-muted);
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>
