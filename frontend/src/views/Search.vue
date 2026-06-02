<template>
  <div class="search-page page-bleed">
    <!-- 顶部工具栏（仅从详情页跳转来时显示） -->
    <div v-if="$route.query.returnTo === 'video'" class="search-back-toolbar page-rail page-rail--gallery">
      <button class="back-btn" type="button" @click="$router.back()">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="14" height="14">
          <polyline points="15 18 9 12 15 6"/>
        </svg>
        返回详情
      </button>
    </div>

    <!-- 搜索核心区域 -->
    <div class="search-hero" :class="{ compact: searched }">
      <transition name="hero-fade">
        <div v-if="!searched" class="hero-intro">
          <h1 class="hero-title">影片检索</h1>
          <p class="hero-subtitle">搜索影片、番号、演员或工作室</p>
        </div>
      </transition>

      <div class="command-capsule-container page-rail page-rail--standard">
        <!-- 主指令胶囊 -->
        <div class="command-capsule" :class="{ focused: isSearchFocused }">
          <div class="capsule-main">
            <input
              v-model="contentId"
              placeholder="搜索番号"
              @focus="isSearchFocused = true"
              @blur="isSearchFocused = false"
              @keyup.enter="doSearch"
              @input="contentId = contentId.toUpperCase()"
              class="capsule-input primary"
            />
            <div class="capsule-divider"></div>
            <input
              v-model="keyword"
              placeholder="或输入标题关键词"
              @focus="isSearchFocused = true"
              @blur="isSearchFocused = false"
              @keyup.enter="doSearch"
              class="capsule-input"
            />
          </div>

          <button type="button" @click="doSearch" :disabled="loading" class="capsule-search-btn" title="开始探索">
            <span v-if="loading" class="spinner"></span>
            <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" width="18" height="18">
              <circle cx="11" cy="11" r="8"/>
              <path d="m21 21-4.35-4.35"/>
            </svg>
          </button>
        </div>

        <!-- 排序 + 筛选条 -->
        <div class="sort-strip">
          <div class="sort-strip-left">
            <span v-if="searched" class="sort-result-count">{{ loading ? '搜索中...' : totalLabel }}</span>
            <span v-else class="sort-strip-label">排序</span>
            <div class="sort-pills">
              <button
                type="button"
                v-for="pill in sortPills"
                :key="pill.key"
                class="sort-pill"
                :class="{ active: pill.key === 'random' ? sortState.random : sortState[pill.key] !== null, random: pill.key === 'random' && sortState.random }"
                @click="cycleSort(pill.key)"
              >
                <span class="pill-label">{{ pill.label }}</span>
                <svg v-if="sortState[pill.key] === 'desc'" class="pill-arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" width="12" height="12">
                  <path d="M12 5v14M19 12l-7 7-7-7"/>
                </svg>
                <svg v-else-if="sortState[pill.key] === 'asc'" class="pill-arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" width="12" height="12">
                  <path d="M12 19V5M5 12l7-7 7 7"/>
                </svg>
                <svg v-else-if="pill.key === 'random' && sortState.random" class="pill-check" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" width="12" height="12">
                  <path d="M20 6L9 17l-5-5"/>
                </svg>
              </button>
            </div>
            <button v-if="hasSort" class="sort-clear-btn" type="button" @click="clearSort" title="清除排序">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
                <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
              </svg>
            </button>
          </div>
          <div class="sort-strip-right">
            <GlassSelect
              v-model="serviceCode"
              :options="versionOptions"
              size="compact"
              placement="right"
              aria-label="版本筛选"
              class="version-filter"
              @change="doSearch"
            />
            <div class="bar-divider"></div>
            <button class="filter-item toggle" type="button" :class="{ active: showMoreFilters }" @click="showMoreFilters = !showMoreFilters">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="14" height="14">
                <path d="M20 7h-9m14 10h-9M5 7h14M5 17h14"/><circle cx="7" cy="7" r="2"/><circle cx="17" cy="17" r="2"/>
              </svg>
              高级筛选
            </button>
          </div>
        </div>

        <div v-if="activeFilterChips.length" class="applied-filter-row" aria-label="已应用筛选">
          <button
            v-for="chip in activeFilterChips"
            :key="chip.key + '-' + (chip.value || chip.label)"
            class="applied-chip"
            type="button"
            @click="removeFilterChip(chip)"
          >
            <span>{{ chip.label }}</span>
            <b aria-hidden="true">×</b>
          </button>
        </div>

        <!-- 高级筛选详情面板 -->
        <transition name="tray-slide">
          <div v-if="showMoreFilters" class="advanced-panel">
            <div class="panel-grid">
              <div class="panel-field">
                <label>工作室</label>
                <input v-model="makerName" placeholder="输入工作室名称" class="panel-input" @keyup.enter="doSearch" />
              </div>
              <div class="panel-field">
                <label>演员</label>
                <input v-model="actressName" placeholder="输入演员名称" class="panel-input" @keyup.enter="doSearch" />
              </div>
              <div class="panel-field">
                <label>系列</label>
                <input v-model="seriesName" placeholder="输入系列名称" class="panel-input" @keyup.enter="doSearch" />
              </div>
              <div class="panel-field">
                <label>年份</label>
                <input v-model.number="year" placeholder="输入年份" type="number" class="panel-input" @keyup.enter="doSearch" />
              </div>
              <div class="panel-field full">
                <label>题材标签</label>
                <div class="panel-tag-input">
                  <div class="tray-tags">
                    <span v-for="(tag, idx) in categoryTags" :key="idx" class="tray-tag">
                      {{ tag }}<b @click="removeCategoryTag(idx)">×</b>
                    </span>
                  </div>
                  <input
                    v-model="categoryInput"
                    placeholder="输入题材并按空格或回车..."
                    @compositionstart="isComposing = true"
                    @compositionend="handleCompositionEnd"
                    @keydown.space="handleCategoryKeydown"
                    @keydown.enter="handleCategoryKeydown"
                    class="panel-input"
                  />
                </div>
              </div>
            </div>
            <div class="panel-footer">
              <button class="btn-clear" type="button" @click="clearFilters">重置</button>
              <button class="btn-apply" type="button" @click="applyFilters">查看结果</button>
            </div>
          </div>
        </transition>
      </div>
    </div>


    <!-- 分页控制（顶部） -->
    <div v-if="totalPages > 1" class="pagination-bar page-rail page-rail--gallery">
      <button class="page-btn" type="button" :disabled="page <= 1" @click="goPage(1)">«</button>
      <button class="page-btn" type="button" :disabled="page <= 1" @click="goPage(page - 1)">‹</button>
      <span class="page-indicator">{{ page }} / {{ totalPages }}</span>
      <button class="page-btn" type="button" :disabled="page >= totalPages" @click="goPage(page + 1)">›</button>
      <button class="page-btn" type="button" :disabled="page >= totalPages" @click="goPage(totalPages)">»</button>
      <div class="jump-wrap">
        <input
          v-model.number="jumpPage"
          class="jump-input"
          type="number"
          min="1"
          :max="totalPages"
          @keyup.enter="doJumpPage"
          :placeholder="totalPages"
        />
        <button class="jump-btn" type="button" @click="doJumpPage">跳转</button>
      </div>
    </div>

    <!-- 加载骨架屏 -->
    <div v-if="loading" class="skeleton-grid page-rail page-rail--gallery">
      <AppleSkeleton v-for="n in 12" :key="n" variant="card" />
    </div>

    <AppleErrorState
      v-else-if="searchError"
      class="page-rail page-rail--standard"
      title="影片检索失败"
      :description="searchError.message"
      :source-label="searchError.serviceLabel"
      :details="searchError.status ? `HTTP ${searchError.status}` : '网络连接'"
      retry-label="重试"
      :retrying="loading"
      @retry="runSearchFromRoute"
    />

    <!-- 搜索结果网格 -->
    <div v-else-if="results.length > 0" class="results-grid page-rail page-rail--gallery">
      <div
        v-for="item in results"
        :key="item.content_id || item.dvd_id"
        class="result-card-group"
      >
        <MovieCard
          :contentId="item.display_code || item.dvd_id || item.content_id"
          :dvdId="item.display_code || item.dvd_id || item.content_id"
          :displayCode="item.display_code || item.dvd_id || item.content_id"
          :canonicalCode="item.canonical_code || ''"
          :variantLabels="item.variant_labels || []"
          :variantExplanations="item.variant_explanations || []"
          :coverUrl="cardImageUrl(item)"
          :title="item.title_en_translated || item.title_ja_translated || item.title_en || item.title_ja"
          :serviceCode="item.service_code || ''"
          :releaseDate="item.release_date || ''"
          :runtimeMins="item.runtime_mins || ''"
          :sampleUrl="item.sample_url || ''"
          @click="openModal(item)"
        />
        <button
          v-if="item.variant_group_count > 1"
          class="variant-expand-btn"
          type="button"
          @click.stop="toggleVariantGroup(item)"
        >
          <span v-if="isVariantGroupExpanded(item)">收起版本</span>
          <span v-else>另 {{ item.variant_group_count - 1 }} 个版本</span>
        </button>
        <div v-if="isVariantGroupExpanded(item)" class="variant-inline-list">
          <button
            v-for="variant in variantGroupItems(item)"
            :key="variant.content_id || variant.dvd_id"
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

    <!-- 空状态 -->
    <AppleEmptyState
      v-else-if="searched"
      class="page-rail page-rail--standard"
      :title="sortState.random ? '暂无随机探索结果' : '未找到相关影片'"
      description="尝试其他关键词、番号或筛选条件。"
      action-label="重置筛选"
      @action="clearFilters"
    />

    <!-- 分页控制（底部） -->
    <div v-if="totalPages > 1" class="pagination-bar page-rail page-rail--gallery">
      <button class="page-btn" type="button" :disabled="page <= 1" @click="goPage(1)">«</button>
      <button class="page-btn" type="button" :disabled="page <= 1" @click="goPage(page - 1)">‹</button>
      <span class="page-indicator">{{ page }} / {{ totalPages }}</span>
      <button class="page-btn" type="button" :disabled="page >= totalPages" @click="goPage(page + 1)">›</button>
      <button class="page-btn" type="button" :disabled="page >= totalPages" @click="goPage(totalPages)">»</button>
      <div class="jump-wrap">
        <input
          v-model.number="jumpPage"
          class="jump-input"
          type="number"
          min="1"
          :max="totalPages"
          @keyup.enter="doJumpPage"
          :placeholder="totalPages"
        />
        <button class="jump-btn" type="button" @click="doJumpPage">跳转</button>
      </div>
    </div>
  </div>
</template>

<script>
import api from '../api'
import { videoCardCoverUrl } from '../utils/imageUrl.js'
import { openVideoModal } from '../utils/modalState'
import { createRequestSequence } from '../utils/requestSequence.js'
import { loadSearchPreferences } from '../utils/searchPreferences.js'
import { variantGroupKey, visibleVariantItems } from '../utils/videoVariantPresentation.js'
import {
  buildSearchApiParams,
  canonicalizeSearchState,
  cycleSearchSort,
  filterChipsFromSearchState,
  parseSearchQuery,
  searchQueryEquals,
  searchHasUserConditions,
  searchQueryFromState,
  sortStateFromSortValue,
  sortValueFromSortState,
} from '../utils/searchRouteState.js'
import MovieCard from '../components/MovieCard.vue'
import AppleSkeleton from '../components/AppleSkeleton.vue'
import AppleEmptyState from '../components/AppleEmptyState.vue'
import AppleErrorState from '../components/AppleErrorState.vue'
import GlassSelect from '../components/GlassSelect.vue'

function sortStateFromPreference(defaultSort = 'random') {
  return sortStateFromSortValue(defaultSort === 'none' ? 'random' : defaultSort)
}

export default {
  name: 'Search',
  components: { MovieCard, AppleSkeleton, AppleEmptyState, AppleErrorState, GlassSelect },
  data() {
    return {
      keyword: '',
      contentId: '',
      results: [],
      loading: false,
      searched: false,
      total: 0,
      searchError: null,

      // 筛选
      categoryName: '',
      categoryTags: [],
      categoryInput: '',
      makerName: '',
      seriesName: '',
      actressName: '',
      year: null,
      serviceCode: '',
      serviceCodeOptions: [
        { value: 'digital', label: '数字版' },
        { value: 'mono', label: '单体版' },
        { value: 'rental', label: '租赁版' },
        { value: 'ebook', label: '写真' },
      ],

      // 折叠更多筛选
      showMoreFilters: false,

      // 排序状态
      sortState: {
        release_date: null,
        title_ja: null,
        runtime_mins: null,
        random: true,
      },
      sortPills: [
        { key: 'release_date', label: '日期' },
        { key: 'title_ja', label: '标题' },
        { key: 'runtime_mins', label: '时长' },
        { key: 'random', label: '随机' },
      ],

      // 分页
      page: 1,
      pageSize: 30,
      totalPages: 1,
      jumpPage: null,
      isSearchFocused: false,
      isComposing: false,
      searchSettingsReady: false,
      appliedSearchPrefsKey: '',
      appliedConfigPageSize: null,
      expandedVariantGroups: {},
      searchSequence: createRequestSequence()
    }
  },
  computed: {
    searchState() {
      return {
        contentId: this.contentId,
        keyword: this.keyword,
        serviceCode: this.serviceCode,
        year: this.year,
        makerName: this.makerName,
        actressName: this.actressName,
        seriesName: this.seriesName,
        categoryTags: this.categoryTags,
        sort: sortValueFromSortState(this.sortState),
        page: this.page,
      }
    },
    hasFilters() {
      return Boolean(this.categoryTags.length || this.keyword || this.contentId || this.makerName || this.seriesName || this.actressName || this.year || this.serviceCode || this.hasSort)
    },
    hasSort() {
      return Object.values(this.sortState).some(v => v !== null && v !== false)
    },
    activeFilterChips() {
      return filterChipsFromSearchState(this.searchState)
    },
    versionOptions() {
      return [{ value: '', label: '全部版本' }, ...this.serviceCodeOptions]
    },
    totalLabel() {
      if (this.sortState.random) return '随机探索结果'
      if (this.total < 0) return '结果'
      return `共 ${this.total} 条`
    }
  },
  async mounted() {
    document.addEventListener('mousedown', this._onDocumentClick = (e) => {
      // 关闭高级筛选
      if (this.showMoreFilters) {
        const panel = this.$el?.querySelector('.advanced-panel')
        const toggle = this.$el?.querySelector('.filter-item.toggle')
        if ((!panel || !panel.contains(e.target)) && (!toggle || !toggle.contains(e.target))) {
          this.showMoreFilters = false
        }
      }
    })

    this.applySearchPreferences({ force: true })
    await this.loadConfiguredPageSize()

    this.searchSettingsReady = true
    if (!Object.keys(this.$route.query || {}).length) {
      this.replaceSearchRoute({ sort: sortValueFromSortState(this.sortState), page: 1 }, { replace: true })
      return
    }
    this.syncRouteQuery(this.$route.query)
    this.runSearchFromRoute()
  },
  async activated() {
    if (!this.searchSettingsReady) return
    const preferencesChanged = this.applySearchPreferences()
    const pageSizeChanged = await this.loadConfiguredPageSize()
    const routeChanged = this.syncRouteQuery(this.$route.query)
    if (routeChanged || ((preferencesChanged || pageSizeChanged) && (this.hasFilters || this.searched))) {
      this.runSearchFromRoute()
    }
  },
  beforeUnmount() {
    document.removeEventListener('mousedown', this._onDocumentClick)
    this.searchSequence.invalidate()
  },
  watch: {
    '$route.query'(q) {
      this.syncRouteQuery(q)
      if (this.searchSettingsReady) this.runSearchFromRoute()
    }
  },
  methods: {
    applySearchPreferences({ force = false } = {}) {
      const prefs = loadSearchPreferences()
      const prefsKey = JSON.stringify(prefs)
      if (!force && prefsKey === this.appliedSearchPrefsKey) return false
      if (!Object.keys(this.$route?.query || {}).length) {
        this.sortState = sortStateFromPreference(prefs.defaultSort)
        this.serviceCode = prefs.defaultServiceCode
      }
      this.appliedSearchPrefsKey = prefsKey
      return true
    },
    async loadConfiguredPageSize() {
      try {
        const resp = await api.getConfig()
        const ps = Number(resp.data?.javinfo?.page_size)
        if (ps && ps !== this.appliedConfigPageSize) {
          this.pageSize = ps
          this.appliedConfigPageSize = ps
          return true
        }
      } catch {}
      return false
    },
    syncRouteQuery(q = {}) {
      const next = parseSearchQuery(q)
      const nextSortState = sortStateFromSortValue(next.sort)
      let changed = false
      const assign = (key, value) => {
        if (this[key] !== value) {
          this[key] = value
          changed = true
        }
      }
      assign('contentId', next.contentId)
      assign('keyword', next.keyword)
      assign('serviceCode', next.serviceCode)
      assign('year', next.year)
      assign('makerName', next.makerName)
      assign('actressName', next.actressName)
      assign('seriesName', next.seriesName)
      assign('page', next.page)
      if (JSON.stringify(next.categoryTags) !== JSON.stringify(this.categoryTags)) {
        this.categoryTags = next.categoryTags
        changed = true
      }
      if (JSON.stringify(nextSortState) !== JSON.stringify(this.sortState)) {
        this.sortState = nextSortState
        changed = true
      }
      return changed
    },
    async loadFilters() {
      // categories now use category_name text input
    },

    clearFilters() {
      this.keyword = ''
      this.contentId = ''
      this.makerName = ''
      this.seriesName = ''
      this.actressName = ''
      this.categoryName = ''
      this.categoryTags = []
      this.categoryInput = ''
      this.year = null
      this.serviceCode = ''
      this.sortState = sortStateFromSortValue('random')
      this.results = []
      this.total = 0
      this.totalPages = 1
      this.page = 1
      this.jumpPage = null
      this.searched = false
      this.replaceSearchRoute({ sort: 'random', page: 1 }, { replace: true })
    },
    addCategoryTag() {
      const tag = this.categoryInput.trim()
      if (tag && !this.categoryTags.includes(tag)) {
        this.categoryTags.push(tag)
      }
      this.categoryInput = ''
    },
    handleCompositionEnd() {
      setTimeout(() => {
        this.isComposing = false
      }, 50)
    },
    handleCategoryKeydown(e) {
      if (this.isComposing || e.isComposing || e.keyCode === 229) return
      if (e.key === ' ' || e.key === 'Enter') {
        e.preventDefault()
        this.addCategoryTag()
      }
    },
    removeCategoryTag(idx) {
      this.categoryTags.splice(idx, 1)
      this.doSearch()
    },
    applyFilters() {
      this.showMoreFilters = false
      this.doSearch()
    },
    buildSearchParams(page) {
      return {
        ...buildSearchApiParams({ ...this.searchState, page }, { pageSize: this.pageSize }),
        variant_mode: 'grouped',
        include_variant_explanations: 1,
      }
    },
    replaceSearchRoute(patch = {}, { replace = false } = {}) {
      const query = searchQueryFromState({ ...this.searchState, ...patch })
      if (this.$route.query.returnTo) query.returnTo = this.$route.query.returnTo
      if (searchQueryEquals(this.$route.query || {}, query)) {
        this.runSearchFromRoute()
        return
      }
      const nav = replace ? this.$router.replace : this.$router.push
      nav.call(this.$router, { path: this.$route.path, query })
        .catch(() => {})
    },
    doSearch() {
      const patch = { page: 1 }
      if (sortValueFromSortState(this.sortState) === 'random' && searchHasUserConditions({ ...this.searchState, page: 1 })) {
        patch.sort = 'release_date_desc'
      }
      this.replaceSearchRoute(patch)
    },
    async runSearchFromRoute() {
      this.loading = true
      this.searched = true
      this.searchError = null
      const token = this.searchSequence.next()
      try {
        const resp = await api.searchVideos(this.buildSearchParams(this.page))
        if (!this.searchSequence.isCurrent(token)) return
        const data = resp.data
        this.results = data.data || []
        this.expandedVariantGroups = {}
        this.total = this.sortState.random ? -1 : (data.total_count ?? 0)
        this.totalPages = data.total_pages || 1
      } catch (e) {
        if (!this.searchSequence.isCurrent(token)) return
        console.error('Search failed:', e)
        this.searchError = api.formatApiError
          ? api.formatApiError(e, { service: 'JavInfo', action: '检索', fallback: '请检查 JavInfo 服务后重试。' })
          : { message: '检索失败，请稍后重试。', serviceLabel: 'JavInfo', status: e.response?.status || 0 }
        this.results = []
        this.total = 0
      } finally {
        if (this.searchSequence.isCurrent(token)) this.loading = false
      }
    },
    async goPage(p) {
      if (p < 1 || p > this.totalPages || p === this.page) return
      this.replaceSearchRoute({ page: p })
      window.scrollTo({ top: 0, behavior: 'smooth' })
    },
    doJumpPage() {
      if (!this.jumpPage) return
      const p = Math.max(1, Math.min(this.totalPages, this.jumpPage))
      this.jumpPage = null
      this.goPage(p)
    },
    cycleSort(key) {
      this.replaceSearchRoute({ sort: cycleSearchSort(sortValueFromSortState(this.sortState), key), page: 1 })
    },
    clearSort({ search = true } = {}) {
      this.sortState = sortStateFromSortValue('random')
      if (search) this.doSearch()
    },
    removeFilterChip(chip) {
      const patch = { page: 1 }
      if (chip.key === 'categoryTags') {
        patch.categoryTags = this.categoryTags.filter(tag => tag !== chip.value)
      } else {
        patch[chip.key] = chip.key === 'year' ? null : ''
      }
      this.replaceSearchRoute(canonicalizeSearchState({ ...this.searchState, ...patch }))
    },
    openModal(video) {
      openVideoModal(video, this.$route.fullPath || this.$route.path)
    },
    cardImageUrl(item) {
      return videoCardCoverUrl(item)
    },
    variantGroupKey,
    isVariantGroupExpanded(item) {
      const key = this.variantGroupKey(item)
      return Boolean(key && this.expandedVariantGroups[key])
    },
    toggleVariantGroup(item) {
      const key = this.variantGroupKey(item)
      if (!key) return
      this.expandedVariantGroups = {
        ...this.expandedVariantGroups,
        [key]: !this.expandedVariantGroups[key],
      }
    },
    variantGroupItems(item) {
      return visibleVariantItems(item)
    }
  }
}
</script>

<style scoped src="../features/search/search.css"></style>
