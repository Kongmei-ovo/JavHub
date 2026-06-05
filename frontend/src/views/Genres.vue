<template>
  <div class="genres-page page-bleed">
    <!-- 顶部 Tab 栏 -->
    <div class="genres-hero">
      <h1 class="hero-title">随机探索</h1>
      <p class="hero-subtitle">随机浏览，发现更多内容</p>
      <div class="tab-bar" role="tablist" aria-label="探索类型">
        <button
          v-for="tab in tabs"
          :key="tab.key"
          class="tab-btn"
          type="button"
          role="tab"
          :aria-selected="activeTab === tab.key"
          :class="{ active: activeTab === tab.key }"
          @click="switchTab(tab.key)"
        >
          {{ tab.label }}
        </button>
      </div>
    </div>

    <!-- 题材 Tab：气泡云 -->
    <div v-if="activeTab === 'genre'" class="tag-cloud-wrap page-rail page-rail--standard" ref="cloudRef" role="tabpanel">
      <div class="cloud-header">
        <span class="cloud-hint"></span>
        <button class="shuffle-btn" type="button" @click="reshuffle" :disabled="loading">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="14" height="14">
            <polyline points="23 4 23 10 17 10"/>
            <polyline points="1 20 1 14 7 14"/>
            <path d="M3.51 9a9 9 0 0114.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0020.49 15"/>
          </svg>
          换一批
        </button>
      </div>

      <div v-if="loading" class="loading-wrap">
        <div class="spinner-large"></div>
        <p>加载题材中...</p>
      </div>

      <AppleErrorState
        v-else-if="categoryError"
        title="题材加载失败"
        description="数据源当前不可用，探索内容暂时不能刷新。"
        retry-label="重试"
        @retry="reloadGenreData"
      />

      <div v-else ref="tagCloudRef" class="tag-cloud" :style="cloudStyle">
        <template v-for="(tag, index) in mobileDisplayedTags" :key="`${tag.id}-${genreAnimationToken}`">
          <button
            class="bubble"
            type="button"
            :data-id="tag.id"
            :style="bubbleStyle(tag, index)"
            @click="goGenre(tag)"
          >
            <div class="bubble-content">
              {{ displayName(tag, 'name_ja', 'name_en') || tag.name }}
            </div>
          </button>
        </template>
      </div>
    </div>

    <!-- 演员 Tab：头像卡片 -->
    <div v-if="activeTab === 'actress'" class="actress-tab page-rail page-rail--standard" role="tabpanel">
      <div class="cloud-header">
        <span class="cloud-hint"></span>
        <button class="shuffle-btn" type="button" @click="shuffleActresses" :disabled="actressesLoading">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="14" height="14">
            <polyline points="23 4 23 10 17 10"/>
            <polyline points="1 20 1 14 7 14"/>
            <path d="M3.51 9a9 9 0 0114.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0020.49 15"/>
          </svg>
          换一批
        </button>
      </div>

      <div v-if="actressesLoading" class="actress-grid" :style="actressGridStyle">
        <div v-for="n in 12" :key="n" class="actress-skeleton-card" aria-hidden="true">
          <div class="actress-skeleton-avatar"></div>
          <div class="actress-skeleton-line"></div>
          <div class="actress-skeleton-line short"></div>
        </div>
      </div>

      <AppleErrorState
        v-else-if="actressError"
        title="演员加载失败"
        description="演员数据源暂时不可用。"
        retry-label="重试"
        @retry="loadActresses(actressPage)"
      />

      <div v-else class="actress-grid" :style="actressGridStyle">
        <button
          v-for="actress in displayedActresses"
          :key="actress.id"
          class="actress-card"
          type="button"
          @click="goActress(actress)"
        >
          <div class="actress-avatar">
            <img
              :src="actressAvatar(actress)"
              :alt="displayName(actress, 'name_kanji', 'name_romaji') || 'Unknown'"
              @error="handleActressImgError"
              loading="lazy"
              decoding="async"
            />
          </div>
          <div class="actress-name">{{ displayName(actress, 'name_kanji', 'name_romaji') || 'Unknown' }}</div>
        </button>
      </div>
    </div>

    <!-- 系列 Tab：系列气泡云 -->
    <div v-if="activeTab === 'series'" class="tag-cloud-wrap page-rail page-rail--standard" role="tabpanel">
      <div class="cloud-header">
        <span class="cloud-hint"></span>
        <button class="shuffle-btn" type="button" @click="reshuffleSeries" :disabled="seriesLoading">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="14" height="14">
            <polyline points="23 4 23 10 17 10"/>
            <polyline points="1 20 1 14 7 14"/>
            <path d="M3.51 9a9 9 0 0114.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0020.49 15"/>
          </svg>
          换一批
        </button>
      </div>

      <div v-if="seriesLoading" class="loading-wrap">
        <div class="spinner-large"></div>
        <p>加载系列中...</p>
      </div>

      <AppleErrorState
        v-else-if="seriesError"
        title="系列加载失败"
        description="系列数据源暂时不可用。"
        retry-label="重试"
        @retry="loadSeries(seriesPage)"
      />

      <div v-else ref="seriesCloudRef" class="tag-cloud" :style="cloudStyle">
        <template v-for="(item, index) in displayedSeries" :key="`${item.id}-${seriesAnimationToken}`">
          <button
            class="bubble"
            type="button"
            :style="bubbleStyle(item, index)"
            @click="goSeries(item)"
          >
            <div class="bubble-content">
              {{ displayName(item, 'name_ja', 'name_en') }}
            </div>
          </button>
        </template>
      </div>
    </div>
  </div>
</template>

<script>
import api from '../api'
import { displayName } from '../utils/displayLang.js'
import { applyImageFallback } from '../utils/imageFallback.js'
import AppleErrorState from '../components/AppleErrorState.vue'

function shuffle(arr) {
  const a = [...arr]
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1))
    ;[a[i], a[j]] = [a[j], a[i]]
  }
  return a
}

const LS_KEY = 'genres_bubble_cfg'

const TABS = [
  { key: 'genre',    label: '题材' },
  { key: 'actress', label: '演员' },
  { key: 'series',   label: '系列' },
]

const DEFAULT_CFG = {
  baseSize: 16,
  fillPercent: 50,
  spacing: 16,
  bubbleCount: 36,        // 每页显示的气泡数量
  defaultTab: 'genre',
  actressAvatarSize: 'medium',
  actressPageSize: 36,
  seriesPageSize: 24,
}

const CFG_KEYS = Object.keys(DEFAULT_CFG)

export default {
  name: 'Genres',
  components: { AppleErrorState },
  data() {
    return {
      activeTab: DEFAULT_CFG.defaultTab,
      tabs: TABS,
      categories: [],
      shuffledTags: [],
      displayedTags: [],
      genreAnimationToken: 0,
      loading: false,
      categoryError: '',
      cfg: { ...DEFAULT_CFG },
      // 演员
      actressRawPage: [],       // 后端返回的原始这一页数据
      displayedActresses: [],
      actressesLoading: false,
      actressError: '',
      actressPage: 1,
      actressTotalPages: 1,
      // 系列
      seriesRawPage: [],
      displayedSeries: [],
      seriesAnimationToken: 0,
      seriesLoading: false,
      seriesError: '',
      seriesPage: 1,
      seriesTotalPages: 1,
      mobileMediaQuery: null,
      isMobileViewport: typeof window !== 'undefined' && window.matchMedia?.('(max-width: 768px)').matches,
    }
  },
  computed: {
    cloudStyle() {
      return {
        gap: this.isMobileViewport
          ? `clamp(8px, ${Math.max(8, this.cfg.spacing)}px, 14px)`
          : `${this.cfg.spacing}px`,
      }
    },
    mobileDisplayedTags() {
      if (!this.isMobileViewport) return this.displayedTags
      const mobileCount = Math.min(Number(this.cfg.bubbleCount) || DEFAULT_CFG.bubbleCount, 24)
      return this.displayedTags.slice(0, mobileCount)
    },
    actressGridStyle() {
      const size = this.cfg.actressAvatarSize || 'medium'
      const avatarMap = { small: '60px', medium: '80px', large: '100px' }
      const avatar = avatarMap[size] || '80px'
      return {
        '--actress-avatar-size': avatar,
        gridTemplateColumns: this.isMobileViewport
          ? `repeat(auto-fit, minmax(clamp(84px, 28vw, ${avatar}), 1fr))`
          : `repeat(auto-fill, minmax(${avatar}, 1fr))`,
      }
    },
    actressPageSize() {
      return Number(this.cfg.actressPageSize) || DEFAULT_CFG.actressPageSize
    },
    seriesPageSize() {
      return Number(this.cfg.seriesPageSize) || DEFAULT_CFG.seriesPageSize
    },
  },
  watch: {
    'cfg.bubbleCount'(newVal) {
      // bubbleCount 改变时重新截取显示范围
      this.displayedTags = this.shuffledTags.slice(0, newVal)
    },
    'cfg.actressAvatarSize'() {
      if (this.activeTab === 'actress') this.loadActresses(1)
    },
    'cfg.actressPageSize'() {
      if (this.activeTab === 'actress') this.loadActresses(1)
    },
    'cfg.seriesPageSize'() {
      if (this.activeTab === 'series') this.loadSeries(1)
    },
    '$route.query.tab'() {
      this.applyRouteTab()
    },
  },
  async mounted() {
    if (typeof window !== 'undefined' && window.matchMedia) {
      this.mobileMediaQuery = window.matchMedia('(max-width: 768px)')
      this.isMobileViewport = this.mobileMediaQuery.matches
      if (this.mobileMediaQuery.addEventListener) {
        this.mobileMediaQuery.addEventListener('change', this.handleMobileViewportChange)
      } else if (this.mobileMediaQuery.addListener) {
        this.mobileMediaQuery.addListener(this.handleMobileViewportChange)
      }
    }
    this.loadCfg()
    this.activeTab = this.tabFromRoute() || (this.tabs.some(tab => tab.key === this.cfg.defaultTab) ? this.cfg.defaultTab : 'genre')
    const initialLoads = []
    if (this.activeTab === 'genre') initialLoads.push(this.loadCategories())
    if (this.activeTab === 'actress') initialLoads.push(this.loadActresses())
    if (this.activeTab === 'series') initialLoads.push(this.loadSeries())
    await Promise.all(initialLoads)
  },
  methods: {
    displayName,
    loadCfg() {
      try {
        const saved = localStorage.getItem(LS_KEY)
        if (saved) {
          const parsed = JSON.parse(saved)
          const fallbackPageSize = { small: 48, medium: 36, large: 20 }
          this.cfg = CFG_KEYS.reduce((cfg, key) => {
            if (Object.prototype.hasOwnProperty.call(parsed, key)) cfg[key] = parsed[key]
            return cfg
          }, { ...DEFAULT_CFG })
          if (!parsed.actressPageSize && parsed.actressAvatarSize) {
            this.cfg.actressPageSize = fallbackPageSize[parsed.actressAvatarSize] || DEFAULT_CFG.actressPageSize
          }
        }
      } catch {}
    },
    handleMobileViewportChange(event) {
      this.isMobileViewport = event.matches
    },
    tabFromRoute(query = this.$route.query) {
      const tab = Array.isArray(query?.tab) ? query.tab[0] : query?.tab
      return this.tabs.some(item => item.key === tab) ? tab : ''
    },
    applyRouteTab() {
      const tab = this.tabFromRoute()
      if (!tab || tab === this.activeTab) return
      this.activateTab(tab)
    },
    activateTab(tab) {
      if (!this.tabs.some(item => item.key === tab)) return
      this.activeTab = tab
      if (tab === 'genre' && !this.categories.length && !this.loading) {
        this.loadCategories()
      }
      if (tab === 'actress' && !this.actressRawPage.length && !this.actressesLoading) {
        this.loadActresses(this.actressPage)
      }
      if (tab === 'series' && !this.seriesRawPage.length && !this.seriesLoading) {
        this.loadSeries(this.seriesPage)
      }
    },
    bubbleStyle(_item, index = 0) {
      const size = this.cfg.baseSize
      const fill = this.cfg.fillPercent / 100
      if (this.isMobileViewport) {
        return {
          '--bubble-index': index,
          fontSize: `clamp(13px, ${size * 0.86}px, 15px)`,
          padding: `clamp(7px, ${Math.round(size * fill * 0.44)}px, 10px) clamp(11px, ${Math.round(size * fill * 0.9)}px, 16px)`,
        }
      }
      return {
        '--bubble-index': index,
        fontSize: `${size}px`,
        padding: `${Math.round(size * fill * 0.6)}px ${Math.round(size * fill * 1.2)}px`,
      }
    },
    async loadCategories() {
      this.loading = true
      this.categoryError = ''
      try {
        const resp = await api.listCategories()
        this.categories = Array.isArray(resp.data) ? resp.data : (resp.data.data || [])
        this.shuffledTags = shuffle(this.categories)
        this.displayedTags = this.shuffledTags.slice(0, this.cfg.bubbleCount)
        this.genreAnimationToken += 1
        this.categoryError = ''
      } catch (e) {
        console.error('Load categories failed:', e)
        this.categories = []
        this.displayedTags = []
        this.categoryError = 'load_failed'
      } finally {
        this.loading = false
      }
    },
    async reloadGenreData() {
      this.categoryError = ''
      await this.loadCategories()
    },
    reshuffle() {
      this.shuffledTags = shuffle(this.categories)
      this.displayedTags = this.shuffledTags.slice(0, this.cfg.bubbleCount)
      this.genreAnimationToken += 1
    },
    goGenre(tag) {
      const name = displayName(tag, 'name_ja', 'name_en') || tag.name || ''
      const filterValue = tag.id || tag.name_ja || tag.name_en || tag.name || name
      this.$router.push({
        name: 'DiscoveryDetail',
        params: { type: 'category', value: String(filterValue) },
        query: name ? { name } : {},
      })
    },
    switchTab(tab) {
      if (!this.tabs.some(item => item.key === tab)) return
      if (tab === this.activeTab && this.tabFromRoute() === tab) return
      this.$router.push({ path: this.$route.path, query: { ...this.$route.query, tab } })
        .catch(() => {})
      this.activateTab(tab)
    },
    actressAvatar(actress) {
      const imageUrl = actress?.image_url || actress?.avatar_url || actress?.javinfo_avatar_url
      if (imageUrl) {
        const url = String(imageUrl).trim()
        if (url.startsWith('http')) return url
        return `https://awsimgsrc.dmm.co.jp/pics_dig/mono/actjpgs/${url.replace(/^\//, '')}`
      }
      const name = encodeURIComponent(actress.name_romaji || actress.name_kanji || '')
      return `/api/actors/avatar/${name}`
    },
    handleActressImgError(e) {
      applyImageFallback(e, { label: String(e.target?.alt || '?').slice(0, 1) })
    },
    async loadActresses(page = 1) {
      this.actressesLoading = true
      this.actressError = ''
      try {
        const pageSize = this.actressPageSize
        const resp = await api.listActresses(page, pageSize, { has_valid_avatar: 1 })
        const raw = resp.data
        this.actressRawPage = Array.isArray(raw.data) ? raw.data : (Array.isArray(raw) ? raw : [])
        this.displayedActresses = shuffle([...this.actressRawPage])
        this.actressTotalPages = raw.total_pages || 1
        this.actressPage = page
      } catch (e) {
        console.error('Load actresses FAILED:', e?.message, 'status:', e?.response?.status, 'data:', e?.response?.data, 'full:', e)
        this.actressRawPage = []
        this.displayedActresses = []
        this.actressError = 'load_failed'
      } finally {
        this.actressesLoading = false
      }
    },
    shuffleActresses() {
      // 随机选一页加载
      const randomPage = Math.floor(Math.random() * this.actressTotalPages) + 1
      this.loadActresses(randomPage)
    },
    async loadSeries(page = 1) {
      this.seriesLoading = true
      this.seriesError = ''
      try {
        const pageSize = this.seriesPageSize
        const resp = await api.listSeries(page, pageSize)
        const raw = resp.data
        this.seriesRawPage = Array.isArray(raw.data) ? raw.data : (Array.isArray(raw) ? raw : [])
        this.displayedSeries = shuffle([...this.seriesRawPage])
        this.seriesAnimationToken += 1
        this.seriesTotalPages = raw.total_pages || 1
        this.seriesPage = page
      } catch (e) {
        console.error('Load series failed:', e)
        this.seriesRawPage = []
        this.displayedSeries = []
        this.seriesError = 'load_failed'
      } finally {
        this.seriesLoading = false
      }
    },
    reshuffleSeries() {
      const randomPage = Math.floor(Math.random() * this.seriesTotalPages) + 1
      this.loadSeries(randomPage)
    },
    goActress(actress) {
      const name = displayName(actress, 'name_kanji', 'name_romaji') || actress.name || String(actress.id || '')
      const query = name ? { name } : {}
      if (actress.id) query.actress_id = actress.id
      this.$router.push({
        path: `/actor/${encodeURIComponent(name)}`,
        query,
      })
    },
    goSeries(item) {
      const name = item.name_ja || item.name_en || item.name || ''
      this.$router.push({
        name: 'DiscoveryDetail',
        params: { type: 'series', value: String(item.id || name) },
        query: name ? { name } : {},
      })
    },
  },
  beforeUnmount() {
    if (this.mobileMediaQuery?.removeEventListener) {
      this.mobileMediaQuery.removeEventListener('change', this.handleMobileViewportChange)
    } else if (this.mobileMediaQuery?.removeListener) {
      this.mobileMediaQuery.removeListener(this.handleMobileViewportChange)
    }
  }
}
</script>

<style scoped>
.genres-page { min-height: 100dvh; background: var(--bg-primary); }
.genres-hero {
  text-align: center;
  padding: 48px 20px 28px;
  background: var(--hero-background);
}
.hero-title {
  color: var(--text-primary);
  font-size: var(--page-title-size);
  font-weight: var(--page-title-weight);
  line-height: var(--page-title-line);
  margin-bottom: 10px;
  letter-spacing: 0;
}
.hero-subtitle { font-size: var(--type-card-title); color: var(--text-secondary); letter-spacing: 0; }
.tag-cloud-wrap { --page-max: 1200px; padding-block: 16px; }
.cloud-header { display: flex; align-items: center; justify-content: space-between; padding: 0 4px 20px; }
.cloud-hint { font-size: var(--type-control); color: var(--text-muted); font-weight: 500; letter-spacing: 0.01em; }
.shuffle-btn {
  display: flex; align-items: center; gap: 6px;
  background: var(--surface-specular-edge), var(--surface-noise), var(--material-glass-control);
  backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
  -webkit-backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
  border: 1px solid var(--glass-control-border);
  box-shadow: var(--glass-control-shadow);
  color: var(--text-primary);
  font-size: var(--type-control); font-weight: 500;
  cursor: pointer;
  padding: 7px 16px;
  border-radius: 999px;
  transition: background 0.25s cubic-bezier(0.23, 1, 0.32, 1), border-color 0.25s cubic-bezier(0.23, 1, 0.32, 1), box-shadow 0.25s cubic-bezier(0.23, 1, 0.32, 1), color 0.25s cubic-bezier(0.23, 1, 0.32, 1), transform 0.25s cubic-bezier(0.23, 1, 0.32, 1);
}
.shuffle-btn:hover:not(:disabled) { background: var(--surface-specular-edge-strong), var(--surface-noise), var(--material-glass-control-hover); border-color: var(--glass-control-border-hover); color: var(--text-primary); box-shadow: var(--glass-control-shadow-hover); }
.shuffle-btn:focus-visible:not(:disabled) { outline: none; background: var(--surface-specular-edge-strong), var(--surface-noise), var(--material-glass-control-hover); border-color: var(--glass-control-border-hover); color: var(--text-primary); box-shadow: var(--glass-control-shadow-hover), var(--focus-ring); }
.shuffle-btn:active:not(:disabled) { transform: scale(0.96); }
.shuffle-btn:disabled { opacity: 0.4; cursor: not-allowed; }
.loading-wrap { text-align: center; padding: 60px; color: var(--text-secondary); }
.spinner-large { width: 40px; height: 40px; border: 3px solid var(--glass-control-border); border-top-color: var(--glass-active-border); border-radius: 50%; animation: spin 0.8s linear infinite; margin: 0 auto 16px; box-shadow: var(--glass-control-shadow); }

/* Tab Bar */
.tab-bar {
  display: inline-flex;
  gap: 4px;
  justify-content: center;
  margin-top: 18px;
  padding: 5px;
  border: 1px solid var(--glass-control-border);
  border-radius: 999px;
  background: var(--surface-specular-edge), var(--surface-noise), var(--material-glass-control);
  box-shadow: var(--glass-control-shadow);
  backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
  -webkit-backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
}
.tab-btn {
  padding: 7px 20px;
  background: var(--surface-specular-edge), var(--surface-noise), var(--material-glass-subtle);
  border: 1px solid var(--glass-control-border);
  color: var(--text-secondary);
  font-size: var(--type-body);
  font-weight: 650;
  cursor: pointer;
  border-radius: 999px;
  box-shadow: var(--glass-control-shadow);
  transition: var(--transition);
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.tab-btn:hover {
  background: var(--surface-specular-edge-strong), var(--surface-noise), var(--material-glass-control-hover);
  border-color: var(--glass-control-border-hover);
  color: var(--text-primary);
}
.tab-btn:focus-visible {
  outline: none;
  background: var(--surface-specular-edge-strong), var(--surface-noise), var(--material-glass-control-hover);
  border-color: var(--glass-control-border-hover);
  color: var(--text-primary);
  box-shadow: var(--glass-control-shadow-hover), var(--focus-ring);
}
.tab-btn.active {
  background: var(--surface-specular-edge-strong), var(--surface-noise), var(--glass-active-material);
  border-color: var(--glass-active-border);
  color: var(--text-primary);
  box-shadow: var(--glass-active-shadow);
}

/* 演员卡片：整个圆形，参照VideoModal */
.actress-tab { --page-max: 1200px; padding-block: 20px; }
.actress-grid { display: grid; gap: 20px; justify-items: center; }
.actress-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 9px;
  min-width: calc(var(--actress-avatar-size, 80px) + 22px);
  padding: 10px;
  border: 1px solid var(--glass-control-border);
  border-radius: calc(var(--radius-card) - 2px);
  background: var(--surface-specular-edge), var(--surface-noise), var(--material-glass-subtle);
  color: inherit;
  font: inherit;
  cursor: pointer;
  box-shadow: var(--glass-control-shadow);
  backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
  -webkit-backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
  transition: background var(--motion-fast), border-color var(--motion-fast), box-shadow var(--motion-fast), transform var(--motion-fast);
}
.actress-card:hover {
  background: var(--surface-specular-edge-strong), var(--surface-noise), var(--material-glass-control-hover);
  border-color: var(--glass-control-border-hover);
  box-shadow: var(--glass-control-shadow-hover);
  transform: translateY(-3px);
}
.actress-card:focus-visible {
  outline: none;
  background: var(--surface-specular-edge-strong), var(--surface-noise), var(--material-glass-control-hover);
  border-color: var(--glass-control-border-hover);
  box-shadow: var(--glass-control-shadow-hover), var(--focus-ring-wide);
}
.actress-card:active { transform: translateY(-1px) scale(0.985); }
.actress-avatar {
  width: var(--actress-avatar-size, 80px);
  height: var(--actress-avatar-size, 80px);
  border-radius: 24px;
  overflow: hidden;
  background: var(--surface-specular-edge), var(--surface-noise), var(--material-glass-control);
  border: 1px solid var(--glass-control-border);
  box-shadow: var(--glass-inner-shadow);
  transition: border-color var(--motion-fast), box-shadow var(--motion-fast), transform var(--motion-fast);
  flex-shrink: 0;
}
.actress-card:hover .actress-avatar { border-color: var(--glass-control-border-hover); box-shadow: var(--glass-control-shadow-hover); }
.actress-card:focus-visible .actress-avatar { border-color: var(--glass-control-border-hover); box-shadow: var(--glass-control-shadow-hover); }
.actress-avatar img { width: 100%; height: 100%; object-fit: cover; object-position: top center; transition: transform var(--motion-emphasized); }
.actress-card:hover .actress-avatar img { transform: translateY(-2px); }
.actress-card:focus-visible .actress-avatar img { transform: translateY(-2px); }
.actress-name { font-size: var(--type-caption); font-weight: 600; color: var(--text-primary); text-align: center; max-width: 90px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.actress-skeleton-card {
  display: grid;
  justify-items: center;
  gap: 8px;
  width: var(--actress-avatar-size, 80px);
  pointer-events: none;
}
.actress-skeleton-avatar,
.actress-skeleton-line {
  position: relative;
  overflow: hidden;
  background: var(--surface-specular-edge), var(--surface-noise), var(--material-glass-subtle);
  border: 1px solid var(--glass-control-border);
  box-shadow: var(--glass-inner-shadow);
  backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
  -webkit-backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
}
.actress-skeleton-avatar {
  width: var(--actress-avatar-size, 80px);
  height: var(--actress-avatar-size, 80px);
  border-radius: 24px;
}
.actress-skeleton-line {
  width: min(72px, calc(var(--actress-avatar-size, 80px) * 0.82));
  height: 10px;
  border-radius: 999px;
}
.actress-skeleton-line.short {
  width: min(46px, calc(var(--actress-avatar-size, 80px) * 0.56));
  opacity: 0.72;
}
.actress-skeleton-avatar::after,
.actress-skeleton-line::after {
  content: "";
  position: absolute;
  inset: 0;
  background: linear-gradient(100deg, transparent 0%, var(--material-glass-control-hover) 46%, transparent 72%);
  transform: translateX(-110%);
  animation: actressSkeletonShimmer 1.35s ease-in-out infinite;
}

@keyframes actressSkeletonShimmer {
  to { transform: translateX(110%); }
}

.tag-cloud {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  align-items: center;
  padding: 24px 18px;
  background: var(--surface-specular-edge-strong), var(--surface-noise), var(--material-glass-sheet);
  border: 1px solid var(--glass-edge);
  border-radius: var(--radius-card);
  box-shadow: var(--glass-surface-shadow);
  backdrop-filter: blur(var(--glass-blur-sheet)) saturate(var(--glass-saturate-surface));
  -webkit-backdrop-filter: blur(var(--glass-blur-sheet)) saturate(var(--glass-saturate-surface));
  gap: 12px;
}

.bubble {
  position: relative;
  padding: 7px 15px;
  border-radius: 999px;
  color: var(--text-primary);
  font-size: var(--type-body);
  font-weight: 500;
  font-family: inherit;
  cursor: pointer;
  user-select: none;
  white-space: nowrap;
  background: var(--surface-specular-edge), var(--surface-noise), var(--material-glass-control);
  backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
  -webkit-backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
  border: 1px solid var(--glass-control-border);
  box-shadow: var(--glass-control-shadow);
  transition: background 0.4s cubic-bezier(0.23, 1, 0.32, 1), border-color 0.4s cubic-bezier(0.23, 1, 0.32, 1), box-shadow 0.4s cubic-bezier(0.23, 1, 0.32, 1), color 0.4s cubic-bezier(0.23, 1, 0.32, 1), opacity 0.4s cubic-bezier(0.23, 1, 0.32, 1), transform 0.4s cubic-bezier(0.23, 1, 0.32, 1);
  overflow: hidden;
  opacity: 0;
  transform: scale(0.92);
  animation: bubble-enter 260ms cubic-bezier(0.2, 0.8, 0.2, 1) forwards;
  animation-delay: min(calc(var(--bubble-index, 0) * 5ms), 180ms);
}

.bubble:hover {
  background: var(--surface-specular-edge-strong), var(--surface-noise), var(--material-glass-control-hover);
  border-color: var(--glass-control-border-hover);
  box-shadow: var(--glass-control-shadow-hover);
  transform: translateY(-2px);
}

.bubble:focus-visible {
  outline: none;
  background: var(--surface-specular-edge-strong), var(--surface-noise), var(--material-glass-control-hover);
  border-color: var(--glass-control-border-hover);
  box-shadow: var(--glass-control-shadow-hover), var(--focus-ring-wide);
  transform: translateY(-2px);
}

.bubble-content {
  position: relative;
  z-index: 2;
}

.bubble.active {
  background: var(--surface-specular-edge-strong), var(--surface-noise), var(--glass-active-material);
  color: var(--text-primary);
  border-color: var(--glass-active-border);
  box-shadow: var(--glass-active-shadow);
}

@keyframes bubble-enter {
  from {
    opacity: 0;
    transform: scale(0.92) translateY(4px);
  }
  to {
    opacity: 1;
    transform: scale(1) translateY(0);
  }
}

@media (max-width: 768px) {
  .genres-hero {
    padding: 44px 16px 28px;
  }
  .hero-title {
    font-size: var(--page-title-size-mobile);
  }
  .tab-bar {
    flex-wrap: wrap;
  }
  .tab-btn,
  .shuffle-btn,
  .bubble {
    min-height: 44px;
  }
  .tag-cloud-wrap,
  .actress-tab {
    padding-block: 20px;
  }
  .tag-cloud {
    padding: 18px 10px;
    border-radius: 20px;
  }
  .actress-grid {
    gap: 16px 10px;
  }
  .actress-avatar,
  .actress-skeleton-avatar {
    border-radius: 18px;
  }
  .loading-wrap {
    padding: 42px 16px;
  }
}

</style>
