<template>
  <div class="genres-page">
    <!-- 顶部 Tab 栏 -->
    <div class="genres-hero">
      <h1 class="hero-title">个性推荐</h1>
      <p class="hero-subtitle">随机浏览，发现更多内容</p>
      <div class="tab-bar">
        <button
          v-for="tab in tabs"
          :key="tab.key"
          class="tab-btn"
          :class="{ active: activeTab === tab.key }"
          @click="switchTab(tab.key)"
        >
          {{ tab.label }}
          <span v-if="tab.key === 'series' && displayedSeries.length" class="tab-count">{{ displayedSeries.length }}</span>
        </button>
      </div>
    </div>

    <!-- 题材 Tab：气泡云 -->
    <div v-if="activeTab === 'genre'" class="tag-cloud-wrap" ref="cloudRef">
      <div class="cloud-header">
        <span class="cloud-hint">共 {{ categories.length }} 个题材</span>
        <button class="shuffle-btn" @click="reshuffle" :disabled="loading">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
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

      <div v-else-if="statsLoading" class="loading-wrap">
        <div class="spinner-large"></div>
        <p>加载统计中...</p>
      </div>

      <div v-else ref="tagCloudRef" class="tag-cloud" :style="cloudStyle">
        <template v-for="tag in displayedTags" :key="tag.id">
          <div
            v-if="legendaryBubbleClass(tag).includes('rarity-legendary')"
            class="bubble rarity-legendary"
            :data-id="tag.id"
            :style="bubbleStyle(tag)"
            @click="goGenre(tag)"
          >
            <div class="legendary-inner">
              {{ displayName(tag, 'name_ja', 'name_en') || tag.name }}
            </div>
          </div>
          <div
            v-else
            class="bubble"
            :class="legendaryBubbleClass(tag)"
            :data-id="tag.id"
            :style="bubbleStyle(tag)"
            @click="goGenre(tag)"
          >
            {{ displayName(tag, 'name_ja', 'name_en') || tag.name }}
          </div>
        </template>
      </div>
    </div>

    <!-- 演员 Tab：头像卡片 -->
    <div v-if="activeTab === 'actress'" class="actress-tab">
      <div class="actress-header" v-if="!actressesLoading && displayedActresses.length">
        <button class="shuffle-btn" @click="prevActressPage" :disabled="actressPage <= 1">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14"><polyline points="15 18 9 12 15 6"/></svg>
          上一页
        </button>
        <button class="shuffle-btn" @click="randomActressPage">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
            <polyline points="23 4 23 10 17 10"/>
            <polyline points="1 20 1 14 7 14"/>
            <path d="M3.51 9a9 9 0 0114.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0020.49 15"/>
          </svg>
          随机
        </button>
        <button class="shuffle-btn" @click="nextActressPage" :disabled="actressPage >= actressTotalPages">
          下一页
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14"><polyline points="9 18 15 12 9 6"/></svg>
        </button>
      </div>

      <div v-if="actressesLoading" class="loading-wrap">
        <div class="spinner-large"></div>
        <p>加载演员中...</p>
      </div>

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
    <div v-if="activeTab === 'series'" class="tag-cloud-wrap">
      <div class="cloud-header">
        <span class="cloud-hint">共 {{ seriesList.length }} 个系列</span>
        <button class="shuffle-btn" @click="reshuffleSeries" :disabled="seriesLoading">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
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

      <div v-else ref="seriesCloudRef" class="tag-cloud" :style="cloudStyle">
        <template v-for="item in displayedSeries" :key="item.id">
          <div
            v-if="legendaryBubbleClass(item).includes('rarity-legendary')"
            class="bubble rarity-legendary"
            :style="bubbleStyle(item)"
            @click="goSeries(item)"
          >
            <div class="legendary-inner">
              {{ displayName(item, 'name_ja', 'name_en') }}
            </div>
          </div>
          <div
            v-else
            class="bubble"
            :class="legendaryBubbleClass(item)"
            :style="bubbleStyle(item)"
            @click="goSeries(item)"
          >
            {{ displayName(item, 'name_ja', 'name_en') }}
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

// === Color Palettes ===
const PALETTES = {
  // 莫奈：低饱和粉紫灰调，百合、淡紫、雾霾蓝
  monet: [
    'linear-gradient(135deg, #c4b5d8, #a5b4c8)',
    'linear-gradient(135deg, #d4c4e0, #b8c5d6)',
    'linear-gradient(135deg, #c8d4c0, #a8b8a0)',
    'linear-gradient(135deg, #d0c0dc, #b0a8c8)',
    'linear-gradient(135deg, #e0d0d8, #c8b8c0)',
    'linear-gradient(135deg, #c0cce0, #a8b8cc)',
    'linear-gradient(135deg, #d8c8dc, #c0b0cc)',
    'linear-gradient(135deg, #ccd4d8, #b8c4c8)',
  ],
  // 夕阳：低饱和暖橙褐调，砖红、琥珀、锈橙
  sunset: [
    'linear-gradient(135deg, #c89080, #d8a898)',
    'linear-gradient(135deg, #c87868, #d8a088)',
    'linear-gradient(135deg, #d0a880, #c8a078)',
    'linear-gradient(135deg, #d09888, #c08070)',
    'linear-gradient(135deg, #c88078, #d8a090)',
    'linear-gradient(135deg, #d0a070, #c89060)',
    'linear-gradient(135deg, #c89880, #d8b090)',
    'linear-gradient(135deg, #d0a888, #c09070)',
  ],
  // 海洋：低饱和蓝绿灰调，石青、雾蓝、松石绿
  ocean: [
    'linear-gradient(135deg, #7aaec0, #8cbcc8)',
    'linear-gradient(135deg, #88c0b0, #a0d0c0)',
    'linear-gradient(135deg, #90c8c0, #a8d8d0)',
    'linear-gradient(135deg, #78b0a8, #90c8c0)',
    'linear-gradient(135deg, #7ab0c0, #8cc0cc)',
    'linear-gradient(135deg, #80b8c8, #98c8d8)',
    'linear-gradient(135deg, #88c0b8, #a0d0c8)',
    'linear-gradient(135deg, #7ab0b8, #90c0c8)',
  ],
  // 森林：低饱和苔绿灰调，苔藓绿、橄榄、灰绿
  forest: [
    'linear-gradient(135deg, #90b898, #a0c8a8)',
    'linear-gradient(135deg, #7aa888, #8ab898)',
    'linear-gradient(135deg, #88a880, #98b890)',
    'linear-gradient(135deg, #98b8a8, #a8c8b8)',
    'linear-gradient(135deg, #80a888, #90b898)',
    'linear-gradient(135deg, #88a090, #98b0a0)',
    'linear-gradient(135deg, #90b898, #a0c8a8)',
    'linear-gradient(135deg, #78a080, #88b090)',
  ],
  // 金色：低饱和琥珀金，琥珀、褐金、锈金
  gold: [
    'linear-gradient(135deg, #a88050, #c8a068)',
    'linear-gradient(135deg, #c89050, #d8b070)',
    'linear-gradient(135deg, #b88840, #c8a060)',
    'linear-gradient(135deg, #a88060, #b89870)',
    'linear-gradient(135deg, #c08050, #d0a068)',
    'linear-gradient(135deg, #d0b080, #c8a068)',
    'linear-gradient(135deg, #b89058, #c8a870)',
    'linear-gradient(135deg, #a87848, #c09860)',
  ],
  // 动漫：高饱和粉紫
  anime: [
    'linear-gradient(135deg, #e8a0c8, #f0b8d8)',
    'linear-gradient(135deg, #c0a0e0, #d0b0f0)',
    'linear-gradient(135deg, #f0a0b0, #f8c0d0)',
    'linear-gradient(135deg, #a0c0ff, #b0d8ff)',
    'linear-gradient(135deg, #ffa0c0, #ffc0d8)',
    'linear-gradient(135deg, #c0e0ff, #d0f0ff)',
    'linear-gradient(135deg, #e0a0d0, #f0b8e0)',
    'linear-gradient(135deg, #80c0a0, #90d0b0)',
  ],
  // 复古：暖褐做旧
  retro: [
    'linear-gradient(135deg, #c89050, #d0a068)',
    'linear-gradient(135deg, #8b7355, #a08060)',
    'linear-gradient(135deg, #d09060, #e0b080)',
    'linear-gradient(135deg, #a07040, #b08858)',
    'linear-gradient(135deg, #c8a070, #d8b888)',
    'linear-gradient(135deg, #b08050, #c09868)',
    'linear-gradient(135deg, #9a7060, #b08878)',
    'linear-gradient(135deg, #c0a080, #d0b898)',
  ],
  // 赛博：蓝紫霓虹
  cyber: [
    'linear-gradient(135deg, #00c8ff, #0080ff)',
    'linear-gradient(135deg, #8000ff, #c000ff)',
    'linear-gradient(135deg, #00ffcc, #00e0a0)',
    'linear-gradient(135deg, #ff0080, #ff4000)',
    'linear-gradient(135deg, #0080ff, #00c8ff)',
    'linear-gradient(135deg, #ff00ff, #8000ff)',
    'linear-gradient(135deg, #00ff80, #00c0ff)',
    'linear-gradient(135deg, #ff8000, #ffcc00)',
  ],
  // 马卡龙：粉嫩糖果
  pastel: [
    'linear-gradient(135deg, #f0b8c0, #f8d0d8)',
    'linear-gradient(135deg, #b8d0f0, #c8e0f8)',
    'linear-gradient(135deg, #d0b8f0, #e0c8f8)',
    'linear-gradient(135deg, #f8e0c0, #fff0d8)',
    'linear-gradient(135deg, #c0f0d0, #d0f8e0)',
    'linear-gradient(135deg, #f0c0d8, #f8d8e8)',
    'linear-gradient(135deg, #d8f0f0, #e8f8f8)',
    'linear-gradient(135deg, #f8d0c0, #ffe0d8)',
  ],
  // Nord：冷淡北欧风
  nord: [
    'linear-gradient(135deg, #88c0d0, #81a1c1)',
    'linear-gradient(135deg, #a3be8c, #b48ead)',
    'linear-gradient(135deg, #5e81ac, #81a1c1)',
    'linear-gradient(135deg, #bf616a, #d08770)',
    'linear-gradient(135deg, #8fbcbb, #88c0d0)',
    'linear-gradient(135deg, #b48ead, #a3be8c)',
    'linear-gradient(135deg, #d8dee9, #eceff4)',
    'linear-gradient(135deg, #4c566a, #5e81ac)',
  ],
  // 霓虹：荧光撞色
  neon: [
    'linear-gradient(135deg, #ff0080, #ff4000)',
    'linear-gradient(135deg, #00ff80, #00c0ff)',
    'linear-gradient(135deg, #ff00ff, #00ffff)',
    'linear-gradient(135deg, #ffff00, #ff8000)',
    'linear-gradient(135deg, #00ff00, #80ff00)',
    'linear-gradient(135deg, #8000ff, #ff0080)',
    'linear-gradient(135deg, #00c0ff, #0080ff)',
    'linear-gradient(135deg, #ff8000, #ffff00)',
  ],
  // 大地：土褐森绿
  earth: [
    'linear-gradient(135deg, #8b7355, #a08060)',
    'linear-gradient(135deg, #6b8e5a, #7a9e68)',
    'linear-gradient(135deg, #a08050, #b09068)',
    'linear-gradient(135deg, #5a7a4a, #6a8a58)',
    'linear-gradient(135deg, #9a8060, #aa9070)',
    'linear-gradient(135deg, #7a6a50, #8a7a60)',
    'linear-gradient(135deg, #6b8e3a, #7b9e4a)',
    'linear-gradient(135deg, #8a7060, #9a8070)',
  ],
  // 糖果：糖果色
  candy: [
    'linear-gradient(135deg, #ffb8d0, #ffc8e0)',
    'linear-gradient(135deg, #b8e0ff, #c8f0ff)',
    'linear-gradient(135deg, #ffd0a0, #ffe0b8)',
    'linear-gradient(135deg, #d0ffb8, #e0ffc8)',
    'linear-gradient(135deg, #e0b8ff, #f0c8ff)',
    'linear-gradient(135deg, #ffb8b8, #ffc8c8)',
    'linear-gradient(135deg, #b8ffb8, #c8ffc8)',
    'linear-gradient(135deg, #ffffb8, #ffffd0)',
  ],
}

// __all__ 特殊键：在 getGradient 中拼接所有色系的渐变
function getAllGradients() {
  return Object.values(PALETTES).flat()
}

// Gold legend rarity gradients — legendary(gold) → common(blue) → popular(gray)
const RARITY_GRADIENTS = {
  // 金色传奇：暗色主题友好 - 琥珀、锈金、褐铜
  legendary: [
    'linear-gradient(135deg, #b88040, #d8a868)',
    'linear-gradient(135deg, #c89050, #d8b070)',
    'linear-gradient(135deg, #a87838, #c09058)',
    'linear-gradient(135deg, #b88848, #d0a068)',
  ],
  // 稀有：低饱和紫灰
  rare: [
    'linear-gradient(135deg, #9880b8, #b0a0c8)',
    'linear-gradient(135deg, #b090c8, #a8a0c0)',
    'linear-gradient(135deg, #c0a8d0, #b8b0c0)',
  ],
  // 普通：低饱和灰蓝
  common: [
    'linear-gradient(135deg, #88a8c0, #a0b8c8)',
    'linear-gradient(135deg, #90c0b0, #a8d0c0)',
    'linear-gradient(135deg, #88b8c8, #98c0d0)',
  ],
  // 热门：低饱和灰调
  popular: [
    'linear-gradient(135deg, #909090, #a0a0a0)',
    'linear-gradient(135deg, #808888, #909898)',
    'linear-gradient(135deg, #888898, #9898a8)',
  ],
}

function hashCode(str) {
  let hash = 0
  for (let i = 0; i < str.length; i++) {
    hash = ((hash << 5) - hash) + str.charCodeAt(i)
    hash |= 0
  }
  return Math.abs(hash)
}

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
  colorMode: 'legendary', // 'random' | 'legendary'
  palette: 'monet',       // for random mode: monet/sunset/ocean/forest/gold/custom
  customGradients: [],    // for custom palette
  goldLegend: true,       // enable gold legend mode
  bubbleCount: 36,        // 每页显示的气泡数量
  rarityThresholds: { legendary: 5, epic: 20, rare: 50 }, // 百分比阈值（0-100）
}

export default {
  name: 'Genres',
  data() {
    return {
      activeTab: 'genre',
      tabs: TABS,
      categories: [],
      shuffledTags: [],
      displayedTags: [],
      loading: false,
      statsLoading: false,
      cfg: { ...DEFAULT_CFG },
      categoryStats: {},
      rarityMap: {},
      bubbleRects: new Map(),
      moveThrottle: false,  // 节流阀，避免 handleMouseMove 每帧都跑
      // 演员
      actressRawPage: [],       // 后端返回的原始这一页数据
      displayedActresses: [],
      actressesLoading: false,
      actressPage: 1,
      actressTotalPages: 1,
      // 系列
      seriesList: [],
      displayedSeries: [],
      seriesLoading: false,
    }
  },
  computed: {
    cloudStyle() {
      const c = this.cfg.rarityColors || {}
      return {
        gap: `${this.cfg.spacing}px`,
        '--rarity-legendary': c.legendary || '#c89a30',
        '--rarity-epic': c.epic || '#7040a0',
        '--rarity-rare': c.rare || '#3070a8',
        '--rarity-common': c.common || '#607080',
      }
    },
    actressGridStyle() {
      const size = this.cfg.actressAvatarSize || 'medium'
      const avatarMap = { small: '60px', medium: '80px', large: '100px' }
      const avatar = avatarMap[size] || '80px'
      return {
        '--actress-avatar-size': avatar,
        gridTemplateColumns: `repeat(auto-fill, minmax(${avatar}, 1fr))`,
      }
    },
    actressPageSize() {
      const size = this.cfg.actressAvatarSize || 'medium'
      const map = { small: 48, medium: 36, large: 20 }
      return map[size] || 36
    },
  },
  watch: {
    'cfg.bubbleCount'(newVal) {
      // bubbleCount 改变时重新截取显示范围
      this.displayedTags = this.shuffledTags.slice(0, newVal)
    },
    'cfg.actressAvatarSize'() {
      // page_size 变了，total_pages 也变，重新取第一页
      this.loadActresses(1)
    },
  },
  async mounted() {
    this.loadCfg()
    await Promise.all([
      this.loadCategories(),
      this.loadActresses(),
      this.loadSeries(),
      this.cfg.goldLegend ? this.loadCategoryStats() : Promise.resolve(),
    ])
    // Delegated legendary listeners — set up once after DOM is ready
    this.$nextTick(() => {
      const cloud = this.$refs.tagCloudRef
      if (cloud) {
        cloud.addEventListener('mouseenter', this.onLegendaryEnter, true)
        cloud.addEventListener('mouseleave', this.onLegendaryLeave, true)
      }
    })
  },
  methods: {
    displayName,
    loadCfg() {
      try {
        const saved = localStorage.getItem(LS_KEY)
        if (saved) {
          this.cfg = { ...DEFAULT_CFG, ...JSON.parse(saved) }
        }
      } catch {}
    },
    getGradient(tag, palette) {
      let gradients
      if (palette === '__all__') {
        gradients = getAllGradients()
      } else if (palette === '__custom__') {
        gradients = this.cfg.customGradients.length ? this.cfg.customGradients : PALETTES.monet
      } else {
        gradients = PALETTES[palette] || PALETTES.monet
      }
      const idx = hashCode(tag.name_en || tag.name_ja || tag.name) % gradients.length
      return gradients[idx]
    },
    getRarityGradient(tag) {
      const rarity = this.rarityMap[tag.id] || 'common'
      const grads = RARITY_GRADIENTS[rarity]
      const idx = hashCode((tag.name_en || tag.name_ja || tag.name) + 'rarity') % grads.length
      return grads[idx]
    },
    bubbleStyle(tag) {
      const size = this.cfg.baseSize
      const fill = this.cfg.fillPercent / 100
      const isLegendary = this.cfg.colorMode === 'legendary' && this.cfg.goldLegend
      const style = {
        // background set by CSS class for legendary mode (metallic gradient)
        // inline gradient only for random/palette mode
        background: isLegendary ? undefined : this.getGradient(tag, this.cfg.palette),
        fontSize: `${size}px`,
        padding: `${Math.round(size * fill * 0.6)}px ${Math.round(size * fill * 1.2)}px`,
      }
      return style
    },
    async loadCategories() {
      this.loading = true
      try {
        const resp = await api.listCategories()
        this.categories = Array.isArray(resp.data) ? resp.data : (resp.data.data || [])
        this.shuffledTags = shuffle(this.categories)
        this.displayedTags = this.shuffledTags.slice(0, this.cfg.bubbleCount)
      } catch (e) {
        console.error('Load categories failed:', e)
        this.categories = []
        this.displayedTags = []
      } finally {
        this.loading = false
        this.$nextTick(() => this.initGsap())
      }
    },
    async loadCategoryStats() {
      this.statsLoading = true
      try {
        // 使用共享缓存：内存+localStorage，1小时内不重复请求
        const stats = await api.getCategoryStats()
        const statsMap = {}
        stats.forEach(s => { statsMap[s.id] = s.video_count || 0 })
        this.categoryStats = statsMap
        this.computeRarity(stats)
      } catch (e) {
        console.error('Load category stats failed:', e)
      } finally {
        this.statsLoading = false
        this.$nextTick(() => this.initGsap())
      }
    },
    computeRarity(stats) {
      // Hearthstone风格分布：legendary(橙)=最少出现, epic(紫), rare(蓝), common(白)=最常出现
      // 按 video_count 升序：最少 = legendary，最多 = common
      const sorted = [...stats].sort((a, b) => (a.video_count || 0) - (b.video_count || 0))
      const n = sorted.length
      const { legendary = 5, epic = 20, rare = 50 } = this.cfg.rarityThresholds || {}
      const rarityMap = {}
      sorted.forEach((cat, i) => {
        const pct = i / Math.max(n - 1, 1)  // 0 = rarest (legendary), 1 = most common
        if (pct * 100 < legendary)       rarityMap[cat.id] = 'legendary'  // 橙卡
        else if (pct * 100 < epic)       rarityMap[cat.id] = 'epic'        // 紫卡
        else if (pct * 100 < rare)       rarityMap[cat.id] = 'rare'       // 蓝卡
        else                              rarityMap[cat.id] = 'common'      // 白卡
      })
      this.rarityMap = rarityMap
    },
    updateBubbleRects(bubbles) {
      const newRects = new Map()
      bubbles.forEach(b => newRects.set(b, b.getBoundingClientRect()))
      this.bubbleRects = newRects
    },
    initGsap() {
      const cloud = this.$refs.tagCloudRef
      if (!cloud) return
      const bubbles = cloud.querySelectorAll('.bubble')
      this.updateBubbleRects(bubbles)

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

        // 读取配色 CSS 变量（云容器只读一次）
        const cs = getComputedStyle(cloud)
        const lc = (cs.getPropertyValue('--rarity-legendary').trim() || '#c89a30')
        const ec = (cs.getPropertyValue('--rarity-epic').trim() || '#7040a0')
        const rc = (cs.getPropertyValue('--rarity-rare').trim() || '#3070a8')

        // Proximity scale + 缓存 rect（每气泡只查一次）
        const scales = new Map()
        const hoveredBubbles = []
        const rects = new Map()
        bubbles.forEach(bubble => {
          const r = bubble.getBoundingClientRect()
          rects.set(bubble, r)
          const cx = r.left + r.width / 2
          const cy = r.top + r.height / 2
          const dist = Math.hypot(mouseX - cx, mouseY - cy)
          const maxDist = 160
          if (dist < maxDist) {
            scales.set(bubble, 1 + (1 - dist / maxDist) * 0.5)
            hoveredBubbles.push(bubble)
          } else {
            scales.set(bubble, 1)
          }
        })

        // Collision detection（复用已缓存 rect）
        const overlapped = new Set()
        for (let i = 0; i < hoveredBubbles.length; i++) {
          for (let j = i + 1; j < hoveredBubbles.length; j++) {
            const a = hoveredBubbles[i], b = hoveredBubbles[j]
            const ra = rects.get(a), rb = rects.get(b)
            const sa = scales.get(a), sb = scales.get(b)
            const raS = { left: ra.left - (sa-1)*ra.width/2, right: ra.right + (sa-1)*ra.width/2, top: ra.top - (sa-1)*ra.height/2, bottom: ra.bottom + (sa-1)*ra.height/2 }
            const rbS = { left: rb.left - (sb-1)*rb.width/2, right: rb.right + (sb-1)*rb.width/2, top: rb.top - (sb-1)*rb.height/2, bottom: rb.bottom + (sb-1)*rb.height/2 }
            const intersects = !(raS.right < rbS.left || raS.left > rbS.right || raS.bottom < rbS.top || raS.top > rbS.bottom)
            if (intersects) { overlapped.add(a); overlapped.add(b) }
          }
        }

        let maxZ = 100
        bubbles.forEach(bubble => {
          const scale = scales.get(bubble)
          const isOverlapped = overlapped.has(bubble)
          const isHovered = hoveredBubbles.includes(bubble)
          const isLegendary = bubble.classList.contains('rarity-legendary')
          const isRare = bubble.classList.contains('rarity-rare')
          const inLegendaryMode = this.cfg.colorMode === 'legendary' && this.cfg.goldLegend

          if (isHovered && scale > 1) {
            let outerGlow = ''
            if (isLegendary && inLegendaryMode) {
              outerGlow = `0 0 25px 8px ${lc}fa, 0 0 60px 18px ${lc}d6, 0 0 120px 36px ${lc}8c, 0 0 200px 60px ${lc}4d`
            } else if (bubble.classList.contains('rarity-epic') && inLegendaryMode) {
              outerGlow = `0 0 18px 6px ${ec}e6, 0 0 45px 14px ${ec}a6`
            } else if (isRare && inLegendaryMode) {
              outerGlow = `0 0 14px 5px ${rc}bf, 0 0 35px 12px ${rc}73`
            } else {
              outerGlow = '0 6px 24px rgba(0,0,0,0.35)'
            }
            const gsapOpts = {
              scale,
              opacity: 1,
              zIndex: isOverlapped ? ++maxZ : 50,
              boxShadow: outerGlow,
              duration: 0.12,
              ease: 'back.out(1.2)',
              overwrite: 'auto',
            }
            // 3D tilt：复用已缓存 rect
            if (isLegendary && inLegendaryMode) {
              const r = rects.get(bubble)
              const cx = r.left + r.width / 2
              const cy = r.top + r.height / 2
              const maxTilt = 18
              const tx = Math.round(((mouseY - cy) / (r.height * 0.6)) * maxTilt)
              const ty = Math.round(-((mouseX - cx) / (r.width * 0.6)) * maxTilt)
              gsapOpts.rotationX = Math.max(-maxTilt, Math.min(maxTilt, tx))
              gsapOpts.rotationY = Math.max(-maxTilt, Math.min(maxTilt, ty))
            }
            gsap.to(bubble, gsapOpts)
          } else {
            gsap.to(bubble, {
              scale: 1,
              opacity: 0.88,
              zIndex: 1,
              boxShadow: '',
              duration: 0.18,
              ease: 'power3.out',
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
      // Clear boxShadow inline style → CSS breathing animation auto-resumes
      gsap.to(bubbles, {
        scale: 1, opacity: 0.88, zIndex: 1,
        boxShadow: '',
        duration: 0.3, ease: 'back.out(1.2)', stagger: 0.004,
      })
    },
    // --- Legendary 3D Tilt (GSAP) — delegated from cloud ---
    onLegendaryEnter(e) {
      const bubble = e.target.closest ? e.target.closest('.bubble.rarity-legendary') : null
      if (!bubble) return
      // Stop the breathing y-float on this bubble so tilt feels clean
      gsap.killTweensOf(bubble)
      gsap.to(bubble, { y: 0, duration: 0.3, ease: 'power2.out' })
    },
    onLegendaryLeave(e) {
      const bubble = e.target.closest ? e.target.closest('.bubble.rarity-legendary') : null
      if (!bubble) return
      // Elastic 3D return to neutral
      gsap.to(bubble, {
        rotationY: 0,
        rotationX: 0,
        scale: 1,
        duration: 1.0,
        ease: 'elastic.out(1, 0.45)',
        overwrite: 'auto',
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
      this.$router.push({ name: 'GenreDetail', params: { categoryId: tag.id } })
    },
    switchTab(tab) {
      this.activeTab = tab
      if (tab === 'series' && !this._seriesGsapInited) {
        this._seriesGsapInited = true
        this.$nextTick(() => this.initCloudGsap(this.$refs.seriesCloudRef))
      }
    },
    actressAvatar(actress) {
      if (actress.image_url) {
        const url = actress.image_url
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
      try {
        const pageSize = this.actressPageSize
        const resp = await api.listActresses(page, pageSize)
        const raw = resp.data
        this.actressRawPage = Array.isArray(raw.data) ? raw.data : (Array.isArray(raw) ? raw : [])
        this.displayedActresses = shuffle([...this.actressRawPage])
        this.actressTotalPages = raw.total_pages || 1
        this.actressPage = page
      } catch (e) {
        console.error('Load actresses FAILED:', e?.message, 'status:', e?.response?.status, 'data:', e?.response?.data, 'full:', e)
      } finally {
        this.actressesLoading = false
      }
    },
    async loadSeries() {
      this.seriesLoading = true
      try {
        const resp = await api.listSeries()
        this.seriesList = resp.data?.data || resp.data || []
        this.displayedSeries = shuffle(this.seriesList).slice(0, 60)
      } catch (e) {
        console.error('Load series failed:', e)
      } finally {
        this.seriesLoading = false
      }
    },
    randomActressPage() {
      // 本地 shuffle 当前页，不调后端
      this.displayedActresses = shuffle([...this.actressRawPage])
    },
    nextActressPage() {
      if (this.actressPage < this.actressTotalPages) {
        this.loadActresses(this.actressPage + 1)
      }
    },
    prevActressPage() {
      if (this.actressPage > 1) {
        this.loadActresses(this.actressPage - 1)
      }
    },
    reshuffleSeries() {
      this.displayedSeries = shuffle(this.seriesList).slice(0, 60)
    },
    goActress(actress) {
      const name = actress.name_kanji || actress.name_romaji || actress.name || ''
      this.$router.push({ name: 'Actor', query: { name } })
    },
    goSeries(item) {
      // 系列点击 → 搜索结果页，带 series 参数
      this.$router.push({ path: '/search', query: { series: item.name } })
    },
    legendaryBubbleClass(tag) {
      if (this.cfg.colorMode !== 'legendary' || !this.cfg.goldLegend) return ''
      const rarity = this.rarityMap[tag.id] || 'common'
      if (rarity === 'legendary') return 'rarity-legendary'
      return `rarity-${rarity}`
    },
  },
  beforeUnmount() {
    const cloud = this.$refs.tagCloudRef
    if (cloud) {
      cloud.removeEventListener('mousemove', this.handleMouseMove)
      cloud.removeEventListener('mouseleave', this.handleMouseLeave)
      cloud.removeEventListener('mouseenter', this.onLegendaryEnter, true)
      cloud.removeEventListener('mouseleave', this.onLegendaryLeave, true)
      const bubbles = cloud.querySelectorAll('.bubble')
      gsap.killTweensOf(bubbles)
    }
    const seriesCloud = this.$refs.seriesCloudRef
    if (seriesCloud) {
      seriesCloud.removeEventListener('mouseenter', this.onLegendaryEnter, true)
      seriesCloud.removeEventListener('mouseleave', this.onLegendaryLeave, true)
      const bubbles = seriesCloud.querySelectorAll('.bubble')
      gsap.killTweensOf(bubbles)
    }
  }
}
</script>

<style scoped>
.genres-page { min-height: 100vh; background: var(--bg-primary); }
.genres-hero { text-align: center; padding: 48px 20px 32px; background: linear-gradient(180deg, var(--bg-secondary) 0%, var(--bg-primary) 100%); }
.hero-title { font-size: 36px; font-weight: 700; color: var(--text-primary); margin-bottom: 8px; }
.hero-subtitle { font-size: 14px; color: var(--text-muted); }
.tag-cloud-wrap { padding: 20px; max-width: 1200px; margin: 0 auto; }
.cloud-header { display: flex; align-items: center; justify-content: space-between; padding: 0 4px 16px; }
.cloud-hint { font-size: 13px; color: var(--text-muted); }
.shuffle-btn { display: flex; align-items: center; gap: 6px; background: var(--bg-card); border: 1px solid var(--border); color: var(--text-secondary); font-size: 13px; cursor: pointer; padding: 6px 14px; border-radius: 20px; transition: var(--transition); }
.shuffle-btn:hover:not(:disabled) { border-color: var(--accent); color: var(--accent); }
.shuffle-btn:disabled { opacity: 0.5; cursor: not-allowed; }
.loading-wrap { text-align: center; padding: 60px; color: var(--text-secondary); }
.spinner-large { width: 40px; height: 40px; border: 3px solid rgba(255,255,255,0.1); border-top-color: var(--accent); border-radius: 50%; animation: spin 0.8s linear infinite; margin: 0 auto 16px; }

/* Tab Bar */
.tab-bar { display: flex; gap: 4px; justify-content: center; margin-top: 24px; }
.tab-btn { padding: 8px 24px; background: var(--bg-card); border: 1px solid var(--border); color: var(--text-secondary); font-size: 14px; font-weight: 600; cursor: pointer; border-radius: 20px; transition: var(--transition); display: inline-flex; align-items: center; gap: 6px; }
.tab-btn:hover { border-color: var(--accent); color: var(--accent); }
.tab-btn.active { background: var(--accent); border-color: var(--accent); color: #fff; }
.tab-count { background: rgba(255,255,255,0.2); border-radius: 10px; padding: 1px 7px; font-size: 11px; }
.tab-btn.active .tab-count { background: rgba(255,255,255,0.3); }

/* 演员卡片：整个圆形，参照VideoModal */
.actress-tab { padding: 20px; max-width: 1200px; margin: 0 auto; }
.actress-header { display: flex; align-items: center; justify-content: space-between; padding: 0 4px 16px; }
.actress-grid { display: grid; gap: 20px; justify-items: center; }
.actress-card { display: flex; flex-direction: column; align-items: center; gap: 8px; cursor: pointer; transition: var(--transition); }
.actress-card:hover { transform: translateY(-4px); }
.actress-avatar { width: var(--actress-avatar-size, 80px); height: var(--actress-avatar-size, 80px); border-radius: 50%; overflow: hidden; background: var(--bg-secondary); border: 2px solid var(--border); transition: border-color 0.2s, box-shadow 0.2s; flex-shrink: 0; }
.actress-card:hover .actress-avatar { border-color: var(--accent); box-shadow: 0 0 16px var(--accent-glow); }
.actress-avatar img { width: 100%; height: 100%; object-fit: cover; object-position: top center; transition: transform 0.3s ease; }
.actress-card:hover .actress-avatar img { transform: scale(1.06); }
.actress-name { font-size: 12px; font-weight: 600; color: var(--text-primary); text-align: center; max-width: 90px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

.tag-cloud { display: flex; flex-wrap: wrap; justify-content: center; align-items: center; padding: 10px 4px; background: var(--bg-primary); border-radius: 16px; }
.bubble {
  border-radius: 50px;
  color: white;
  font-weight: 600;
  cursor: pointer;
  user-select: none;
  white-space: nowrap;
  box-shadow: 0 4px 20px rgba(0,0,0,0.3);
  text-shadow: 0 1px 2px rgba(0,0,0,0.3);
  flex-shrink: 0;
  opacity: 0.88;
  transform-origin: center center;
  position: relative;
  transition: box-shadow 0.3s ease, filter 0.3s ease;
  animation: bubble-float 1.8s ease-in-out infinite;
}

/* ================================================
   LEGENDARY MODE — 炉石传说卡牌质感
   Legendary=橙金 Epic=紫 Rare=蓝 Common=白（无光）
   GSAP: proximity scale + hover glow
   CSS: shimmer (epic/legendary only) + breathing glow (legendary only)
   ================================================ */

/* ---------- 白卡 Common：无光效，纯药丸气泡 ---------- */
.bubble.rarity-common {
  border-radius: 50px;
  box-shadow: 0 3px 10px rgba(0, 0, 0, 0.22);
  background: linear-gradient(135deg, var(--rarity-common), color-mix(in srgb, var(--rarity-common) 70%, #000)) !important;
}
.bubble.rarity-common:hover {
  box-shadow: 0 5px 18px rgba(0, 0, 0, 0.35);
}

/* ---------- 蓝卡 Rare：纯平板，蓝天白云无特效 ---------- */
.bubble.rarity-rare {
  border-radius: 50px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.18);
  background: linear-gradient(135deg, var(--rarity-rare), color-mix(in srgb, var(--rarity-rare) 75%, #000)) !important;
}
.bubble.rarity-rare:hover {
  box-shadow: 0 4px 14px rgba(0, 0, 0, 0.25);
}

/* ---------- 紫卡 Epic：紫色呼吸光晕 + 扫光 ---------- */
.bubble.rarity-epic {
  border-radius: 50px;
  box-shadow:
    0 0 12px 4px color-mix(in srgb, var(--rarity-epic) 60%, transparent),
    0 0 35px 10px color-mix(in srgb, var(--rarity-epic) 35%, transparent);
  background: linear-gradient(135deg, var(--rarity-epic), color-mix(in srgb, var(--rarity-epic) 75%, #000)) !important;
  animation: epic-breathe 2.8s ease-in-out infinite;
}
.bubble.rarity-epic::before {
  content: '';
  position: absolute;
  top: 0; left: -30%;
  width: 26%;
  height: 100%;
  background: linear-gradient(
    105deg,
    transparent 0%,
    rgba(220, 180, 255, 0.35) 45%,
    rgba(240, 210, 255, 0.75) 50%,
    rgba(220, 180, 255, 0.4) 55%,
    transparent 100%
  );
  transform: skewX(-18deg);
  pointer-events: none;
  border-radius: inherit;
  z-index: 1;
  animation: epic-shimmer 2.2s linear infinite;
}
@keyframes epic-breathe {
  0%, 100% {
    box-shadow:
      0 0 10px 3px color-mix(in srgb, var(--rarity-epic) 60%, transparent),
      0 0 30px 9px color-mix(in srgb, var(--rarity-epic) 35%, transparent);
    filter: brightness(1.04) saturate(1.1);
  }
  50% {
    box-shadow:
      0 0 18px 6px color-mix(in srgb, var(--rarity-epic) 80%, transparent),
      0 0 50px 15px color-mix(in srgb, var(--rarity-epic) 50%, transparent);
    filter: brightness(1.1) saturate(1.25);
  }
}
@keyframes epic-shimmer {
  0%   { left: -30%; }
  100% { left: 130%; }
}
/* 浮动动画（所有气泡共用，替换原有逐气泡 GSAP tween） */
@keyframes bubble-float {
  0%, 100% { transform: translateY(0); }
  50%       { transform: translateY(-5px); }
}

/* ---------- 金卡 Legendary：皇家琥珀光晕 + 3D悬浮 ---------- */
.bubble.rarity-legendary {
  border-radius: 14px;
  overflow: visible;
  transform-style: preserve-3d;
  perspective: 800px;
  animation: bubble-float 1.8s ease-in-out infinite;
  /* 静态琥珀金内敛光晕（hover 光效全由 GSAP 接管，避免 CSS 动画冲突闪烁） */
  box-shadow:
    0 0 14px 4px color-mix(in srgb, var(--rarity-legendary) 55%, transparent),
    0 0 38px 10px color-mix(in srgb, var(--rarity-legendary) 30%, transparent),
    0 0 75px 22px color-mix(in srgb, var(--rarity-legendary) 16%, transparent),
    0 4px 16px rgba(0, 0, 0, 0.45);
  /* 皇家金渐变：深金→中金→琥珀金→亮金→中金→深金 */
  background: linear-gradient(
    145deg,
    #8B6914 0%,
    #C9960C 20%,
    #E5B819 35%,
    #F5D033 45%,
    #E5B819 55%,
    #C9960C 70%,
    #8B6914 100%
  ) !important;
  position: relative;
  z-index: 1;
  will-change: transform;
}
/* 3D悬浮层 — 承载旋转和全息 */
.bubble.rarity-legendary .legendary-inner {
  position: relative;
  transform-style: preserve-3d;
  width: 100%;
  height: 100%;
  border-radius: inherit;
}
/* 全息幻彩层 — color-dodge 叠加在金色上 */
.bubble.rarity-legendary .legendary-inner::before {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: inherit;
  background:
    repeating-linear-gradient(
      125deg,
      transparent 0px,
      transparent 3px,
      rgba(255, 255, 255, 0.06) 3px,
      rgba(255, 255, 255, 0.06) 4px
    ),
    repeating-linear-gradient(
      65deg,
      transparent 0px,
      transparent 8px,
      rgba(255, 200, 50, 0.08) 8px,
      rgba(255, 200, 50, 0.08) 9px
    ),
    radial-gradient(ellipse 80% 60% at 50% 40%, rgba(255, 240, 160, 0.18) 0%, transparent 70%);
  mix-blend-mode: color-dodge;
  pointer-events: none;
  z-index: 2;
  opacity: 0.7;
  transition: opacity 0.3s;
}
/* 环绕金晕 — 静态光晕层（位于 inner 之外） */
.bubble.rarity-legendary::before {
  content: '';
  position: absolute;
  inset: -6px;
  border-radius: 18px;
  background: conic-gradient(
    from 0deg,
    transparent 0deg,
    rgba(255, 215, 0, 0.18) 30deg,
    rgba(255, 200, 50, 0.35) 60deg,
    rgba(255, 215, 0, 0.18) 90deg,
    transparent 120deg,
    rgba(255, 215, 0, 0.12) 180deg,
    transparent 210deg,
    rgba(255, 215, 0, 0.22) 250deg,
    rgba(255, 200, 50, 0.35) 290deg,
    rgba(255, 215, 0, 0.18) 330deg,
    transparent 360deg
  );
  z-index: -1;
  pointer-events: none;
  opacity: 0.85;
}
/* 内部金色高光边缘 */
.bubble.rarity-legendary::after {
  content: '';
  position: absolute;
  inset: 2px;
  border-radius: 11px;
  background: linear-gradient(
    145deg,
    rgba(255, 255, 210, 0.35) 0%,
    transparent 40%,
    transparent 60%,
    rgba(139, 105, 20, 0.25) 100%
  );
  pointer-events: none;
  z-index: 3;
}
/* Hover 状态 */
.bubble.rarity-legendary:hover {
  filter: brightness(1.18) saturate(1.45);
  box-shadow:
    0 0 28px 8px color-mix(in srgb, var(--rarity-legendary) 85%, transparent),
    0 0 75px 22px color-mix(in srgb, var(--rarity-legendary) 55%, transparent),
    0 0 130px 48px color-mix(in srgb, var(--rarity-legendary) 28%, transparent),
    0 6px 22px rgba(0, 0, 0, 0.5);
}
.bubble.rarity-legendary:hover::before {
  opacity: 1;
}
.bubble.rarity-legendary:hover .legendary-inner::before {
  opacity: 1;
}

/* ---------- Active状态 ---------- */
.bubble.active {
  opacity: 1;
  filter: brightness(1.1) saturate(1.2);
}

</style>
