<template>
  <div class="search-page">
    <!-- 搜索区域 3×2 Grid -->
    <div class="search-hero">
      <h1 class="hero-title">影片搜索</h1>
      <p class="hero-subtitle">支持番号、演员、厂商、系列、题材多维度检索</p>
      <div class="search-section">
        <div class="search-grid">
          <!-- Row 1: 番号 + 关键词 + 厂商 -->
          <div class="search-box-wrapper code-search">
            <div class="search-box">
              <svg class="search-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="11" cy="11" r="8"/>
                <path d="m21 21-4.35-4.35"/>
              </svg>
              <input v-model="contentId" placeholder="精确番号，如 ABC-123" @keyup.enter="doSearch" @input="contentId = contentId.toUpperCase()" class="search-input" />
            </div>
          </div>
          <div class="search-box-wrapper">
            <div class="search-box">
              <svg class="search-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="11" cy="11" r="8"/>
                <path d="m21 21-4.35-4.35"/>
              </svg>
              <input v-model="keyword" placeholder="关键词搜索" @keyup.enter="doSearch" class="search-input" />
            </div>
          </div>
          <div class="search-box-wrapper">
            <div class="search-box">
              <svg class="search-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="11" cy="11" r="8"/>
                <path d="m21 21-4.35-4.35"/>
              </svg>
              <input v-model="makerName" placeholder="厂商" @keyup.enter="doSearch" class="search-input" />
            </div>
          </div>
          <!-- Row 2: 系列 + 演员 + 题材 -->
          <div class="search-box-wrapper">
            <div class="search-box">
              <svg class="search-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="11" cy="11" r="8"/>
                <path d="m21 21-4.35-4.35"/>
              </svg>
              <input v-model="seriesName" placeholder="系列" @keyup.enter="doSearch" class="search-input" />
            </div>
          </div>
          <div class="search-box-wrapper">
            <div class="search-box">
              <svg class="search-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="11" cy="11" r="8"/>
                <path d="m21 21-4.35-4.35"/>
              </svg>
              <input v-model="actressName" placeholder="演员" @keyup.enter="doSearch" class="search-input" />
            </div>
          </div>
          <div class="search-box-wrapper">
            <div class="search-box">
              <svg class="search-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="11" cy="11" r="8"/>
                <path d="m21 21-4.35-4.35"/>
              </svg>
              <input v-model="categoryName" placeholder="题材" @keyup.enter="doSearch" class="search-input" />
            </div>
          </div>
        </div>
        <button @click="doSearch" :disabled="loading" class="main-search-btn">
          <span v-if="loading" class="spinner"></span>
          <span v-else>搜索</span>
        </button>
      </div>
    </div>

    <!-- 结果信息 -->
    <div v-if="results.length > 0 || loading" class="result-bar">
      <span class="result-count">{{ loading ? '搜索中...' : `${total} 个结果` }}</span>
      <div class="result-sort">
        <span>排序：</span>
        <select v-model="sortBy" @change="doSearch" class="filter-select-small">
          <option value="">默认</option>
          <option value="date_desc">发行日期 ↓</option>
          <option value="date_asc">发行日期 ↑</option>
        </select>
      </div>
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

    <!-- 搜索结果网格 -->
    <div v-else-if="results.length > 0" class="results-grid">
      <div
        v-for="item in results"
        :key="item.content_id || item.dvd_id"
        class="movie-card"
        @click="openModal(item)"
      >
        <div class="card-cover">
          <img
            :src="item.jacket_full_url || item.jacket_thumb_url || '/placeholder.png'"
            :alt="item.dvd_id || item.content_id"
            @error="handleImgError"
            @load="onImgLoad($event)"
            loading="lazy"
            class="cover-img"
          />
        </div>
        <div class="card-info">
          <div class="card-code-row">
            <span class="card-code">{{ item.dvd_id || item.content_id }}</span>
            <span v-if="item.service_code" class="card-type" :class="'type-' + item.service_code">{{ formatServiceCode(item.service_code) }}</span>
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
    <div v-else-if="searched" class="empty-state">
      <p>未找到相关影片</p>
      <p class="text-secondary">尝试其他关键词或筛选条件</p>
    </div>

    <!-- 分页 -->
    <div v-if="results.length > 0 && page < totalPages" class="pagination">
      <button class="btn btn-ghost" @click="loadMore">
        加载更多
      </button>
      <span class="page-info">第 {{ page }} / {{ totalPages }} 页</span>
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
import api from '../api'
import VideoModal from '../components/VideoModal.vue'

export default {
  name: 'Search',
  components: { VideoModal },
  data() {
    return {
      keyword: '',
      contentId: '',
      results: [],
      loading: false,
      searched: false,
      selectedVideo: null,

      // 筛选
      categoryName: '',
      makerName: '',
      seriesName: '',
      actressName: '',

      sortBy: '',

      // 分页
      page: 1,
      pageSize: 30,
      total: 0,
      totalPages: 1
    }
  },
  computed: {
    hasFilters() {
      return this.categoryName || this.keyword || this.contentId || this.makerName || this.seriesName || this.actressName
    }
  },
  methods: {
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
      this.sortBy = ''
      this.results = []
      this.searched = false
    },
    searchByCategory(categoryName) {
      this.closeModal()
      this.categoryName = categoryName
      this.doSearch()
    },
    searchByMaker(makerName) {
      this.closeModal()
      this.makerName = makerName
      this.doSearch()
    },
    searchBySeries(seriesName) {
      this.closeModal()
      this.seriesName = seriesName
      this.doSearch()
    },
    searchByActress(actressName) {
      this.closeModal()
      this.actressName = actressName
      this.doSearch()
    },
    async doSearch() {
      this.loading = true
      this.searched = true
      this.page = 1
      try {
        const params = {
          page: this.page,
          page_size: this.pageSize
        }
        if (this.contentId) params.content_id = this.contentId.trim()
        if (this.keyword) params.q = this.keyword.trim()
        if (this.makerName) params.maker_name = this.makerName.trim()
        if (this.seriesName) params.series_name = this.seriesName.trim()
        if (this.actressName) params.actress_name = this.actressName.trim()
        if (this.categoryName) params.category_name = this.categoryName.trim()

        const resp = await api.searchVideos(params)
        const data = resp.data
        this.results = data.data || []
        this.total = data.total_count || 0
        this.totalPages = data.total_pages || 1
      } catch (e) {
        console.error('Search failed:', e)
        this.results = []
        this.total = 0
      } finally {
        this.loading = false
      }
    },
    async loadMore() {
      this.page++
      this.loading = true
      try {
        const params = {
          page: this.page,
          page_size: this.pageSize
        }
        if (this.contentId) params.content_id = this.contentId.trim()
        if (this.keyword) params.q = this.keyword.trim()
        if (this.makerName) params.maker_name = this.makerName.trim()
        if (this.seriesName) params.series_name = this.seriesName.trim()
        if (this.actressName) params.actress_name = this.actressName.trim()
        if (this.categoryName) params.category_name = this.categoryName.trim()

        const resp = await api.searchVideos(params)
        const data = resp.data
        this.results.push(...(data.data || []))
        this.total = data.total_count || 0
        this.totalPages = data.total_pages || 1
      } catch (e) {
        console.error('Load more failed:', e)
        this.page--
      } finally {
        this.loading = false
      }
    },
    async openModal(video) {
      this.selectedVideo = video
      // 如果需要加载完整详情
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
    handleImgError(e) {
      e.target.src = 'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" width="200" height="280" viewBox="0 0 200 280"><rect fill="%231a1a2e" width="200" height="280"/><text x="50%" y="50%" text-anchor="middle" dy=".3em" fill="%236B6B8A" font-size="14">暂无封面</text></svg>'
    },
    onImgLoad(e) {
      const img = e.target
      if (img.naturalWidth > img.naturalHeight) {
        img.classList.add('wide')
      }
    },
    formatServiceCode(code) {
      const map = {
        'mono': 'DVD',
        'digital': '数字',
        'rental': '租赁',
        'download': '下载',
        'streaming': '流媒体',
        'subscription': '订阅'
      }
      return map[code] || code
    }
  }
}
</script>

<style scoped>
.search-page {
  min-height: 100vh;
  background: var(--bg-primary);
}

.search-hero {
  text-align: center;
  padding: 40px 20px 20px;
  background: linear-gradient(180deg, var(--bg-secondary) 0%, var(--bg-primary) 100%);
}

.hero-title {
  font-size: 32px;
  font-weight: 700;
  margin-bottom: 8px;
}

.hero-subtitle {
  color: var(--text-muted);
  margin-bottom: 24px;
}

.search-section {
  display: flex;
  gap: 12px;
  max-width: 1000px;
  margin: 0 auto;
  padding: 0 20px;
  align-items: stretch;
}

.search-grid {
  flex: 1;
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
}

.search-box-wrapper {
  position: relative;
  min-width: 0;
}

.search-box-wrapper.code-search {
  grid-column: span 1;
}

.search-box {
  display: flex;
  align-items: center;
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  padding: 0 16px;
}

.search-box:focus-within {
  border-color: var(--accent);
}

.search-icon {
  width: 20px;
  height: 20px;
  color: var(--text-muted);
  flex-shrink: 0;
}

.search-input {
  flex: 1;
  border: none;
  outline: none;
  padding: 12px;
  font-size: 15px;
  background: transparent;
  color: var(--text-primary);
}

.main-search-btn {
  background: var(--accent);
  color: white;
  border: none;
  border-radius: var(--radius-md);
  padding: 0 28px;
  font-size: 15px;
  cursor: pointer;
  transition: opacity 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
  white-space: nowrap;
}

.main-search-btn:hover {
  opacity: 0.9;
}

.result-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 20px;
  max-width: 1400px;
  margin: 0 auto;
}

.result-count {
  font-size: 14px;
  color: var(--text-secondary);
}

.result-sort {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: var(--text-muted);
}

.filter-select-small {
  padding: 4px 8px;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  background: var(--bg-card);
  color: var(--text-primary);
  font-size: 12px;
}

.skeleton-grid,
.results-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: 20px;
  padding: 0 20px 40px;
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

.w-60 { width: 60%; }
.w-80 { width: 80%; }

@keyframes shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
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
  object-position: center;
}

.cover-img.wide {
  /* 横向长图，对折显示右半边 */
  object-fit: none;
  object-position: right center;
  clip-path: inset(0 0 0 50%);
}

.card-info {
  padding: 10px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 4px;
}

.card-code-row {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 6px;
  margin-bottom: 4px;
}

.card-code {
  font-weight: bold;
  font-size: 13px;
}

.card-type {
  font-size: 10px;
  padding: 2px 6px;
  border-radius: 4px;
  font-weight: 600;
}

.type-mono {
  background: rgba(76, 175, 80, 0.2);
  color: #4CAF50;
}

.type-digital {
  background: rgba(33, 150, 243, 0.2);
  color: #2196F3;
}

.type-rental {
  background: rgba(255, 152, 0, 0.2);
  color: #FF9800;
}

.type-download {
  background: rgba(156, 39, 176, 0.2);
  color: #9C27B0;
}

.type-streaming,
.type-subscription {
  background: rgba(244, 67, 54, 0.2);
  color: #F44336;
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

.page-info {
  font-size: 13px;
  color: var(--text-muted);
}

.btn {
  padding: 10px 20px;
  border-radius: var(--radius-sm);
  border: none;
  cursor: pointer;
  font-size: 14px;
  transition: var(--transition);
}

.btn-primary {
  background: var(--accent);
  color: white;
}

.btn-ghost {
  background: var(--bg-secondary);
  color: var(--text-primary);
}

.spinner {
  display: inline-block;
  width: 16px;
  height: 16px;
  border: 2px solid rgba(255,255,255,0.3);
  border-top-color: white;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>
