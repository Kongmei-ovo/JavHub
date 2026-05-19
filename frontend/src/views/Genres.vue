<template>
  <div class="genres-page page-bleed">
    <!-- 顶部 Tab 栏 -->
    <div class="genres-hero">
      <h1 class="hero-title">个性推荐</h1>
      <p class="hero-subtitle">随机浏览，发现更多内容</p>
      <div class="tab-bar">
        <button
          v-for="tab in tabs"
          :key="tab.key"
          class="tab-btn"
          type="button"
          :class="{ active: activeTab === tab.key }"
          @click="switchTab(tab.key)"
        >
          {{ tab.label }}
        </button>
      </div>
    </div>

    <!-- 题材 Tab：气泡云 -->
    <div v-if="activeTab === 'genre'" class="tag-cloud-wrap page-rail page-rail--standard" ref="cloudRef">
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
        description="数据源当前不可用，推荐内容暂时不能刷新。"
        retry-label="重试"
        @retry="reloadGenreData"
      />

      <div v-else ref="tagCloudRef" class="tag-cloud" :style="cloudStyle">
        <template v-for="tag in mobileDisplayedTags" :key="tag.id">
          <div
            class="bubble"
            :data-id="tag.id"
            :style="bubbleStyle(tag)"
            @click="goGenre(tag)"
          >
            <div class="bubble-content">
              {{ displayName(tag, 'name_ja', 'name_en') || tag.name }}
            </div>
          </div>
        </template>
      </div>
    </div>

    <!-- 演员 Tab：头像卡片 -->
    <div v-if="activeTab === 'actress'" class="actress-tab page-rail page-rail--standard">
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
        <div
          v-for="actress in displayedActresses"
          :key="actress.id"
          class="actress-card"
          @click="goActress(actress)"
        >
          <div class="actress-avatar">
            <img
              :src="actressAvatar(actress)"
              :alt="displayName(actress, 'name_kanji', 'name_romaji') || 'Unknown'"
              @error="handleActressImgError"
              loading="lazy"
            />
          </div>
          <div class="actress-name">{{ displayName(actress, 'name_kanji', 'name_romaji') || 'Unknown' }}</div>
        </div>
      </div>
    </div>

    <!-- 系列 Tab：系列气泡云 -->
    <div v-if="activeTab === 'series'" class="tag-cloud-wrap page-rail page-rail--standard">
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
        <template v-for="item in displayedSeries" :key="item.id">
          <div
            class="bubble"
            :style="bubbleStyle(item)"
            @click="goSeries(item)"
          >
            <div class="bubble-content">
              {{ displayName(item, 'name_ja', 'name_en') }}
            </div>
          </div>
        </template>
      </div>
    </div>
  </div>
</template>

<script>
import gsap from 'gsap'
import api from '../api'
import { displayName } from '../utils/displayLang.js'
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
      loading: false,
      categoryError: '',
      cfg: { ...DEFAULT_CFG },
      moveThrottle: false,  // 节流阀，避免 handleMouseMove 每帧都跑
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
    this.activeTab = this.tabs.some(tab => tab.key === this.cfg.defaultTab) ? this.cfg.defaultTab : 'genre'
    const initialLoads = [
      this.loadCategories(),
    ]
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
    bubbleStyle() {
      const size = this.cfg.baseSize
      const fill = this.cfg.fillPercent / 100
      if (this.isMobileViewport) {
        return {
          fontSize: `clamp(13px, ${size * 0.86}px, 15px)`,
          padding: `clamp(7px, ${Math.round(size * fill * 0.44)}px, 10px) clamp(11px, ${Math.round(size * fill * 0.9)}px, 16px)`,
        }
      }
      return {
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
        this.categoryError = ''
      } catch (e) {
        console.error('Load categories failed:', e)
        this.categories = []
        this.displayedTags = []
        this.categoryError = 'load_failed'
      } finally {
        this.loading = false
        this.$nextTick(() => this.initGsap())
      }
    },
    async reloadGenreData() {
      this.categoryError = ''
      await this.loadCategories()
    },
    initGsap() {
      const cloud = this.$refs.tagCloudRef
      if (!cloud) return
      const bubbles = cloud.querySelectorAll('.bubble')

      gsap.fromTo(bubbles,
        { scale: 0, opacity: 0 },
        { scale: 1, opacity: 1, duration: 0.25, stagger: 0.005, ease: 'back.out(1.7)' }
      )

      // 浮动动画已迁移至 CSS @keyframes bubble-float（全量复用，无 GSAP tween）
      cloud.addEventListener('mousemove', this.handleMouseMove)
      cloud.addEventListener('mouseleave', this.handleMouseLeave)
    },
    initCloudGsap(cloudEl) {
      if (!cloudEl) return
      // 浮动动画已迁移至 CSS @keyframes bubble-float
    },
    handleMouseMove(e) {
      if (this.moveThrottle) return
      this.moveThrottle = true
      const cloud = this.$refs.tagCloudRef
      if (!cloud) { this.moveThrottle = false; return }
      const mouseX = e.clientX
      const mouseY = e.clientY

      requestAnimationFrame(() => {
        const bubbles = cloud.querySelectorAll('.bubble')

        bubbles.forEach(bubble => {
          const r = bubble.getBoundingClientRect()
          const cx = r.left + r.width / 2
          const cy = r.top + r.height / 2
          const dist = Math.hypot(mouseX - cx, mouseY - cy)
          const maxDist = 120

          if (dist < maxDist) {
            gsap.to(bubble, {
              zIndex: 10,
              duration: 0.3,
              ease: 'power2.out',
              overwrite: 'auto',
            })
          } else {
            gsap.to(bubble, {
              rotationX: 0,
              rotationY: 0,
              zIndex: 1,
              duration: 0.4,
              ease: 'power2.out',
              overwrite: 'auto',
            })
          }
        })

        this.moveThrottle = false
      })
    },
    handleMouseLeave() {
      const cloud = this.$refs.tagCloudRef
      if (!cloud) return
      const bubbles = cloud.querySelectorAll('.bubble')
      gsap.to(bubbles, {
        rotationX: 0,
        rotationY: 0,
        zIndex: 1,
        duration: 0.5,
        ease: 'power2.out',
        stagger: 0.002
      })
    },
    reshuffle() {
      const cloud = this.$refs.tagCloudRef
      if (cloud) {
        const bubbles = cloud.querySelectorAll('.bubble')
        gsap.killTweensOf(bubbles)
        gsap.to(bubbles, { scale: 0, opacity: 0, duration: 0.08, stagger: 0, ease: 'power2.in' })
      }
      this.shuffledTags = shuffle(this.categories)
      this.displayedTags = this.shuffledTags.slice(0, this.cfg.bubbleCount)
      this.$nextTick(() => {
        const newBubbles = this.$refs.tagCloudRef?.querySelectorAll('.bubble')
        if (!newBubbles?.length) return
        gsap.fromTo(newBubbles,
          { scale: 0, opacity: 0, rotation: 0 },
          {
            scale: 1,
            opacity: 0.88,
            duration: 0.55,
            stagger: {
              each: 0.012,
              from: 'center',
              grid: 'auto',
            },
            ease: 'back.out(1.7)',
          }
        )
      })
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
      this.activeTab = tab
      if (tab === 'actress' && !this.actressRawPage.length && !this.actressesLoading) {
        this.loadActresses(this.actressPage)
      }
      if (tab === 'series' && !this.seriesRawPage.length && !this.seriesLoading) {
        this.loadSeries(this.seriesPage)
      }
      if (tab === 'series' && !this._seriesGsapInited) {
        this._seriesGsapInited = true
        this.$nextTick(() => this.initCloudGsap(this.$refs.seriesCloudRef))
      }
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
      e.target.src = 'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" width="120" height="120" viewBox="0 0 120 120"><circle cx="60" cy="60" r="60" fill="%231a1a2e"/><circle cx="60" cy="48" r="20" fill="%23333"/><ellipse cx="60" cy="95" rx="30" ry="22" fill="%23333"/></svg>'
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
      const name = actress.name_kanji || actress.name_romaji || actress.name || ''
      this.$router.push({
        name: 'DiscoveryDetail',
        params: { type: 'actress', value: String(actress.id || name) },
        query: name ? { name } : {},
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
    const cloud = this.$refs.tagCloudRef
    if (cloud) {
      cloud.removeEventListener('mousemove', this.handleMouseMove)
      cloud.removeEventListener('mouseleave', this.handleMouseLeave)
      const bubbles = cloud.querySelectorAll('.bubble')
      gsap.killTweensOf(bubbles)
    }
    const seriesCloud = this.$refs.seriesCloudRef
    if (seriesCloud) {
      const bubbles = seriesCloud.querySelectorAll('.bubble')
      gsap.killTweensOf(bubbles)
    }
  }
}
</script>

<style scoped>
.genres-page { min-height: 100dvh; background: var(--bg-primary); }
.genres-hero {
  text-align: center;
  padding: 76px 20px 40px;
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
.hero-subtitle { font-size: var(--type-section-title); color: var(--text-secondary); letter-spacing: 0; }
.tag-cloud-wrap { --page-max: 1200px; padding-block: 20px; }
.cloud-header { display: flex; align-items: center; justify-content: space-between; padding: 0 4px 20px; }
.cloud-hint { font-size: var(--type-control); color: var(--text-muted); font-weight: 500; letter-spacing: 0.01em; }
.shuffle-btn {
  display: flex; align-items: center; gap: 6px;
  background: var(--glass-control-bg);
  backdrop-filter: blur(20px) saturate(160%);
  -webkit-backdrop-filter: blur(20px) saturate(160%);
  border: 1px solid var(--glass-control-border);
  box-shadow: var(--glass-inner-shadow);
  color: var(--text-primary);
  font-size: var(--type-control); font-weight: 500;
  cursor: pointer;
  padding: 7px 16px;
  border-radius: 999px;
  transition: all 0.25s cubic-bezier(0.23, 1, 0.32, 1);
}
.shuffle-btn:hover:not(:disabled) { background: var(--glass-control-bg-hover); border-color: var(--glass-control-border-hover); color: var(--text-primary); }
.shuffle-btn:active:not(:disabled) { transform: scale(0.96); }
.shuffle-btn:disabled { opacity: 0.4; cursor: not-allowed; }
.loading-wrap { text-align: center; padding: 60px; color: var(--text-secondary); }
.spinner-large { width: 40px; height: 40px; border: 3px solid var(--border-light); border-top-color: var(--accent); border-radius: 50%; animation: spin 0.8s linear infinite; margin: 0 auto 16px; }

/* Tab Bar */
.tab-bar {
  display: inline-flex;
  gap: 4px;
  justify-content: center;
  margin-top: 24px;
  padding: 5px;
  border: 1px solid var(--glass-control-border);
  border-radius: 999px;
  background: var(--glass-control-bg);
  box-shadow: var(--glass-inner-shadow);
  backdrop-filter: blur(24px) saturate(170%);
  -webkit-backdrop-filter: blur(24px) saturate(170%);
}
.tab-btn {
  padding: 8px 24px;
  background: var(--glass-subtle-bg);
  border: 1px solid var(--glass-control-border);
  color: var(--text-secondary);
  font-size: var(--type-body);
  font-weight: 650;
  cursor: pointer;
  border-radius: 999px;
  box-shadow: inset 0 1px 0 var(--glass-highlight);
  transition: var(--transition);
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.tab-btn:hover {
  background: var(--glass-control-bg-hover);
  border-color: var(--glass-control-border-hover);
  color: var(--text-primary);
}
.tab-btn.active {
  background: var(--glass-active-bg);
  border-color: var(--glass-active-border);
  color: var(--text-primary);
  box-shadow: var(--glass-active-shadow);
}

/* 演员卡片：整个圆形，参照VideoModal */
.actress-tab { --page-max: 1200px; padding-block: 20px; }
.actress-grid { display: grid; gap: 20px; justify-items: center; }
.actress-card { display: flex; flex-direction: column; align-items: center; gap: 8px; cursor: pointer; transition: var(--transition); }
.actress-card:hover { transform: translateY(-4px); }
.actress-avatar { width: var(--actress-avatar-size, 80px); height: var(--actress-avatar-size, 80px); border-radius: 24px; overflow: hidden; background: var(--surface-control); border: 1px solid var(--border-light); transition: border-color 0.2s, box-shadow 0.2s; flex-shrink: 0; }
.actress-card:hover .actress-avatar { border-color: var(--border-light); box-shadow: var(--shadow-hover); }
.actress-avatar img { width: 100%; height: 100%; object-fit: cover; object-position: top center; transition: transform 0.3s ease; }
.actress-card:hover .actress-avatar img { transform: translateY(-2px); }
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
  background: var(--surface-control);
  border: 1px solid var(--border-light);
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.48);
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
  background: linear-gradient(100deg, transparent 0%, rgba(255,255,255,0.38) 46%, transparent 72%);
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
  padding: 30px 10px;
  background: var(--glass-control-bg);
  border: 1px solid var(--glass-edge);
  border-radius: var(--radius-card);
  box-shadow: var(--glass-inner-shadow);
  backdrop-filter: blur(22px) saturate(150%);
  -webkit-backdrop-filter: blur(22px) saturate(150%);
  gap: 16px;
}

.bubble {
  position: relative;
  padding: 8px 18px;
  border-radius: 999px;
  color: var(--text-primary);
  font-size: var(--type-body);
  font-weight: 500;
  cursor: pointer;
  user-select: none;
  white-space: nowrap;
  background: var(--surface-card);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  border: 1px solid var(--border-light);
  transition: all 0.4s cubic-bezier(0.23, 1, 0.32, 1);
  overflow: hidden;
}

.bubble:hover {
  background: var(--surface-control-hover);
  border-color: var(--border-light);
  transform: translateY(-2px);
}

.bubble-content {
  position: relative;
  z-index: 2;
}

.bubble.active {
  background: var(--glass-active-bg);
  color: var(--text-primary);
  border-color: var(--glass-active-border);
  box-shadow: var(--glass-active-shadow);
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
