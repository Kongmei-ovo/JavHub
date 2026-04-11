<template>
  <div class="genres-page">
    <!-- Hero -->
    <div class="genres-hero">
      <h1 class="hero-title">题材发现</h1>
      <p class="hero-subtitle">随机浏览，发现更多内容</p>
    </div>

    <!-- 标签气泡云 -->
    <div class="tag-cloud-wrap">
      <div v-if="loading" class="loading-wrap">
        <div class="spinner-large"></div>
        <p>加载题材中...</p>
      </div>

      <div v-else class="tag-cloud">
        <div
          v-for="tag in shuffledTags"
          :key="tag.id"
          class="bubble"
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

export default {
  name: 'Genres',
  data() {
    return {
      categories: [],
      shuffledTags: [],
      loading: false
    }
  },
  async mounted() {
    await this.loadCategories()
  },
  methods: {
    bubbleStyle(tag) {
      const idx = hashCode(tag.name_en || tag.name_ja || tag.name) % BUBBLE_COLORS.length
      const baseSize = 16 + (hashCode((tag.name_en || tag.name_ja || tag.name) + 'size') % 14)
      const size = `${baseSize}px`
      return {
        background: BUBBLE_COLORS[idx],
        fontSize: size,
        '--bubble-delay': `${(hashCode((tag.name_en || tag.name_ja || tag.name) + 'delay') % 20) * 0.1}s`,
        '--bubble-x': `${(hashCode((tag.name_en || tag.name_ja || tag.name) + 'x') % 60 - 30)}px`,
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
      }
    },
    goGenre(tag) {
      this.$router.push({ name: 'GenreDetail', params: { categoryId: tag.id } })
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
  gap: 16px;
  justify-content: center;
  align-items: center;
  padding: 30px 20px;
}

.bubble {
  padding: 10px 20px;
  border-radius: 50px;
  color: white;
  font-weight: 600;
  cursor: pointer;
  user-select: none;
  white-space: nowrap;
  box-shadow: 0 4px 20px rgba(0,0,0,0.3);
  animation: floatBubble 3s ease-in-out infinite;
  animation-delay: var(--bubble-delay, 0s);
  text-shadow: 0 1px 2px rgba(0,0,0,0.3);
  flex-shrink: 0;
  opacity: 0.65;
  filter: brightness(0.85);
  transition: transform 0.5s cubic-bezier(0.25, 0.46, 0.45, 0.94),
              box-shadow 0.3s ease,
              filter 0.25s ease,
              opacity 0.25s ease;
}

@keyframes floatBubble {
  0%, 100% { transform: translateY(0) translateX(var(--bubble-x, 0px)); }
  50% { transform: translateY(-8px) translateX(var(--bubble-x, 0px)); }
}

.bubble:hover {
  transform: scale(1.18) translateY(-6px) !important;
  box-shadow: 0 12px 40px rgba(0,0,0,0.45);
  filter: brightness(1.15);
  opacity: 1;
  z-index: 10;
  transition: transform 0.5s cubic-bezier(0.25, 0.46, 0.45, 0.94),
              box-shadow 0.3s ease,
              filter 0.25s ease,
              opacity 0.25s ease;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>
