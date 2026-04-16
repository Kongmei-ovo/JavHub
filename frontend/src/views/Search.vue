<template>
  <div class="search-page">
    <!-- 搜索区域 3×2 Grid -->
    <div class="search-hero">
      <h1 class="hero-title">影片搜索</h1>

      <!-- 移动端折叠触发按钮（桌面端隐藏） -->
      <button class="search-expand-btn" @click="searchExpanded = !searchExpanded">
        <svg class="search-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="11" cy="11" r="8"/>
          <path d="m21 21-4.35-4.35"/>
        </svg>
        <span>搜索</span>
        <svg class="chevron-icon" :class="{ expanded: searchExpanded }" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <polyline points="6 9 12 15 18 9"/>
        </svg>
      </button>

      <!-- 搜索表单（移动端可折叠，桌面端始终显示） -->
      <div class="search-section" :class="{ 'search-section--mobile-hidden': !searchExpanded }">
        <div class="search-row">
          <div class="search-box-wrapper code-search">
            <div class="search-box">
              <svg class="search-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="11" cy="11" r="8"/>
                <path d="m21 21-4.35-4.35"/>
              </svg>
              <input v-model="contentId" placeholder="番号" @keyup.enter="doSearch" @input="contentId = contentId.toUpperCase()" class="search-input" />
            </div>
          </div>
          <div class="search-box-wrapper">
            <div class="search-box">
              <svg class="search-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="11" cy="11" r="8"/>
                <path d="m21 21-4.35-4.35"/>
              </svg>
              <input v-model="keyword" placeholder="标题" @keyup.enter="doSearch" class="search-input" />
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
          <div class="search-box-wrapper">
            <div class="search-box">
              <svg class="search-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="11" cy="11" r="8"/>
                <path d="m21 21-4.35-4.35"/>
              </svg>
              <input v-model="seriesName" placeholder="系列" @keyup.enter="doSearch" class="search-input" />
            </div>
          </div>
          <div class="search-box-wrapper year-search">
            <input v-model.number="year" placeholder="年份" @keyup.enter="doSearch" class="year-input" type="number" min="1900" max="2100" />
          </div>
          <div class="search-box-wrapper">
            <div class="search-box">
              <svg class="search-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="11" cy="11" r="8"/>
                <path d="m21 21-4.35-4.35"/>
              </svg>
              <input v-model="makerName" placeholder="工作室" @keyup.enter="doSearch" class="search-input" />
            </div>
          </div>
        </div>
        <button @click="doSearch" :disabled="loading" class="main-search-btn">
          <span v-if="loading" class="spinner"></span>
          <span v-else>搜索</span>
        </button>
      </div>
    </div>

    <!-- 结果信息 + 分页 -->
    <div v-if="results.length > 0 || loading" class="result-bar">
      <div class="result-bar-left">
        <span class="result-count">{{ loading ? '搜索中...' : `${total} 个结果` }}</span>
        <div class="result-sort">
          <span class="sort-label">排序：</span>
          <div class="sort-rows">
            <div v-for="(cond, idx) in sortConditions" :key="idx" class="sort-row">
              <select v-model="cond.value" @change="onSortChange(idx)" class="filter-select-small">
                <option value="">无</option>
                <option value="release_date_desc">发售日期 ↓</option>
                <option value="release_date_asc">发售日期 ↑</option>
                <option value="title_ja_desc">标题 Z→A</option>
                <option value="title_ja_asc">标题 A→Z</option>
                <option value="runtime_mins_desc">时长 长→短</option>
                <option value="runtime_mins_asc">时长 短→长</option>
                <option value="random">随机</option>
              </select>
              <button v-if="sortConditions.length > 1" class="sort-remove-btn" @click="removeSort(idx)" title="移除">×</button>
            </div>
            <button class="btn btn-ghost sort-add-btn" @click="addSort">+ 添加</button>
          </div>
        </div>
      </div>
    </div>

    <!-- 分页控制（顶部） -->
    <div v-if="results.length > 0" class="pagination-bar">
      <button class="page-btn" :disabled="page <= 1" @click="goPage(1)">«</button>
      <button class="page-btn" :disabled="page <= 1" @click="goPage(page - 1)">‹</button>
      <span class="page-indicator">{{ page }} / {{ totalPages }}</span>
      <button class="page-btn" :disabled="page >= totalPages" @click="goPage(page + 1)">›</button>
      <button class="page-btn" :disabled="page >= totalPages" @click="goPage(totalPages)">»</button>
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
        <button class="jump-btn" @click="doJumpPage">跳转</button>
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
            :src="cardImageUrl(item)"
            :alt="item.dvd_id || item.content_id"
            @error="handleImgError"
            @load="onImgLoad($event)"
            loading="lazy"
            class="cover-img"
          />
          <div v-if="item.sample_url" class="card-preview-badge" title="有预览视频">
            <svg viewBox="0 0 24 24" fill="currentColor" width="12" height="12">
              <path d="M8 5v14l11-7z"/>
            </svg>
          </div>
        </div>
        <div class="card-info">
          <div class="card-code-row">
            <span class="card-code">{{ item.dvd_id || item.content_id }}</span>
            <span v-if="item.service_code" class="card-type" :class="'type-' + item.service_code">{{ formatServiceCode(item.service_code) }}</span>
          </div>
          <div class="card-title" :title="item.title_en || item.title_ja">
            {{ item.title_en_translated || item.title_ja_translated || item.title_en || item.title_ja }}
          </div>
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

    <!-- 分页控制（底部） -->
    <div v-if="results.length > 0" class="pagination-bar">
      <button class="page-btn" :disabled="page <= 1" @click="goPage(1)">«</button>
      <button class="page-btn" :disabled="page <= 1" @click="goPage(page - 1)">‹</button>
      <span class="page-indicator">{{ page }} / {{ totalPages }}</span>
      <button class="page-btn" :disabled="page >= totalPages" @click="goPage(page + 1)">›</button>
      <button class="page-btn" :disabled="page >= totalPages" @click="goPage(totalPages)">»</button>
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
        <button class="jump-btn" @click="doJumpPage">跳转</button>
      </div>
    </div>

    <!-- 影片详情弹窗 -->
    <VideoModal
      v-if="selectedVideo"
      :visible="!!selectedVideo"
      :video="selectedVideo"
      @close="closeModal"
      @download="handleDownload"
      @navigate="handleNavigate"
    />
  </div>
</template>

<script>
import api from '../api'
import VideoModal from '../components/VideoModal.vue'
import { jacketHdUrl } from '../utils/imageUrl.js'
import { useRoute } from 'vue-router'

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
      year: null,

      sortConditions: [{ value: '' }],

      // 分页
      page: 1,
      pageSize: 30,
      total: 0,
      totalPages: 1,
      jumpPage: null,
      searchExpanded: false,
    }
  },
  computed: {
    hasFilters() {
      return this.categoryName || this.keyword || this.contentId || this.makerName || this.seriesName || this.actressName
    }
  },
  mounted() {
    const route = useRoute()
    const q = route.query
    if (q.actress) {
      this.actressName = q.actress
    }
    if (q.maker) {
      this.makerName = q.maker
    }
    if (q.series) {
      this.seriesName = q.series
    }
    if (q.keyword || q.q) {
      this.keyword = q.keyword || q.q
    }
    // 从设置加载 page_size
    api.getConfig().then(resp => {
      const ps = resp.data?.javinfo?.page_size
      if (ps) this.pageSize = ps
    }).catch(() => {})
    if (this.hasFilters) {
      this.doSearch()
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
      this.year = null
      this.sortConditions = [{ value: '' }]
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
        if (this.year) params.year = this.year
        if (this.categoryName) params.category_name = this.categoryName.trim()
        if (this.sortConditions.length > 0) {
          const parts = []
          for (const cond of this.sortConditions) {
            if (!cond.value) continue
            if (cond.value === 'random') { parts.unshift('random'); continue }
            const idx = cond.value.lastIndexOf('_')
            const field = cond.value.substring(0, idx)
            const order = cond.value.substring(idx + 1)
            parts.push(`${field}:${order}`)
          }
          if (parts.length === 1 && parts[0] === 'random') {
            params.random = '1'
          } else if (parts.length > 0) {
            params.sort_by = parts.join(',')
          }
        }

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
    async goPage(p) {
      if (p < 1 || p > this.totalPages || p === this.page) return
      this.page = p
      this.loading = true
      this.searched = true
      try {
        const params = { page: this.page, page_size: this.pageSize }
        if (this.contentId) params.content_id = this.contentId.trim()
        if (this.keyword) params.q = this.keyword.trim()
        if (this.makerName) params.maker_name = this.makerName.trim()
        if (this.seriesName) params.series_name = this.seriesName.trim()
        if (this.actressName) params.actress_name = this.actressName.trim()
        if (this.year) params.year = this.year
        if (this.categoryName) params.category_name = this.categoryName.trim()
        if (this.sortConditions.length > 0) {
          const parts = []
          for (const cond of this.sortConditions) {
            if (!cond.value) continue
            if (cond.value === 'random') { parts.unshift('random'); continue }
            const idx = cond.value.lastIndexOf('_')
            const field = cond.value.substring(0, idx)
            const order = cond.value.substring(idx + 1)
            parts.push(`${field}:${order}`)
          }
          if (parts.length === 1 && parts[0] === 'random') {
            params.random = '1'
          } else if (parts.length > 0) {
            params.sort_by = parts.join(',')
          }
        }

        const resp = await api.searchVideos(params)
        const data = resp.data
        this.results = data.data || []
        this.total = data.total_count || 0
        this.totalPages = data.total_pages || 1
        window.scrollTo({ top: 0, behavior: 'smooth' })
      } catch (e) {
        console.error('Page change failed:', e)
      } finally {
        this.loading = false
      }
    },
    doJumpPage() {
      if (!this.jumpPage) return
      const p = Math.max(1, Math.min(this.totalPages, this.jumpPage))
      this.jumpPage = null
      this.goPage(p)
    },
    onSortChange(idx) {
      // 选择非空值时，如果已经是最后一个，添加新行
      if (this.sortConditions[idx].value && idx === this.sortConditions.length - 1) {
        this.sortConditions.push({ value: '' })
      }
      this.doSearch()
    },
    addSort() {
      this.sortConditions.push({ value: '' })
    },
    removeSort(idx) {
      this.sortConditions.splice(idx, 1)
      this.doSearch()
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
    handleNavigate({ type, item }) {
      // 关闭弹窗，跳转到搜索页并自动搜索
      this.selectedVideo = null
      const q = {}
      if (type === 'actress') {
        q.actress = item.name_kanji || item.name_romaji || item.name_en || ''
        this.$router.push({ path: '/search', query: q })
      } else if (type === 'maker') {
        q.maker = item.name_en || item.name_ja || ''
        this.$router.push({ path: '/search', query: q })
      } else if (type === 'series') {
        q.series = item.name_en || item.name_ja || ''
        this.$router.push({ path: '/search', query: q })
      } else if (type === 'category') {
        q.keyword = item.name_en || item.name_ja || ''
        this.$router.push({ path: '/search', query: q })
      }
    },
    handleImgError(e) {
      e.target.src = 'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" width="200" height="280" viewBox="0 0 200 280"><rect fill="%231a1a2e" width="200" height="280"/><text x="50%" y="50%" text-anchor="middle" dy=".3em" fill="%236B6B8A" font-size="14">暂无封面</text></svg>'
    },
    cardImageUrl(item) {
      return jacketHdUrl(item.jacket_thumb_url) || item.jacket_thumb_url || '/placeholder.png'
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
  padding: 30px 20px 24px;
  background: linear-gradient(180deg, var(--bg-secondary) 0%, var(--bg-primary) 100%);
}

.hero-title {
  font-family: 'Playfair Display', 'Noto Serif SC', serif;
  font-size: 44px;
  font-weight: 700;
  letter-spacing: 2px;
  margin-bottom: 0;
}

.hero-subtitle {
  color: var(--text-muted);
  margin-bottom: 24px;
}

.search-section {
  display: flex;
  align-items: stretch;
  gap: 10px;
  max-width: 1600px;
  margin: 12px auto 0;
  padding: 0 20px;
}

.search-row {
  display: flex;
  flex: 1;
  flex-wrap: wrap;
  gap: 10px;
  align-items: stretch;
  min-width: 0;
}

.search-box-wrapper {
  position: relative;
  flex: 1;
  min-width: 0;
}

.year-input {
  width: 100%;
  height: 44px;
  padding: 0 10px;
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  background: var(--bg-card);
  color: var(--text-primary);
  font-size: 15px;
  outline: none;
  box-sizing: border-box;
  -moz-appearance: textfield;
}

.year-input::-webkit-outer-spin-button,
.year-input::-webkit-inner-spin-button {
  -webkit-appearance: none;
  margin: 0;
}

.year-input:focus {
  border-color: var(--accent);
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
  flex-shrink: 0;
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
  margin: 16px auto 0;
}

.result-bar-left { display: flex; align-items: center; gap: 16px; }
.result-count {
  font-size: 14px;
  color: var(--text-secondary);
}

.result-sort { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.sort-label {
  font-size: 12px;
  color: var(--text-secondary);
  white-space: nowrap;
}

.sort-rows { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
.sort-row { display: flex; align-items: center; gap: 2px; }
.sort-remove-btn {
  background: none; border: none; color: var(--text-muted); cursor: pointer;
  font-size: 14px; padding: 2px 4px; border-radius: 4px; line-height: 1;
}
.sort-remove-btn:hover { color: var(--text-primary); }
.sort-add-btn {
  font-size: 12px !important;
  padding: 4px 10px !important;
  border: 1px solid var(--border) !important;
  border-radius: var(--radius-sm) !important;
  background: var(--bg-secondary) !important;
  color: var(--text-secondary) !important;
  cursor: pointer;
  line-height: normal !important;
}
.sort-add-btn:hover { border-color: var(--accent) !important; color: var(--accent) !important; }

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
  position: relative;
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

.card-preview-badge {
  position: absolute;
  top: 6px;
  right: 6px;
  background: rgba(0,0,0,0.65);
  border-radius: 4px;
  padding: 3px 5px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  pointer-events: none;
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

.pagination-bar {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 8px;
  padding: 16px 20px;
  max-width: 1400px;
  margin: 0 auto;
}

.page-btn {
  background: var(--bg-card);
  border: 1px solid var(--border);
  color: var(--text-primary);
  padding: 5px 10px;
  border-radius: var(--radius-sm);
  cursor: pointer;
  font-size: 13px;
  transition: var(--transition);
}
.page-btn:hover:not(:disabled) { border-color: var(--accent); color: var(--accent); }
.page-btn:disabled { opacity: 0.4; cursor: not-allowed; }

.page-indicator { font-size: 13px; color: var(--text-secondary); padding: 0 4px; }

.jump-wrap { display: flex; align-items: center; gap: 4px; margin-left: 8px; }
.jump-input {
  width: 50px; padding: 4px 6px; border: 1px solid var(--border);
  border-radius: var(--radius-sm); background: var(--bg-card); color: var(--text-primary);
  font-size: 12px; text-align: center;
}
.jump-input::-webkit-inner-spin-button,
.jump-input::-webkit-outer-spin-button { -webkit-appearance: none; }
.jump-btn {
  background: var(--bg-secondary); border: 1px solid var(--border);
  color: var(--text-primary); padding: 4px 10px; border-radius: var(--radius-sm);
  cursor: pointer; font-size: 12px; transition: var(--transition);
}
.jump-btn:hover { border-color: var(--accent); color: var(--accent); }

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

/* === 移动端折叠搜索 === */
@media (max-width: 768px) {
  /* 隐藏桌面端搜索按钮（在表单内） */
  .search-expand-btn {
    display: flex;
  }

  /* 折叠状态：隐藏搜索表单 */
  .search-section--mobile-hidden {
    display: none;
  }

  /* 移动端折叠按钮样式 */
  .search-expand-btn {
    display: none; /* 桌面端默认隐藏 */
    align-items: center;
    justify-content: center;
    gap: 8px;
    width: calc(100% - 40px);
    margin: 0 auto;
    padding: 12px 20px;
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: var(--radius-md);
    color: var(--text-secondary);
    font-size: 15px;
    cursor: pointer;
    transition: border-color 0.2s;
  }

  .search-expand-btn:active {
    border-color: var(--accent);
  }

  .search-expand-btn .search-icon {
    width: 20px;
    height: 20px;
    color: var(--text-muted);
  }

  .search-expand-btn .chevron-icon {
    width: 18px;
    height: 18px;
    color: var(--text-muted);
    margin-left: auto;
    transition: transform 0.25s ease;
  }

  .search-expand-btn .chevron-icon.expanded {
    transform: rotate(180deg);
  }

  /* 移动端搜索区 padding 收紧 */
  .search-hero {
    padding: 20px 16px 16px;
  }

  .search-section {
    margin-top: 12px;
  }

  .search-row {
    flex-direction: column;
    gap: 8px;
  }

  .search-box-wrapper {
    min-width: 100%;
  }

  .main-search-btn {
    width: 100%;
    margin-top: 4px;
    padding: 12px;
  }
}
}
</style>
