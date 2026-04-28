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
        <VideoCard 
          v-for="item in filteredItems" 
          :key="item.entity_id"
          :content-id="item.entity_id"
          :cover-url="item.metadata?.jacket_thumb_url"
          :actress="item.metadata?.actress_name"
          @click="openVideo(item)"
        />
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
import { state } from '../utils/favoriteState'
import { openVideoModal } from '../utils/modalState'
import VideoCard from '../components/VideoCard.vue'

export default {
  name: 'Favorites',
  components: { VideoCard },
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

    return {
      state,
      activeTab,
      tabs,
      filteredItems,
      openVideo
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

@media (max-width: 768px) {
  .favorites-page { padding: 40px 20px; }
  .curate-title { font-size: 32px; }
  .favorites-grid { grid-template-columns: repeat(auto-fill, minmax(170px, 1fr)); gap: 20px; }
  .segment-item { padding: 8px 16px; font-size: 13px; }
}
</style>
