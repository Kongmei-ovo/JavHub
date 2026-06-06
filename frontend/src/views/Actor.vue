<template>
  <div class="actor-page page-bleed">
    <!-- Hero -->
    <div class="actor-hero page-rail page-rail--gallery">
      <div class="hero-content">
        <div class="actor-avatar">
          <img
            :src="avatarUrl"
            :alt="actorName"
            loading="eager"
            decoding="async"
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
              {{ actorMovieCountLabel }}
            </span>
            <span v-if="isActorFavorited" class="meta-item meta-item--favorite">已收藏</span>
            <span v-if="isActorSubscribed" class="meta-item meta-item--subscribed">已订阅</span>
          </div>
          <div class="actor-actions">
            <button
              class="actor-action-btn"
              :class="{ active: isActorFavorited }"
              type="button"
              @click="toggleActorFavorite"
            >
              <svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true">
                <path
                  d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z"
                  fill="currentColor"
                />
              </svg>
              {{ isActorFavorited ? '取消收藏' : '收藏演员' }}
            </button>
            <button
              v-if="actressId"
              class="actor-action-btn actor-action-btn--subscribe"
              :class="{ active: isActorSubscribed }"
              type="button"
              @click="toggleActorSubscription"
            >
              <svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true">
                <path d="M19 3H5a2 2 0 0 0-2 2v16l9-4 9 4V5a2 2 0 0 0-2-2zm-2 11H7v-2h10v2zm0-4H7V8h10v2z" fill="currentColor"/>
              </svg>
              {{ isActorSubscribed ? '取消订阅' : '订阅演员' }}
            </button>
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
    <div v-if="actressId && supplementStatus" class="supplement-card page-rail page-rail--gallery">
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
    <div v-if="loading" class="loading-wrap page-rail page-rail--standard">
      <div class="spinner-large"></div>
      <p>加载作品集中...</p>
    </div>

    <!-- Movies by Year -->
    <div v-else-if="movies.length > 0" class="movies-section page-rail page-rail--gallery">
      <div class="section-header">
        <h2>全部作品</h2>
        <div class="header-right">
          <div v-if="variantCount > 0" class="variant-switch">
            <button
              class="switch-btn"
              :class="{ active: !showVariants }"
              @click="showVariants = false"
            >合并版本</button>
            <button
              class="switch-btn"
              :class="{ active: showVariants }"
              @click="showVariants = true"
            >展开版本 <span class="variant-badge">{{ variantCount }}</span></button>
          </div>
          <span class="movie-count">{{ sectionMovieCountLabel }}</span>
        </div>
      </div>

      <!-- Year groups -->
      <div v-for="group in visibleYearGroups" :key="group.year" :id="'year-' + group.year" class="year-group">
        <div class="year-header">
          <span class="year-label">{{ group.year }}</span>
          <span class="year-count">{{ yearGroupCountLabel(group) }}</span>
        </div>
        <div v-if="group.movies.length > 0" class="movies-grid">
          <div
            v-for="movie in group.movies"
            :key="movieKey(movie)"
            class="movie-card-wrap"
          >
            <MovieCard
              :contentId="movie.code || movie.id"
              :dvdId="movie.display_code || movie.code || movie.id"
              :displayCode="movie.display_code || movie.code || movie.id"
              :canonicalCode="movie.canonical_code || ''"
              :variantLabels="movie.variant_labels || []"
              :variantExplanations="movie.variant_explanations || []"
              :coverUrl="cardImageUrl(movie)"
              :title="movie.title || ''"
              :serviceCode="displayServiceCode(movie)"
              :releaseDate="movie.date || ''"
              :runtimeMins="movie._raw?.runtime_mins || ''"
              :sampleUrl="movie._raw?.sample_url || ''"
              @click="openModal(movie)"
            />
            <button
              v-if="movie.variant_group_count > 1 && !showVariants"
              class="variant-label"
              type="button"
              @click.stop="showVariants = true"
            >
              另 {{ movie.variant_group_count - 1 }} 个版本
            </button>
          </div>
        </div>
        <div v-else class="year-empty">该年份暂无作品</div>
      </div>
      <div v-if="hasMoreMovies" class="load-more-wrap">
        <button
          class="btn btn-ghost load-more-btn"
          :disabled="loadingMoreMovies"
          @click="loadMoreMovies"
        >
          {{ loadingMoreMovies ? '加载中...' : loadMoreMoviesLabel }}
        </button>
      </div>
    </div>

    <!-- Empty State -->
    <div v-else class="empty-state page-rail page-rail--standard">
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
      <div v-if="yearNavItems.length > 1" class="year-nav">
        <button
          v-for="item in yearNavItems"
          :key="item.year"
          class="year-nav-item"
          :class="{ active: activeYear === item.year, loading: item.loading }"
          :title="yearNavTitle(item)"
          @click="scrollToYear(item.year)"
        >
          {{ item.year.toString().slice(2) }}
        </button>
      </div>
    </transition>

  </div>
</template>

<script>
import api from '../api'
import { actressImgUrl } from '../utils/imageUrl.js'
import { displayName } from '../utils/displayLang.js'
import { openVideoModal } from '../utils/modalState.js'
import favoriteState from '../utils/favoriteState'
import subscriptionState from '../utils/subscriptionState'
import { applyImageFallback } from '../utils/imageFallback.js'
import MovieCard from '../components/MovieCard.vue'

const MOVIE_PAGE_SIZE = 100

export default {
  name: 'Actor',
  components: { MovieCard },
  data() {
    return {
      actorName: '',
      actressData: null,
      movies: [],
      totalCount: 0,
      catalogTotalCount: 0,
      moviePage: 1,
      movieTotalPages: 1,
      loadingMoreMovies: false,
      loading: false,
      activeYear: null,
      yearRange: [],
      yearLoadState: {},
      yearLoadingYear: null,
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
    displayMovies() {
      if (this.showVariants) return this.flattenVariantGroups(this.movies)
      return this.movies
    },
    variantCount() {
      return this.movies.reduce((sum, movie) => sum + Math.max(0, Number(movie.variant_group_count || 1) - 1), 0)
    },
    loadedMovieCount() {
      return this.displayMovies.length
    },
    actorMovieCountLabel() {
      const total = this.catalogTotalCount || this.totalCount
      if (total > 0) return `${total} 部作品`
      return `${this.loadedMovieCount} 部作品`
    },
    sectionMovieCountLabel() {
      const total = this.catalogTotalCount || this.totalCount
      if (total > this.loadedMovieCount) return `已显示 ${this.loadedMovieCount}/${total} 部`
      return `${this.loadedMovieCount} 部`
    },
    loadMoreMoviesLabel() {
      const total = this.catalogTotalCount || this.totalCount
      if (total > this.movies.length) return `加载更多 (${this.movies.length}/${total})`
      return `加载更多 (${this.movies.length})`
    },
    yearGroups() {
      const groups = {}
      for (const m of this.displayMovies) {
        const year = this.movieYear(m)
        if (!groups[year]) groups[year] = []
        groups[year].push(m)
      }
      return Object.keys(groups)
        .sort((a, b) => b.localeCompare(a))
        .map(year => ({ year, movies: groups[year] }))
    },
    visibleYearGroups() {
      const groupsByYear = new Map(this.yearGroups.map(group => [group.year, group]))
      for (const [year, state] of Object.entries(this.yearLoadState)) {
        if (state?.loaded && !groupsByYear.has(year)) {
          groupsByYear.set(year, { year, movies: [] })
        }
      }
      return Array.from(groupsByYear.values())
        .map(group => {
          const state = this.yearLoadState[group.year] || {}
          return {
            ...group,
            totalCount: Number.isInteger(state.totalCount) ? state.totalCount : null,
          }
        })
        .sort((a, b) => b.year.localeCompare(a.year))
    },
    yearNavItems() {
      const loadedYears = this.yearGroups.map(group => group.year).filter(year => year !== '未知')
      const years = this.yearRange.length ? this.yearRange : loadedYears
      return years.map(year => {
        const group = this.yearGroups.find(item => item.year === year)
        const state = this.yearLoadState[year] || {}
        return {
          year,
          loaded: Boolean(group || state.loaded),
          loading: this.yearLoadingYear === year,
          count: Number.isInteger(state.totalCount) ? state.totalCount : (group ? group.movies.length : null),
        }
      })
    },
    actressId() {
      return this.$route.query.actress_id || this.actressData?.id || null
    },
    isSupplementRunning() {
      const s = this.supplementStatus?.last_job?.status
      return s === 'running' || s === 'queued'
    },
    hasMoreMovies() {
      if (this.totalCount < 0 || this.movieTotalPages < 0) {
        return this.movies.length >= this.moviePage * MOVIE_PAGE_SIZE
      }
      return this.moviePage < this.movieTotalPages
    },
    routeIdentity() {
      return `${this.$route.query.actress_id || ''}:${this.$route.query.name || this.$route.params.name || ''}`
    },
    actorFavoriteId() {
      return this.actressId || this.actorName
    },
    isActorFavorited() {
      return favoriteState.isFavorited('actress', this.actorFavoriteId)
    },
    isActorSubscribed() {
      return this.actressId ? subscriptionState.isSubscribed(this.actressId) : false
    },
  },
  async mounted() {
    favoriteState.init().catch(err => {
      console.error('Failed to initialize favorites:', err)
    })
    subscriptionState.refresh().catch(err => {
      console.error('Failed to initialize subscriptions:', err)
    })
    await this.loadRouteActor()
  },
  beforeUnmount() {
    this._stopSupplementPolling()
    if (this._yearObserver) this._yearObserver.disconnect()
  },
  watch: {
    routeIdentity(newIdentity, oldIdentity) {
      if (newIdentity !== oldIdentity) this.loadRouteActor()
    },
    actressId(newId, oldId) {
      if (newId && newId !== oldId) {
        this.loadSupplementStatus()
        this.loadCandidateSummary()
      }
    },
  },
  methods: {
    async loadRouteActor() {
      this.actorName = this.$route.query.name || this.$route.params.name || ''
      this.actressData = null
      this.supplementStatus = null
      this.candidateSummary = { candidate: 0, needsMagnet: 0, ready: 0 }
      this.yearRange = []
      this.yearLoadState = {}
      this.yearLoadingYear = null
      this.activeYear = null
      this._stopSupplementPolling()
      if (!this.actorName) return
      await this.loadActressInfo()
      this.loadActorMovies()
      this.loadSupplementStatus()
      this.loadCandidateSummary()
    },
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
        display_code: m.display_code || m.dvd_id || m.content_id || '',
        canonical_code: m.canonical_code || '',
        variant_labels: Array.isArray(m.variant_labels) ? m.variant_labels : [],
        variant_explanations: Array.isArray(m.variant_explanations) ? m.variant_explanations : [],
        variant_group_count: Number(m.variant_group_count || 1),
        variant_group_items: Array.isArray(m.variant_group_items) ? m.variant_group_items : [],
        title: m.title_en || m.title_ja || m.canonical_number || '',
        cover_url: m.jacket_thumb_url || '',
        date: m.release_date || '',
        actor: m.actress_name || this.actorName,
        genres: m.categories || [],
        _raw: m,
        _dataOrigin: m.data_origin || null,
      }
    },
    async fetchActorMoviePage(page, { pageSize = MOVIE_PAGE_SIZE, year = null, sortBy = 'release_date:desc', includeTotal = false } = {}) {
      const requestOptions = {
        include_supplement: '1',
        include_total: includeTotal,
        variant_mode: 'grouped',
        variant_scope: 'indexed',
        include_variant_explanations: 1,
      }
      if (year) requestOptions.year = Number(year)
      if (sortBy) requestOptions.sort_by = sortBy
      if (this.actressId) {
        const resp = await api.getActressVideos(this.actressId, page, pageSize, requestOptions)
        return resp.data
      }
      const resp = await api.searchVideos({
        actress_name: this.actorName,
        page,
        page_size: pageSize,
        include_total: includeTotal,
        variant_mode: 'grouped',
        variant_scope: 'indexed',
        include_variant_explanations: 1,
        year: year ? Number(year) : undefined,
        sort_by: sortBy,
      })
      return resp.data
    },
    appendMoviePage(data, { trustTotals = false } = {}) {
      const incoming = (data.data || []).map(m => this.normalizeMovie(m))
      this.mergeMovies(incoming)
      if (trustTotals && Number.isInteger(data.total_count) && data.total_count >= 0) {
        this.totalCount = data.total_count
        if (!this.catalogTotalCount) this.catalogTotalCount = data.total_count
      } else if (!this.totalCount) {
        this.totalCount = this.movies.length
      }
      if (trustTotals && Number.isInteger(data.total_pages) && data.total_pages >= 0) {
        this.movieTotalPages = data.total_pages
      } else if (!this.movieTotalPages) {
        this.movieTotalPages = 1
      }
      this.$nextTick(() => this._setupYearObserver())
    },
    mergeMovies(incoming) {
      const seen = new Set(this.movies.map(movie => this.movieKey(movie)))
      for (const movie of incoming) {
        const key = this.movieKey(movie)
        if (seen.has(key)) continue
        seen.add(key)
        this.movies.push(movie)
      }
    },
    movieKey(movie) {
      return movie.id || movie.code || `${movie.title}:${movie.date}`
    },
    flattenVariantGroups(movies) {
      const flattened = []
      const seen = new Set()
      for (const movie of movies) {
        const items = Array.isArray(movie.variant_group_items) && movie.variant_group_items.length
          ? movie.variant_group_items
          : [movie._raw || movie]
        for (const raw of items) {
          const normalized = raw === movie._raw ? movie : this.normalizeMovie(raw)
          const key = this.movieKey(normalized)
          if (seen.has(key)) continue
          seen.add(key)
          flattened.push(normalized)
        }
      }
      return flattened
    },
    movieYear(movie) {
      return movie.date ? String(movie.date).slice(0, 4) : '未知'
    },
    movieYearFromApiItem(item) {
      const date = item?.release_date || item?.date || ''
      const year = String(date).slice(0, 4)
      return /^\d{4}$/.test(year) ? year : null
    },
    buildYearRange(latestYear, earliestYear) {
      const latest = Number(latestYear)
      const earliest = Number(earliestYear)
      if (!Number.isInteger(latest) || !Number.isInteger(earliest)) return []
      const start = Math.max(latest, earliest)
      const end = Math.min(latest, earliest)
      const years = []
      for (let year = start; year >= end; year -= 1) years.push(String(year))
      return years
    },
    async loadYearBounds(seedData = null) {
      const latestYear = this.movieYearFromApiItem(seedData?.data?.[0])
        || this.yearGroups.find(group => group.year !== '未知')?.year
      if (!latestYear) return
      let earliestYear = latestYear
      try {
        const oldest = await this.fetchActorMoviePage(1, {
          pageSize: 1,
          sortBy: 'release_date:asc',
          includeTotal: false,
        })
        earliestYear = this.movieYearFromApiItem(oldest?.data?.[0]) || latestYear
      } catch (e) {
        console.warn('Load actor year bounds failed:', e)
      }
      this.yearRange = this.buildYearRange(latestYear, earliestYear)
    },
    async loadActorMovies() {
      this.loading = true
      try {
        this.movies = []
        this.moviePage = 1
        this.movieTotalPages = 1
        this.totalCount = 0
        this.catalogTotalCount = 0
        this.yearRange = []
        this.yearLoadState = {}
        this.yearLoadingYear = null
        const first = await this.fetchActorMoviePage(1, { includeTotal: true })
        this.appendMoviePage(first, { trustTotals: true })
        this.loadYearBounds(first)
      } catch (e) {
        console.error('Load actor movies failed:', e)
      } finally {
        this.loading = false
      }
    },
    async loadMoreMovies() {
      if (!this.hasMoreMovies || this.loadingMoreMovies) return
      this.loadingMoreMovies = true
      try {
        const nextPage = this.moviePage + 1
        const data = await this.fetchActorMoviePage(nextPage)
        this.moviePage = nextPage
        this.appendMoviePage(data)
      } catch (e) {
        console.error('Load more actor movies failed:', e)
      } finally {
        this.loadingMoreMovies = false
      }
    },
    async loadYearMovies(year) {
      const targetYear = String(year || '').trim()
      if (!/^\d{4}$/.test(targetYear) || this.yearLoadingYear === targetYear) return
      const currentState = this.yearLoadState[targetYear]
      if (currentState?.loaded) return
      this.yearLoadingYear = targetYear
      this.yearLoadState = {
        ...this.yearLoadState,
        [targetYear]: { ...(currentState || {}), loading: true },
      }
      try {
        const data = await this.fetchActorMoviePage(1, {
          year: targetYear,
          sortBy: 'release_date:desc',
          includeTotal: true,
        })
        const incoming = (data.data || []).map(m => this.normalizeMovie(m))
        this.mergeMovies(incoming)
        this.yearLoadState = {
          ...this.yearLoadState,
          [targetYear]: {
            loaded: true,
            loading: false,
            totalCount: Number.isInteger(data.total_count) ? data.total_count : incoming.length,
            totalPages: Number.isInteger(data.total_pages) ? data.total_pages : 1,
          },
        }
        this.$nextTick(() => this._setupYearObserver())
      } catch (e) {
        console.error('Load actor year movies failed:', e)
        this.yearLoadState = {
          ...this.yearLoadState,
          [targetYear]: { loaded: false, loading: false, totalCount: null },
        }
      } finally {
        this.yearLoadingYear = null
      }
    },
    _setupYearObserver() {
      if (this._yearObserver) this._yearObserver.disconnect()
      if (!this.visibleYearGroups.length) return
      if (!this.activeYear || !this.visibleYearGroups.some(group => group.year === this.activeYear)) {
        this.activeYear = this.visibleYearGroups[0].year
      }
      this._yearObserver = new IntersectionObserver((entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            const year = entry.target.id.replace('year-', '')
            this.activeYear = year
          }
        }
      }, { rootMargin: '-80px 0px -70% 0px' })
      for (const group of this.visibleYearGroups) {
        const el = document.getElementById('year-' + group.year)
        if (el) this._yearObserver.observe(el)
      }
    },
    async scrollToYear(year) {
      const targetYear = String(year)
      this.activeYear = targetYear
      let el = document.getElementById('year-' + targetYear)
      if (!el) {
        await this.loadYearMovies(year)
        await this.$nextTick()
        el = document.getElementById('year-' + targetYear)
      }
      if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' })
    },
    yearGroupCountLabel(group) {
      if (Number.isInteger(group.totalCount) && group.totalCount > group.movies.length) {
        return `${group.movies.length}/${group.totalCount} 部`
      }
      return `${group.movies.length} 部`
    },
    yearNavTitle(item) {
      if (item.loading) return `${item.year} 加载中`
      if (Number.isInteger(item.count)) return `${item.year} · ${item.count} 部`
      return `${item.year}`
    },
    openModal(movie) {
      openVideoModal(movie._raw || movie, this.$route.fullPath || this.$route.path)
    },
    cardImageUrl(movie) {
      return movie.cover_url || movie.jacket_thumb_url || movie.jacket_full_url || ''
    },
    displayServiceCode(movie) {
      if (movie._raw?.data_origin === 'supplement') return ''
      return movie._raw?.service_code || ''
    },
    handleAvatarError(e) {
      applyImageFallback(e, { label: (this.translatedName || this.actorName || '?').slice(0, 1) })
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
        const resp = await api.getDownloadCandidateSummary({
          status: 'candidate',
          actress_id: this.actressId,
        })
        const summary = resp.data || {}
        this.candidateSummary = {
          candidate: summary.candidate || summary.total || 0,
          needsMagnet: summary.needs_magnet || 0,
          ready: summary.ready || 0,
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
    async toggleActorFavorite() {
      const id = this.actorFavoriteId
      if (!id) return
      try {
        await favoriteState.toggle('actress', id, this.actressData || { name: this.actorName })
      } catch (e) {
        console.error('Toggle actor favorite failed:', e)
      }
    },
    async toggleActorSubscription() {
      if (!this.actressId) return
      try {
        await subscriptionState.toggle(this.actressId, this.translatedName || this.actorName)
      } catch (e) {
        console.error('Toggle actor subscription failed:', e)
      }
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

<style scoped src="../features/actor/actor.css"></style>
