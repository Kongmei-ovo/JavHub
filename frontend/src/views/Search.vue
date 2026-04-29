<template>
  <div class="search-page">
    <!-- 顶部工具栏（仅从详情页跳转来时显示） -->
    <div v-if="$route.query.returnTo === 'video'" class="search-back-toolbar">
      <button class="back-btn" @click="$router.back()">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="14" height="14">
          <polyline points="15 18 9 12 15 6"/>
        </svg>
        返回详情
      </button>
    </div>

    <!-- 搜索核心区域 -->
    <div class="search-hero">
      <h1 class="hero-title">发现</h1>
      <p class="hero-subtitle">搜索影片、番号、演员或工作室</p>
      
      <div class="command-capsule-container">
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

          <button @click="doSearch" :disabled="loading" class="capsule-search-btn" title="开始探索">
            <span v-if="loading" class="spinner"></span>
            <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" width="18" height="18">
              <circle cx="11" cy="11" r="8"/>
              <path d="m21 21-4.35-4.35"/>
            </svg>
          </button>
        </div>

        <!-- 快速筛选盘 (Filter Tray) -->
        <div class="filter-tray">
          <div class="filter-group">
            <div class="filter-item">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="14" height="14">
                <path d="M12 2.69l5.66 5.66a8 8 0 11-11.31 0z"/>
              </svg>
              <select v-model="serviceCode" class="tray-select">
                <option value="">全部版本</option>
                <option v-for="sc in serviceCodeOptions" :key="sc.value" :value="sc.value">{{ sc.label }}</option>
              </select>
            </div>
            
            <button class="filter-item toggle" :class="{ active: showMoreFilters }" @click="showMoreFilters = !showMoreFilters">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="14" height="14">
                <path d="M20 7h-9m14 10h-9M5 7h14M5 17h14"/><circle cx="7" cy="7" r="2"/><circle cx="17" cy="17" r="2"/>
              </svg>
              高级筛选
            </button>
          </div>
        </div>

        <!-- 高级筛选详情面板 -->
        <transition name="tray-slide">
          <div v-if="showMoreFilters" class="advanced-panel">
            <div class="panel-grid">
              <div class="panel-field">
                <label>工作室</label>
                <input v-model="makerName" placeholder="Maker Name" class="panel-input" @keyup.enter="doSearch" />
              </div>
              <div class="panel-field">
                <label>演员</label>
                <input v-model="actressName" placeholder="Actress Name" class="panel-input" @keyup.enter="doSearch" />
              </div>
              <div class="panel-field">
                <label>系列</label>
                <input v-model="seriesName" placeholder="Series Name" class="panel-input" @keyup.enter="doSearch" />
              </div>
              <div class="panel-field">
                <label>年份</label>
                <input v-model.number="year" placeholder="YYYY" type="number" class="panel-input" @keyup.enter="doSearch" />
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
              <button class="btn-clear" @click="clearFilters">重置</button>
              <button class="btn-apply" @click="doSearch">查看结果</button>
            </div>
          </div>
        </transition>
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
          <!-- Favorite Toggle -->
          <button 
            class="favorite-toggle" 
            :class="{ 'is-active': isFavorited('video', item.dvd_id || item.content_id) }" 
            @click.stop="toggleFavorite(item)"
          >
            <svg viewBox="0 0 24 24" :fill="isFavorited('video', item.dvd_id || item.content_id) ? 'currentColor' : 'none'" stroke="currentColor" stroke-width="2">
              <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l8.84-8.84 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/>
            </svg>
          </button>
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
import favoriteState from '../utils/favoriteState'

export default {
  name: 'Search',
  data() {
...
    isFavorited(type, id) {
      return favoriteState.isFavorited(type, id)
    },
    async toggleFavorite(item) {
      try {
        const id = item.dvd_id || item.content_id
        await favoriteState.toggle('video', id, {
          title: item.title_en_translated || item.title_ja_translated || item.title_en || item.title_ja,
          jacket_thumb_url: this.cardImageUrl(item)
        })
      } catch (err) {
        console.error('Failed to toggle favorite:', err)
      }
    },
    async doSearch() {

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
      jumpPage: null,
      isSearchFocused: false,
      isComposing: false
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
    if (q.actress !== undefined && q.actress !== this.actressName) { this.actressName = q.actress; changed = true }
    if (q.maker !== undefined && q.maker !== this.makerName) { this.makerName = q.maker; changed = true }
    if (q.series !== undefined && q.series !== this.seriesName) { this.seriesName = q.series; changed = true }
    if (q.q !== undefined && q.q !== this.keyword) { this.keyword = q.q; changed = true }
    if (q.keyword !== undefined && q.keyword !== this.keyword) { this.keyword = q.keyword; changed = true }
    
    // 处理题材标签
    if (q.category_name !== undefined) {
      const tags = q.category_name.split(' ').filter(t => t)
      if (JSON.stringify(tags) !== JSON.stringify(this.categoryTags)) {
        this.categoryTags = tags
        changed = true
      }
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
      
      if (q.category_name !== undefined) {
        const tags = q.category_name.split(' ').filter(t => t)
        if (JSON.stringify(tags) !== JSON.stringify(this.categoryTags)) {
          this.categoryTags = tags
          changed = true
        }
      }

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
      const contentId = video.content_id || video.dvd_id

      // 先获取 JavInfoApi 完整数据，再打开弹窗（避免多次渲染）
      let fullVideo = { ...video }
      try {
        const resp = await api.getVideo(contentId)
        if (resp.data) {
          fullVideo = { ...video, ...resp.data }
        }
      } catch (e) {
        console.error('Load video detail failed:', e)
      }

      // 打开弹窗，使用完整数据（一次渲染到位）
      openVideoModal(fullVideo, this.$route.path)

      // 异步获取外部元数据（简介、评分等），不阻塞前台
      api.getVideoMetadata(contentId).then(resp => {
        if (resp.data && Object.keys(resp.data).length > 0) {
          openVideoModal({ ...modalState.selectedVideo, ...resp.data }, this.$route.path)
        }
      }).catch(e => console.warn('Load lazy metadata failed:', e))
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
/* ================================================
   ✨ 指令胶囊 (Command Capsule) - Search 2.0
   ================================================ */

.search-hero {
  padding: 60px 20px 40px;
  background: var(--bg-primary);
  text-align: center;
}

.hero-title {
  font-size: 48px;
  font-weight: 800;
  letter-spacing: -0.04em;
  margin-bottom: 8px;
  background: linear-gradient(135deg, var(--text-primary) 0%, var(--text-secondary) 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.hero-subtitle {
  font-size: 15px;
  color: var(--text-muted);
  margin-bottom: 40px;
  letter-spacing: 0.02em;
}

.command-capsule-container {
  max-width: 800px;
  margin: 0 auto;
  position: relative;
  z-index: 10;
}

/* 主胶囊容器 */
.command-capsule {
  display: flex;
  align-items: center;
  background: rgba(255, 255, 255, 0.03);
  backdrop-filter: blur(30px);
  -webkit-backdrop-filter: blur(30px);
  border: 1px solid var(--border-light);
  border-radius: 30px;
  padding: 6px 6px 6px 24px;
  transition: all 0.5s var(--ease-pro);
  box-shadow: 0 20px 50px rgba(0, 0, 0, 0.3);
}

.command-capsule.focused {
  background: rgba(255, 255, 255, 0.06);
  border-color: var(--accent);
  box-shadow: 0 30px 80px rgba(0, 0, 0, 0.5), 0 0 0 4px rgba(255, 255, 255, 0.03);
  transform: scale(1.01);
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
  font-size: 15px;
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
  background: var(--text-primary);
  color: var(--bg-primary);
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
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.4);
}

.capsule-search-btn:hover {
  background: var(--accent);
  transform: scale(1.1) rotate(5deg);
  box-shadow: 0 0 20px var(--accent-glow);
}

.capsule-search-btn:active {
  transform: scale(0.9);
}

/* 筛选盘 (Filter Tray) */
.filter-tray {
  margin-top: 24px;
  display: flex;
  justify-content: center;
}

.filter-group {
  display: flex;
  gap: 10px;
}

.filter-item {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid var(--border);
  border-radius: 20px;
  padding: 0 20px;
  height: 38px;
  min-width: 150px;
  color: var(--text-secondary);
  font-size: 13px;
  cursor: pointer;
  transition: all 0.3s var(--ease-pro);
}

.filter-item:hover {
  background: rgba(255, 255, 255, 0.08);
  border-color: var(--border-light);
}

.filter-item.toggle.active {
  background: var(--accent-bg);
  border-color: var(--accent);
  color: var(--accent);
}

.tray-select {
  background: transparent;
  border: none;
  color: inherit;
  font-size: inherit;
  outline: none;
  cursor: pointer;
  padding-right: 4px;
}

/* 高级面板 (Advanced Panel) - 绝对定位消除重排 */
.advanced-panel {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  margin-top: 16px;
  background: var(--bg-card);
  backdrop-filter: blur(25px);
  -webkit-backdrop-filter: blur(25px);
  border: 1px solid var(--border-light);
  border-radius: 24px;
  padding: 32px;
  box-shadow: 0 40px 100px rgba(0, 0, 0, 0.6);
  z-index: 100;
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
  font-size: 12px;
  font-weight: 600;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  padding-left: 4px;
}

.panel-input {
  background: rgba(0, 0, 0, 0.2);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 12px 16px;
  color: var(--text-primary);
  font-size: 14px;
  transition: all 0.3s var(--ease-pro);
}

.panel-input:focus {
  border-color: var(--accent);
  background: rgba(0, 0, 0, 0.3);
  outline: none;
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
  background: var(--white-10);
  border: 1px solid var(--border-light);
  color: var(--text-primary);
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 12px;
  display: flex;
  align-items: center;
  gap: 6px;
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
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid var(--border);
  color: var(--text-secondary);
  padding: 10px 24px;
  border-radius: 12px;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.3s var(--ease-pro);
}

.btn-clear:hover {
  background: rgba(255, 255, 255, 0.1);
  color: var(--text-primary);
}

.btn-apply {
  background: linear-gradient(135deg, #fcf6ba 0%, #d4af37 100%);
  color: #121212;
  border: none;
  padding: 10px 36px;
  border-radius: 12px;
  font-weight: 700;
  cursor: pointer;
  font-size: 14px;
  box-shadow: 0 4px 20px rgba(212, 175, 55, 0.2);
  transition: all 0.3s var(--ease-pro);
}

.btn-apply:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 30px rgba(212, 175, 55, 0.4);
  filter: brightness(1.1);
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
  padding: 40px 20px;
  max-width: 1600px;
  margin: 0 auto;
}

.result-bar {
  max-width: 1600px;
  margin: 0 auto;
  padding: 20px;
  border-bottom: 1px solid var(--border);
}

.pagination-bar {
  padding: 30px 20px;
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

/* ===== 恢复旧版电影卡片样式 ===== */
.skeleton-card {
  background: var(--bg-card);
  border-radius: var(--radius-md);
  overflow: hidden;
  border: 1px solid var(--border);
}

.skeleton-cover {
  aspect-ratio: 3/4;
  background: var(--bg-card-hover);
  animation: pulse 2s infinite ease-in-out;
}

@keyframes pulse {
  0% { opacity: 1; }
  50% { opacity: 0.5; }
  100% { opacity: 1; }
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
  transition: all 0.3s cubic-bezier(0.2, 0, 0, 1);
  border: 1px solid var(--border);
}

.movie-card:hover {
  transform: translateY(-4px);
  box-shadow: var(--shadow-hover);
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
  transform: scale(1.05);
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

.jump-wrap { display: flex; align-items: center; gap: 4px; margin-left: 12px; }
.jump-input {
  width: 56px; 
  padding: 6px 8px; 
  border: 1px solid var(--border);
  border-radius: var(--radius-md); 
  background: var(--bg-card); 
  color: var(--text-primary);
  font-size: 12px; 
  text-align: center;
  transition: var(--transition-pro);
}
.jump-input:focus {
  outline: none;
  border-color: var(--accent);
  background: var(--bg-card-hover);
}
.jump-input::-webkit-inner-spin-button,
.jump-input::-webkit-outer-spin-button { -webkit-appearance: none; }
.jump-btn {
  background: var(--bg-secondary); 
  border: 1px solid var(--border);
  color: var(--text-primary); 
  padding: 6px 14px; 
  border-radius: var(--radius-md);
  cursor: pointer; 
  font-size: 12px; 
  transition: var(--transition-pro);
}
.jump-btn:hover { 
  border-color: var(--accent); 
  color: var(--accent); 
  background: var(--bg-card-hover);
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

/* ===== Mobile Responsive ===== */
@media (max-width: 768px) {
  .results-grid {
    grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
    gap: 16px;
    padding: 20px;
  }
  .panel-grid {
    grid-template-columns: 1fr;
  }
  .panel-field.full {
    grid-column: span 1;
  }
  .hero-title {
    font-size: 32px;
  }
  .command-capsule {
    padding: 4px 4px 4px 16px;
  }
  .capsule-divider {
    margin: 0 6px;
  }
  .filter-tray {
    flex-direction: column;
    align-items: center;
    gap: 12px;
  }
}
</style>
