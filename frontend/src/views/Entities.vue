<template>
  <div class="entities-page page-shell page-shell--workspace">
    <header class="entities-header">
      <div>
        <h1>实体目录</h1>
        <p>{{ activeConfig.label }} · {{ totalLabel }}</p>
      </div>
      <button class="btn btn-primary btn-sm" type="button" :disabled="loading" @click="loadEntities">
        {{ loading ? '刷新中...' : '刷新' }}
      </button>
    </header>

    <div class="entity-tabs" role="tablist" aria-label="实体类型">
      <button
        v-for="tab in entityTabs"
        :key="tab.key"
        class="entity-tab"
        type="button"
        :class="{ active: activeTab === tab.key }"
        @click="switchTab(tab.key)"
      >
        {{ tab.label }}
      </button>
    </div>

    <section class="entity-toolbar">
      <div class="search-box">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
          <circle cx="11" cy="11" r="8"/>
          <path d="m21 21-4.35-4.35"/>
        </svg>
        <input
          v-model="searchKeyword"
          :placeholder="`搜索${activeConfig.label}`"
          @keyup.enter="submitSearch"
        />
        <button v-if="searchKeyword" type="button" aria-label="清空搜索" @click="clearSearch">×</button>
      </div>
      <button class="btn btn-ghost btn-sm" type="button" @click="submitSearch">搜索</button>
    </section>

    <div v-if="loading" class="state-panel">加载中...</div>
    <div v-else-if="error" class="state-panel error">
      <strong>目录加载失败</strong>
      <span>{{ error }}</span>
      <button class="btn btn-primary btn-sm" type="button" @click="loadEntities">重试</button>
    </div>
    <div v-else-if="items.length === 0" class="state-panel">暂无{{ activeConfig.label }}</div>

    <div v-else class="entity-grid">
      <article v-for="item in items" :key="entityKey(item)" class="entity-card">
        <button class="entity-main" type="button" @click="openEntity(item)">
          <strong>{{ displayName(item) }}</strong>
          <span>{{ secondaryName(item) }}</span>
          <small>{{ entityMeta(item) }}</small>
        </button>
        <button class="entity-fav" type="button" title="收藏" aria-label="收藏实体" @click="toggleEntityFavorite(item)">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7">
            <path d="M20.84 4.61a5.5 5.5 0 00-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 00-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 000-7.78z"/>
          </svg>
        </button>
      </article>
    </div>

    <footer class="entity-pagination">
      <button class="btn btn-ghost btn-sm" type="button" :disabled="page <= 1 || loading" @click="goPage(page - 1)">上一页</button>
      <span>{{ page }} / {{ totalPages }}</span>
      <button class="btn btn-ghost btn-sm" type="button" :disabled="page >= totalPages || loading" @click="goPage(page + 1)">下一页</button>
    </footer>
  </div>
</template>

<script>
import api from '../api'
import { favoriteState } from '../utils/favoriteState'

const ENTITY_TABS = [
  { key: 'actresses', label: 'JavInfo演员', entityType: 'actress', discoveryType: 'actress', loader: 'listActresses', paged: true },
  { key: 'actors', label: '演员', entityType: 'actor', discoveryType: 'actor', loader: 'listActors', paged: true },
  { key: 'categories', label: '题材', entityType: 'category', discoveryType: 'category', loader: 'listCategories', paged: false },
  { key: 'series', label: '系列', entityType: 'series', discoveryType: 'series', loader: 'listSeries', paged: true },
  { key: 'makers', label: '厂商', entityType: 'maker', discoveryType: 'maker', loader: 'listMakers', paged: true },
  { key: 'labels', label: '厂牌', entityType: 'label', discoveryType: 'label', loader: 'listLabels', paged: true },
  { key: 'directors', label: '导演', entityType: 'director', discoveryType: 'director', loader: 'listDirectors', paged: true },
  { key: 'authors', label: '作者', entityType: 'author', discoveryType: 'author', loader: 'listAuthors', paged: true },
]

const ENTITY_LOADERS = {
  listActresses: (page, pageSize, options) => api.listActresses(page, pageSize, options),
  listActors: (_page, _pageSize, options) => api.listActors(options),
  listCategories: () => api.listCategories(),
  listSeries: (page, pageSize, options) => api.listSeries(page, pageSize, options),
  listMakers: (_page, _pageSize, options) => api.listMakers(options),
  listLabels: (_page, _pageSize, options) => api.listLabels(options),
  listDirectors: (_page, _pageSize, options) => api.listDirectors(options),
  listAuthors: (_page, _pageSize, options) => api.listAuthors(options),
}

export default {
  name: 'Entities',
  data() {
    return {
      entityTabs: ENTITY_TABS,
      activeTab: this.$route.query.tab || 'actresses',
      searchKeyword: this.$route.query.q || '',
      page: Number(this.$route.query.page || 1) || 1,
      pageSize: 36,
      total: 0,
      totalPages: 1,
      items: [],
      loading: false,
      error: '',
    }
  },
  computed: {
    activeConfig() {
      return this.entityTabs.find(tab => tab.key === this.activeTab) || this.entityTabs[0]
    },
    totalLabel() {
      return this.total ? `${this.total} 项` : `${this.items.length} 项`
    },
  },
  mounted() {
    this.loadEntities()
  },
  watch: {
    '$route.query'(query) {
      const nextTab = query.tab || 'actresses'
      const nextQ = query.q || ''
      const nextPage = Number(query.page || 1) || 1
      if (nextTab === this.activeTab && nextQ === this.searchKeyword && nextPage === this.page) return
      this.activeTab = nextTab
      this.searchKeyword = nextQ
      this.page = nextPage
      this.loadEntities()
    },
  },
  methods: {
    syncRoute() {
      const query = { tab: this.activeTab }
      if (this.searchKeyword) query.q = this.searchKeyword
      if (this.page > 1) query.page = String(this.page)
      this.$router.replace({ path: '/entities', query }).catch(() => {})
    },
    async loadEntities() {
      this.loading = true
      this.error = ''
      try {
        const cfg = this.activeConfig
        const options = { q: this.searchKeyword || undefined, page: this.page, page_size: this.pageSize }
        const resp = await ENTITY_LOADERS[cfg.loader](this.page, this.pageSize, options)
        const normalized = this.normalizeResponse(resp.data)
        this.items = normalized.items
        this.total = normalized.total
        this.totalPages = normalized.totalPages
        this.syncRoute()
      } catch (err) {
        this.error = err.response?.data?.detail || err.message || '加载失败'
      } finally {
        this.loading = false
      }
    },
    normalizeResponse(data) {
      const items = Array.isArray(data) ? data : (data?.data || data?.items || [])
      const filtered = this.activeConfig.paged ? items : this.filterClientSide(items)
      const total = Number(data?.total || data?.total_count || filtered.length) || filtered.length
      const totalPages = Number(data?.total_pages || Math.max(1, Math.ceil(total / this.pageSize))) || 1
      return { items: filtered, total, totalPages }
    },
    filterClientSide(items) {
      const q = this.searchKeyword.trim().toLowerCase()
      if (!q) return items
      return items.filter(item => this.displayName(item).toLowerCase().includes(q) || this.secondaryName(item).toLowerCase().includes(q))
    },
    switchTab(tab) {
      if (tab === this.activeTab) return
      this.activeTab = tab
      this.page = 1
      this.items = []
      this.loadEntities()
    },
    submitSearch() {
      this.page = 1
      this.loadEntities()
    },
    clearSearch() {
      this.searchKeyword = ''
      this.submitSearch()
    },
    goPage(page) {
      this.page = Math.max(1, Math.min(this.totalPages, page))
      this.loadEntities()
    },
    entityKey(item) {
      return `${this.activeConfig.key}:${item.id || item.actress_id || item.name || item.name_ja || item.name_en}`
    },
    displayName(item) {
      return item.name_translated || item.name_ja_translated || item.name_en_translated
        || item.name_kanji_translated || item.name_romaji_translated
        || item.display_name || item.name_kanji || item.name_ja || item.name_en || item.name_romaji || item.name
        || item.title || String(item.id || item.actress_id || '')
    },
    secondaryName(item) {
      const names = [item.name_ja, item.name_en, item.name_romaji, item.alias].filter(Boolean)
      return names.find(name => name !== this.displayName(item)) || ''
    },
    entityMeta(item) {
      const count = item.movie_count ?? item.video_count ?? item.total_videos ?? item.count
      const id = item.id || item.actress_id
      return [id ? `ID ${id}` : '', count != null ? `${count} 部作品` : ''].filter(Boolean).join(' · ')
    },
    openEntity(item) {
      const cfg = this.activeConfig
      const name = this.displayName(item)
      const value = item.id || item.actress_id || name
      if (cfg.key === 'actresses') {
        this.$router.push({ path: `/actor/${encodeURIComponent(name)}`, query: value ? { name, actress_id: value } : { name } })
        return
      }
      this.$router.push({ name: 'DiscoveryDetail', params: { type: cfg.discoveryType, value: String(value) }, query: { name } })
    },
    async toggleEntityFavorite(item) {
      const cfg = this.activeConfig
      const id = item.id || item.actress_id || this.displayName(item)
      await favoriteState.toggle(cfg.entityType, String(id), item)
    },
  },
}
</script>

<style scoped>
.entities-page {
  min-height: 100dvh;
}

.entities-header,
.entity-toolbar,
.entity-pagination {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.entities-header {
  margin-bottom: 14px;
  padding-bottom: 10px;
  border-bottom: 1px solid var(--border-light);
}

.entities-header h1 {
  margin: 0;
  font-size: var(--type-workbench-title);
  letter-spacing: 0;
}

.entities-header p {
  margin: 4px 0 0;
  color: var(--text-secondary);
  font-size: var(--type-caption);
}

.entity-tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 12px;
}

.entity-tab {
  min-height: 36px;
  padding: 7px 12px;
  border: 1px solid var(--glass-control-border);
  border-radius: var(--radius-control);
  background: var(--material-glass-subtle);
  color: var(--text-secondary);
  cursor: pointer;
}

.entity-tab.active {
  background: var(--glass-active-material);
  color: var(--text-primary);
  border-color: var(--glass-active-border);
  box-shadow: var(--glass-active-shadow);
}

.entity-toolbar {
  margin-bottom: 12px;
}

.search-box {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 1;
  min-height: 42px;
  padding: 0 12px;
  border: 1px solid var(--border);
  border-radius: var(--radius-control);
  background: var(--surface-card);
}

.search-box svg {
  width: 18px;
  height: 18px;
  color: var(--text-muted);
}

.search-box input {
  flex: 1;
  min-width: 0;
  border: 0;
  background: transparent;
  color: var(--text-primary);
  font: inherit;
  outline: none;
}

.search-box button {
  width: 30px;
  height: 30px;
  border: 0;
  border-radius: 999px;
  background: transparent;
  color: var(--text-secondary);
  cursor: pointer;
}

.entity-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 10px;
}

.entity-card {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 38px;
  gap: 8px;
  align-items: stretch;
  min-width: 0;
  padding: 10px;
  border: 1px solid var(--border-light);
  border-radius: var(--radius-md);
  background: var(--surface-card);
}

.entity-main {
  display: grid;
  gap: 4px;
  min-width: 0;
  border: 0;
  background: transparent;
  color: var(--text-primary);
  text-align: left;
  cursor: pointer;
}

.entity-main strong,
.entity-main span,
.entity-main small {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.entity-main span,
.entity-main small {
  color: var(--text-secondary);
  font-size: 12px;
}

.entity-fav {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 38px;
  height: 38px;
  border: 1px solid var(--border-light);
  border-radius: 999px;
  background: var(--surface-control);
  color: #ff375f;
  cursor: pointer;
}

.entity-fav svg {
  width: 16px;
  height: 16px;
}

.state-panel {
  display: grid;
  justify-items: center;
  gap: 8px;
  padding: 42px;
  border: 1px solid var(--border-light);
  border-radius: var(--radius-lg);
  background: var(--surface-card);
  color: var(--text-secondary);
}

.state-panel.error {
  color: var(--badge-error-text);
}

.entity-pagination {
  justify-content: center;
  margin-top: 18px;
}

.entity-pagination span {
  min-width: 90px;
  text-align: center;
  color: var(--text-secondary);
  font-size: 12px;
}

@media (max-width: 768px) {
  .entities-header,
  .entity-toolbar {
    align-items: stretch;
    flex-direction: column;
  }

  .entity-grid {
    grid-template-columns: 1fr;
  }
}
</style>
