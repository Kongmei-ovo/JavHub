<template>
  <div class="entities-page page-shell page-shell--workspace">
    <header class="entities-hero apple-surface">
      <div class="entities-hero__copy">
        <span class="entities-kicker">{{ activeConfig.label }}</span>
        <h1>实体目录</h1>
      </div>
      <div class="entities-hero__metrics" aria-label="目录统计">
        <strong>{{ totalLabel }}</strong>
        <button class="btn btn-primary btn-sm" type="button" :disabled="loading" @click="loadEntities">
          {{ loading ? '刷新中...' : '刷新' }}
        </button>
      </div>
    </header>

    <section class="entities-controls apple-surface" aria-label="实体目录筛选">
      <div class="entity-tabs" role="tablist" aria-label="实体类型">
        <button
          v-for="tab in entityTabs"
          :key="tab.key"
          class="entity-tab"
          type="button"
          :class="{ active: activeTab === tab.key }"
          :aria-selected="activeTab === tab.key"
          role="tab"
          @click="switchTab(tab.key)"
        >
          <span>{{ tab.label }}</span>
          <small class="entity-tab-count">{{ tabCountLabel(tab) }}</small>
        </button>
      </div>

      <div class="entity-toolbar">
        <div class="search-box">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" aria-hidden="true">
            <circle cx="11" cy="11" r="7.5"/>
            <path d="m20 20-3.8-3.8"/>
          </svg>
          <input
            v-model="searchKeyword"
            :placeholder="`搜索${activeConfig.label}`"
            @keyup.enter="submitSearch"
          />
          <button v-if="searchKeyword" type="button" aria-label="清空搜索" @click="clearSearch">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
              <path d="M18 6 6 18M6 6l12 12"/>
            </svg>
          </button>
        </div>
        <button class="btn btn-ghost btn-sm" type="button" :disabled="loading" @click="submitSearch">搜索</button>
      </div>
    </section>

    <div
      v-if="loading"
      :class="usesPortraitCards ? 'entity-grid entity-grid--loading' : 'entity-list-grid entity-list-grid--loading'"
      aria-label="实体目录加载中"
    >
      <article
        v-for="n in 12"
        :key="n"
        :class="[usesPortraitCards ? 'entity-card entity-card--skeleton' : 'entity-list-card entity-list-card--skeleton', 'apple-surface']"
        aria-hidden="true"
      >
        <template v-if="usesPortraitCards">
          <div class="entity-card__media apple-skeleton-block"></div>
          <div class="entity-card__body">
            <div class="entity-skeleton-line entity-skeleton-line--short apple-skeleton-block"></div>
            <div class="entity-skeleton-line apple-skeleton-block"></div>
          </div>
        </template>
        <div v-else class="entity-list-card__body">
          <div class="entity-skeleton-line entity-skeleton-line--short apple-skeleton-block"></div>
          <div class="entity-skeleton-line apple-skeleton-block"></div>
          <div class="entity-skeleton-line entity-skeleton-line--tiny apple-skeleton-block"></div>
        </div>
      </article>
    </div>

    <div v-else-if="error" class="state-panel state-panel--error apple-surface">
      <div>
        <strong>目录加载失败</strong>
        <span>{{ error }}</span>
      </div>
      <button class="btn btn-primary btn-sm" type="button" @click="loadEntities">重试</button>
    </div>

    <div v-else-if="items.length === 0" class="state-panel apple-surface">
      <div>
        <strong>暂无{{ activeConfig.label }}</strong>
        <span>换个关键词或实体类型再试试。</span>
      </div>
      <button v-if="searchKeyword" class="btn btn-ghost btn-sm" type="button" @click="clearSearch">清空搜索</button>
    </div>

    <div v-else-if="usesPortraitCards" class="entity-grid">
      <ActorPortraitCard
        v-for="item in items"
        :key="entityKey(item)"
        :actor="entityActorCard(item)"
        :name="displayName(item)"
        :subtitle="secondaryName(item)"
        :avatar-url="entityAvatarUrl(item)"
        :meta="entityMeta(item) || activeConfig.label"
        :show-favorite="canFavoriteEntity"
        :favorited="canFavoriteEntity && isEntityFavorited(item)"
        density="standard"
        @open="openEntity(item)"
        @favorite="toggleEntityFavorite(item)"
      />
    </div>

    <div v-else :class="['entity-list-grid', { 'entity-list-grid--wide': usesWideTextCards }]">
      <article v-for="item in items" :key="entityKey(item)" class="entity-list-card apple-surface">
        <button class="entity-list-card__open" type="button" :aria-label="`打开${displayName(item)}`" @click="openEntity(item)">
          <span class="entity-list-card__type">{{ activeConfig.label }}</span>
          <strong>{{ displayName(item) }}</strong>
          <span v-if="secondaryName(item)" class="entity-list-card__subtitle">{{ secondaryName(item) }}</span>
          <small v-if="entityMeta(item)">{{ entityMeta(item) }}</small>
        </button>

        <button
          v-if="canFavoriteEntity"
          class="entity-list-card__favorite"
          type="button"
          :class="{ active: isEntityFavorited(item) }"
          :title="isEntityFavorited(item) ? '取消收藏' : '收藏'"
          :aria-label="isEntityFavorited(item) ? '取消收藏实体' : '收藏实体'"
          @click="toggleEntityFavorite(item)"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true">
            <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/>
          </svg>
        </button>
      </article>
    </div>

    <footer class="entity-pagination apple-surface">
      <button class="btn btn-ghost btn-sm" type="button" :disabled="page <= 1 || loading" @click="goPage(page - 1)">上一页</button>
      <span>{{ page }} / {{ totalPages }}</span>
      <button class="btn btn-ghost btn-sm" type="button" :disabled="page >= totalPages || loading" @click="goPage(page + 1)">下一页</button>
    </footer>
  </div>
</template>

<script>
import api from '../api'
import { favoriteState } from '../utils/favoriteState'
import ActorPortraitCard from '../components/ActorPortraitCard.vue'
import { actressImgUrl } from '../utils/imageUrl.js'

const ENTITY_TABS = [
  { key: 'actresses', label: '资料库演员', entityType: 'actress', discoveryType: 'actress', loader: 'listActresses', paged: true, portrait: true, favorite: true },
  { key: 'actors', label: 'Emby演员', entityType: 'actor', discoveryType: 'actor', loader: 'listInventoryActors', paged: true, portrait: true, inventoryRoute: true, favorite: false },
  { key: 'categories', label: '题材', entityType: 'category', discoveryType: 'category', loader: 'listCategories', paged: false },
  { key: 'series', label: '系列', entityType: 'series', discoveryType: 'series', loader: 'listSeries', paged: true, wideText: true },
  { key: 'makers', label: '厂商', entityType: 'maker', discoveryType: 'maker', loader: 'listMakers', paged: true },
  { key: 'labels', label: '厂牌', entityType: 'label', discoveryType: 'label', loader: 'listLabels', paged: true },
  { key: 'directors', label: '导演', entityType: 'director', discoveryType: 'director', loader: 'listDirectors', paged: true },
  { key: 'authors', label: '作者', entityType: 'author', discoveryType: 'author', loader: 'listAuthors', paged: true },
]

const ENTITY_LOADERS = {
  listActresses: (page, pageSize, options) => api.listActresses(page, pageSize, options),
  listInventoryActors: (_page, _pageSize, options) => api.listInventoryActors({
    search: options.q,
    page: options.page,
    page_size: options.page_size,
    sort_by: 'total_videos',
    sort_order: 'desc',
  }),
  listCategories: () => api.listCategories(),
  listSeries: (page, pageSize, options) => api.listSeries(page, pageSize, options),
  listMakers: (_page, _pageSize, options) => api.listMakers(options),
  listLabels: (_page, _pageSize, options) => api.listLabels(options),
  listDirectors: (_page, _pageSize, options) => api.listDirectors(options),
  listAuthors: (_page, _pageSize, options) => api.listAuthors(options),
}

export default {
  name: 'Entities',
  components: { ActorPortraitCard },
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
    usesPortraitCards() {
      return this.activeConfig.portrait === true
    },
    usesWideTextCards() {
      return this.activeConfig.wideText === true
    },
    canFavoriteEntity() {
      return this.activeConfig.favorite !== false
    },
    totalLabel() {
      return this.total ? `${this.formatNumber(this.total)} 项` : `${this.items.length} 项`
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
        || item.actress_name || item.title || String(item.id || item.actress_id || '')
    },
    secondaryName(item) {
      const names = [item.name_ja, item.name_en, item.name_romaji, item.name_kana, item.actress_name, item.alias].filter(Boolean)
      return names.find(name => name !== this.displayName(item)) || ''
    },
    entityMeta(item) {
      const count = item.movie_count ?? item.video_count ?? item.total_videos ?? item.count
      return count != null ? `${this.formatNumber(count)} 部作品` : ''
    },
    entityAvatarUrl(item) {
      const rawUrl = item.image_url || item.avatar_url || item.javinfo_avatar_url || item.portrait_url
      return actressImgUrl(rawUrl) || ''
    },
    entityActorCard(item) {
      return {
        ...item,
        id: item.id || item.actress_id || this.displayName(item),
        actress_id: item.actress_id || item.id,
        name: this.displayName(item),
        name_kanji: this.displayName(item),
        image_url: this.entityAvatarUrl(item),
      }
    },
    tabCountLabel(tab) {
      if (tab.key !== this.activeTab) return ''
      if (this.loading) return '...'
      return this.total ? this.formatCompactNumber(this.total) : String(this.items.length)
    },
    isEntityFavorited(item) {
      const id = item.id || item.actress_id || this.displayName(item)
      return favoriteState.isFavorited(this.activeConfig.entityType, String(id))
    },
    formatNumber(value) {
      return new Intl.NumberFormat('zh-CN').format(Number(value) || 0)
    },
    formatCompactNumber(value) {
      return new Intl.NumberFormat('zh-CN', { notation: 'compact', maximumFractionDigits: 1 }).format(Number(value) || 0)
    },
    openEntity(item) {
      const cfg = this.activeConfig
      const name = this.displayName(item)
      const value = item.id || item.actress_id || name
      if (cfg.key === 'actresses') {
        this.$router.push({ path: `/actor/${encodeURIComponent(name)}`, query: value ? { name, actress_id: value } : { name } })
        return
      }
      if (cfg.inventoryRoute) {
        this.$router.push({ path: `/inventory/actors/${encodeURIComponent(String(value))}` })
        return
      }
      this.$router.push({ name: 'DiscoveryDetail', params: { type: cfg.discoveryType, value: String(value) }, query: { name } })
    },
    async toggleEntityFavorite(item) {
      if (!this.canFavoriteEntity) return false
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
  padding-top: clamp(18px, 3vw, 34px);
}

.entities-hero {
  position: relative;
  display: flex;
  align-items: end;
  justify-content: space-between;
  gap: 24px;
  min-height: 148px;
  margin-bottom: 16px;
  padding: clamp(22px, 3vw, 34px);
  overflow: hidden;
  background:
    radial-gradient(circle at 14% 10%, rgba(255,255,255,0.98), transparent 32%),
    radial-gradient(circle at 78% 0%, rgba(180, 192, 211, 0.20), transparent 30%),
    linear-gradient(145deg, rgba(255,255,255,0.82), rgba(246,246,248,0.58));
}

.entities-hero::before {
  content: "";
  position: absolute;
  inset: 0;
  pointer-events: none;
  opacity: 0.52;
  background-image:
    linear-gradient(rgba(29,29,31,0.028) 1px, transparent 1px),
    linear-gradient(90deg, rgba(29,29,31,0.024) 1px, transparent 1px);
  background-size: 34px 34px;
  mask-image: linear-gradient(90deg, rgba(0,0,0,0.75), transparent 72%);
}

.entities-hero__copy,
.entities-hero__metrics {
  position: relative;
  z-index: 1;
}

.entities-kicker {
  display: inline-flex;
  margin-bottom: 10px;
  color: var(--text-secondary);
  font-size: var(--type-caption);
  font-weight: 700;
}

.entities-hero h1 {
  margin: 0;
  font-size: clamp(34px, 5vw, 56px);
  font-weight: 700;
  line-height: 0.96;
  letter-spacing: 0;
}

.entities-hero__metrics {
  display: flex;
  align-items: center;
  gap: 14px;
}

.entities-hero__metrics strong {
  color: var(--text-primary);
  font-size: clamp(20px, 2.4vw, 28px);
  font-weight: 750;
  font-variant-numeric: tabular-nums;
}

.entities-controls {
  position: sticky;
  top: 14px;
  z-index: var(--z-raised);
  display: grid;
  gap: 14px;
  margin-bottom: 18px;
  padding: 12px;
}

.entity-tabs {
  display: grid;
  grid-template-columns: repeat(8, minmax(0, 1fr));
  gap: 7px;
}

.entity-tab {
  display: grid;
  place-items: center;
  min-height: 46px;
  padding: 7px 8px;
  border: 1px solid transparent;
  border-radius: var(--radius-md);
  background: transparent;
  color: var(--text-secondary);
  font: inherit;
  font-size: var(--type-control);
  font-weight: 650;
  cursor: pointer;
  transition: background var(--motion-fast), color var(--motion-fast), transform var(--motion-fast), box-shadow var(--motion-fast), border-color var(--motion-fast);
}

.entity-tab:hover {
  background: rgba(255,255,255,0.46);
  color: var(--text-primary);
}

.entity-tab.active {
  border-color: rgba(255,255,255,0.88);
  background: var(--glass-active-material);
  color: var(--text-primary);
  box-shadow: var(--glass-active-shadow);
}

.entity-tab:active {
  transform: scale(0.985);
}

.entity-tab span,
.entity-tab-count {
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.entity-tab-count {
  min-height: 14px;
  margin-top: 2px;
  color: var(--text-muted);
  font-size: var(--type-micro);
  font-weight: 650;
}

.entity-toolbar {
  display: flex;
  align-items: center;
  gap: 10px;
}

.search-box {
  display: flex;
  align-items: center;
  gap: 9px;
  flex: 1;
  min-height: 46px;
  min-width: 0;
  padding: 0 13px;
  border: 1px solid var(--glass-control-border);
  border-radius: var(--radius-control);
  background: rgba(255,255,255,0.48);
  box-shadow: var(--glass-control-shadow);
  backdrop-filter: blur(18px) saturate(170%);
  -webkit-backdrop-filter: blur(18px) saturate(170%);
  transition: border-color var(--motion-fast), box-shadow var(--motion-fast), background var(--motion-fast);
}

.search-box:focus-within {
  border-color: rgba(29,29,31,0.22);
  background: rgba(255,255,255,0.68);
  box-shadow: var(--glass-control-shadow-hover), 0 0 0 4px rgba(var(--accent-rgb), 0.09);
}

.search-box svg {
  width: 18px;
  height: 18px;
  flex: 0 0 auto;
  color: var(--text-muted);
}

.search-box input {
  flex: 1;
  min-width: 0;
  border: 0;
  background: transparent;
  color: var(--text-primary);
  font: inherit;
  font-size: var(--type-control);
  outline: none;
}

.search-box button {
  display: grid;
  place-items: center;
  width: 30px;
  height: 30px;
  border: 0;
  border-radius: 50%;
  background: rgba(29,29,31,0.07);
  color: var(--text-secondary);
  cursor: pointer;
  transition: background var(--motion-fast), color var(--motion-fast), transform var(--motion-fast);
}

.search-box button:hover {
  background: rgba(29,29,31,0.12);
  color: var(--text-primary);
}

.entity-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(164px, 1fr));
  gap: clamp(14px, 1.8vw, 22px);
}

.entity-list-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 12px;
}

.entity-list-grid--wide {
  grid-template-columns: repeat(auto-fit, minmax(min(100%, 420px), 1fr));
}

.entity-list-card {
  position: relative;
  display: grid;
  min-height: 142px;
  overflow: hidden;
  background:
    linear-gradient(145deg, rgba(255,255,255,0.68), rgba(255,255,255,0.42) 52%, rgba(255,255,255,0.52)),
    var(--surface-card);
  transition: transform var(--motion-standard), border-color var(--motion-standard), box-shadow var(--motion-standard), background var(--motion-standard);
}

.entity-list-card:hover {
  transform: translateY(-3px);
  border-color: var(--glass-edge-strong);
  background: var(--surface-card-hover);
  box-shadow: var(--shadow-floating), var(--glass-surface-shadow);
}

.entity-list-card__open {
  display: grid;
  align-content: start;
  gap: 7px;
  width: 100%;
  min-width: 0;
  padding: 16px 58px 16px 16px;
  border: 0;
  background: transparent;
  color: inherit;
  font: inherit;
  text-align: left;
  cursor: pointer;
}

.entity-list-card__open:focus-visible {
  outline: none;
  border-radius: var(--radius-card);
  box-shadow: inset 0 0 0 4px rgba(var(--accent-rgb), 0.14);
}

.entity-list-card__type {
  width: fit-content;
  max-width: 100%;
  min-height: 21px;
  padding: 3px 8px;
  border-radius: var(--radius-xs);
  background: rgba(var(--accent-rgb), 0.07);
  color: var(--text-secondary);
  font-size: var(--type-badge);
  font-weight: 750;
}

.entity-list-card__open strong,
.entity-list-card__subtitle,
.entity-list-card__open small {
  min-width: 0;
  overflow: hidden;
}

.entity-list-card__open small {
  text-overflow: ellipsis;
  white-space: nowrap;
}

.entity-list-card__open strong {
  margin-top: 2px;
  color: var(--text-primary);
  font-size: var(--type-card-title);
  font-weight: 730;
  line-height: 1.34;
  overflow-wrap: anywhere;
  text-wrap: pretty;
  white-space: normal;
}

.entity-list-card__subtitle {
  color: var(--text-secondary);
  font-size: var(--type-caption);
  line-height: 1.38;
  overflow-wrap: anywhere;
  white-space: normal;
}

.entity-list-card__open small {
  color: var(--text-muted);
  font-size: var(--type-caption);
  line-height: 1.25;
}

.entity-list-card__favorite {
  position: absolute;
  top: 12px;
  right: 12px;
  display: grid;
  place-items: center;
  width: 32px;
  height: 32px;
  padding: 0;
  border: 1px solid var(--glass-control-border);
  border-radius: 50%;
  background: var(--surface-control);
  color: #ff375f;
  box-shadow: var(--glass-control-shadow);
  cursor: pointer;
  backdrop-filter: blur(16px) saturate(170%);
  -webkit-backdrop-filter: blur(16px) saturate(170%);
  transition: transform var(--motion-fast), background var(--motion-fast), color var(--motion-fast), box-shadow var(--motion-fast);
}

.entity-list-card__favorite:hover {
  transform: scale(1.06);
  background: var(--surface-control-hover);
}

.entity-list-card__favorite.active {
  background: rgba(255,55,95,0.92);
  color: #fff;
}

.entity-list-card__favorite svg {
  width: 15px;
  height: 15px;
}

.entity-list-card__favorite.active svg {
  fill: currentColor;
}

.entity-card--skeleton {
  padding: 9px;
}

.entity-card--skeleton:hover {
  transform: none;
}

.entity-list-card--skeleton {
  padding: 15px 16px;
}

.entity-list-card--skeleton:hover {
  transform: none;
}

.entity-list-card__body {
  display: grid;
  align-content: center;
  gap: 10px;
  min-width: 0;
}

.entity-skeleton-line {
  height: 12px;
  width: 86%;
  border-radius: 999px;
}

.entity-skeleton-line--short {
  width: 58%;
}

.entity-skeleton-line--tiny {
  width: 34%;
}

.state-panel {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  max-width: 720px;
  margin: 40px auto;
  padding: 20px 22px;
  color: var(--text-secondary);
}

.state-panel div {
  display: grid;
  gap: 5px;
}

.state-panel strong {
  color: var(--text-primary);
  font-size: var(--type-panel-title);
}

.state-panel span {
  font-size: var(--type-control);
}

.state-panel--error span {
  color: var(--badge-error-text);
}

.entity-pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 18px;
  width: fit-content;
  margin: 24px auto 0;
  padding: 9px;
  border-radius: var(--radius-control);
}

.entity-pagination span {
  min-width: 92px;
  text-align: center;
  color: var(--text-secondary);
  font-size: var(--type-caption);
  font-weight: 700;
}

.btn-sm {
  min-height: 36px;
  padding: 7px 14px;
  font-size: var(--type-caption);
}

:global(:root[data-theme="dark"] .entities-hero) {
  background:
    radial-gradient(circle at 16% 0%, rgba(255,255,255,0.18), transparent 34%),
    radial-gradient(circle at 84% 4%, rgba(255,255,255,0.10), transparent 28%),
    linear-gradient(145deg, rgba(255,255,255,0.115), rgba(14,15,18,0.72) 48%, rgba(255,255,255,0.070));
}

:global(:root[data-theme="dark"] .entities-hero::before) {
  opacity: 0.28;
  background-image:
    linear-gradient(rgba(255,255,255,0.055) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255,255,255,0.045) 1px, transparent 1px);
}

:global(:root[data-theme="dark"] .search-box),
:global(:root[data-theme="dark"] .entity-list-card) {
  border-color: rgba(255,255,255,0.16);
  background:
    linear-gradient(145deg, rgba(255,255,255,0.155), rgba(18,19,21,0.54) 50%, rgba(255,255,255,0.085));
  box-shadow: var(--glass-surface-shadow);
}

:global(:root[data-theme="dark"] .search-box:focus-within) {
  border-color: rgba(255,255,255,0.28);
  background:
    linear-gradient(145deg, rgba(255,255,255,0.19), rgba(26,27,30,0.58) 50%, rgba(255,255,255,0.11));
  box-shadow: var(--glass-control-shadow-hover), 0 0 0 4px rgba(255,255,255,0.08);
}

:global(:root[data-theme="dark"] .search-box button) {
  background: rgba(255,255,255,0.09);
}

:global(:root[data-theme="dark"] .search-box button:hover) {
  background: rgba(255,255,255,0.15);
}

:global(:root[data-theme="dark"] .entity-list-card:hover) {
  background: var(--surface-card-hover);
}

:global(:root[data-theme="dark"] .entity-list-card__type) {
  background: rgba(255,255,255,0.09);
}

@media (max-width: 1180px) {
  .entity-tabs {
    grid-template-columns: repeat(4, minmax(0, 1fr));
  }
}

@media (max-width: 768px) {
  .entities-page {
    padding-top: 14px;
  }

  .entities-hero,
  .entities-hero__metrics,
  .state-panel {
    align-items: stretch;
    flex-direction: column;
  }

  .entities-hero {
    min-height: 0;
  }

  .entities-controls {
    position: static;
  }

  .entity-tabs {
    grid-template-columns: repeat(4, minmax(0, 1fr));
  }

  .entity-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 12px;
  }

  .entity-list-grid {
    grid-template-columns: 1fr;
    gap: 10px;
  }

  .entity-card--skeleton {
    padding: 7px;
  }

  .entity-list-card {
    min-height: 132px;
  }

  .entity-list-card__open {
    padding: 13px 50px 13px 14px;
  }

  .entity-pagination {
    width: 100%;
  }
}
</style>
