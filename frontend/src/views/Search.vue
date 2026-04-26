<template>
  <div class="search-page">
    <!-- 搜索区域 -->
    <div class="search-hero">
      <h1 class="hero-title">影片搜索</h1>
      <div class="search-section">
        <!-- 主检索：番号 + 关键词 -->
        <div class="search-row search-row-main">
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
        </div>

        <!-- 更多筛选（折叠） -->
        <transition name="slide">
          <div v-if="showMoreFilters" class="search-row search-row-more">
            <!-- 题材占一整行：tag 输入 -->
            <div class="search-box-wrapper full-width">
              <div class="search-box tag-input-box">
                <svg class="search-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <circle cx="11" cy="11" r="8"/>
                  <path d="m21 21-4.35-4.35"/>
                </svg>
                <div class="tag-list">
                  <span v-for="(tag, idx) in categoryTags" :key="idx" class="tag-chip">
                    {{ tag }}
                    <button class="tag-remove" @click="removeCategoryTag(idx)">×</button>
                  </span>
                  <input
                    v-model="categoryInput"
                    placeholder="题材（空格添加）"
                    @keydown.space.prevent="addCategoryTag"
                    @keydown.enter.prevent="addCategoryTag"
                    @keyup.enter="doSearch"
                    class="search-input tag-input"
                  />
                </div>
              </div>
            </div>
            <!-- 第二行：工作室(半) + 演员(半) -->
            <div class="search-box-wrapper maker-half">
              <div class="search-box">
                <svg class="search-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <circle cx="11" cy="11" r="8"/>
                  <path d="m21 21-4.35-4.35"/>
                </svg>
                <input v-model="makerName" placeholder="工作室" @keyup.enter="doSearch" class="search-input" />
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
            <!-- 第三行：系列 + 年份 -->
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
              <div class="search-box">
                <svg class="search-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <rect x="3" y="4" width="18" height="18" rx="2" ry="2"/>
                  <line x1="16" y1="2" x2="16" y2="6"/>
                  <line x1="8" y1="2" x2="8" y2="6"/>
                  <line x1="3" y1="10" x2="21" y2="10"/>
                </svg>
                <input v-model.number="year" placeholder="年份" @keyup.enter="doSearch" class="search-input year-input" type="number" min="1900" max="2100" />
              </div>
            </div>
          </div>
        </transition>

        <!-- 操作栏 -->
        <div class="search-actions">
          <button class="more-filter-btn" @click="showMoreFilters = !showMoreFilters">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16">
              <path v-if="showMoreFilters" d="M18 15l-6-6-6 6"/>
              <path v-else d="M6 9l6 6 6-6"/>
            </svg>
            {{ showMoreFilters ? '收起' : '更多筛选' }}
          </button>
          <div class="version-select-wrapper">
            <select v-model="serviceCode" class="version-select">
              <option value="">全部版本</option>
              <option v-for="sc in serviceCodeOptions" :key="sc.value" :value="sc.value">{{ sc.label }}</option>
            </select>
            <svg class="select-arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
              <path d="M6 9l6 6 6-6"/>
            </svg>
          </div>
          <button @click="doSearch" :disabled="loading" class="main-search-btn">
            <span v-if="loading" class="spinner"></span>
            <span v-else>搜索</span>
          </button>
        </div>
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
  </div>
</template>

<script>
import api from '../api'
import { jacketHdUrl } from '../utils/imageUrl.js'
import { useRoute } from 'vue-router'
import { openVideoModal } from '../utils/modalState'

export default {
  name: 'Search',
  data() {
    return {
      keyword: '',
      contentId: '',
      results: [],
      loading: false,
      searched: false,

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
        { value: 'ebook', label: '电子书版' },
      ],

      // 折叠更多筛选
      showMoreFilters: false,

      sortConditions: [{ value: 'random' }],

      // 分页
      page: 1,
      pageSize: 30,
      total: 0,
      totalPages: 1,
      jumpPage: null
    }
  },
  computed: {
    hasFilters() {
      return this.categoryTags.length || this.keyword || this.contentId || this.makerName || this.seriesName || this.actressName
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
  activated() {
    // 检查是否有新的查询参数
    const q = this.$route.query
    let changed = false
    if (q.actress && q.actress !== this.actressName) { this.actressName = q.actress; changed = true }
    if (q.maker && q.maker !== this.makerName) { this.makerName = q.maker; changed = true }
    if (q.series && q.series !== this.seriesName) { this.seriesName = q.series; changed = true }
    if ((q.keyword || q.q) && (q.keyword || q.q) !== this.keyword) {
      this.keyword = q.keyword || q.q
      changed = true
    }
    if (changed) {
      this.doSearch()
    }
  },
  watch: {
    '$route.query'(q) {
      let changed = false
      if (q.actress !== undefined && q.actress !== this.actressName) { this.actressName = q.actress; changed = true }
      if (q.maker !== undefined && q.maker !== this.makerName) { this.makerName = q.maker; changed = true }
      if (q.series !== undefined && q.series !== this.seriesName) { this.seriesName = q.series; changed = true }
      if (q.q !== undefined && q.q !== this.keyword) { this.keyword = q.q; changed = true }
      if (q.keyword !== undefined && q.keyword !== this.keyword) { this.keyword = q.keyword; changed = true }

      if (changed) {
        this.doSearch()
      }
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
      this.categoryTags = []
      this.categoryInput = ''
      this.year = null
      this.sortConditions = [{ value: '' }]
      this.results = []
      this.searched = false
    },
    searchByCategory(categoryName) {
      this.closeModal()
      if (categoryName && !this.categoryTags.includes(categoryName)) {
        this.categoryTags.push(categoryName)
      }
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
    addCategoryTag() {
      const tag = this.categoryInput.trim()
      if (tag && !this.categoryTags.includes(tag)) {
        this.categoryTags.push(tag)
      }
      this.categoryInput = ''
    },
    removeCategoryTag(idx) {
      this.categoryTags.splice(idx, 1)
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
        if (this.serviceCode) params.service_code = this.serviceCode
        if (this.categoryTags.length) params.category_name = this.categoryTags.join(' ')
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
        if (this.serviceCode) params.service_code = this.serviceCode
        if (this.categoryTags.length) params.category_name = this.categoryTags.join(' ')
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
      openVideoModal(video, this.$route.path)
      // 如果需要加载完整详情
      if (!video.magnets && !video.gallery_thumb_first) {
        try {
          const resp = await api.getVideo(video.content_id || video.dvd_id)
          if (resp.data) {
            openVideoModal({ ...video, ...resp.data }, this.$route.path)
          }
        } catch (e) {
          console.error('Load video detail failed:', e)
        }
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
  padding: 36px 20px 28px;
  background: linear-gradient(180deg, rgba(99,102,241,0.06) 0%, var(--bg-primary) 100%);
  position: relative;
  overflow: hidden;
}

.search-hero::before {
  content: '';
  position: absolute;
  top: -50%;
  left: 50%;
  transform: translateX(-50%);
  width: 600px;
  height: 600px;
  background: radial-gradient(circle, rgba(99,102,241,0.08) 0%, transparent 70%);
  pointer-events: none;
}

.hero-title {
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  font-size: 42px;
  font-weight: 800;
  letter-spacing: -0.03em;
  margin-bottom: 0;
  background: linear-gradient(135deg, #FFFFFF 0%, #A1A1AA 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.hero-subtitle {
  color: var(--text-muted);
  margin-bottom: 24px;
}

.search-section {
  display: flex;
  flex-direction: column;
  gap: 10px;
  max-width: 1600px;
  margin: 12px auto 0;
  padding: 0 20px;
}

.search-row {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: stretch;
  min-width: 0;
}

.search-row-main {
  flex-direction: row;
  flex-wrap: wrap;
}

.search-row-main .search-box-wrapper {
  flex: 1 0 calc(50% - 5px);
  min-width: calc(50% - 5px);
}

.search-row-more {
  flex-wrap: wrap;
}

.search-row-more .search-box-wrapper {
  flex: 1;
  min-width: calc(50% - 5px);
}

.search-row-more .maker-half {
  flex: 1;
  min-width: calc(50% - 5px);
}

.search-row-more .full-width {
  flex: 1 1 100%;
  min-width: 100%;
}

.search-box-wrapper {
  position: relative;
  flex: 1;
  min-width: 0;
}

.search-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.more-filter-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 10px 16px;
  background: var(--bg-secondary);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  color: var(--text-secondary);
  font-size: 14px;
  cursor: pointer;
  transition: var(--transition);
  white-space: nowrap;
}
.more-filter-btn:hover {
  border-color: var(--accent);
  color: var(--accent);
}

.version-select-wrapper {
  position: relative;
  display: flex;
  align-items: center;
}

.version-select {
  appearance: none;
  padding: 10px 32px 10px 14px;
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  background: var(--bg-card);
  color: var(--text-primary);
  font-size: 14px;
  cursor: pointer;
  transition: var(--transition);
  min-width: 120px;
}

.version-select:focus {
  outline: none;
  border-color: var(--accent);
}

.version-select:hover {
  border-color: var(--accent);
}

.select-arrow {
  position: absolute;
  right: 10px;
  pointer-events: none;
  color: var(--text-muted);
}

/* 折叠展开动画 */
.slide-enter-active,
.slide-leave-active {
  transition: all 0.2s ease;
  overflow: hidden;
}
.slide-enter-from,
.slide-leave-to {
  opacity: 0;
  max-height: 0;
}
.slide-enter-to,
.slide-leave-from {
  opacity: 1;
  max-height: 200px;
}

.year-input {
  -moz-appearance: textfield;
}
.year-input::-webkit-outer-spin-button,
.year-input::-webkit-inner-spin-button {
  -webkit-appearance: none;
  margin: 0;
}

.search-box {
  display: flex;
  align-items: center;
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  padding: 0 12px;
}

.service-code-wrap {
  flex: 1 1 100%;
}

.service-code-btns {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.service-code-btn {
  padding: 6px 14px;
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  background: var(--bg-card);
  color: var(--text-secondary);
  font-size: 13px;
  cursor: pointer;
  transition: var(--transition);
}
.service-code-btn:hover {
  border-color: var(--accent);
  color: var(--accent);
}
.service-code-btn.active {
  background: var(--accent);
  border-color: var(--accent);
  color: white;
  font-weight: 600;
}

.search-box:focus-within {
  border-color: var(--accent);
}

.tag-input-box {
  flex-wrap: wrap;
  padding: 6px 12px;
  gap: 6px;
}

.tag-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: center;
  flex: 1;
  min-width: 0;
}

.tag-chip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  background: var(--accent);
  color: white;
  padding: 3px 8px;
  border-radius: 12px;
  font-size: 13px;
  white-space: nowrap;
}

.tag-remove {
  background: none;
  border: none;
  color: white;
  cursor: pointer;
  padding: 0;
  font-size: 14px;
  line-height: 1;
  opacity: 0.8;
}
.tag-remove:hover {
  opacity: 1;
}

.tag-input {
  flex: 1;
  min-width: 80px;
  padding: 4px 0;
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
  padding: 12px 8px;
  font-size: 15px;
  background: transparent;
  color: var(--text-primary);
}

.main-search-btn {
  background: linear-gradient(135deg, var(--accent), var(--accent-light));
  color: white;
  border: none;
  border-radius: var(--radius-md);
  padding: 10px 28px;
  font-size: 15px;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  display: flex;
  align-items: center;
  justify-content: center;
  white-space: nowrap;
  flex-shrink: 0;
  box-shadow: 0 4px 16px var(--accent-glow);
}

.main-search-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 24px var(--accent-glow);
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

/* 卡片入场动画 - 交错出现 */
.results-grid .movie-card {
  animation: cardEntrance 0.5s cubic-bezier(0.32, 0.72, 0, 1) both;
}
.results-grid .movie-card:nth-child(1) { animation-delay: 0.02s; }
.results-grid .movie-card:nth-child(2) { animation-delay: 0.04s; }
.results-grid .movie-card:nth-child(3) { animation-delay: 0.06s; }
.results-grid .movie-card:nth-child(4) { animation-delay: 0.08s; }
.results-grid .movie-card:nth-child(5) { animation-delay: 0.10s; }
.results-grid .movie-card:nth-child(6) { animation-delay: 0.12s; }
.results-grid .movie-card:nth-child(7) { animation-delay: 0.14s; }
.results-grid .movie-card:nth-child(8) { animation-delay: 0.16s; }

@keyframes cardEntrance {
  from {
    opacity: 0;
    transform: translateY(24px) scale(0.96);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

.skeleton-card {
  background: var(--bg-card);
  border-radius: var(--radius-md);
  overflow: hidden;
  border: 1px solid var(--border);
}

.skeleton-cover {
  aspect-ratio: 3/4;
  background: linear-gradient(90deg,
    var(--bg-card) 25%,
    rgba(255,255,255,0.05) 50%,
    var(--bg-card) 75%
  );
  background-size: 200% 100%;
  animation: shimmer 1.6s ease-in-out infinite;
}

@keyframes shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
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

.movie-card {
  background: var(--bg-card);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border-radius: var(--radius-md);
  overflow: hidden;
  cursor: pointer;
  transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1),
              box-shadow 0.3s cubic-bezier(0.4, 0, 0.2, 1),
              border-color 0.3s ease;
  border: 1px solid var(--border);
}

.movie-card:hover {
  transform: translateY(-6px) scale(1.02);
  box-shadow: 0 12px 40px rgba(0,0,0,0.5), 0 0 30px var(--accent-glow);
  border-color: var(--accent);
}

.card-cover {
  position: relative;
  width: 100%;
  aspect-ratio: 3/4;
  overflow: hidden;
  background: var(--bg-secondary);
}

.cover-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  object-position: center;
  transition: transform 0.4s cubic-bezier(0.4, 0, 0.2, 1);
}

.movie-card:hover .cover-img {
  transform: scale(1.07);
}

.cover-img.wide {
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
}

/* ===== Mobile Responsive ===== */
@media (max-width: 768px) {
  .search-row-main .search-box-wrapper {
    min-width: 100%;
  }
  .search-row-more .search-box-wrapper {
    min-width: 100%;
  }
  .search-actions {
    flex-wrap: wrap;
  }
  .more-filter-btn {
    flex: 1;
  }
  .main-search-btn {
    flex: 1;
  }
}
</style>
