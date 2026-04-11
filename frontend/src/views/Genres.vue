<template>
  <div class="genres-page">
    <div class="genres-hero">
      <h1 class="hero-title">题材发现</h1>
      <p class="hero-subtitle">随机浏览，发现更多内容</p>
    </div>

    <div class="tag-cloud-wrap" ref="cloudRef">
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
        <div
          v-for="tag in shuffledTags"
          :key="tag.id"
          class="bubble"
          :data-id="tag.id"
          :style="bubbleStyle(tag)"
          @click="goGenre(tag)"
        >
          {{ tag.name_en || tag.name_ja || tag.name }}
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import gsap from 'gsap'
import api from '../api'

// === Color Palettes ===
const PALETTES = {
  monet: [
    'linear-gradient(135deg, #e0c3fc, #8ec5fc)',
    'linear-gradient(135deg, #fbc2eb, #a6c1ee)',
    'linear-gradient(135deg, #d4fc79, #96e6a1)',
    'linear-gradient(135deg, #a18cd1, #fbc2eb)',
    'linear-gradient(135deg, #f093fb, #f5576c)',
    'linear-gradient(135deg, #c2e9fb, #a1c4fd)',
    'linear-gradient(135deg, #e0c3fc, #8ec5fc)',
    'linear-gradient(135deg, #f5f7fa, #c3cfe2)',
  ],
  sunset: [
    'linear-gradient(135deg, #ff9a9e, #fecfef)',
    'linear-gradient(135deg, #fa709a, #fee140)',
    'linear-gradient(135deg, #ffecd2, #fcb69f)',
    'linear-gradient(135deg, #ff7eb3, #fecfef)',
    'linear-gradient(135deg, #fa709a, #fee140)',
    'linear-gradient(135deg, #f97316, #fbbf24)',
    'linear-gradient(135deg, #ff9a9e, #fecfef)',
    'linear-gradient(135deg, #f97316, #fb923c)',
  ],
  ocean: [
    'linear-gradient(135deg, #4facfe, #00f2fe)',
    'linear-gradient(135deg, #43e97b, #38f9d7)',
    'linear-gradient(135deg, #84fab0, #8fd3f4)',
    'linear-gradient(135deg, #0fd850, #00f2fe)',
    'linear-gradient(135deg, #4facfe, #00f2fe)',
    'linear-gradient(135deg, #89f7fe, #66a6ff)',
    'linear-gradient(135deg, #4facfe, #00f2fe)',
    'linear-gradient(135deg, #43e97b, #38f9d7)',
  ],
  forest: [
    'linear-gradient(135deg, #43e97b, #38f9d7)',
    'linear-gradient(135deg, #56ab2f, #a8e063)',
    'linear-gradient(135deg, #11998e, #38ef7d)',
    'linear-gradient(135deg, #84fab0, #8fd3f4)',
    'linear-gradient(135deg, #56ab2f, #a8e063)',
    'linear-gradient(135deg, #11998e, #38ef7d)',
    'linear-gradient(135deg, #43e97b, #38f9d7)',
    'linear-gradient(135deg, #0ba360, #3cba92)',
  ],
  gold: [
    'linear-gradient(135deg, #f79711, #ffd200)',
    'linear-gradient(135deg, #f5af19, #f12711)',
    'linear-gradient(135deg, #f12711, #f5af19)',
    'linear-gradient(135deg, #f79711, #ffd700)',
    'linear-gradient(135deg, #f5af19, #f12711)',
    'linear-gradient(135deg, #fcff00, #f79711)',
    'linear-gradient(135deg, #ffd700, #f79711)',
    'linear-gradient(135deg, #f5af19, #ffd700)',
  ],
}

// Gold legend rarity gradients — legendary(gold) → common(blue) → popular(gray)
const RARITY_GRADIENTS = {
  legendary: [
    'linear-gradient(135deg, #f79711, #ffd700)',
    'linear-gradient(135deg, #f5af19, #f12711)',
    'linear-gradient(135deg, #fcff00, #f79711)',
    'linear-gradient(135deg, #ffd700, #f79711)',
  ],
  rare: [
    'linear-gradient(135deg, #e040fb, #7c4dff)',
    'linear-gradient(135deg, #7c4dff, #e040fb)',
    'linear-gradient(135deg, #f48fb1, #e040fb)',
  ],
  common: [
    'linear-gradient(135deg, #4facfe, #00f2fe)',
    'linear-gradient(135deg, #43e97b, #38f9d7)',
    'linear-gradient(135deg, #4facfe, #00f2fe)',
  ],
  popular: [
    'linear-gradient(135deg, #cfd9df, #e2ebf0)',
    'linear-gradient(135deg, #bdc3c7, #2c3e50)',
    'linear-gradient(135deg, #bdc3c7, #2c3e50)',
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
const DEFAULT_CFG = {
  baseSize: 16,
  fillPercent: 50,
  spacing: 16,
  colorMode: 'random',   // 'random' | 'legendary'
  palette: 'monet',      // for random mode: monet/sunset/ocean/forest/gold/custom
  customGradients: [],   // for custom palette
  goldLegend: true,      // enable gold legend mode
}

export default {
  name: 'Genres',
  data() {
    return {
      categories: [],
      shuffledTags: [],
      loading: false,
      statsLoading: false,
      cfg: { ...DEFAULT_CFG },
      categoryStats: {},  // { categoryId: video_count }
      rarityMap: {},      // { categoryId: 'legendary'|'rare'|'common'|'popular' }
      bubbleRects: new Map(),
    }
  },
  computed: {
    cloudStyle() {
      return { gap: `${this.cfg.spacing}px` }
    },
  },
  async mounted() {
    this.loadCfg()
    await this.loadCategories()
    if (this.cfg.goldLegend) {
      await this.loadCategoryStats()
    }
  },
  methods: {
    loadCfg() {
      try {
        const saved = localStorage.getItem(LS_KEY)
        if (saved) {
          this.cfg = { ...DEFAULT_CFG, ...JSON.parse(saved) }
        }
      } catch {}
    },
    getGradient(tag, palette) {
      const gradients = palette === 'custom' && this.cfg.customGradients.length
        ? this.cfg.customGradients
        : PALETTES[palette] || PALETTES.monet
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
      const gradient = this.cfg.colorMode === 'legendary' && this.cfg.goldLegend
        ? this.getRarityGradient(tag)
        : this.getGradient(tag, this.cfg.palette)
      return {
        background: gradient,
        fontSize: `${size}px`,
        padding: `${Math.round(size * fill * 0.6)}px ${Math.round(size * fill * 1.2)}px`,
      }
    },
    async loadCategories() {
      this.loading = true
      try {
        const resp = await api.listCategories()
        this.categories = Array.isArray(resp.data) ? resp.data : (resp.data.data || [])
        this.shuffledTags = shuffle(this.categories)
      } catch (e) {
        console.error('Load categories failed:', e)
        this.categories = []
      } finally {
        this.loading = false
        this.$nextTick(() => this.initGsap())
      }
    },
    async loadCategoryStats() {
      this.statsLoading = true
      try {
        const resp = await api.categoryStats()
        const stats = Array.isArray(resp.data) ? resp.data : (resp.data || [])
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
      // Sort categories by video_count ascending
      const sorted = [...stats].sort((a, b) => (a.video_count || 0) - (b.video_count || 0))
      const n = sorted.length
      const rarityMap = {}
      sorted.forEach((cat, i) => {
        const pct = i / Math.max(n - 1, 1)  // 0 = rarest, 1 = most popular
        if (pct < 0.2) rarityMap[cat.id] = 'legendary'
        else if (pct < 0.5) rarityMap[cat.id] = 'rare'
        else if (pct < 0.8) rarityMap[cat.id] = 'common'
        else rarityMap[cat.id] = 'popular'
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

      bubbles.forEach((bubble, i) => {
        gsap.to(bubble, {
          y: -5,
          duration: 1.4 + (i % 4) * 0.2,
          repeat: -1, yoyo: true, ease: 'sine.inOut', delay: i * 0.03,
        })
      })

      cloud.addEventListener('mousemove', this.handleMouseMove)
      cloud.addEventListener('mouseleave', this.handleMouseLeave)
    },
    handleMouseMove(e) {
      const cloud = this.$refs.tagCloudRef
      if (!cloud) return
      const mouseX = e.clientX
      const mouseY = e.clientY
      const bubbles = cloud.querySelectorAll('.bubble')

      const scales = new Map()
      const hoveredBubbles = []
      bubbles.forEach(bubble => {
        const r = bubble.getBoundingClientRect()
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

      // Collision detection
      const overlapped = new Set()
      for (let i = 0; i < hoveredBubbles.length; i++) {
        for (let j = i + 1; j < hoveredBubbles.length; j++) {
          const a = hoveredBubbles[i], b = hoveredBubbles[j]
          const ra = a.getBoundingClientRect(), rb = b.getBoundingClientRect()
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
        if (scale > 1) {
          gsap.to(bubble, { scale, opacity: 1, zIndex: isOverlapped ? ++maxZ : 50, duration: 0.15, ease: 'back.out(1.2)', overwrite: 'auto' })
        } else {
          gsap.to(bubble, { scale: 1, opacity: 0.88, zIndex: 1, duration: 0.2, ease: 'power3.out', overwrite: 'auto' })
        }
      })
      this.updateBubbleRects(bubbles)
    },
    handleMouseLeave() {
      const cloud = this.$refs.tagCloudRef
      if (!cloud) return
      const bubbles = cloud.querySelectorAll('.bubble')
      gsap.to(bubbles, { scale: 1, opacity: 0.88, zIndex: 1, duration: 0.3, ease: 'back.out(1.2)', stagger: 0.004 })
    },
    reshuffle() {
      const cloud = this.$refs.tagCloudRef
      if (cloud) {
        const bubbles = cloud.querySelectorAll('.bubble')
        gsap.to(bubbles, { scale: 0, opacity: 0, duration: 0.08, stagger: 0, ease: 'power2.in' })
      }
      this.shuffledTags = shuffle(this.categories)
      this.$nextTick(() => {
        const newBubbles = this.$refs.tagCloudRef?.querySelectorAll('.bubble')
        if (!newBubbles?.length) return
        gsap.fromTo(newBubbles,
          { scale: 0, opacity: 0 },
          { scale: 1, opacity: 0.88, duration: 0.3, stagger: 0.006, ease: 'back.out(1.7)' }
        )
      })
    },
    goGenre(tag) {
      this.$router.push({ name: 'GenreDetail', params: { categoryId: tag.id } })
    },
  },
  beforeUnmount() {
    const cloud = this.$refs.tagCloudRef
    if (cloud) {
      cloud.removeEventListener('mousemove', this.handleMouseMove)
      cloud.removeEventListener('mouseleave', this.handleMouseLeave)
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
.tag-cloud { display: flex; flex-wrap: wrap; justify-content: center; align-items: center; padding: 10px 4px; background: var(--bg-primary); border-radius: 16px; }
.bubble { border-radius: 50px; color: white; font-weight: 600; cursor: pointer; user-select: none; white-space: nowrap; box-shadow: 0 4px 20px rgba(0,0,0,0.3); text-shadow: 0 1px 2px rgba(0,0,0,0.3); flex-shrink: 0; opacity: 0.88; transform-origin: center center; position: relative; }
@keyframes spin { to { transform: rotate(360deg); } }
</style>
