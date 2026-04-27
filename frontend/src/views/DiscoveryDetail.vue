<template>
  <div class="genre-detail-page">
    <!-- 顶部工具栏 -->
    <div class="toolbar">
      <div class="toolbar-left">
        <button class="back-btn" @click="handleBack">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
            <polyline points="15 18 9 12 15 6"/>
          </svg>
          {{ isFromVideo ? '返回详情' : '返回' }}
        </button>
        <h2 class="category-title">
          <span class="type-label">{{ typeLabel }}发现:</span>
          {{ displayNameValue || value }}
        </h2>
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
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
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
          <div
            v-for="item in group"
            :key="item.content_id || item.dvd_id"
            class="movie-card"
            @click="openModal(item)"
          >
            <div class="card-cover">
              <img
                :src="cardImageUrl(item)"
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
      </div>
    </template>

    <!-- 结果网格：普通模式 -->
    <div v-else-if="results.length > 0" class="results-grid">
      <div
        v-for="item in results"
        :key="item.content_id || item.dvd_id"
        class="movie-card"
        @click="openModal(item)"
      >
        <div class="card-cover">
          <img
            :src="cardImageUrl(item)"
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

const PAGE_SIZE = 30

export default {
  name: 'DiscoveryDetail',
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
      
      // 根据类型填充参数
      if (this.type === 'category') params.category_id = parseInt(this.value)
      else if (this.type === 'maker') params.maker_name = this.value
      else if (this.type === 'series') params.series_name = this.value
      else if (this.type === 'actress') params.actress_name = this.value

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
    handleImgError(e) { e.target.src = 'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" width="200" height="280" viewBox="0 0 200 280"><rect fill="%231a1a2e" width="200" height="280"/><text x="50%" y="50%" text-anchor="middle" dy=".3em" fill="%236B6B8A" font-size="14">暂无封面</text></svg>' },
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
.category-title { font-size: 18px; font-weight: 700; color: var(--text-primary); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.type-label { font-size: 14px; color: var(--text-muted); margin-right: 8px; font-weight: normal; }
.result-bar { display: flex; align-items: center; justify-content: space-between; padding: 12px 20px; max-width: 1400px; margin: 0 auto; }
.result-bar-left { display: flex; align-items: center; gap: 12px; }
.result-count { font-size: 13px; color: var(--text-secondary); white-space: nowrap; }
.sort-select { padding: 6px 10px; background: var(--bg-card); border: 1px solid var(--border); border-radius: var(--radius-sm); color: var(--text-primary); font-size: 13px; cursor: pointer; outline: none; transition: var(--transition); }
.sort-select:focus { border-color: var(--accent); }
.shuffle-btn { display: flex; align-items: center; gap: 6px; background: var(--bg-card); border: 1px solid var(--border); color: var(--text-secondary); font-size: 13px; cursor: pointer; padding: 6px 14px; border-radius: 20px; transition: var(--transition); flex-shrink: 0; }
.shuffle-btn:hover:not(:disabled) { border-color: var(--accent); color: var(--accent); }
.shuffle-btn:disabled { opacity: 0.5; cursor: not-allowed; }
.pagination-bar { display: flex; justify-content: center; align-items: center; gap: 8px; padding: 12px 20px; max-width: 1400px; margin: 0 auto; }
.pagination-bar.bottom { border-top: 1px solid var(--border); }
.page-btn { background: var(--bg-card); border: 1px solid var(--border); color: var(--text-primary); padding: 5px 10px; border-radius: var(--radius-sm); cursor: pointer; font-size: 13px; transition: var(--transition); }
.page-btn:hover:not(:disabled) { border-color: var(--accent); color: var(--accent); }
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
.movie-card { background: var(--bg-card); border-radius: var(--radius-md); overflow: hidden; cursor: pointer; transition: transform 0.3s cubic-bezier(0.2, 0, 0, 1), border-color 0.3s, box-shadow 0.3s; border: 1px solid var(--border); }
.movie-card:hover { transform: translateY(-4px); border-color: var(--accent); box-shadow: var(--shadow-hover); }
.card-cover { width: 100%; aspect-ratio: 3/4; overflow: hidden; background: var(--bg-secondary); }
.cover-img { width: 100%; height: 100%; object-fit: cover; object-position: top center; transition: transform 0.5s cubic-bezier(0.2, 0, 0, 1); }
.movie-card:hover .cover-img { transform: translateY(-2px); }
.card-info { padding: 12px; }
.card-code-row { display: flex; justify-content: flex-start; margin-bottom: 6px; }
.card-code { font-weight: bold; font-size: 13px; color: var(--accent); font-family: var(--font-mono); }
.card-title { font-size: 13px; color: var(--text-primary); display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; margin-bottom: 6px; line-height: 1.4; }
.card-meta { display: flex; gap: 8px; font-size: 11px; color: var(--text-muted); font-family: var(--font-mono); }
.empty-state { text-align: center; padding: 60px; color: var(--text-muted); }
.skeleton { background: var(--bg-card-hover); position: relative; overflow: hidden; }
.skeleton::after { content: ""; position: absolute; inset: 0; background: linear-gradient(90deg, transparent, var(--white-06), transparent); transform: translateX(-100%); animation: shimmer 2s infinite; }
</style>
