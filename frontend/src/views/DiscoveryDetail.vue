<template>
  <div class="genre-detail-page">
    <!-- 顶部工具栏 -->
    <div class="toolbar">
      <div class="toolbar-left">
        <button class="back-btn" @click="handleBack">
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
          :class="{ 'is-active': isEntityFavorited }"
          @click="toggleEntityFavorite"
          :title="isEntityFavorited ? '取消收藏' : '收藏'"
        >
          <svg viewBox="0 0 24 24" width="16" height="16">
            <path v-if="isEntityFavorited" d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z" fill="currentColor"/>
            <path v-else d="M16.5 3c-1.74 0-3.41.81-4.5 2.09C10.91 3.81 9.24 3 7.5 3 4.42 3 2 5.42 2 8.5c0 3.78 3.4 6.86 8.55 11.54L12 21.35l1.45-1.32C18.6 15.36 22 12.28 22 8.5 22 5.42 19.58 3 16.5 3zm-4.4 15.55l-.1.1-.1-.1C7.14 14.24 4 11.39 4 8.5 4 6.5 5.5 5 7.5 5c1.54 0 3.04.99 3.57 2.36h1.87C13.46 5.99 14.96 5 16.5 5c2 0 3.5 1.5 3.5 3.5 0 2.89-3.14 5.74-7.9 10.05z" fill="currentColor"/>
          </svg>
        </button>
      </div>
    </div>

    <!-- 排序 + 结果信息栏 -->
    <div class="result-bar">
      <div class="result-bar-left">
        <span class="result-count">{{ loading ? '加载中...' : `${total} 个结果` }}</span>
        <select v-model="sortValue" @change="doSearch" class="sort-select">
          <option value="random">随机</option>
          <option value="release_date_desc">发售日期 ↓</option>
          <option value="release_date_asc">发售日期 ↑</option>
          <option value="year_chronicle_asc">年份编年 ↓</option>
          <option value="year_chronicle_desc">年份编年 ↑</option>
          <option value="title_ja_desc">标题 Z→A</option>
          <option value="title_ja_asc">标题 A→Z</option>
          <option value="runtime_mins_desc">时长 长→短</option>
          <option value="runtime_mins_asc">时长 短→长</option>
        </select>
        <select v-model="serviceCode" @change="doSearch" class="sort-select">
          <option value="">全部版本</option>
          <option v-for="sc in serviceCodeOptions" :key="sc.value" :value="sc.value">{{ sc.label }}</option>
        </select>
      </div>
      <button class="shuffle-btn" @click="refresh" :disabled="loading">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="14" height="14">
          <polyline points="23 4 23 10 17 10"/>
          <path d="M20.49 15a9 9 0 11-2.12-9.36L23 10"/>
        </svg>
        刷新
      </button>
    </div>

    <!-- 分页（顶部） -->
    <div v-if="totalPages > 1" class="pagination-bar">
      <button class="page-btn" :disabled="page <= 1" @click="goPage(1)">«</button>
      <button class="page-btn" :disabled="page <= 1" @click="goPage(page - 1)">‹</button>
      <span class="page-indicator">{{ page }} / {{ totalPages }}</span>
      <button class="page-btn" :disabled="page >= totalPages" @click="goPage(page + 1)">›</button>
      <button class="page-btn" :disabled="page >= totalPages" @click="goPage(totalPages)">»</button>
    </div>

    <!-- 加载骨架屏 -->
    <div v-if="loading" class="skeleton-grid">
      <div v-for="n in 12" :key="n" class="skeleton-card">
        <div class="skeleton-cover"></div>
        <div class="skeleton-info">
          <div class="skeleton-line w-60"></div>
          <div class="skeleton-line w-80"></div>
        </div>
      </div>
    </div>

    <!-- 结果网格：年份编年模式 -->
    <template v-else-if="results.length > 0 && isChronicle">
      <div v-for="(group, year) in groupedByYear" :key="year" class="year-section">
        <div class="year-header">{{ year === 'null' ? '未知' : year }}</div>
        <div class="results-grid">
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
    <div v-else-if="results.length > 0" class="results-grid">
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
    <div v-else-if="searched && !loading" class="empty-state">
      <p>暂无相关影片</p>
    </div>

    <!-- 分页（底部） -->
    <div v-if="totalPages > 1" class="pagination-bar bottom">
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
import { jacketHdUrl } from '../utils/imageUrl.js'
import { modalState, openVideoModal } from '../utils/modalState'
import { favoriteState } from '../utils/favoriteState'
import MovieCard from '../components/MovieCard.vue'

const PAGE_SIZE = 30

export default {
  name: 'DiscoveryDetail',
  components: { MovieCard },
  data() {
    return {
      metadata: [], // 缓存列表数据用于显示显示名
      sortValue: 'random',
      serviceCode: '',
      serviceCodeOptions: [
        { value: 'digital', label: '数字版' },
        { value: 'mono', label: '单体版' },
        { value: 'rental', label: '租赁版' },
        { value: 'ebook', label: '电子书版' },
      ],
      results: [],
      loading: false,
      searched: false,
      page: 1,
      total: 0,
      totalPages: 1,
    }
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
    isChronicle() {
      return this.sortValue === 'year_chronicle_asc' || this.sortValue === 'year_chronicle_desc'
    },
    isFromVideo() {
      return modalState.interrupted || this.$route.query.returnTo === 'video'
    },
    isEntityFavorited() {
      return favoriteState.isFavorited(this.type, this.value)
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
    handleBack() { this.$router.back() },
    async toggleEntityFavorite() {
      try {
        await favoriteState.toggle(this.type, this.value)
      } catch (err) {
        console.error('Toggle entity favorite failed:', err)
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
      this.sortValue = 'random'
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

      if (this.sortValue === 'random') {
        params.random = '1'
      } else if (this.sortValue === 'year_chronicle_asc') {
        params.sort_by = 'release_date:asc'
      } else if (this.sortValue === 'year_chronicle_desc') {
        params.sort_by = 'release_date:desc'
      } else {
        const idx = this.sortValue.lastIndexOf('_')
        if (idx > 0) {
          const field = this.sortValue.substring(0, idx)
          const order = this.sortValue.substring(idx + 1)
          params.sort_by = `${field}:${order}`
        }
      }
      return params
    },
    async doSearch() {
      this.loading = true
      this.searched = true
      this.page = 1
      try {
        const resp = await api.searchVideos(this.buildParams())
        this.results = resp.data.data || []
        this.total = resp.data.total_count || 0
        this.totalPages = resp.data.total_pages || 1
      } catch (e) {
        console.error('Search failed:', e)
        this.results = []; this.total = 0
      } finally { this.loading = false }
    },
    async refresh() { this.doSearch() },
    async goPage(p) {
      if (p < 1 || p > this.totalPages) return
      this.page = p
      this.loading = true
      try {
        const resp = await api.searchVideos(this.buildParams())
        this.results = resp.data.data || []
        window.scrollTo({ top: 0, behavior: 'smooth' })
      } catch (e) { console.error('Page change failed:', e) }
      finally { this.loading = false }
    },
    async openModal(video) {
      const contentId = video.content_id || video.dvd_id
      let fullVideo = { ...video }
      try {
        const resp = await api.getVideo(contentId)
        if (resp.data) fullVideo = { ...video, ...resp.data }
      } catch (e) {}
      openVideoModal(fullVideo, this.$route.path)
      api.getVideoMetadata(contentId).then(resp => {
        if (resp.data) openVideoModal({ ...modalState.selectedVideo, ...resp.data }, this.$route.path)
      })
    },
    cardImageUrl(item) { return jacketHdUrl(item.jacket_thumb_url) || item.jacket_thumb_url || '/placeholder.png' }
  }
}
</script>

<style scoped>
.genre-detail-page { min-height: 100vh; background: var(--bg-primary); }
.toolbar { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 12px 20px; max-width: 1400px; margin: 0 auto; border-bottom: 1px solid var(--border); flex-wrap: wrap; }
.toolbar-left { display: flex; align-items: center; gap: 12px; flex: 1; min-width: 0; }
.back-btn { display: flex; align-items: center; gap: 4px; background: none; border: 1px solid var(--border); color: var(--text-secondary); font-size: 13px; cursor: pointer; padding: 6px 12px; border-radius: var(--radius-sm); transition: var(--transition); flex-shrink: 0; }
.back-btn:hover { border-color: var(--accent); color: var(--accent); }
.entity-fav-btn {
  width: 32px; height: 32px; border-radius: 50%; background: var(--bg-card);
  border: 1px solid var(--border); display: flex; align-items: center; justify-content: center;
  color: var(--text-muted); cursor: pointer; transition: all 0.2s cubic-bezier(0.23, 1, 0.32, 1);
  flex-shrink: 0; padding: 0;
}
.entity-fav-btn:hover { border-color: var(--accent); color: var(--accent); background: var(--bg-card-hover); }
.entity-fav-btn.is-active { color: #FF375F; border-color: rgba(255, 55, 95, 0.3); background: rgba(255, 55, 95, 0.1); }
.entity-fav-btn.is-active:hover { background: rgba(255, 55, 95, 0.2); }
.category-title { font-size: 18px; font-weight: 700; color: var(--text-primary); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.type-label { font-size: 14px; color: var(--text-muted); margin-right: 8px; font-weight: normal; }
.result-bar { display: flex; align-items: center; justify-content: space-between; padding: 12px 20px; max-width: 1400px; margin: 0 auto; }
.result-bar-left { display: flex; align-items: center; gap: 12px; }
.result-count { font-size: 13px; color: var(--text-secondary); white-space: nowrap; }
.sort-select { 
  padding: 8px 12px; 
  background: var(--bg-card); 
  border: 1px solid var(--border); 
  border-radius: var(--radius-md); 
  color: var(--text-primary); 
  font-size: 13px; 
  cursor: pointer; 
  outline: none; 
  transition: var(--transition-pro);
  backdrop-filter: blur(10px);
}
.sort-select:hover {
  background: var(--bg-card-hover);
  border-color: var(--border-light);
}
.sort-select:focus { 
  border-color: var(--accent); 
  background: var(--bg-card-hover);
  box-shadow: 0 0 0 4px rgba(255, 255, 255, 0.05);
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
  padding: 8px 16px; 
  border-radius: var(--radius-md); 
  transition: var(--transition-pro); 
  flex-shrink: 0; 
  backdrop-filter: blur(10px);
}
.shuffle-btn:hover:not(:disabled) { 
  border-color: var(--accent); 
  color: var(--accent); 
  background: var(--bg-card-hover);
}
.shuffle-btn:disabled { opacity: 0.5; cursor: not-allowed; }
.pagination-bar { display: flex; justify-content: center; align-items: center; gap: 8px; padding: 12px 20px; max-width: 1400px; margin: 0 auto; }
.pagination-bar.bottom { border-top: 1px solid var(--border); }
.page-btn { 
  background: var(--bg-card); 
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
  border-color: var(--accent); 
  color: var(--accent); 
  background: var(--bg-card-hover);
}
.page-btn:disabled { opacity: 0.4; cursor: not-allowed; }
.page-indicator { font-size: 13px; color: var(--text-secondary); padding: 0 4px; }
.skeleton-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: 20px; padding: 20px; max-width: 1400px; margin: 0 auto; }
.skeleton-card { background: var(--bg-card); border-radius: var(--radius-md); overflow: hidden; border: 1px solid var(--border); }
.skeleton-cover { aspect-ratio: 3/4; background: var(--bg-card-hover); position: relative; overflow: hidden; }
.skeleton-cover::after { content: ""; position: absolute; inset: 0; background: linear-gradient(90deg, transparent, var(--white-06), transparent); transform: translateX(-100%); animation: shimmer 2s infinite; }
.skeleton-info { padding: 12px; }
.skeleton-line { height: 12px; background: var(--border); border-radius: 6px; margin-bottom: 8px; }
.skeleton-line.w-60 { width: 60%; }
.skeleton-line.w-80 { width: 80%; }
@keyframes shimmer { 100% { transform: translateX(100%); } }
.year-section { margin-bottom: 8px; }
.year-header { font-size: 13px; font-weight: 700; color: var(--accent-light); padding: 12px 20px 8px; max-width: 1400px; margin: 0 auto; letter-spacing: 0.05em; border-left: 3px solid var(--accent); padding-left: 12px; margin-left: 20px; margin-right: 20px; font-family: var(--font-mono); }
.results-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 24px !important; padding: 0 20px 24px; max-width: 1400px; margin: 0 auto; }
.empty-state { text-align: center; padding: 60px; color: var(--text-muted); }
.skeleton { background: var(--bg-card-hover); position: relative; overflow: hidden; }
.skeleton::after { content: ""; position: absolute; inset: 0; background: linear-gradient(90deg, transparent, var(--white-06), transparent); transform: translateX(-100%); animation: shimmer 2s infinite; }
</style>
