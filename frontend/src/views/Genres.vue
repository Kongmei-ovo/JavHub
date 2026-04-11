<template>
  <div class="genres-page">
    <!-- Hero -->
    <div class="genres-hero">
      <h1 class="hero-title">题材发现</h1>
      <p class="hero-subtitle">随机浏览，发现更多内容</p>
    </div>

    <!-- 标签气泡云 -->
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

const BUBBLE_COLORS = [
  'linear-gradient(135deg, #667eea, #764ba2)',
  'linear-gradient(135deg, #f093fb, #f5576c)',
  'linear-gradient(135deg, #4facfe, #00f2fe)',
  'linear-gradient(135deg, #43e97b, #38f9d7)',
  'linear-gradient(135deg, #fa709a, #fee140)',
  'linear-gradient(135deg, #a18cd1, #fbc2eb)',
  'linear-gradient(135deg, #ff9a9e, #fecfef)',
  'linear-gradient(135deg, #ffecd2, #fcb69f)',
  'linear-gradient(135deg, #84fab0, #8fd3f4)',
  'linear-gradient(135deg, #cfd9df, #e2ebf0)',
  'linear-gradient(135deg, #a1c4fd, #c2e9fb)',
  'linear-gradient(135deg, #d4fc79, #96e6a1)',
]

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
  baseSize: 16,       // px, uniform font size
  fillPercent: 50,     // padding = fontSize * fillPercent/100
  spacing: 16,         // gap px
}

export default {
  name: 'Genres',
  data() {
    return {
      categories: [],
      shuffledTags: [],
      loading: false,
      cfg: { ...DEFAULT_CFG },
      // Track visible bounding rects for collision detection
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
    bubbleStyle(tag) {
      const idx = hashCode(tag.name_en || tag.name_ja || tag.name) % BUBBLE_COLORS.length
      const size = this.cfg.baseSize
      const fill = this.cfg.fillPercent / 100
      return {
        background: BUBBLE_COLORS[idx],
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
    rectsEqual(a, b, tolerance = 1) {
      return (
        Math.abs(a.left - b.left) <= tolerance &&
        Math.abs(a.top - b.top) <= tolerance &&
        Math.abs(a.width - b.width) <= tolerance &&
        Math.abs(a.height - b.height) <= tolerance
      )
    },
    updateBubbleRects(bubbles) {
      const newRects = new Map()
      bubbles.forEach(b => {
        const r = b.getBoundingClientRect()
        newRects.set(b, r)
      })
      this.bubbleRects = newRects
    },
    initGsap() {
      const cloud = this.$refs.tagCloudRef
      if (!cloud) return
      const bubbles = cloud.querySelectorAll('.bubble')

      this.updateBubbleRects(bubbles)

      // entrance: simultaneous pop-in
      gsap.fromTo(bubbles,
        { scale: 0, opacity: 0 },
        {
          scale: 1,
          opacity: 1,
          duration: 0.25,
          stagger: 0.005,
          ease: 'back.out(1.7)',
        }
      )

      // subtle float (y-axis only)
      bubbles.forEach((bubble, i) => {
        gsap.to(bubble, {
          y: -5,
          duration: 1.4 + (i % 4) * 0.2,
          repeat: -1,
          yoyo: true,
          ease: 'sine.inOut',
          delay: i * 0.03,
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

      // Build current rects and detect collision pairs
      const hoveredRects = new Map()
      const hoveredBubbles = []

      // Phase 1: determine scales for all bubbles
      const scales = new Map()
      bubbles.forEach(bubble => {
        const r = bubble.getBoundingClientRect()
        const cx = r.left + r.width / 2
        const cy = r.top + r.height / 2
        const dist = Math.hypot(mouseX - cx, mouseY - cy)
        const maxDist = 160

        if (dist < maxDist) {
          const scale = 1 + (1 - dist / maxDist) * 0.5
          scales.set(bubble, scale)
          hoveredBubbles.push(bubble)
        } else {
          scales.set(bubble, 1)
        }
        hoveredRects.set(bubble, { ...r, scale: scales.get(bubble) })
      })

      // Phase 2: collision detection — when hovered bubbles scale up,
      // do they overlap each other? Collect all bubbles that are overlapped.
      const overlapped = new Set()
      for (let i = 0; i < hoveredBubbles.length; i++) {
        for (let j = i + 1; j < hoveredBubbles.length; j++) {
          const a = hoveredBubbles[i]
          const b = hoveredBubbles[j]
          const ra = hoveredRects.get(a)
          const rb = hoveredRects.get(b)
          const sa = ra.scale
          const sb = rb.scale

          // Scaled bounding rect of a
          const raScaled = {
            left: ra.left - (sa - 1) * ra.width / 2,
            right: ra.right + (sa - 1) * ra.width / 2,
            top: ra.top - (sa - 1) * ra.height / 2,
            bottom: ra.bottom + (sa - 1) * ra.height / 2,
          }
          const rbScaled = {
            left: rb.left - (sb - 1) * rb.width / 2,
            right: rb.right + (sb - 1) * rb.width / 2,
            top: rb.top - (sb - 1) * rb.height / 2,
            bottom: rb.bottom + (sb - 1) * rb.height / 2,
          }

          const intersects = !(raScaled.right < rbScaled.left ||
                               raScaled.left > rbScaled.right ||
                               raScaled.bottom < rbScaled.top ||
                               raScaled.top > rbScaled.bottom)
          if (intersects) {
            overlapped.add(a)
            overlapped.add(b)
          }
        }
      }

      // Phase 3: assign z-index — overlapped bubbles get high z, others get low
      let maxZ = 100
      bubbles.forEach(bubble => {
        const scale = scales.get(bubble)
        const isOverlapped = overlapped.has(bubble)

        if (scale > 1) {
          // Near mouse: scale up, raise z if overlapped
          gsap.to(bubble, {
            scale,
            opacity: 1,
            zIndex: isOverlapped ? ++maxZ : 50,
            duration: 0.15,
            ease: 'back.out(1.2)',
            overwrite: 'auto',
          })
        } else {
          gsap.to(bubble, {
            scale: 1,
            opacity: 0.88,
            zIndex: 1,
            duration: 0.2,
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
      gsap.to(bubbles, {
        scale: 1,
        opacity: 0.88,
        zIndex: 1,
        duration: 0.3,
        ease: 'back.out(1.2)',
        stagger: 0.004,
      })
    },
    reshuffle() {
      const cloud = this.$refs.tagCloudRef
      // Simultaneous shrink — no stagger, all bubbles vanish at once
      if (cloud) {
        const bubbles = cloud.querySelectorAll('.bubble')
        gsap.to(bubbles, {
          scale: 0,
          opacity: 0,
          duration: 0.08,
          stagger: 0,
          ease: 'power2.in',
        })
      }
      // Immediately shuffle data — Vue reuses DOM nodes with same keys
      // Old bubble elements (with new shuffled content) stay in DOM
      this.shuffledTags = shuffle(this.categories)
      this.$nextTick(() => {
        const newBubbles = this.$refs.tagCloudRef?.querySelectorAll('.bubble')
        if (!newBubbles?.length) return
        // All bubbles start at scale 0 and stagger in simultaneously
        gsap.fromTo(newBubbles,
          { scale: 0, opacity: 0 },
          {
            scale: 1,
            opacity: 0.88,
            duration: 0.3,
            stagger: 0.006,
            ease: 'back.out(1.7)',
          }
        )
      })
    },
    goGenre(tag) {
      this.$router.push({ name: 'GenreDetail', params: { categoryId: tag.id } })
    },
    saveCfg() {
      localStorage.setItem(LS_KEY, JSON.stringify(this.cfg))
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
.genres-page {
  min-height: 100vh;
  background: var(--bg-primary);
}

.genres-hero {
  text-align: center;
  padding: 48px 20px 32px;
  background: linear-gradient(180deg, var(--bg-secondary) 0%, var(--bg-primary) 100%);
}

.hero-title {
  font-size: 36px;
  font-weight: 700;
  color: var(--text-primary);
  margin-bottom: 8px;
}

.hero-subtitle {
  font-size: 14px;
  color: var(--text-muted);
}

.tag-cloud-wrap {
  padding: 20px;
  max-width: 1200px;
  margin: 0 auto;
}

.cloud-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 4px 16px;
}

.cloud-hint {
  font-size: 13px;
  color: var(--text-muted);
}

.shuffle-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  background: var(--bg-card);
  border: 1px solid var(--border);
  color: var(--text-secondary);
  font-size: 13px;
  cursor: pointer;
  padding: 6px 14px;
  border-radius: 20px;
  transition: var(--transition);
}

.shuffle-btn:hover:not(:disabled) {
  border-color: var(--accent);
  color: var(--accent);
}

.shuffle-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.loading-wrap {
  text-align: center;
  padding: 60px;
  color: var(--text-secondary);
}

.spinner-large {
  width: 40px;
  height: 40px;
  border: 3px solid rgba(255,255,255,0.1);
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  margin: 0 auto 16px;
}

.tag-cloud {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  align-items: center;
  padding: 10px 4px;
  cursor: default;
  /* Opaque background eliminates "white frame" during shuffle */
  background: var(--bg-primary);
  border-radius: 16px;
}

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
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>
