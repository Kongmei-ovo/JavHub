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

<style scoped>
/* ================================================
   ✨ 指令胶囊 (Command Capsule) - Search 2.0
   ================================================ */

.search-hero {
  padding: 76px 0 48px;
  background: var(--hero-background);
  text-align: center;
  transition: padding 0.3s ease;
}

.search-hero.compact {
  padding: 24px 0 20px;
}

.hero-intro {
  text-align: center;
}

.hero-title {
  color: var(--text-primary);
  font-size: var(--page-title-size);
  font-weight: var(--page-title-weight);
  line-height: var(--page-title-line);
  letter-spacing: 0;
  margin-bottom: 12px;
}

.hero-subtitle {
  font-size: var(--type-section-title);
  color: var(--text-secondary);
  margin-bottom: 44px;
  letter-spacing: -0.01em;
}

.hero-fade-enter-active { transition: all 0.3s ease; }
.hero-fade-leave-active { transition: all 0.2s ease; }
.hero-fade-enter-from, .hero-fade-leave-to { opacity: 0; transform: translateY(-10px); }

.command-capsule-container {
  --page-max: 800px;
  position: relative;
  z-index: 10;
}

/* 主胶囊容器 */
.command-capsule {
  display: flex;
  align-items: center;
  background: var(--material-glass-sheet);
  backdrop-filter: blur(var(--glass-blur-sheet)) saturate(var(--glass-saturate-surface));
  -webkit-backdrop-filter: blur(var(--glass-blur-sheet)) saturate(var(--glass-saturate-surface));
  border: 1px solid var(--border-light);
  border-radius: 999px;
  padding: 6px 6px 6px 24px;
  transition: all 0.5s var(--ease-pro);
  box-shadow: var(--shadow-floating);
}

.command-capsule.focused {
  background: var(--surface-input-focus);
  border-color: var(--accent);
  box-shadow: var(--glass-control-shadow-hover), 0 0 0 4px rgba(var(--accent-rgb), 0.12), var(--shadow-floating);
  transform: translateY(-1px);
}

.capsule-main {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 0;
}

.capsule-input {
  flex: 1;
  background: transparent;
  border: none;
  outline: none;
  color: var(--text-primary);
  font-size: var(--type-card-title);
  padding: 12px 10px;
  min-width: 0;
}

.capsule-input.primary {
  font-family: var(--font-mono);
  font-weight: 600;
  letter-spacing: -0.01em;
}

.capsule-divider {
  width: 1px;
  height: 18px;
  background: var(--border);
  margin: 0 12px;
}

.capsule-search-btn {
  background: var(--accent);
  color: var(--text-on-accent);
  border: none;
  border-radius: 50%;
  width: 44px;
  height: 44px;
  padding: 0;
  cursor: pointer;
  transition: all 0.3s var(--ease-pro);
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: none;
}

.capsule-search-btn:hover {
  background: var(--accent-light);
  transform: scale(1.04);
  box-shadow: 0 10px 24px rgba(var(--accent-rgb), 0.18);
}

.capsule-search-btn:active {
  transform: scale(0.9);
}

/* 筛选盘 (Filter Tray) */
/* ===== 排序 + 筛选条 ===== */
.sort-strip {
  --filter-control-height: 32px;
  --filter-control-radius: 16px;
  --filter-control-width: 112px;
  margin-top: 16px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.sort-strip-left {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.sort-strip-right {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.sort-strip-label {
  font-size: var(--type-caption);
  font-weight: 650;
  color: var(--text-muted);
  letter-spacing: 0;
}

.sort-result-count {
  font-size: var(--type-caption);
  color: var(--text-muted);
  white-space: nowrap;
  padding-right: 4px;
  border-right: 1px solid var(--border);
  margin-right: 4px;
}

.bar-divider {
  width: 1px;
  height: 20px;
  background: var(--border);
  flex-shrink: 0;
}

.sort-pills {
  display: flex;
  gap: 8px;
}

.sort-pill {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  min-height: var(--filter-control-height);
  width: 72px;
  padding: 0 12px;
  background: var(--surface-control);
  border: 1px solid var(--glass-control-border);
  border-radius: var(--filter-control-radius);
  color: var(--text-secondary);
  font-size: var(--type-control);
  font-weight: 500;
  cursor: pointer;
  transition: all 0.25s cubic-bezier(0.23, 1, 0.32, 1);
  user-select: none;
  box-shadow: var(--glass-control-shadow);
  backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
  -webkit-backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
}

.sort-pill:hover {
  background: var(--surface-control-hover);
  border-color: var(--glass-control-border-hover);
  color: var(--text-primary);
  box-shadow: var(--glass-control-shadow-hover);
}

.sort-pill.active {
  background: var(--active-bg);
  border-color: var(--active-border);
  color: var(--text-primary);
  box-shadow: var(--glass-active-shadow);
}

.sort-pill.active:hover {
  background: var(--surface-control-hover);
  border-color: var(--active-border);
}

.sort-pill.random.active {
  background: var(--active-bg);
  border-color: var(--active-border);
  color: var(--text-primary);
  box-shadow: var(--glass-active-shadow);
}

.sort-pill.random.active:hover {
  background: var(--surface-control-hover);
  border-color: var(--active-border);
}

.pill-label {
  line-height: 1;
}

.pill-arrow {
  opacity: 0.8;
  flex-shrink: 0;
}

.pill-check {
  opacity: 0.8;
  flex-shrink: 0;
}

.sort-clear-btn {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: var(--surface-control);
  border: 1px solid var(--glass-control-border);
  color: var(--text-muted);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s cubic-bezier(0.23, 1, 0.32, 1);
  padding: 0;
  flex-shrink: 0;
  box-shadow: var(--glass-control-shadow);
  backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
  -webkit-backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
}

.sort-clear-btn:hover {
  background: rgba(255, 55, 95, 0.1);
  border-color: rgba(255, 55, 95, 0.3);
  color: #FF375F;
}

.filter-item {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  width: var(--filter-control-width);
  min-height: var(--filter-control-height);
  background: var(--surface-control);
  border: 1px solid var(--glass-control-border);
  border-radius: var(--filter-control-radius);
  padding: 0 12px;
  color: var(--text-secondary);
  font-size: var(--type-caption);
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s var(--ease-pro);
  white-space: nowrap;
  box-shadow: var(--glass-control-shadow);
  backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
  -webkit-backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
}

.filter-item:hover {
  background: var(--surface-control-hover);
  border-color: var(--glass-control-border-hover);
  box-shadow: var(--glass-control-shadow-hover);
}

.filter-item.toggle.active {
  background: var(--active-bg);
  border-color: var(--active-border);
  color: var(--text-primary);
  box-shadow: var(--glass-active-shadow);
}

.version-filter {
  width: var(--filter-control-width);
  min-width: var(--filter-control-width);
  --glass-select-height: var(--filter-control-height);
  --glass-select-padding: 0 12px;
  --glass-select-font: 12px;
  --glass-select-radius: var(--filter-control-radius);
}

.applied-filter-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: center;
  margin-top: 12px;
}

.applied-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  min-height: 32px;
  max-width: min(100%, 280px);
  padding: 0 10px 0 12px;
  border: 1px solid var(--glass-control-border);
  border-radius: 999px;
  background: var(--surface-control);
  color: var(--text-secondary);
  font-size: var(--type-caption);
  cursor: pointer;
  transition: transform var(--motion-standard), background var(--motion-standard), border-color var(--motion-standard), box-shadow var(--motion-standard), color var(--motion-fast);
  box-shadow: var(--glass-control-shadow);
  backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
  -webkit-backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
}

.applied-chip:hover {
  border-color: var(--glass-control-border-hover);
  background: var(--surface-control-hover);
  color: var(--text-primary);
  transform: translateY(-1px);
  box-shadow: var(--glass-control-shadow-hover);
}

.applied-chip span {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.applied-chip b {
  flex-shrink: 0;
  color: var(--text-muted);
  font-size: 14px;
  line-height: 1;
}

/* 高级面板 (Advanced Panel) - 绝对定位消除重排 */
.advanced-panel {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  margin-top: 16px;
  background: var(--material-glass-sheet);
  backdrop-filter: blur(var(--glass-blur-sheet)) saturate(var(--glass-saturate-surface));
  -webkit-backdrop-filter: blur(var(--glass-blur-sheet)) saturate(var(--glass-saturate-surface));
  border: 1px solid var(--border-light);
  border-radius: var(--radius-card);
  padding: 32px;
  box-shadow: var(--shadow-sheet);
  z-index: var(--z-sheet);
  transform: translateZ(0);
  animation: panelEntry 0.5s var(--ease-pro) both;
}

@keyframes panelEntry {
  from { opacity: 0; transform: translateY(-10px) scale(0.98) translateZ(0); }
  to { opacity: 1; transform: translateY(0) scale(1) translateZ(0); }
}

.panel-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 24px;
  text-align: left;
}

.panel-field {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.panel-field.full { grid-column: span 2; }

.panel-field label {
  font-size: var(--type-caption);
  font-weight: 650;
  color: var(--text-muted);
  letter-spacing: 0;
  padding-left: 4px;
}

.panel-input {
  background: var(--surface-input);
  border: 1px solid var(--glass-control-border);
  border-radius: 12px;
  padding: 12px 16px;
  color: var(--text-primary);
  font-size: var(--type-body);
  transition: all 0.3s var(--ease-pro);
  box-shadow: var(--glass-control-shadow);
  backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
  -webkit-backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
}

.panel-input:focus {
  border-color: var(--accent);
  background: var(--surface-input-focus);
  outline: none;
  box-shadow: var(--glass-control-shadow), 0 0 0 4px rgba(var(--accent-rgb), 0.12);
}

.panel-tag-input {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.tray-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.tray-tag {
  background: var(--surface-control);
  border: 1px solid var(--glass-control-border);
  color: var(--text-primary);
  padding: 4px 12px;
  border-radius: 12px;
  font-size: var(--type-caption);
  display: flex;
  align-items: center;
  gap: 6px;
  box-shadow: var(--glass-control-shadow);
  backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
  -webkit-backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
}

.tray-tag b {
  cursor: pointer;
  opacity: 0.5;
  font-size: 14px;
}
.tray-tag b:hover { opacity: 1; }

.panel-footer {
  margin-top: 32px;
  padding-top: 24px;
  border-top: 1px solid var(--border);
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

.btn-clear {
  background: var(--surface-control);
  border: 1px solid var(--glass-control-border);
  color: var(--text-primary);
  padding: 10px 24px;
  border-radius: 12px;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.3s var(--ease-pro);
  box-shadow: var(--glass-control-shadow);
  backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
  -webkit-backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
}

.btn-clear:hover {
  background: var(--surface-control-hover);
  color: var(--text-primary);
  border-color: var(--glass-control-border-hover);
  box-shadow: var(--glass-control-shadow-hover);
}

.btn-apply {
  background: var(--accent);
  color: var(--text-on-accent);
  border: none;
  padding: 10px 36px;
  border-radius: var(--radius-control);
  font-weight: 650;
  cursor: pointer;
  font-size: 14px;
  box-shadow: none;
  transition: all 0.3s var(--ease-pro);
}

.btn-apply:hover {
  transform: translateY(-1px);
  background: var(--accent-light);
  box-shadow: 0 10px 24px rgba(var(--accent-rgb), 0.18);
}

/* 极速响应动效 */
.tray-slide-enter-active {
  transition: all 0.4s var(--ease-pro);
}

.tray-slide-leave-active {
  transition: all 0.15s cubic-bezier(0.4, 0, 1, 1);
  pointer-events: none;
}

.tray-slide-enter-from,
.tray-slide-leave-to {
  opacity: 0;
  transform: translateY(-16px) scale(0.99) translateZ(0);
}

/* 结果网格样式同步 2.0 */
.results-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 30px;
  padding-block: 40px;
}

.result-card-group {
  min-width: 0;
}

.variant-expand-btn {
  width: 100%;
  margin-top: 8px;
  min-height: 32px;
  border: 1px solid var(--glass-control-border);
  border-radius: var(--radius-control);
  background: var(--material-glass-control);
  color: var(--text-secondary);
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  box-shadow: var(--glass-control-shadow);
  backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
  -webkit-backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
  transition: transform var(--motion-standard), background var(--motion-standard), border-color var(--motion-standard), box-shadow var(--motion-standard), color var(--motion-fast), opacity var(--motion-fast);
}

.variant-expand-btn:hover {
  border-color: var(--glass-control-border-hover);
  color: var(--text-primary);
  background: var(--material-glass-control-hover);
  box-shadow: var(--glass-control-shadow-hover);
  transform: translateY(-1px);
}

.variant-expand-btn:active {
  transform: translateY(0) scale(0.99);
}

.variant-expand-btn:focus-visible,
.variant-inline-item:focus-visible {
  outline: none;
  box-shadow: var(--glass-control-shadow), 0 0 0 4px rgba(var(--accent-rgb), 0.14);
}

.variant-inline-list {
  display: grid;
  gap: 6px;
  margin-top: 8px;
}

.variant-inline-item {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: center;
  gap: 8px;
  min-height: 34px;
  padding: 6px 8px;
  border: 1px solid var(--glass-control-border);
  border-radius: var(--radius-md);
  background: var(--material-glass-control);
  color: var(--text-secondary);
  cursor: pointer;
  box-shadow: var(--glass-control-shadow);
  backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
  -webkit-backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
  transition: transform var(--motion-standard), background var(--motion-standard), border-color var(--motion-standard), box-shadow var(--motion-standard), color var(--motion-fast), opacity var(--motion-fast);
}

.variant-inline-item:hover {
  border-color: var(--glass-control-border-hover);
  background: var(--material-glass-control-hover);
  color: var(--text-primary);
  transform: translateY(-1px);
  box-shadow: var(--glass-control-shadow-hover);
}

.variant-inline-item:active {
  transform: translateY(0) scale(0.99);
}

.variant-inline-code {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-family: var(--font-mono);
  font-size: 12px;
  font-weight: 650;
}

.variant-inline-labels {
  display: inline-flex;
  gap: 4px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.variant-inline-labels span {
  padding: 1px 5px;
  border-radius: 999px;
  background: var(--badge-info-bg);
  border: 1px solid var(--badge-info-border);
  color: var(--badge-info-text);
  font-size: 10px;
  font-weight: 650;
}

.pagination-bar {
  padding-block: 12px;
}

.page-info {
  font-size: 13px;
  color: var(--text-muted);
}

.empty-state {
  text-align: center;
  padding: 60px 20px;
  color: var(--text-muted);
}

.pagination {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 16px;
  padding: 20px;
}

.pagination-bar {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 8px;
  padding-block: 16px;
}

.page-btn {
  background: var(--material-glass-control);
  border: 1px solid var(--glass-control-border);
  color: var(--text-primary);
  padding: 6px 12px;
  border-radius: var(--radius-control);
  cursor: pointer;
  font-size: 13px;
  box-shadow: var(--glass-control-shadow);
  backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
  -webkit-backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
  transition: transform var(--motion-standard), background var(--motion-standard), border-color var(--motion-standard), box-shadow var(--motion-standard), color var(--motion-fast), opacity var(--motion-fast);
}
.page-btn:hover:not(:disabled) {
  border-color: var(--glass-control-border-hover);
  color: var(--text-primary);
  background: var(--material-glass-control-hover);
  box-shadow: var(--glass-control-shadow-hover);
  transform: translateY(-1px);
}
.page-btn:active:not(:disabled) { transform: translateY(0) scale(0.99); }
.page-btn:disabled { opacity: 0.4; cursor: not-allowed; }

.page-indicator { font-size: 13px; color: var(--text-secondary); padding: 0 4px; }

.jump-wrap { display: flex; align-items: center; gap: 4px; margin-left: 12px; }
.jump-input {
  width: 56px;
  padding: 6px 8px;
  border: 1px solid var(--glass-control-border);
  border-radius: var(--radius-control);
  background: var(--material-glass-control);
  color: var(--text-primary);
  font-size: 12px;
  text-align: center;
  box-shadow: var(--glass-control-shadow);
  backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
  -webkit-backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
  transition: background var(--motion-standard), border-color var(--motion-standard), box-shadow var(--motion-standard), color var(--motion-fast), opacity var(--motion-fast);
}
.jump-input:focus {
  outline: none;
  border-color: var(--glass-control-border-hover);
  background: var(--material-glass-control-hover);
  box-shadow: var(--glass-control-shadow), 0 0 0 4px rgba(var(--accent-rgb), 0.12);
}
.jump-input::-webkit-inner-spin-button,
.jump-input::-webkit-outer-spin-button { -webkit-appearance: none; }
.jump-btn {
  background: var(--material-glass-control);
  border: 1px solid var(--glass-control-border);
  color: var(--text-primary);
  padding: 6px 14px;
  border-radius: var(--radius-control);
  cursor: pointer;
  font-size: 12px;
  box-shadow: var(--glass-control-shadow);
  backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
  -webkit-backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
  transition: transform var(--motion-standard), background var(--motion-standard), border-color var(--motion-standard), box-shadow var(--motion-standard), color var(--motion-fast), opacity var(--motion-fast);
}
.jump-btn:hover {
  border-color: var(--glass-control-border-hover);
  color: var(--text-primary);
  background: var(--material-glass-control-hover);
  box-shadow: var(--glass-control-shadow-hover);
  transform: translateY(-1px);
}
.jump-btn:active { transform: translateY(0) scale(0.99); }

.page-info {
  font-size: 13px;
  color: var(--text-muted);
}

.spinner {
  display: inline-block;
  width: 16px;
  height: 16px;
  border: 2px solid rgba(255,255,255,0.35);
  border-top-color: var(--text-on-accent);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* ===== Mobile Responsive ===== */
@media (max-width: 768px) {
  .search-hero {
    padding: 44px 0 30px;
  }
  .search-hero.compact {
    padding: 20px 0 18px;
  }
  .results-grid {
    grid-template-columns: repeat(auto-fit, minmax(var(--video-grid-min-mobile), 1fr));
    gap: var(--video-grid-gap-mobile) !important;
    padding-block: 20px;
    padding-inline: 0;
  }
  .panel-grid {
    grid-template-columns: 1fr;
  }
  .panel-field.full {
    grid-column: span 1;
  }
  .hero-title {
    font-size: var(--page-title-size-mobile);
  }
  .command-capsule {
    align-items: stretch;
    gap: 8px;
    padding: 8px;
    border-radius: 24px;
  }
  .capsule-main {
    min-width: 0;
    flex-direction: column;
    align-items: stretch;
    gap: 2px;
  }
  .capsule-divider {
    width: auto;
    height: 1px;
    margin: 0 8px;
  }
  .capsule-input {
    min-height: 44px;
    padding: 10px 12px;
  }
  .capsule-search-btn {
    width: 50px;
    height: auto;
    min-height: 96px;
    flex-shrink: 0;
    border-radius: 18px;
  }
  .sort-strip {
    --filter-control-height: 44px;
    --filter-control-radius: 18px;
    --filter-control-width: min(160px, 46vw);
    flex-direction: column;
    align-items: stretch;
    gap: 10px;
  }
  .sort-strip-left, .sort-strip-right {
    justify-content: center;
  }
  .sort-strip-right .version-filter {
    width: var(--filter-control-width);
    min-width: var(--filter-control-width);
    --glass-select-padding: 0 12px;
  }
  .sort-strip-left {
    align-items: center;
  }
  .sort-pills {
    flex-wrap: wrap;
    justify-content: center;
  }
  .sort-pill,
  .filter-item,
  .sort-clear-btn {
    min-height: var(--compact-toolbar-height);
  }
  .sort-clear-btn {
    width: 44px;
  }
  .applied-filter-row {
    justify-content: flex-start;
  }
  .applied-chip {
    min-height: 38px;
  }
  .advanced-panel {
    position: static;
    margin-top: 12px;
    padding: 18px;
    border-radius: 18px;
  }
  .variant-inline-item {
    grid-template-columns: 1fr;
    align-items: stretch;
    gap: 6px;
    padding: 8px;
  }
  .variant-inline-labels {
    justify-content: flex-start;
  }
  .panel-footer {
    margin-top: 20px;
    padding-top: 16px;
  }
  .btn-clear,
  .btn-apply {
    min-height: 44px;
    flex: 1;
  }
  .pagination-bar {
    flex-wrap: wrap;
  }
  .page-btn,
  .jump-btn {
    min-width: 44px;
    min-height: 44px;
  }
  .jump-input {
    min-height: 44px;
  }
}
</style>
