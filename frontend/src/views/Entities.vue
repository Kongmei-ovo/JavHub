<template>
  <div class="entities-page page-shell page-shell--workspace">
    <header class="entities-hero apple-surface">
      <div class="entities-hero__copy">
        <span class="entities-kicker">{{ activeConfig.label }}</span>
        <h1>分类目录</h1>
      </div>
      <div class="entities-hero__metrics" aria-label="目录统计">
        <strong>{{ totalLabel }}</strong>
        <button class="btn btn-primary btn-sm" type="button" :disabled="loading" @click="loadEntities">
          {{ loading ? '刷新中...' : '刷新' }}
        </button>
      </div>
    </header>

    <section class="entities-controls apple-surface" aria-label="分类目录筛选">
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

    <AppleSkeleton v-if="loading" :class="usesPortraitCards ? 'entity-grid entity-grid--loading' : 'entity-list-grid entity-list-grid--loading'" :variant="usesPortraitCards ? 'gallery' : 'list'" :items="12" :columns="usesPortraitCards ? 'repeat(auto-fill, minmax(148px, 1fr))' : 'repeat(auto-fit, minmax(min(100%, 320px), 1fr))'" label="分类目录加载中" />

    <AppleErrorState v-else-if="error" class="state-panel state-panel--error" title="目录加载失败" :description="error" next-step="重新加载会保留当前目录类型和搜索条件；如果仍失败，可以查看运行日志。" retry-label="重试" secondary-action-label="查看日志" @retry="loadEntities" @secondary-action="$router.push('/logs')" />

    <AppleEmptyState v-else-if="items.length === 0" class="state-panel" :title="`暂无${activeConfig.label}`" description="当前目录没有匹配的实体。" next-step="可以清空搜索查看全部实体，或切换到资料库演员继续浏览。" action-label="清空搜索" secondary-action-label="资料库演员" density="compact" @action="clearSearch" @secondary-action="switchTab('actresses')" />

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
import AppleSkeleton from '../components/AppleSkeleton.vue'
import AppleEmptyState from '../components/AppleEmptyState.vue'
import AppleErrorState from '../components/AppleErrorState.vue'
import { actressImgUrl } from '../utils/imageUrl.js'

const ENTITY_TABS = [
  { key: 'actresses', label: '资料库演员', entityType: 'actress', discoveryType: 'actress', loader: 'listActresses', paged: true, portrait: true, favorite: true },
  { key: 'categories', label: '题材', entityType: 'category', discoveryType: 'category', loader: 'listCategories', paged: false },
  { key: 'series', label: '系列', entityType: 'series', discoveryType: 'series', loader: 'listSeries', paged: true, wideText: true },
  { key: 'makers', label: '厂商', entityType: 'maker', discoveryType: 'maker', loader: 'listMakers', paged: true },
  { key: 'labels', label: '厂牌', entityType: 'label', discoveryType: 'label', loader: 'listLabels', paged: true },
  { key: 'directors', label: '导演', entityType: 'director', discoveryType: 'director', loader: 'listDirectors', paged: true },
  { key: 'authors', label: '作者', entityType: 'author', discoveryType: 'author', loader: 'listAuthors', paged: true },
]

const ENTITY_LOADERS = {
  listActresses: (page, pageSize, options) => api.listActresses(page, pageSize, options),
  listCategories: () => api.listCategories(),
  listSeries: (page, pageSize, options) => api.listSeries(page, pageSize, options),
  listMakers: (_page, _pageSize, options) => api.listMakers(options),
  listLabels: (_page, _pageSize, options) => api.listLabels(options),
  listDirectors: (_page, _pageSize, options) => api.listDirectors(options),
  listAuthors: (_page, _pageSize, options) => api.listAuthors(options),
}

export default {
  name: 'Entities',
  components: { ActorPortraitCard, AppleSkeleton, AppleEmptyState, AppleErrorState },
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
      tabCounts: {},
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
    this.loadTabCounts()
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
      const total = this.resolveTotal(data, filtered.length)
      const rawPages = Number(data?.total_pages)
      const totalPages = Number.isFinite(rawPages) && rawPages >= 1
        ? rawPages
        : Math.max(1, Math.ceil(total / this.pageSize))
      return { items: filtered, total, totalPages }
    },
    resolveTotal(data, fallback) {
      // 上游在 include_total=false 时会返回 -1，需回退到本页条数
      const raw = Number(data?.total ?? data?.total_count)
      return Number.isFinite(raw) && raw >= 0 ? raw : fallback
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
      // 搜索时活动 tab 显示过滤后的总数；其余 tab 始终显示全局数量
      if (tab.key === this.activeTab && this.searchKeyword) {
        if (this.loading) return '...'
        return this.formatCompactNumber(this.total || this.items.length)
      }
      const count = this.tabCounts[tab.key]
      if (count != null) return this.formatCompactNumber(count)
      if (tab.key === this.activeTab && !this.loading) {
        return this.formatCompactNumber(this.total || this.items.length)
      }
      return ''
    },
    async loadTabCounts() {
      await Promise.all(this.entityTabs.map(async (tab) => {
        try {
          const resp = await ENTITY_LOADERS[tab.loader](1, 1, { page: 1, page_size: 1 })
          const data = resp.data
          let count
          if (tab.paged) {
            const raw = Number(data?.total ?? data?.total_count)
            count = Number.isFinite(raw) && raw >= 0 ? raw : undefined
          } else {
            const arr = Array.isArray(data) ? data : (data?.data || data?.items || [])
            count = arr.length
          }
          if (count != null) this.tabCounts = { ...this.tabCounts, [tab.key]: count }
        } catch (err) {
          /* 单个分类统计失败不影响其他 tab */
        }
      }))
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

<style scoped src="../features/entities/entities.css"></style>
