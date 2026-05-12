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
          <h1 class="actor-name">{{ translatedName || actorName }}</h1>
          <p v-if="translatedName && translatedName !== actorName" class="actor-name-original">{{ actorName }}</p>
          <div class="actor-meta">
            <span class="meta-item">
              <svg viewBox="0 0 24 24" fill="currentColor" width="14" height="14">
                <path d="M4 19.5A2.5 2.5 0 016.5 17H20"/>
                <path d="M6.5 2H20v20H6.5A2.5 2.5 0 014 19.5v-15A2.5 2.5 0 016.5 2z"/>
              </svg>
              {{ variantInfo.canonical.length }} 部作品
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

    <!-- Supplement Status Card -->
    <div v-if="actressId && supplementStatus" class="supplement-card">
      <div class="supplement-header">
        <h3>补全状态</h3>
        <span
          class="supplement-badge"
          :class="{
            'badge-running': supplementStatus.last_job?.status === 'running' || supplementStatus.last_job?.status === 'queued',
            'badge-failed': supplementStatus.last_job?.status === 'failed',
            'badge-ok': supplementStatus.last_job?.status === 'succeeded',
          }"
        >
          {{ statusLabel(supplementStatus.last_job?.status) }}
        </span>
      </div>
      <div v-if="supplementStatus.last_job?.last_error && supplementStatus.last_job?.status === 'failed'" class="supplement-error">
        {{ supplementStatus.last_job.last_error }}
      </div>
      <div class="supplement-counters">
        <div class="counter-item">
          <span class="counter-value">{{ supplementStatus.supplement_movies ?? '—' }}</span>
          <span class="counter-label">补全影片</span>
        </div>
        <div class="counter-item">
          <span class="counter-value">{{ supplementStatus.matched_r18 ?? '—' }}</span>
          <span class="counter-label">已匹配</span>
        </div>
        <div class="counter-item">
          <span class="counter-value">{{ supplementStatus.supplement_only ?? '—' }}</span>
          <span class="counter-label">仅补全</span>
        </div>
        <div class="counter-item">
          <span class="counter-value">{{ supplementStatus.resolved_videos ?? '—' }}</span>
          <span class="counter-label">可展示</span>
        </div>
        <div class="counter-item">
          <span class="counter-value">{{ candidateSummary.candidate }}</span>
          <span class="counter-label">下载候选</span>
        </div>
      </div>
      <div v-if="candidateSummary.candidate > 0" class="candidate-summary">
        {{ candidateSummary.needsMagnet }} 个待补磁力，{{ candidateSummary.ready }} 个可批准
      </div>
      <div class="supplement-actions">
        <button
          class="btn btn-primary btn-sm"
          :disabled="isSupplementRunning"
          @click="startSupplement"
        >
          {{ isSupplementRunning ? '补全中...' : '补全作品' }}
        </button>
        <button class="btn btn-ghost btn-sm" @click="refreshResolved">刷新 resolved</button>
        <button class="btn btn-ghost btn-sm" @click="goSupplementMovies">字段管理</button>
        <button class="btn btn-ghost btn-sm" @click="goSupplementJobs">任务队列</button>
        <button class="btn btn-ghost btn-sm" @click="goDownloadCandidates">处理候选</button>
      </div>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="loading-wrap">
      <div class="spinner-large"></div>
      <p>加载作品集中...</p>
    </div>

    <!-- Movies by Year -->
    <div v-else-if="movies.length > 0" class="movies-section">
      <div class="section-header">
        <h2>全部作品</h2>
        <div class="header-right">
          <div v-if="variantCount > 0" class="variant-switch">
            <button
              class="switch-btn"
              :class="{ active: !showVariants }"
              @click="showVariants = false"
            >标准版</button>
            <button
              class="switch-btn"
              :class="{ active: showVariants }"
              @click="showVariants = true"
            >变体 <span class="variant-badge">{{ variantCount }}</span></button>
          </div>
          <span class="movie-count">{{ displayMovies.length }} 部</span>
        </div>
      </div>

      <!-- Year groups -->
      <div v-for="group in yearGroups" :key="group.year" :id="'year-' + group.year" class="year-group">
        <div class="year-header">
          <span class="year-label">{{ group.year }}</span>
          <span class="year-count">{{ group.movies.length }} 部</span>
        </div>
        <div class="movies-grid">
          <div
            v-for="movie in group.movies"
            :key="movie.code || movie.id"
            class="movie-card-wrap"
          >
            <MovieCard
              :contentId="movie.code || movie.id"
              :coverUrl="cardImageUrl(movie)"
              :title="movie.title || ''"
              :serviceCode="displayServiceCode(movie)"
              :releaseDate="movie.date || ''"
              :runtimeMins="movie._raw?.runtime_mins || ''"
              :sampleUrl="movie._raw?.sample_url || ''"
              :isFavorited="false"
              @click="openModal(movie)"
            />
            <span v-if="movie._variant" class="variant-label">
              {{ variantLabel(movie._variant) }}
            </span>
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

    <!-- Year Navigator (right side) -->
    <transition name="nav-fade">
      <div v-if="yearGroups.length > 1" class="year-nav">
        <button
          v-for="group in yearGroups"
          :key="group.year"
          class="year-nav-item"
          :class="{ active: activeYear === group.year }"
          @click="scrollToYear(group.year)"
        >
          {{ group.year.toString().slice(2) }}
        </button>
      </div>
    </transition>

  </div>
</template>

<script>
import api from '../api'
import { actressImgUrl, jacketHdUrl } from '../utils/imageUrl.js'
import { displayName } from '../utils/displayLang.js'
import { openVideoModal } from '../utils/modalState.js'
import { groupByVariant, variantLabel } from '../utils/videoVariant.js'
import MovieCard from '../components/MovieCard.vue'

export default {
  name: 'Actor',
  components: { MovieCard },
  data() {
    return {
      actorName: '',
      actressData: null,
      movies: [],
      totalCount: 0,
      loading: false,
      activeYear: null,
      showVariants: false,
      supplementStatus: null,
      candidateSummary: { candidate: 0, needsMagnet: 0, ready: 0 },
      supplementLoading: false,
      supplementPolling: null,
      _yearObserver: null
    }
  },
  computed: {
    avatarUrl() {
      if (this.actressData?.image_url) return actressImgUrl(this.actressData.image_url)
      return ''
    },
    translatedName() {
      if (!this.actressData) return this.actorName
      return displayName(this.actressData, 'name_kanji', 'name_romaji') || this.actorName
    },
    variantInfo() {
      return groupByVariant(this.movies)
    },
    displayMovies() {
      if (this.showVariants) return this.variantInfo.variants
      return this.variantInfo.canonical
    },
    variantCount() {
      return this.variantInfo.totalVariants
    },
    yearGroups() {
      const groups = {}
      for (const m of this.displayMovies) {
        const year = m.date ? m.date.slice(0, 4) : '未知'
        if (!groups[year]) groups[year] = []
        groups[year].push(m)
      }
      return Object.keys(groups)
        .sort((a, b) => b.localeCompare(a))
        .map(year => ({ year, movies: groups[year] }))
    },
    actressId() {
      return this.$route.query.actress_id || this.actressData?.id || null
    },
    isSupplementRunning() {
      const s = this.supplementStatus?.last_job?.status
      return s === 'running' || s === 'queued'
    },
  },
  mounted() {
    this.actorName = this.$route.query.name || this.$route.params.name || ''
    if (this.actorName) {
      this.loadActressInfo()
      this.loadActorMovies()
      this.loadSupplementStatus()
      this.loadCandidateSummary()
    }
  },
  beforeUnmount() {
    this._stopSupplementPolling()
    if (this._yearObserver) this._yearObserver.disconnect()
  },
  watch: {
    actressId(newId, oldId) {
      if (newId && newId !== oldId) {
        this.loadSupplementStatus()
        this.loadCandidateSummary()
      }
    },
  },
  methods: {
    async loadActressInfo() {
      try {
        const actressId = this.$route.query.actress_id
        if (actressId) {
          // 直接用 ID 获取（从订阅页跳转时带过来）
          const resp = await api.getActress(actressId)
          this.actressData = resp.data || resp
          return
        }
        // 兜底：按名字搜索
        const resp = await api.searchActors(this.actorName)
        const results = resp.data?.data || resp.data || []
        const match = results.find(a =>
          (a.name_kanji === this.actorName) ||
          (a.name_romaji === this.actorName) ||
          (a.name_kanji && this.actorName.includes(a.name_kanji))
        )
        if (match) this.actressData = match
      } catch (e) {
        console.error('Load actress info failed:', e)
      }
    },
    normalizeMovie(m) {
      return {
        code: m.dvd_id || m.content_id || '',
        id: m.content_id || m.dvd_id || '',
        title: m.title_en || m.title_ja || m.canonical_number || '',
        cover_url: m.jacket_thumb_url || '',
        date: m.release_date || '',
        actor: m.actress_name || this.actorName,
        genres: m.categories || [],
        _raw: m,
        _dataOrigin: m.data_origin || null,
      }
    },
    async loadActorMovies() {
      this.loading = true
      try {
        const pageSize = 100
        let allMovies = []
        let totalCount = 0

        if (this.actressId) {
          const fetchPage = async (page) => {
            const resp = await api.getActressVideos(this.actressId, page, pageSize, { include_supplement: '1' })
            return resp.data
          }
          const first = await fetchPage(1)
          allMovies = (first.data || []).map(m => this.normalizeMovie(m))
          totalCount = first.total_count || allMovies.length
          const totalPages = first.total_pages || 1
          if (totalPages > 1) {
            const pagePromises = []
            for (let page = 2; page <= totalPages; page++) {
              pagePromises.push(fetchPage(page))
            }
            const results = await Promise.all(pagePromises)
            for (const r of results) {
              allMovies.push(...(r.data || []).map(m => this.normalizeMovie(m)))
            }
          }
        } else {
          const resp = await api.searchVideos({ actress_name: this.actorName, page: 1, page_size: pageSize })
          const data = resp.data
          allMovies = (data.data || []).map(m => this.normalizeMovie(m))
          totalCount = data.total_count || allMovies.length
          const totalPages = data.total_pages || 1
          if (totalPages > 1) {
            const pagePromises = []
            for (let page = 2; page <= totalPages; page++) {
              pagePromises.push(api.searchVideos({ actress_name: this.actorName, page, page_size: pageSize }))
            }
            const results = await Promise.all(pagePromises)
            for (const r of results) {
              allMovies.push(...(r.data.data || []).map(m => this.normalizeMovie(m)))
            }
          }
        }

        this.movies = allMovies
        this.totalCount = totalCount
        this.$nextTick(() => this._setupYearObserver())
      } catch (e) {
        console.error('Load actor movies failed:', e)
      } finally {
        this.loading = false
      }
    },
    _setupYearObserver() {
      if (this._yearObserver) this._yearObserver.disconnect()
      if (!this.yearGroups.length) return
      this.activeYear = this.yearGroups[0].year
      this._yearObserver = new IntersectionObserver((entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            const year = entry.target.id.replace('year-', '')
            this.activeYear = year
          }
        }
      }, { rootMargin: '-80px 0px -70% 0px' })
      for (const group of this.yearGroups) {
        const el = document.getElementById('year-' + group.year)
        if (el) this._yearObserver.observe(el)
      }
    },
    scrollToYear(year) {
      const el = document.getElementById('year-' + year)
      if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' })
    },
    openModal(movie) {
      openVideoModal(movie._raw || movie, this.$route.path)
    },
    cardImageUrl(movie) {
      return jacketHdUrl(movie.cover_url) || movie.cover_url || ''
    },
    displayServiceCode(movie) {
      if (movie._raw?.data_origin === 'supplement') return ''
      return movie._raw?.service_code || ''
    },
    handleAvatarError(e) {
      e.target.src = 'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" width="120" height="120" viewBox="0 0 120 120"><rect fill="%23333" width="120" height="120" rx="60"/><text x="50%" y="55%" text-anchor="middle" dy=".3em" fill="%23999" font-size="40">?</text></svg>'
    },
    async loadSupplementStatus() {
      if (!this.actressId) return
      try {
        const resp = await api.getSupplementActressStatus(this.actressId)
        this.supplementStatus = resp.data || resp
        if (this.isSupplementRunning) {
          this._startSupplementPolling()
        }
      } catch (e) {
        console.warn('Load supplement status failed:', e)
      }
    },
    async loadCandidateSummary() {
      if (!this.actressId) return
      try {
        const resp = await api.listDownloadCandidates({
          status: 'candidate',
          actress_id: this.actressId,
          limit: 100000,
        })
        const rows = resp.data?.data || []
        const needsMagnet = rows.filter(row => !row.magnet).length
        this.candidateSummary = {
          candidate: rows.length,
          needsMagnet,
          ready: rows.length - needsMagnet,
        }
      } catch (e) {
        console.warn('Load actor candidate summary failed:', e)
      }
    },
    async startSupplement() {
      if (!this.actressId || this.isSupplementRunning) return
      try {
        await api.startSupplementFilmographyJob(this.actressId)
        await this.loadSupplementStatus()
      } catch (e) {
        console.error('Start supplement failed:', e)
      }
    },
    async refreshResolved() {
      if (!this.actressId) return
      try {
        await api.refreshSupplementActressResolved(this.actressId)
        await this.loadSupplementStatus()
      } catch (e) {
        console.error('Refresh resolved failed:', e)
      }
    },
    goSupplementMovies() {
      this.$router.push({ path: '/supplement', query: { tab: 'movies', actress_id: this.actressId } })
    },
    goSupplementJobs() {
      this.$router.push({ path: '/supplement', query: { tab: 'jobs', actress_id: this.actressId } })
    },
    goDownloadCandidates() {
      this.$router.push({
        path: '/downloads',
        query: {
          tab: 'candidates',
          status: 'candidate',
          actress_id: this.actressId,
        },
      })
    },
    statusLabel(status) {
      const map = { queued: '排队中', running: '运行中', succeeded: '已完成', failed: '失败' }
      return map[status] || status || '未知'
    },
    _startSupplementPolling() {
      this._stopSupplementPolling()
      this.supplementPolling = setInterval(async () => {
        await this.loadSupplementStatus()
        if (!this.isSupplementRunning) this._stopSupplementPolling()
      }, 4000)
    },
    _stopSupplementPolling() {
      if (this.supplementPolling) {
        clearInterval(this.supplementPolling)
        this.supplementPolling = null
      }
    },
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
  margin-bottom: 4px;
}

.actor-name-original {
  font-size: 14px;
  color: var(--text-muted);
  margin: 0 0 8px;
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

.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.variant-switch {
  display: inline-flex;
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  overflow: hidden;
}

.switch-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 14px;
  background: transparent;
  border: none;
  color: var(--text-muted);
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
}

.switch-btn:hover {
  color: var(--text-secondary);
}

.switch-btn.active {
  background: rgba(255, 255, 255, 0.1);
  color: var(--text-primary);
  font-weight: 600;
}

.variant-badge {
  font-size: 11px;
  padding: 1px 6px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 10px;
  font-weight: 600;
}

.movie-count {
  font-size: 14px;
  color: var(--text-secondary);
}

.movie-card-wrap {
  position: relative;
}

.variant-label {
  position: absolute;
  bottom: 8px;
  left: 8px;
  padding: 2px 8px;
  background: rgba(var(--accent-rgb, 120, 120, 255), 0.8);
  backdrop-filter: blur(8px);
  border-radius: 10px;
  font-size: 11px;
  color: #fff;
  font-weight: 600;
  pointer-events: none;
  z-index: 1;
}

/* Year Groups */
.year-group {
  margin-bottom: 32px;
}

.year-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 16px;
  padding-bottom: 10px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
  scroll-margin-top: 20px;
}

.year-label {
  font-size: 22px;
  font-weight: 700;
  color: var(--text-primary);
  letter-spacing: -0.02em;
}

.year-count {
  font-size: 13px;
  color: var(--text-muted);
  font-weight: 500;
}

.movies-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 20px;
}

/* Year Navigator */
.year-nav {
  position: fixed;
  right: 16px;
  top: 50%;
  transform: translateY(-50%);
  display: flex;
  flex-direction: column;
  gap: 2px;
  z-index: 100;
  background: rgba(22, 22, 24, 0.8);
  backdrop-filter: blur(20px) saturate(180%);
  -webkit-backdrop-filter: blur(20px) saturate(180%);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 12px;
  padding: 6px 4px;
}

.year-nav-item {
  border: none;
  background: transparent;
  color: var(--text-muted);
  font-size: 11px;
  font-weight: 600;
  padding: 4px 8px;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s cubic-bezier(0.23, 1, 0.32, 1);
  text-align: center;
  min-width: 32px;
}

.year-nav-item:hover {
  background: rgba(255, 255, 255, 0.08);
  color: var(--text-secondary);
}

.year-nav-item.active {
  background: var(--accent);
  color: var(--bg-primary);
}

.nav-fade-enter-active { transition: opacity 0.3s ease; }
.nav-fade-leave-active { transition: opacity 0.2s ease; }
.nav-fade-enter-from, .nav-fade-leave-to { opacity: 0; }

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

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* Supplement Card */
.supplement-card {
  margin: 0 40px 20px;
  padding: 20px 24px;
  background: var(--bg-secondary);
  border: 1px solid var(--border);
  border-radius: 16px;
}

.supplement-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.supplement-header h3 {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0;
}

.supplement-badge {
  font-size: 12px;
  padding: 3px 10px;
  border-radius: 10px;
  font-weight: 600;
}

.badge-running {
  background: rgba(59, 130, 246, 0.2);
  color: #60a5fa;
}

.badge-failed {
  background: rgba(239, 68, 68, 0.2);
  color: #f87171;
}

.badge-ok {
  background: rgba(34, 197, 94, 0.2);
  color: #4ade80;
}

.supplement-error {
  margin-bottom: 12px;
  padding: 8px 12px;
  background: rgba(239, 68, 68, 0.1);
  border-radius: 8px;
  font-size: 13px;
  color: #f87171;
}

.supplement-counters {
  display: flex;
  gap: 24px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}

.counter-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.counter-value {
  font-size: 20px;
  font-weight: 700;
  color: var(--text-primary);
}

.counter-label {
  font-size: 12px;
  color: var(--text-muted);
}

.candidate-summary {
  margin-bottom: 12px;
  color: var(--text-secondary);
  font-size: 13px;
}

.supplement-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.btn-sm {
  padding: 6px 14px;
  font-size: 13px;
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

  .year-nav {
    right: 6px;
    padding: 4px 3px;
  }

  .year-nav-item {
    font-size: 10px;
    padding: 3px 5px;
    min-width: 26px;
  }

  .year-label {
    font-size: 18px;
  }

  .supplement-card {
    margin: 0 16px 16px;
  }
  .supplement-counters {
    gap: 16px;
  }
}
</style>
