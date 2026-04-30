<template>
  <div class="favorites-page">
    <div class="curate-header">
      <h1 class="curate-title">私人策展</h1>
      <div class="curate-stats">
        共 {{ count }} 个收藏项
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
          <span v-if="tab.count > 0" class="tab-badge">{{ tab.count }}</span>
        </button>
      </div>
    </div>

    <!-- 加载状态 -->
    <div v-if="videoLoading" class="favorites-grid" style="opacity: 0.5;">
      <div v-for="n in 8" :key="n" class="skeleton-card">
        <div class="skeleton-cover"></div>
        <div class="skeleton-info">
          <div class="skeleton-line w-60"></div>
          <div class="skeleton-line w-80"></div>
        </div>
      </div>
    </div>

    <!-- 收藏内容 -->
    <div v-else class="curate-content">
      <!-- 影片网格 -->
      <div v-if="activeTab === 'video' || activeTab === 'all'" v-show="videoItems.length > 0" class="favorites-grid">
        <MovieCard
          v-for="item in displayVideoItems"
          :key="'v-' + item.entity_id"
          :contentId="item.entity_id"
          :coverUrl="cardImageUrl(item.metadata || {})"
          :title="item.metadata?.title_en_translated || item.metadata?.title_ja_translated || item.metadata?.title_en || item.metadata?.title_ja || item.metadata?.title || ''"
          :serviceCode="item.metadata?.service_code || ''"
          :releaseDate="item.metadata?.release_date || ''"
          :runtimeMins="item.metadata?.runtime_mins || item.metadata?.runtime || ''"
          :sampleUrl="item.metadata?.sample_url || ''"
          :isFavorited="isFavorited('video', item.entity_id)"
          @click="openVideo(item)"
          @toggle-favorite="toggleFavorite('video', item.entity_id)"
        />
      </div>

      <!-- 非影片收藏：标签云 -->
      <div v-if="nonVideoItems.length > 0" class="entity-section">
        <div v-if="activeTab === 'all'" class="section-label">{{ sectionLabel }}</div>
        <div class="entity-cloud">
          <div
            v-for="item in nonVideoItems"
            :key="item.entity_type + '-' + item.entity_id"
            class="entity-bubble"
            @click="navigateToEntity(item)"
          >
            <span class="entity-name">{{ entityDisplayName(item) }}</span>
            <span class="entity-type-tag">{{ typeLabel(item.entity_type) }}</span>
            <button class="entity-fav-btn" @click.stop="toggleFavorite(item.entity_type, item.entity_id)">
              <svg viewBox="0 0 24 24" width="12" height="12">
                <path d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z" fill="currentColor"/>
              </svg>
            </button>
          </div>
        </div>
      </div>

      <!-- 空状态 -->
      <div v-if="displayVideoItems.length === 0 && nonVideoItems.length === 0" class="curate-empty">
        <div class="empty-icon">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="48" height="48">
            <path d="M20.84 4.61a5.5 5.5 0 00-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 00-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 000-7.78z"/>
          </svg>
        </div>
        <h3>开始你的策展</h3>
        <p>在探索过程中点击心形图标，将喜欢的项目收入此处。</p>
        <button class="btn-explore" @click="$router.push('/genres')">去探索</button>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { state, favoriteState } from '../utils/favoriteState'
import { openVideoModal } from '../utils/modalState'
import { jacketHdUrl } from '../utils/imageUrl.js'
import { displayName } from '../utils/displayLang.js'
import api from '../api'
import MovieCard from '../components/MovieCard.vue'

const TYPE_LABELS = {
  video: '影片',
  actress: '演员',
  category: '题材',
  series: '系列',
  maker: '工作室',
}

export default {
  name: 'Favorites',
  components: { MovieCard },
  setup() {
    const router = useRouter()
    const activeTab = ref('all')
    const videoLoading = ref(false)
    const videoItems = ref([])

    // 动态计算各类型数量
    const typeCounts = computed(() => {
      const counts = {}
      state.items.forEach(item => {
        counts[item.entity_type] = (counts[item.entity_type] || 0) + 1
      })
      counts.video = videoItems.value.length || counts.video || 0
      return counts
    })

    const tabs = computed(() => [
      { id: 'all', label: '全部', count: state.count },
      { id: 'video', label: '影片', count: typeCounts.value.video || 0 },
      { id: 'actress', label: '演员', count: typeCounts.value.actress || 0 },
      { id: 'category', label: '题材', count: typeCounts.value.category || 0 },
      { id: 'series', label: '系列', count: typeCounts.value.series || 0 },
      { id: 'maker', label: '工作室', count: typeCounts.value.maker || 0 },
    ])

    // 从新接口加载完整影片数据
    const loadVideos = async () => {
      videoLoading.value = true
      try {
        const resp = await api.getFavoriteVideos()
        videoItems.value = (resp.data || []).map(v => ({
          entity_type: 'video',
          entity_id: v.content_id || v.dvd_id,
          metadata: v,
          created_at: v._created_at
        }))
      } catch (e) {
        console.error('Failed to load favorite videos:', e)
      } finally {
        videoLoading.value = false
      }
    }

    onMounted(loadVideos)

    // 影片展示列表
    const displayVideoItems = computed(() => {
      if (activeTab.value === 'video') return videoItems.value
      if (activeTab.value === 'all') return videoItems.value
      return []
    })

    // 非影片收藏
    const nonVideoItems = computed(() => {
      const items = state.items.filter(i => i.entity_type !== 'video')
      if (activeTab.value === 'all') return items
      return items.filter(i => i.entity_type === activeTab.value)
    })

    const sectionLabel = computed(() => {
      const types = [...new Set(nonVideoItems.value.map(i => i.entity_type))]
      return types.map(t => TYPE_LABELS[t] || t).join('、')
    })

    const typeLabel = (type) => TYPE_LABELS[type] || type

    const entityDisplayName = (item) => {
      const m = item.metadata || {}
      return m.name_translated || m.name_ja_translated || m.name_en_translated
        || m.name_kanji_translated || m.name_romaji_translated
        || m.name_ja || m.name_en || m.name_kanji || m.name_romaji || m.name
        || m.title || item.entity_id
    }

    const navigateToEntity = (item) => {
      const type = item.entity_type
      const id = item.entity_id
      const name = entityDisplayName(item)
      if (type === 'video') {
        openVideo(item)
      } else {
        router.push({ name: 'DiscoveryDetail', params: { type, value: id }, query: { name } })
      }
    }

    const openVideo = (item) => {
      if (item.entity_type === 'video') {
        openVideoModal(item.metadata || { content_id: item.entity_id })
      }
    }

    const isFavorited = (type, id) => {
      return favoriteState.isFavorited(type, id)
    }

    const toggleFavorite = async (type, id) => {
      try {
        await favoriteState.toggle(type, id)
        if (type === 'video') await loadVideos()
      } catch (err) {
        console.error('Failed to toggle favorite:', err)
      }
    }

    const cardImageUrl = (metadata) => {
      return jacketHdUrl(metadata.jacket_thumb_url) || metadata.jacket_thumb_url || '/placeholder.png'
    }

    return {
      state,
      count: favoriteState.count,
      activeTab,
      tabs,
      videoLoading,
      videoItems,
      displayVideoItems,
      nonVideoItems,
      sectionLabel,
      typeLabel,
      entityDisplayName,
      navigateToEntity,
      openVideo,
      isFavorited,
      toggleFavorite,
      cardImageUrl
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
  flex-wrap: wrap;
  justify-content: center;
}

.segment-item {
  border: none;
  background: transparent;
  color: var(--text-secondary);
  padding: 8px 20px;
  font-size: 13px;
  font-weight: 600;
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.3s var(--ease-pro);
  display: inline-flex;
  align-items: center;
  gap: 6px;
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

.tab-badge {
  font-size: 10px;
  background: rgba(255, 255, 255, 0.08);
  padding: 1px 6px;
  border-radius: 8px;
  font-weight: 500;
}

.segment-item.active .tab-badge {
  background: rgba(255, 255, 255, 0.15);
}

.curate-content {
  margin-top: 40px;
}

.favorites-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 30px;
  margin-bottom: 40px;
}

/* ===== 非影片收藏区 ===== */
.entity-section {
  margin-top: 20px;
}

.section-label {
  font-size: 13px;
  color: var(--text-muted);
  margin-bottom: 16px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.entity-cloud {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

.entity-bubble {
  position: relative;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 10px 18px;
  background: var(--bg-card);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  border: 1px solid var(--border);
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.25s cubic-bezier(0.23, 1, 0.32, 1);
}

.entity-bubble:hover {
  background: var(--bg-card-hover);
  border-color: var(--border-light);
  transform: translateY(-2px);
}

.entity-name {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
}

.entity-type-tag {
  font-size: 10px;
  color: var(--text-muted);
  background: rgba(255, 255, 255, 0.05);
  padding: 2px 6px;
  border-radius: 4px;
}

.entity-fav-btn {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: none;
  border: none;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #FF375F;
  cursor: pointer;
  opacity: 0.6;
  transition: all 0.2s;
  padding: 0;
}

.entity-fav-btn:hover {
  opacity: 1;
  transform: scale(1.15);
}

/* ===== 空状态 ===== */
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

/* Skeleton loading */
.skeleton-card {
  background: var(--bg-card);
  border-radius: var(--radius-md);
  overflow: hidden;
  border: 1px solid var(--border);
}

.skeleton-cover {
  width: 100%;
  aspect-ratio: 3/4;
  background: var(--bg-secondary);
  animation: pulse 1.5s ease-in-out infinite;
}

.skeleton-info {
  padding: 10px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.skeleton-line {
  height: 12px;
  border-radius: 4px;
  background: var(--bg-secondary);
  animation: pulse 1.5s ease-in-out infinite;
}

.skeleton-line.w-60 { width: 60%; margin: 0 auto; }
.skeleton-line.w-80 { width: 80%; margin: 0 auto; }

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}

@media (max-width: 768px) {
  .favorites-page { padding: 40px 20px; }
  .curate-title { font-size: 32px; }
  .favorites-grid { grid-template-columns: repeat(auto-fill, minmax(170px, 1fr)); gap: 20px; }
  .segment-item { padding: 6px 14px; font-size: 12px; }
}
</style>
