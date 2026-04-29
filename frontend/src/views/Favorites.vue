<template>
  <div class="favorites-page">
    <div class="curate-header">
      <h1 class="curate-title">私人策展</h1>
      <div class="curate-stats">
        共 {{ state.count }} 个收藏项
      </div>
      
      <!-- iOS 风格的分段选择器 -->
      <div class="segmented-control">
        <button 
          v-for="tab in tabs" 
          :key="tab.id"
          class="segment-item"
          :class="{ active: activeTab === tab.id }"
          @click="activeTab = tab.id"
        >
          {{ tab.label }}
        </button>
      </div>
    </div>

    <!-- 收藏网格 -->
    <div class="curate-content">
      <div v-if="filteredItems.length > 0" class="favorites-grid">
        <div
          v-for="item in filteredItems"
          :key="item.entity_id"
          class="movie-card"
          @click="openVideo(item)"
        >
          <div class="card-cover">
            <img
              :src="cardImageUrl(item.metadata || {})"
              :alt="item.entity_id"
              @error="handleImgError"
              @load="onImgLoad($event)"
              loading="lazy"
              class="cover-img"
            />
            <div v-if="item.metadata?.sample_url" class="card-preview-badge" title="有预览视频">
              <svg viewBox="0 0 24 24" fill="currentColor" width="12" height="12">
                <path d="M8 5v14l11-7z"/>
              </svg>
            </div>
            <!-- Favorite Toggle -->
            <button 
              class="favorite-toggle" 
              :class="{ 'is-active': isFavorited(item.entity_type, item.entity_id) }" 
              @click.stop="toggleFavorite(item)"
            >
              <svg viewBox="0 0 24 24" :fill="isFavorited(item.entity_type, item.entity_id) ? 'currentColor' : 'none'" stroke="currentColor" stroke-width="2">
                <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l8.84-8.84 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/>
              </svg>
            </button>
          </div>
          <div class="card-info">
            <div class="card-code-row">
              <span class="card-code">{{ item.entity_id }}</span>
              <span v-if="item.metadata?.service_code" class="card-type" :class="'type-' + item.metadata.service_code">{{ formatServiceCode(item.metadata.service_code) }}</span>
            </div>
            <div class="card-title" :title="item.metadata?.title_en || item.metadata?.title_ja || item.metadata?.title">
              {{ item.metadata?.title_en_translated || item.metadata?.title_ja_translated || item.metadata?.title_en || item.metadata?.title_ja || item.metadata?.title }}
            </div>
            <div class="card-meta">
              <span v-if="item.metadata?.release_date" class="meta-date">{{ item.metadata.release_date }}</span>
              <span v-if="item.metadata?.runtime_mins" class="meta-time">{{ item.metadata.runtime_mins }}分钟</span>
              <span v-else-if="item.metadata?.runtime" class="meta-time">{{ item.metadata.runtime }}分钟</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 空状态：Apple 风格 -->
      <div v-else class="curate-empty">
        <div class="empty-icon">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="48" height="48">
            <path d="M20.84 4.61a5.5 5.5 0 00-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 00-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 000-7.78z"/>
          </svg>
        </div>
        <h3>开始你的策展</h3>
        <p>在探索过程中点击心形图标，将喜欢的项目收入此处。</p>
        <button class="btn-explore" @click="$router.push('/search')">去探索</button>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed } from 'vue'
import { state, favoriteState } from '../utils/favoriteState'
import { openVideoModal } from '../utils/modalState'
import { jacketHdUrl } from '../utils/imageUrl.js'

export default {
  name: 'Favorites',
  setup() {
    const activeTab = ref('all')
    const tabs = [
      { id: 'all', label: '全部' },
      { id: 'video', label: '影片' },
      { id: 'actress', label: '演员' },
      { id: 'maker', label: '工作室' }
    ]

    const filteredItems = computed(() => {
      if (activeTab.value === 'all') return state.items
      return state.items.filter(i => i.entity_type === activeTab.value)
    })

    const openVideo = (item) => {
      if (item.entity_type === 'video') {
        openVideoModal(item.metadata || { content_id: item.entity_id })
      }
    }

    const isFavorited = (type, id) => {
      return favoriteState.isFavorited(type, id)
    }

    const toggleFavorite = async (item) => {
      try {
        await favoriteState.toggle(item.entity_type, item.entity_id, item.metadata)
      } catch (err) {
        console.error('Failed to toggle favorite:', err)
      }
    }

    const handleImgError = (e) => {
      e.target.src = 'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" width="200" height="280" viewBox="0 0 200 280"><rect fill="%231a1a2e" width="200" height="280"/><text x="50%" y="50%" text-anchor="middle" dy=".3em" fill="%236B6B8A" font-size="14">暂无封面</text></svg>'
    }

    const cardImageUrl = (metadata) => {
      return jacketHdUrl(metadata.jacket_thumb_url) || metadata.jacket_thumb_url || '/placeholder.png'
    }

    const onImgLoad = (e) => {
      const img = e.target
      if (img.naturalWidth > img.naturalHeight) {
        img.classList.add('wide')
      }
    }

    const formatServiceCode = (code) => {
      const map = {
        'mono': 'DVD',
        'digital': '数字',
        'rental': '租赁',
        'download': '下载',
        'streaming': '流媒体',
        'subscription': '订阅'
      }
      return map[code] || code
    }

    return {
      state,
      activeTab,
      tabs,
      filteredItems,
      openVideo,
      isFavorited,
      toggleFavorite,
      handleImgError,
      cardImageUrl,
      onImgLoad,
      formatServiceCode
    }
  }
}
</script>

<style scoped>
.favorites-page {
  padding: 60px 40px;
  max-width: 1600px;
  margin: 0 auto;
  min-height: 100vh;
}

.curate-header {
  text-align: center;
  margin-bottom: 50px;
}

.curate-title {
  font-size: 42px;
  font-weight: 800;
  letter-spacing: -0.03em;
  margin-bottom: 8px;
  color: var(--text-primary);
}

.curate-stats {
  font-size: 14px;
  color: var(--text-muted);
  margin-bottom: 32px;
}

/* Segmented Control - Apple Look */
.segmented-control {
  display: inline-flex;
  background: rgba(255, 255, 255, 0.05);
  padding: 4px;
  border-radius: 14px;
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border: 1px solid var(--border-light);
}

.segment-item {
  border: none;
  background: transparent;
  color: var(--text-secondary);
  padding: 8px 28px;
  font-size: 14px;
  font-weight: 600;
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.3s var(--ease-pro);
}

.segment-item:hover {
  color: var(--text-primary);
}

.segment-item.active {
  background: var(--white-10);
  color: var(--text-primary);
  box-shadow: 0 4px 12px rgba(0,0,0,0.3);
  border: 1px solid var(--border-light);
}

.curate-content {
  margin-top: 40px;
}

.favorites-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 32px;
}

.curate-empty {
  padding: 120px 20px;
  text-align: center;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.empty-icon {
  color: var(--text-muted);
  margin-bottom: 24px;
  opacity: 0.4;
}

.curate-empty h3 {
  font-size: 22px;
  font-weight: 700;
  margin-bottom: 12px;
  color: var(--text-primary);
}

.curate-empty p {
  color: var(--text-muted);
  margin-bottom: 40px;
  font-size: 15px;
}

.btn-explore {
  background: var(--text-primary);
  color: var(--bg-primary);
  border: none;
  padding: 14px 48px;
  border-radius: 24px;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.3s var(--ease-pro);
}

.btn-explore:hover {
  transform: scale(1.05);
  box-shadow: 0 10px 30px rgba(0,0,0,0.4);
}

/* ===== 恢复旧版电影卡片样式 ===== */
.movie-card {
  background: var(--bg-card);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border-radius: var(--radius-md);
  overflow: hidden;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.2, 0, 0, 1);
  border: 1px solid var(--border);
}

.movie-card:hover {
  transform: translateY(-4px);
  box-shadow: var(--shadow-hover);
  border-color: var(--accent);
}

.card-cover {
  position: relative;
  width: 100%;
  aspect-ratio: 3/4;
  overflow: hidden;
  background: var(--bg-secondary);
}

.cover-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  object-position: center;
  transition: transform 0.4s cubic-bezier(0.4, 0, 0.2, 1);
}

.movie-card:hover .cover-img {
  transform: scale(1.05);
}

.cover-img.wide {
  object-fit: none;
  object-position: right center;
  clip-path: inset(0 0 0 50%);
}

.card-preview-badge {
  position: absolute;
  top: 6px;
  right: 6px;
  background: rgba(0,0,0,0.65);
  border-radius: 4px;
  padding: 3px 5px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  pointer-events: none;
}

.card-info {
  padding: 10px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 4px;
}

.card-code-row {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 6px;
  margin-bottom: 4px;
}

.card-code {
  font-weight: bold;
  font-size: 13px;
}

.card-type {
  font-size: 10px;
  padding: 2px 6px;
  border-radius: 4px;
  font-weight: 600;
}

.type-mono { background: rgba(76, 175, 80, 0.2); color: #4CAF50; }
.type-digital { background: rgba(33, 150, 243, 0.2); color: #2196F3; }
.type-rental { background: rgba(255, 152, 0, 0.2); color: #FF9800; }
.type-download { background: rgba(156, 39, 176, 0.2); color: #9C27B0; }
.type-streaming, .type-subscription { background: rgba(244, 67, 54, 0.2); color: #F44336; }

.card-title {
  font-size: 12px;
  color: var(--text-secondary);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  margin-bottom: 4px;
}

.card-meta {
  display: flex;
  gap: 8px;
  font-size: 11px;
  color: var(--text-muted);
}

.favorite-toggle {
  position: absolute;
  top: 12px;
  left: 12px;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: rgba(0, 0, 0, 0.3);
  backdrop-filter: blur(8px);
  border: 1px solid rgba(255, 255, 255, 0.1);
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  cursor: pointer;
  transition: all 0.3s var(--ease-pro);
  opacity: 0;
  transform: scale(0.8);
  z-index: 5;
}

.movie-card:hover .favorite-toggle {
  opacity: 1;
  transform: scale(1);
}

.favorite-toggle:hover {
  background: rgba(0, 0, 0, 0.5);
  transform: scale(1.1);
}

.favorite-toggle.is-active {
  opacity: 1;
  transform: scale(1);
  color: #FFD60A;
  background: rgba(255, 214, 10, 0.15);
  border-color: rgba(255, 214, 10, 0.3);
}

@media (max-width: 768px) {
  .favorites-page { padding: 40px 20px; }
  .curate-title { font-size: 32px; }
  .favorites-grid { grid-template-columns: repeat(auto-fill, minmax(170px, 1fr)); gap: 20px; }
  .segment-item { padding: 8px 16px; font-size: 13px; }
}
</style>
