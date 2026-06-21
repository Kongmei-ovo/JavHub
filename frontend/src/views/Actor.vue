<template>
  <div class="actor-page page-bleed">
    <div class="actor-hero page-rail page-rail--gallery">
      <div class="hero-content">
        <div v-if="avatarUrl" class="actor-avatar">
          <img
            :src="avatarUrl"
            :alt="actorName"
            loading="eager"
            decoding="async"
            @error="handleAvatarError"
          />
        </div>
        <div
          v-else
          class="actor-avatar image-fallback"
          :data-fallback-label="avatarFallbackLabel"
        ></div>
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
    <AppleSkeleton v-if="loading" class="loading-wrap page-rail page-rail--standard" variant="gallery" :items="8" label="演员作品加载中" />

    <AppleErrorState
      v-else-if="movieError"
      class="empty-state page-rail page-rail--standard"
      title="演员作品加载失败"
      :description="movieError"
      next-step="重新加载会保留当前演员；如果仍失败，可以返回上一页重新进入。"
      retry-label="重新加载"
      secondary-action-label="轻量加载首屏"
      @retry="loadActorMovies"
      @secondary-action="loadActorMoviesCompact"
    />

    <!-- Movies by Year -->
    <div v-else-if="movies.length > 0" class="movies-section page-rail page-rail--gallery">
      <div class="section-header">
        <h2>全部作品</h2>
        <div class="header-right">
          <div v-if="variantCount > 0 && viewMode === 'cover'" class="variant-switch">
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
          <div class="view-switch" role="group" aria-label="视图切换">
            <button class="switch-btn" :class="{ active: viewMode === 'cover' }" @click="viewMode = 'cover'">封面</button>
            <button class="switch-btn" :class="{ active: viewMode === 'list' }" @click="setListView">列表</button>
          </div>
          <button class="btn btn-ghost csv-btn" type="button" :disabled="exportingCsv" @click="exportCsv">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" width="14" height="14" aria-hidden="true"><path d="M12 3v12m0 0l-4-4m4 4l4-4M5 21h14"/></svg>
            {{ exportingCsv ? (exportProgress || '导出中…') : '导出 CSV' }}
          </button>
          <span class="movie-count">{{ sectionMovieCountLabel }}</span>
        </div>
      </div>

      <!-- Cover mode: year groups -->
      <template v-if="viewMode === 'cover'">
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
              class="variant-expand-btn"
              type="button"
              @click.stop="toggleVariantGroup(movie)"
            >
              <span v-if="isVariantGroupExpanded(movie)">收起版本</span>
              <span v-else>另 {{ movie.variant_group_count - 1 }} 个版本</span>
            </button>
            <div v-if="isVariantGroupExpanded(movie)" class="variant-inline-list">
              <button
                v-for="variant in variantGroupItems(movie)"
                :key="variant.content_id || variant.dvd_id || variant.display_code"
                class="variant-inline-item"
                type="button"
                @click.stop="openModal(variant)"
              >
                <span class="variant-inline-code">{{ variant.display_code || variant.dvd_id || variant.content_id }}</span>
                <span class="variant-inline-labels">
                  <span
                    v-for="label in (variant.variant_labels || []).slice(0, 2)"
                    :key="label.key || label.label"
                  >{{ label.short_label || label.label }}</span>
                </span>
              </button>
            </div>
          </div>
        </div>
        <div v-else class="year-empty">该年份暂无作品</div>
      </div>
      </template>

      <!-- List mode: flat sortable table (番号 · 片名 · 时长 · 出演时间 · 115) -->
      <div v-else class="movie-list">
        <div class="movie-list-head">
          <button type="button" class="ml-col ml-code" :class="listSortClass('code')" @click="setListSort('code')">番号<span class="ml-arrow">{{ listSortArrow('code') }}</span></button>
          <span class="ml-col ml-title">片名</span>
          <button type="button" class="ml-col ml-runtime" :class="listSortClass('runtime')" @click="setListSort('runtime')">时长<span class="ml-arrow">{{ listSortArrow('runtime') }}</span></button>
          <button type="button" class="ml-col ml-date" :class="listSortClass('date')" @click="setListSort('date')">出演时间<span class="ml-arrow">{{ listSortArrow('date') }}</span></button>
          <span class="ml-col ml-owned">115</span>
        </div>
        <button
          v-for="movie in sortedListMovies"
          :key="movieKey(movie)"
          type="button"
          class="movie-list-row"
          @click="openModal(movie)"
        >
          <span class="ml-col ml-code">{{ movie.display_code || movie.code || movie.id }}</span>
          <span class="ml-col ml-title">{{ movie.title || '—' }}</span>
          <span class="ml-col ml-runtime">{{ movie._raw?.runtime_mins ? movie._raw.runtime_mins + ' 分' : '—' }}</span>
          <span class="ml-col ml-date">{{ movie.date || '—' }}</span>
          <span class="ml-col ml-owned">
            <span class="owned-badge" :class="isOwned(movie) ? 'is-owned' : 'not-owned'">{{ isOwned(movie) ? '已拥有' : '未拥有' }}</span>
          </span>
        </button>
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

    <AppleEmptyState
      v-else
      class="empty-state page-rail page-rail--standard"
      title="暂无演员作品"
      description="当前演员还没有可展示的作品。"
      next-step="可以重新加载作品集，或回到分类目录继续浏览演员。"
      action-label="重新加载"
      secondary-action-label="分类目录"
      density="compact"
      @action="loadActorMovies"
      @secondary-action="$router.push('/entities')"
    />

    <!-- Year Navigator (right side) -->
    <transition name="nav-fade">
      <div v-if="yearNavItems.length > 1 && viewMode === 'cover'" class="year-nav">
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
import { variantGroupKey, visibleVariantItems } from '../utils/videoVariantPresentation.js'
import { movieOwnKeys, sortFilmList, filmsToCsv, downloadCsv } from '../features/actor/filmListExport.js'
import MovieCard from '../components/MovieCard.vue'
import AppleSkeleton from '../components/AppleSkeleton.vue'
import AppleEmptyState from '../components/AppleEmptyState.vue'
import AppleErrorState from '../components/AppleErrorState.vue'

const MOVIE_PAGE_SIZE = 100
const RECOVERY_MOVIE_PAGE_SIZE = 24

export default {
  name: 'Actor',
  components: { MovieCard, AppleSkeleton, AppleEmptyState, AppleErrorState },
  data() {
    return {
      actorName: '',
      actressData: null,
      movies: [],
      totalCount: 0,
      catalogTotalCount: 0,
      moviePage: 1,
      moviePageSize: MOVIE_PAGE_SIZE,
      movieTotalPages: 1,
      loadingMoreMovies: false,
      loading: false,
      movieError: '',
      activeYear: null,
      yearRange: [],
      yearLoadState: {},
      yearLoadingYear: null,
      showVariants: false,
      expandedVariantGroups: {},
      _yearObserver: null,
      viewMode: 'cover', // 'cover' | 'list'
      listSortKey: 'date', // 'code' | 'runtime' | 'date'
      listSortDir: 'desc',
      ownedKeys: {}, // owned content_id / number -> true
      exportingCsv: false,
      exportProgress: '',
    }
  },
  computed: {
    avatarUrl() {
      if (this.actressData?.image_url) return actressImgUrl(this.actressData.image_url)
      return ''
    },
    avatarFallbackLabel() {
      return (this.translatedName || this.actorName || '?').slice(0, 1)
    },
    translatedName() {
      if (!this.actressData) return this.actorName
      return displayName(this.actressData, 'name_kanji', 'name_romaji') || this.actorName
    },
    displayMovies() {
      if (this.showVariants) return this.flattenVariantGroups(this.movies)
      return this.movies
    },
    sortedListMovies() {
      return sortFilmList(this.displayMovies, this.listSortKey, this.listSortDir)
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
    hasMoreMovies() {
      if (this.totalCount < 0 || this.movieTotalPages < 0) {
        return this.movies.length >= this.moviePage * this.moviePageSize
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
    if (this._yearObserver) this._yearObserver.disconnect()
  },
  watch: {
    routeIdentity(newIdentity, oldIdentity) {
      if (newIdentity !== oldIdentity) this.loadRouteActor()
    },
  },
  methods: {
    async loadRouteActor() {
      this.actorName = this.$route.query.name || this.$route.params.name || ''
      this.actressData = null
      this.yearRange = []
      this.yearLoadState = {}
      this.yearLoadingYear = null
      this.activeYear = null
      this.expandedVariantGroups = {}
      if (!this.actorName) return
      await this.loadActressInfo()
      this.loadActorMovies()
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
    async loadActorMovies({ pageSize = MOVIE_PAGE_SIZE } = {}) {
      this.loading = true
      this.movieError = ''
      try {
        this.movies = []
        this.moviePage = 1
        this.moviePageSize = pageSize
        this.movieTotalPages = 1
        this.totalCount = 0
        this.catalogTotalCount = 0
        this.yearRange = []
        this.yearLoadState = {}
        this.yearLoadingYear = null
        this.expandedVariantGroups = {}
        this.ownedKeys = {}
        const first = await this.fetchActorMoviePage(1, { pageSize, includeTotal: true })
        this.appendMoviePage(first, { trustTotals: true })
        this.loadYearBounds(first)
        if (this.viewMode === 'list') this.refreshOwnedStatus()
      } catch (e) {
        console.error('Load actor movies failed:', e)
        this.movieError = e.response?.data?.detail || e.message || '演员作品加载失败'
      } finally {
        this.loading = false
      }
    },
    async loadActorMoviesCompact() {
      return this.loadActorMovies({ pageSize: RECOVERY_MOVIE_PAGE_SIZE })
    },
    async loadMoreMovies() {
      if (!this.hasMoreMovies || this.loadingMoreMovies) return
      this.loadingMoreMovies = true
      try {
        const nextPage = this.moviePage + 1
        const data = await this.fetchActorMoviePage(nextPage, { pageSize: this.moviePageSize })
        this.moviePage = nextPage
        this.appendMoviePage(data)
        if (this.viewMode === 'list') this.refreshOwnedStatus()
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
    variantGroupKey,
    isVariantGroupExpanded(movie) {
      if (this.showVariants) return false
      const key = this.variantGroupKey(movie)
      return Boolean(key && this.expandedVariantGroups[key])
    },
    toggleVariantGroup(movie) {
      const key = this.variantGroupKey(movie)
      if (!key) return
      this.expandedVariantGroups = {
        ...this.expandedVariantGroups,
        [key]: !this.expandedVariantGroups[key],
      }
    },
    variantGroupItems(movie) {
      return visibleVariantItems(movie._raw || movie)
    },
    cardImageUrl(movie) {
      return movie.cover_url || movie.jacket_thumb_url || movie.jacket_full_url || ''
    },
    // --- list view: sort, ownership, CSV export ---------------------------
    setListView() {
      this.viewMode = 'list'
      this.refreshOwnedStatus()
    },
    setListSort(key) {
      if (this.listSortKey === key) {
        this.listSortDir = this.listSortDir === 'asc' ? 'desc' : 'asc'
      } else {
        this.listSortKey = key
        this.listSortDir = key === 'code' ? 'asc' : 'desc'
      }
    },
    listSortArrow(key) {
      if (this.listSortKey !== key) return ''
      return this.listSortDir === 'asc' ? '↑' : '↓'
    },
    listSortClass(key) {
      return { active: this.listSortKey === key }
    },
    isOwned(movie) {
      return movieOwnKeys(movie).some(k => this.ownedKeys[k])
    },
    ownedMapFor(owned) {
      const map = {}
      for (const k of (owned || [])) map[String(k)] = true
      return map
    },
    async refreshOwnedStatus() {
      const keys = [...new Set(this.displayMovies.flatMap(movieOwnKeys))]
      if (!keys.length) return
      try {
        const resp = await api.getMoviesOwnedStatus(keys)
        this.ownedKeys = this.ownedMapFor(resp.data?.owned || resp.owned)
      } catch (e) {
        console.error('Load owned status failed:', e)
      }
    },
    async fetchAllMoviesForExport() {
      const pageSize = MOVIE_PAGE_SIZE
      const collected = []
      const seen = new Set()
      const pushPage = (data) => {
        for (const m of (data.data || [])) {
          const nm = this.normalizeMovie(m)
          const key = this.movieKey(nm)
          if (seen.has(key)) continue
          seen.add(key)
          collected.push(nm)
        }
      }
      const first = await this.fetchActorMoviePage(1, { pageSize, includeTotal: true })
      const total = Number.isInteger(first.total_count) && first.total_count >= 0 ? first.total_count : null
      const totalPages = Number.isInteger(first.total_pages) && first.total_pages > 0 ? first.total_pages : null
      pushPage(first)
      const lastPage = totalPages || (total ? Math.ceil(total / pageSize) : 1)
      for (let p = 2; p <= lastPage; p += 1) {
        this.exportProgress = `导出中… ${collected.length}${total ? '/' + total : ''}`
        const before = collected.length
        pushPage(await this.fetchActorMoviePage(p, { pageSize }))
        if (collected.length === before) break // safety: page returned nothing new
      }
      return collected
    },
    async exportCsv() {
      if (this.exportingCsv) return
      this.exportingCsv = true
      this.exportProgress = '导出中…'
      try {
        const all = await this.fetchAllMoviesForExport()
        let ownedMap = {}
        try {
          const resp = await api.getMoviesOwnedStatus([...new Set(all.flatMap(movieOwnKeys))])
          ownedMap = this.ownedMapFor(resp.data?.owned || resp.owned)
        } catch (e) {
          console.error('Owned status for CSV failed:', e)
        }
        const csv = filmsToCsv(all, m => movieOwnKeys(m).some(k => ownedMap[k]))
        const name = (this.translatedName || this.actorName || 'actress').replace(/[\\/:*?"<>|]/g, '_')
        downloadCsv(csv, `${name}-作品集.csv`)
      } catch (e) {
        console.error('CSV export failed:', e)
      } finally {
        this.exportingCsv = false
        this.exportProgress = ''
      }
    },
    displayServiceCode(movie) {
      if (movie._raw?.data_origin === 'supplement') return ''
      return movie._raw?.service_code || ''
    },
    handleAvatarError(e) {
      applyImageFallback(e, { label: this.avatarFallbackLabel })
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
  }
}
</script>

<style scoped src="../features/actor/actor.css"></style>
