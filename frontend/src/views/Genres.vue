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
          :class="legendaryBubbleClass(tag)"
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
  // 金色传说：低饱和琥珀金，琥珀、褐金、锈金（暗色主题友好）
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
      const isLegendary = this.cfg.colorMode === 'legendary' && this.cfg.goldLegend
      const gradient = isLegendary
        ? this.getRarityGradient(tag)
        : this.getGradient(tag, this.cfg.palette)
      const style = {
        background: gradient,
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

      // No legendary pulse animations — glow is hover-only via handleMouseMove
      cloud.addEventListener('mousemove', this.handleMouseMove)
      cloud.addEventListener('mouseleave', this.handleMouseLeave)
    },
    handleMouseMove(e) {
      const cloud = this.$refs.tagCloudRef
      if (!cloud) return
      const mouseX = e.clientX
      const mouseY = e.clientY
      const bubbles = cloud.querySelectorAll('.bubble')

      // Proximity scale for all nearby bubbles
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

      // Collision detection for z-index layering
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
        const isHovered = hoveredBubbles.includes(bubble)
        const isLegendary = bubble.classList.contains('rarity-legendary')
        const isRare = bubble.classList.contains('rarity-rare')
        const inLegendaryMode = this.cfg.colorMode === 'legendary' && this.cfg.goldLegend

        if (isHovered && scale > 1) {
          // Proximity scale + hover outer glow (GSAP overrides CSS breathing)
          let outerGlow = ''
          if (isLegendary && inLegendaryMode) {
            outerGlow = '0 0 20px 6px rgba(255, 200, 0, 0.95), 0 0 50px 16px rgba(255, 160, 0, 0.7), 0 0 100px 30px rgba(255, 120, 0, 0.45)'
          } else if (isRare && inLegendaryMode) {
            outerGlow = '0 0 16px 5px rgba(180, 110, 255, 0.9), 0 0 40px 12px rgba(155, 80, 240, 0.6)'
          } else {
            outerGlow = '0 6px 24px rgba(0,0,0,0.35)'
          }
          gsap.to(bubble, {
            scale,
            opacity: 1,
            zIndex: isOverlapped ? ++maxZ : 50,
            boxShadow: outerGlow,
            duration: 0.12,
            ease: 'back.out(1.2)',
            overwrite: 'auto',
          })
        } else {
          // Clear GSAP boxShadow → CSS breathing animation resumes
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
      this.updateBubbleRects(bubbles)
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
    reshuffle() {
      const cloud = this.$refs.tagCloudRef
      if (cloud) {
        const bubbles = cloud.querySelectorAll('.bubble')
        gsap.killTweensOf(bubbles)
        gsap.to(bubbles, { scale: 0, opacity: 0, duration: 0.08, stagger: 0, ease: 'power2.in' })
      }
      this.shuffledTags = shuffle(this.categories)
      this.$nextTick(() => {
        const newBubbles = this.$refs.tagCloudRef?.querySelectorAll('.bubble')
        if (!newBubbles?.length) return
        // Explosion burst from center: each bubble flies outward from the grid center
        // with random direction, overshoot scale (1.5 → 1), then settle
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
    legendaryBubbleClass(tag) {
      if (this.cfg.colorMode !== 'legendary' || !this.cfg.goldLegend) return ''
      // Only the ACTUAL legendary tier gets 'legendary' class (triggers shimmer)
      // rare/common/popular get their tier class only (no shimmer, just breathing or glow)
      const rarity = this.rarityMap[tag.id] || 'common'
      if (rarity === 'legendary') return 'legendary rarity-legendary'
      return `rarity-${rarity}`
    },
  },
  beforeUnmount() {
    const cloud = this.$refs.tagCloudRef
    if (cloud) {
      cloud.removeEventListener('mousemove', this.handleMouseMove)
      cloud.removeEventListener('mouseleave', this.handleMouseLeave)
      const bubbles = cloud.querySelectorAll('.bubble')
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
}

/* ================================================
   LEGENDARY MODE — 炉石传说橙卡质感
   GSAP: proximity scale + z-index + hover outer glow
   CSS: shimmer (legendary only) + breathing (all legendary bubbles)
   ================================================ */

/* Shimmer sweep — only on ACTUAL legendary tier bubbles */
.bubble.rarity-legendary::before {
  content: '';
  position: absolute;
  top: 0; left: -30%;
  width: 28%;
  height: 100%;
  background: linear-gradient(
    90deg,
    transparent 0%,
    rgba(255, 245, 180, 0.55) 40%,
    rgba(255, 255, 220, 0.95) 50%,
    rgba(255, 245, 180, 0.55) 60%,
    transparent 100%
  );
  transform: skewX(-18deg);
  pointer-events: none;
  border-radius: inherit;
  z-index: 1;
  animation: legendary-shimmer 2.4s linear infinite;
}

@keyframes legendary-shimmer {
  0%   { left: -30%; }
  100% { left: 130%; }
}

/* Breathing glow — ALL legendary-mode bubbles breathe (legendary + rare + common) */
.bubble.legendary {
  animation: legendary-breathe 2.2s ease-in-out infinite;
}
.bubble.rarity-rare {
  animation: rare-breathe 3s ease-in-out infinite;
}

@keyframes legendary-breathe {
  0%, 100% {
    box-shadow:
      0 0 8px  3px rgba(255, 185, 0, 0.88),
      0 0 22px 6px rgba(255, 150, 0, 0.62),
      0 0 50px 14px rgba(255, 110, 0, 0.32);
    filter: brightness(1.05) saturate(1.1);
  }
  50% {
    box-shadow:
      0 0 14px 5px rgba(255, 210, 0, 1),
      0 0 36px 10px rgba(255, 170, 0, 0.78),
      0 0 80px 22px rgba(255, 130, 0, 0.48);
    filter: brightness(1.14) saturate(1.3);
  }
}

@keyframes rare-breathe {
  0%, 100% {
    box-shadow:
      0 0 6px  2px rgba(170, 100, 255, 0.78),
      0 0 16px 4px rgba(148, 76, 220, 0.50);
    filter: brightness(1.03) saturate(1.08);
  }
  50% {
    box-shadow:
      0 0 10px 3px rgba(185, 115, 255, 0.92),
      0 0 26px 7px rgba(165, 90, 240, 0.65);
    filter: brightness(1.08) saturate(1.18);
  }
}

/* Hover: GSAP pauses CSS animations via animation-play-state */
.bubble.legendary:hover,
.bubble.rarity-legendary:hover {
  animation-play-state: paused;
}
.bubble.rarity-legendary:hover::before {
  animation-play-state: paused;
}

/* Popular: no glow */
.bubble.rarity-popular {
  box-shadow: 0 4px 14px rgba(0,0,0,0.22);
}

/* Common: subtle blue glow (no breathing in legendary mode) */
.bubble.rarity-common {
  box-shadow: 0 0 6px 2px rgba(100, 160, 200, 0.45);
  filter: brightness(1.03);
}

</style>
