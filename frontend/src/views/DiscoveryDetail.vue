<template>
  <div class="genre-detail-page page-bleed">
    <!-- 顶部工具栏 -->
    <div class="toolbar page-rail page-rail--gallery">
      <div class="toolbar-left">
        <button class="back-btn" type="button" @click="handleBack">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="14" height="14">
            <polyline points="15 18 9 12 15 6"/>
          </svg>
          {{ isFromVideo ? '返回详情' : '返回' }}
        </button>
        <h2 class="category-title">
          <span class="type-label">{{ typeLabel }}发现:</span>
          {{ displayNameValue || value }}
        </h2>
        <button
          class="entity-fav-btn"
          type="button"
          :class="{ 'is-active': isEntityFavorited }"
          @click="toggleEntityFavorite"
          :title="isEntityFavorited ? '取消收藏' : '收藏'"
        >
          <svg viewBox="0 0 24 24" width="16" height="16">
            <path v-if="isEntityFavorited" d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z" fill="currentColor"/>
            <path v-else d="M16.5 3c-1.74 0-3.41.81-4.5 2.09C10.91 3.81 9.24 3 7.5 3 4.42 3 2 5.42 2 8.5c0 3.78 3.4 6.86 8.55 11.54L12 21.35l1.45-1.32C18.6 15.36 22 12.28 22 8.5 22 5.42 19.58 3 16.5 3zm-4.4 15.55l-.1.1-.1-.1C7.14 14.24 4 11.39 4 8.5 4 6.5 5.5 5 7.5 5c1.54 0 3.04.99 3.57 2.36h1.87C13.46 5.99 14.96 5 16.5 5c2 0 3.5 1.5 3.5 3.5 0 2.89-3.14 5.74-7.9 10.05z" fill="currentColor"/>
          </svg>
        </button>
        <button
          v-if="type === 'actress'"
          class="entity-sub-btn"
          type="button"
          :class="{ 'is-active': isEntitySubscribed }"
          @click="toggleEntitySubscription"
          :title="isEntitySubscribed ? '取消订阅' : '订阅'"
        >
          <svg viewBox="0 0 24 24" width="16" height="16">
            <path v-if="isEntitySubscribed" d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z" fill="currentColor"/>
            <path v-else d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.42 0-8-3.58-8-8s3.58-8 8-8 8 3.58 8 8-3.58 8-8 8zm-1-4h2v2h-2v-2zm0-2h2V7h-2v7z" fill="currentColor"/>
          </svg>
        </button>
      </div>
    </div>

    <!-- 排序 + 版本筛选栏 -->
    <div class="result-bar page-rail page-rail--gallery">
      <div class="result-bar-left">
        <span class="result-count">{{ loading ? '加载中...' : `${total} 个结果` }}</span>
        <div class="sort-pills">
          <button
            v-for="pill in sortPills"
            :key="pill.key"
            class="sort-pill"
            :class="{ active: sortState[pill.key] !== null, random: pill.key === 'random' && sortState.random }"
            type="button"
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
      </div>
      <div class="result-bar-right">
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
        <button class="chronicle-btn" type="button" :class="{ active: chronicleMode }" @click="toggleChronicle" title="年份编年视图">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="14" height="14">
            <rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/>
          </svg>
          编年
        </button>
      </div>
    </div>

    <!-- 分页（顶部） -->
    <div v-if="totalPages > 1" class="pagination-bar page-rail page-rail--gallery">
      <button class="page-btn" :disabled="page <= 1" @click="goPage(1)">«</button>
      <button class="page-btn" :disabled="page <= 1" @click="goPage(page - 1)">‹</button>
      <span class="page-indicator">{{ page }} / {{ totalPages }}</span>
      <button class="page-btn" :disabled="page >= totalPages" @click="goPage(page + 1)">›</button>
      <button class="page-btn" :disabled="page >= totalPages" @click="goPage(totalPages)">»</button>
    </div>

    <!-- 加载骨架屏 -->
    <div v-if="loading" class="skeleton-grid page-rail page-rail--gallery">
      <AppleSkeleton v-for="n in 12" :key="n" variant="card" />
    </div>

    <!-- 结果网格：年份编年模式 -->
    <template v-else-if="results.length > 0 && isChronicle">
      <div v-for="(group, year) in groupedByYear" :key="year" class="year-section">
        <div class="year-header page-rail page-rail--gallery">{{ year === 'null' ? '未知' : year }}</div>
        <div class="results-grid page-rail page-rail--gallery">
          <MovieCard
            v-for="item in group"
            :key="item.content_id || item.dvd_id"
            :contentId="item.dvd_id || item.content_id"
            :coverUrl="cardImageUrl(item)"
            :title="item.title_en_translated || item.title_ja_translated || item.title_en || item.title_ja || ''"
            :releaseDate="item.release_date || ''"
            :runtimeMins="item.runtime_mins || ''"
            @click="openModal(item)"
          />
        </div>
      </div>
    </template>

    <!-- 结果网格：普通模式 -->
    <div v-else-if="results.length > 0" class="results-grid page-rail page-rail--gallery">
      <MovieCard
        v-for="item in results"
        :key="item.content_id || item.dvd_id"
        :contentId="item.dvd_id || item.content_id"
        :coverUrl="cardImageUrl(item)"
        :title="item.title_en_translated || item.title_ja_translated || item.title_en || item.title_ja || ''"
        :releaseDate="item.release_date || ''"
        :runtimeMins="item.runtime_mins || ''"
        @click="openModal(item)"
      />
    </div>

    <!-- 空状态 -->
    <AppleEmptyState
      v-else-if="searched && !loading"
      class="page-rail page-rail--standard"
      title="暂无相关影片"
      description="这个分类暂时没有匹配影片，可以返回推荐页换一个入口。"
      action-label="返回"
      @action="handleBack"
    />

    <!-- 分页（底部） -->
    <div v-if="totalPages > 1" class="pagination-bar bottom page-rail page-rail--gallery">
      <button class="page-btn" :disabled="page <= 1" @click="goPage(1)">«</button>
      <button class="page-btn" :disabled="page <= 1" @click="goPage(page - 1)">‹</button>
      <span class="page-indicator">{{ page }} / {{ totalPages }}</span>
      <button class="page-btn" :disabled="page >= totalPages" @click="goPage(page + 1)">›</button>
      <button class="page-btn" :disabled="page >= totalPages" @click="goPage(totalPages)">»</button>
    </div>
  </div>
</template>

<script>
import api from '../api'
import { displayName } from '../utils/displayLang.js'
import { videoCardCoverUrl } from '../utils/imageUrl.js'
import { modalState, openVideoModal } from '../utils/modalState'
import { favoriteState } from '../utils/favoriteState'
import subscriptionState from '../utils/subscriptionState'
import { createRequestSequence } from '../utils/requestSequence.js'
import MovieCard from '../components/MovieCard.vue'
import AppleSkeleton from '../components/AppleSkeleton.vue'
import AppleEmptyState from '../components/AppleEmptyState.vue'
import GlassSelect from '../components/GlassSelect.vue'

const PAGE_SIZE = 30

export default {
  name: 'DiscoveryDetail',
  components: { MovieCard, AppleSkeleton, AppleEmptyState, GlassSelect },
  data() {
    return {
      metadata: [], // 缓存列表数据用于显示显示名
      sortState: {
        release_date: null,
        title_ja: null,
        runtime_mins: null,
        random: true,
      },
      sortPills: [
        { key: 'random', label: '随机' },
        { key: 'release_date', label: '日期' },
        { key: 'title_ja', label: '标题' },
        { key: 'runtime_mins', label: '时长' },
      ],
      chronicleMode: false,
      serviceCode: '',
      serviceCodeOptions: [
        { value: 'digital', label: '数字版' },
        { value: 'mono', label: '单体版' },
        { value: 'rental', label: '租赁版' },
        { value: 'ebook', label: '写真' },
      ],
      results: [],
      loading: false,
      searched: false,
      page: 1,
      total: 0,
      totalPages: 1,
      searchSequence: createRequestSequence()
    }
  },
  beforeUnmount() {
    this.searchSequence.invalidate()
  },
  computed: {
    type() { return this.$route.params.type },
    value() { return this.$route.params.value },
    typeLabel() {
      const map = { category: '题材', maker: '工作室', series: '系列', actress: '演员' }
      return map[this.type] || '内容'
    },
    displayNameValue() {
      // 优先使用 query 传来的名称（从 Genres 页跳转时携带）
      if (this.$route.query.name) return this.$route.query.name
      if (this.type === 'category' && this.metadata.length) {
        const cat = this.metadata.find(c => c.id === parseInt(this.value))
        return cat ? (displayName(cat, 'name_ja', 'name_en') || cat.name) : ''
      }
      // 其他类型直接显示 value (名称)
      return this.value
    },
    versionOptions() {
      return [{ value: '', label: '全部版本' }, ...this.serviceCodeOptions]
    },
    isChronicle() {
      return this.chronicleMode
    },
    isFromVideo() {
      return modalState.interrupted || this.$route.query.returnTo === 'video'
    },
    isEntityFavorited() {
      return favoriteState.isFavorited(this.type, this.value)
    },
    isEntitySubscribed() {
      if (this.type !== 'actress') return false
      return subscriptionState.isSubscribed(this.value)
    },
    groupedByYear() {
      const groups = {}
      for (const item of this.results) {
        const yearKey = item.release_date ? String(item.release_date.slice(0, 4)) : 'null'
        if (!groups[yearKey]) groups[yearKey] = []
        groups[yearKey].push(item)
      }
      return Object.keys(groups)
        .sort((a, b) => {
          if (a === 'null') return 1
          if (b === 'null') return -1
          return this.sortValue === 'year_chronicle_asc' ? a.localeCompare(b) : b.localeCompare(a)
        })
        .reduce((acc, key) => { acc[key] = groups[key]; return acc }, {})
    }
  },
  async mounted() {
    subscriptionState.init()
    if (this.type === 'category') {
      await this.loadMetadata()
    }
    this.doSearch()
  },
  watch: {
    '$route.params'() {
      this.resetFilters()
      this.doSearch()
    }
  },
  methods: {
    cycleSort(key) {
      if (key === 'random') {
        this.sortState.random = !this.sortState.random
        if (this.sortState.random) {
          this.sortState.release_date = null
          this.sortState.title_ja = null
          this.sortState.runtime_mins = null
        }
      } else {
        const cycle = { null: 'desc', desc: 'asc', asc: null }
        this.sortState[key] = cycle[this.sortState[key]]
        if (this.sortState[key] !== null) this.sortState.random = false
      }
      this.doSearch()
    },
    toggleChronicle() {
      this.chronicleMode = !this.chronicleMode
      if (this.chronicleMode && this.sortState.random) {
        this.sortState.random = false
        this.sortState.release_date = 'asc'
      }
      this.doSearch()
    },
    handleBack() { this.$router.back() },
    async toggleEntityFavorite() {
      try {
        await favoriteState.toggle(this.type, this.value)
      } catch (err) {
        console.error('Toggle entity favorite failed:', err)
      }
    },
    async toggleEntitySubscription() {
      if (this.type !== 'actress') return
      const subscribed = await subscriptionState.toggle(this.value, this.displayNameValue || this.value)
      if (this.$message) {
        this.$message[subscribed ? 'success' : 'info'](
          subscribed ? `已订阅 ${this.displayNameValue || this.value}` : '已取消订阅'
        )
      }
    },
    async loadMetadata() {
      try {
        if (this.type === 'category') {
          const resp = await api.listCategories()
          this.metadata = Array.isArray(resp.data) ? resp.data : (resp.data.data || [])
        }
      } catch (e) { console.error('Load metadata failed:', e) }
    },
    resetFilters() {
      this.sortState = { release_date: null, title_ja: null, runtime_mins: null, random: true }
      this.chronicleMode = false
      this.serviceCode = ''
      this.page = 1
    },
    buildParams() {
      const params = { page: this.page, page_size: PAGE_SIZE }
      if (this.serviceCode) params.service_code = this.serviceCode

      // 根据类型填充参数：支持 ID (数字) 和名称 (字符串)
      const v = this.value
      const isNumeric = /^\d+$/.test(v)
      if (this.type === 'category') {
        params.category_id = isNumeric ? parseInt(v) : undefined
        if (!isNumeric) params.category_name = v
      } else if (this.type === 'maker') {
        if (isNumeric) params.maker_id = parseInt(v); else params.maker_name = v
      } else if (this.type === 'series') {
        if (isNumeric) params.series_id = parseInt(v); else params.series_name = v
      } else if (this.type === 'actress') {
        if (isNumeric) params.actress_id = parseInt(v); else params.actress_name = v
      }

      if (this.sortState.random) {
        params.random = '1'
      } else {
        const sortParts = []
        for (const [field, dir] of Object.entries(this.sortState)) {
          if (field === 'random' || dir === null) continue
          sortParts.push(`${field}:${dir}`)
        }
        if (sortParts.length > 0) params.sort_by = sortParts.join(',')
        if (this.chronicleMode && !params.sort_by) params.sort_by = 'release_date:asc'
      }
      return params
    },
    async doSearch() {
      this.loading = true
      this.searched = true
      this.page = 1
      const token = this.searchSequence.next()
      try {
        const resp = await api.searchVideos(this.buildParams())
        if (!this.searchSequence.isCurrent(token)) return
        this.results = resp.data.data || []
        this.total = resp.data.total_count || 0
        this.totalPages = resp.data.total_pages || 1
      } catch (e) {
        if (!this.searchSequence.isCurrent(token)) return
        console.error('Search failed:', e)
        this.results = []; this.total = 0
      } finally {
        if (this.searchSequence.isCurrent(token)) this.loading = false
      }
    },
    async refresh() { this.doSearch() },
    async goPage(p) {
      if (p < 1 || p > this.totalPages) return
      this.page = p
      this.loading = true
      const token = this.searchSequence.next()
      try {
        const resp = await api.searchVideos(this.buildParams())
        if (!this.searchSequence.isCurrent(token)) return
        this.results = resp.data.data || []
        window.scrollTo({ top: 0, behavior: 'smooth' })
      } catch (e) {
        if (!this.searchSequence.isCurrent(token)) return
        console.error('Page change failed:', e)
      } finally {
        if (this.searchSequence.isCurrent(token)) this.loading = false
      }
    },
    openModal(video) {
      openVideoModal(video, this.$route.path)
    },
    cardImageUrl(item) { return videoCardCoverUrl(item) }
  }
}
</script>

<style scoped>
.genre-detail-page { min-height: 100dvh; background: var(--bg-primary); }
.toolbar { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding-block: 12px; border-bottom: 1px solid var(--border); flex-wrap: wrap; }
.toolbar-left { display: flex; align-items: center; gap: 12px; flex: 1; min-width: 0; }
.back-btn { display: flex; align-items: center; gap: 4px; min-height: 44px; background: none; border: 1px solid var(--border); color: var(--text-secondary); font-size: 13px; cursor: pointer; padding: 6px 12px; border-radius: var(--radius-sm); transition: var(--transition); flex-shrink: 0; }
.back-btn:hover { border-color: var(--border-light); color: var(--text-primary); }
.entity-fav-btn {
  width: 44px; height: 44px; border-radius: 50%; background: var(--surface-card);
  border: 1px solid var(--border); display: flex; align-items: center; justify-content: center;
  color: var(--text-muted); cursor: pointer; transition: all 0.2s cubic-bezier(0.23, 1, 0.32, 1);
  flex-shrink: 0; padding: 0;
}
.entity-fav-btn:hover { border-color: var(--border-light); color: var(--text-primary); background: var(--bg-card-hover); }
.entity-fav-btn.is-active { color: #FF375F; border-color: rgba(255, 55, 95, 0.3); background: rgba(255, 55, 95, 0.1); }
.entity-fav-btn.is-active:hover { background: rgba(255, 55, 95, 0.2); }
.entity-sub-btn {
  background: none;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  padding: 6px 8px;
  min-width: 44px;
  min-height: 44px;
  cursor: pointer;
  color: var(--text-muted);
  display: flex;
  align-items: center;
  transition: all 0.2s;
  margin-left: 6px;
}
.entity-sub-btn:hover {
  border-color: var(--border-light);
  color: var(--text-primary);
}
.entity-sub-btn.is-active {
  background: var(--active-bg);
  border-color: var(--active-border);
  color: var(--text-primary);
  box-shadow: inset 0 -2px 0 var(--active-indicator);
}
.category-title { font-size: 18px; font-weight: 700; color: var(--text-primary); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.type-label { font-size: 14px; color: var(--text-muted); margin-right: 8px; font-weight: normal; }
.result-bar { --filter-control-height: 32px; --filter-control-radius: 16px; --filter-control-width: 112px; display: flex; align-items: center; justify-content: space-between; padding-block: 12px; position: relative; z-index: var(--z-raised); }
.result-bar-left { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.result-bar-right { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; justify-content: flex-end; min-width: 0; }
.bar-divider { width: 1px; height: 20px; background: var(--border); flex-shrink: 0; }
.sort-pills { display: flex; gap: 8px; }
.sort-pill {
  display: inline-flex; align-items: center; justify-content: center; gap: 4px;
  min-height: var(--filter-control-height); width: 72px;
  padding: 0 12px; background: var(--surface-control); border: 1px solid transparent;
  border-radius: var(--filter-control-radius); color: var(--text-secondary); font-size: 13px; font-weight: 500;
  cursor: pointer; transition: all 0.25s cubic-bezier(0.23,1,0.32,1); user-select: none;
}
.sort-pill:hover { background: var(--surface-control-hover); border-color: var(--border-light); color: var(--text-primary); }
.sort-pill.active,
.sort-pill.random.active { background: var(--active-bg); border-color: var(--active-border); color: var(--text-primary); box-shadow: inset 0 -2px 0 var(--active-indicator); }
.sort-pill.active:hover,
.sort-pill.random.active:hover { background: var(--surface-control-hover); border-color: var(--active-border); }
.pill-label { line-height: 1; }
.pill-arrow, .pill-check { opacity: 0.8; flex-shrink: 0; }
.chronicle-btn {
  display: inline-flex; align-items: center; justify-content: center; gap: 6px;
  width: var(--filter-control-width); min-height: var(--filter-control-height);
  padding: 0 12px; background: var(--surface-control); border: 1px solid var(--border);
  border-radius: var(--filter-control-radius); color: var(--text-muted); font-size: 12px; font-weight: 600;
  cursor: pointer; transition: all 0.25s; user-select: none;
}
.chronicle-btn:hover { background: var(--surface-control-hover); color: var(--text-secondary); }
.chronicle-btn.active { background: var(--active-bg); border-color: var(--active-border); color: var(--text-primary); box-shadow: inset 0 -2px 0 var(--active-indicator); }
.result-count { font-size: 13px; color: var(--text-secondary); white-space: nowrap; }
.version-filter {
  width: var(--filter-control-width);
  min-width: var(--filter-control-width);
  --glass-select-height: var(--filter-control-height);
  --glass-select-padding: 0 12px;
  --glass-select-font: 12px;
  --glass-select-radius: var(--filter-control-radius);
}
.shuffle-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  background: var(--surface-card);
  border: 1px solid var(--border);
  color: var(--text-secondary);
  font-size: 13px;
  cursor: pointer;
  padding: 8px 16px;
  border-radius: var(--radius-md);
  transition: var(--transition-pro);
  flex-shrink: 0;
  backdrop-filter: blur(10px);
}
.shuffle-btn:hover:not(:disabled) {
  border-color: var(--border-light);
  color: var(--text-primary);
  background: var(--bg-card-hover);
}
.shuffle-btn:disabled { opacity: 0.5; cursor: not-allowed; }
.pagination-bar { display: flex; justify-content: center; align-items: center; gap: 8px; padding-block: 12px; }
.pagination-bar.bottom { border-top: 1px solid var(--border); }
.page-btn {
  background: var(--surface-card);
  border: 1px solid var(--border);
  color: var(--text-primary);
  padding: 6px 12px;
  border-radius: var(--radius-md);
  cursor: pointer;
  font-size: 13px;
  transition: var(--transition-pro);
  backdrop-filter: blur(10px);
}
.page-btn:hover:not(:disabled) {
  border-color: var(--border-light);
  color: var(--text-primary);
  background: var(--bg-card-hover);
}
.page-btn:disabled { opacity: 0.4; cursor: not-allowed; }
.page-indicator { font-size: 13px; color: var(--text-secondary); padding: 0 4px; }
.skeleton-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: 20px; padding-block: 20px; }
.year-section { margin-bottom: 8px; }
.year-header { font-size: 13px; font-weight: 700; color: var(--text-secondary); padding: 12px 0 8px 12px; letter-spacing: 0.05em; border-left: 3px solid var(--border-light); font-family: var(--font-mono); }
.results-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 24px !important; padding-block: 0 24px; }

@media (max-width: 768px) {
  .toolbar-left {
    flex-wrap: wrap;
  }
  .result-bar {
    --filter-control-height: 44px;
    --filter-control-radius: 18px;
    --filter-control-width: min(160px, 46vw);
    align-items: stretch;
    flex-direction: column;
    gap: 10px;
  }
  .result-bar-left,
  .result-bar-right {
    justify-content: center;
  }
  .sort-pills {
    flex-wrap: wrap;
    justify-content: center;
  }
  .result-bar-right .version-filter {
    width: var(--filter-control-width);
    min-width: var(--filter-control-width);
  }
}
</style>
