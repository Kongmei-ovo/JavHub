<template>
  <div class="actor-page page-shell page-shell--workspace">
    <div class="actor-header">
      <button class="back-btn" type="button" @click="$router.back()">← 返回</button>
      <ActressAvatar :name="actor.display_name || actor.actress_name" :avatarUrl="actor.avatar_url" :size="100" />
      <h2>{{ actor.display_name || actor.actress_name }}</h2>
      <div class="stats">
        Emby {{ embyVideos.length }} 部 / 缺失 {{ missingVideos.length }} 部
      </div>
      <div class="mapping-banner" :class="{ unmapped: actor.mapping_status !== 'confirmed' }">
        <span v-if="actor.mapping_status === 'confirmed'">
          已映射到 JavInfo：{{ actor.actor_mapping?.javinfo_actress_name || actor.actor_mapping?.javinfo_actress_id }}
        </span>
        <span v-else>未映射到 JavInfo，库存对比会跳过这个演员</span>
        <button class="mapping-link" type="button" @click="$router.push('/normalize')">处理映射</button>
      </div>
    </div>

    <!-- Tab 切换 -->
    <div class="tab-bar">
      <button
        class="tab-btn"
        type="button"
        :class="{ active: activeTab === 'emby' }"
        @click="activeTab = 'emby'; loadEmbyVideos()"
      >
        Emby 已有 ({{ embyVideos.length }})
      </button>
      <button
        class="tab-btn"
        type="button"
        :class="{ active: activeTab === 'missing' }"
        @click="activeTab = 'missing'"
      >
        缺失影片 ({{ missingVideos.length }})
      </button>
    </div>

    <!-- 加载状态 -->
    <div v-if="loading" class="loading">
      <span v-if="activeTab === 'emby'">从 Emby 加载影片中...</span>
      <span v-else>加载中...</span>
    </div>

    <!-- Emby 已有影片 -->
    <template v-else-if="activeTab === 'emby'">
      <div v-for="(groupVideos, year) in groupedEmbyByYear" :key="year" class="year-section">
        <h3 class="year-title">{{ year }}</h3>
        <div class="videos-grid">
          <div
            v-for="video in groupVideos"
            :key="video.item_id"
            class="video-card"
            role="button"
            tabindex="0"
            @click="openEmbyItem(video)"
            @keydown.enter.prevent="openEmbyItem(video)"
            @keydown.space.prevent="openEmbyItem(video)"
          >
            <div class="video-cover">
              <img
                v-if="video.image_tag"
                :src="embyImageUrl(video.item_id, video.image_tag)"
                :alt="video.title"
                @error="handleVideoCoverError($event, video)"
              />
              <div v-else class="no-cover">无封面</div>
            </div>
            <div class="video-info">
              <div class="video-code" :title="video.title">{{ video.displayCode }}</div>
              <div class="video-title" :title="video.title">{{ video.title }}</div>
            </div>
          </div>
        </div>
      </div>
      <div v-if="!loading && Object.keys(groupedEmbyByYear).length === 0" class="empty">
        Emby 中暂无该演员的影片
      </div>
    </template>

    <!-- 缺失影片 -->
    <template v-else-if="activeTab === 'missing'">
      <div v-for="(groupVideos, year) in groupedMissingByYear" :key="year" class="year-section">
        <h3 class="year-title">{{ year }}</h3>
        <div class="videos-grid">
          <div v-for="video in groupVideos" :key="video.content_id" class="missing-card-wrap">
            <VideoCard
              :contentId="video.content_id"
              :title="video.title"
              :coverUrl="video.jacket_thumb_url || ''"
              :actressNames="actor.display_name || actor.actress_name"
              :releaseDate="video.release_date || ''"
              @click="showDetail(video)"
            />
            <button class="candidate-btn" type="button" @click.stop="createCandidate(video)">
              转为候选
            </button>
          </div>
        </div>
      </div>
      <div v-if="!loading && Object.keys(groupedMissingByYear).length === 0" class="empty">
        暂无缺失影片
      </div>
      <div v-else class="candidate-link">
        <button class="back-btn" type="button" @click="viewInventoryCandidates">查看库存下载候选</button>
      </div>
    </template>
  </div>
</template>

<script>
export default {
  name: 'InventoryActor'
}
</script>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import axios from 'axios'
import { ElMessage } from '../utils/message.js'
import ActressAvatar from '../components/ActressAvatar.vue'
import VideoCard from '../components/VideoCard.vue'
import { openVideoModal } from '../utils/modalState'
import { groupEmbyVideosByYear, groupMissingVideosByYear } from '../utils/inventoryVideoGrouping'
import { applyImageFallback } from '../utils/imageFallback.js'
import api from '../api'

const route = useRoute()
const router = useRouter()
const actorId = parseInt(route.params.id)
const actor = ref({})
const embyVideos = ref([])
const missingVideos = ref([])
const loading = ref(false)
const activeTab = ref('emby')

// Emby 已有影片按年分组（编年正序：最早的在前）
const groupedEmbyByYear = computed(() => groupEmbyVideosByYear(embyVideos.value))

// 缺失影片按年分组（编年正序）
const groupedMissingByYear = computed(() => groupMissingVideosByYear(missingVideos.value))

const fetchActor = async () => {
  loading.value = true
  try {
    const res = await axios.get(`/api/inventory/actors/${actorId}`)
    actor.value = res.data
    missingVideos.value = res.data.missing_videos || []
  } finally {
    loading.value = false
  }
}

const loadEmbyVideos = async () => {
  if (embyVideos.value.length > 0) return // 已有数据不重复加载
  loading.value = true
  try {
    const res = await axios.get(`/api/inventory/actors/${actorId}/emby-videos`)
    embyVideos.value = res.data.data || []
  } catch (e) {
    console.error('Failed to load Emby videos:', e)
    embyVideos.value = []
  } finally {
    loading.value = false
  }
}

const embyImageUrl = (itemId, imageTag) => {
  return `/api/proxy/image?url=${encodeURIComponent(
    `${actor.value._emby_api_url}/Items/${itemId}/Images/Primary?tag=${imageTag}`
  )}`
}

const handleVideoCoverError = (event, video) => {
  applyImageFallback(event, { label: String(video?.displayCode || video?.title || '?').slice(0, 6) })
}

const openEmbyItem = (video) => {
  if (actor.value._emby_web_url && actor.value._emby_server_id) {
    const url = `${actor.value._emby_web_url}/web/index.html#!/item?id=${video.item_id}&serverId=${actor.value._emby_server_id}`
    window.open(url, '_blank')
  } else if (actor.value._emby_web_url) {
    window.open(`${actor.value._emby_web_url}/web/index.html#!/details?id=${video.item_id}`, '_blank')
  }
}

const showDetail = (video) => {
  openVideoModal(video, route.fullPath || route.path)
}

const createCandidate = async (video) => {
  try {
    await api.createDownloadCandidate({
      content_id: video.content_id,
      dvd_id: video.dvd_id || video.content_id,
      title: video.title || video.content_id,
      actress_id: actorId,
      actress_name: actor.value.display_name || actor.value.actress_name || '',
      jacket_thumb_url: video.jacket_thumb_url || '',
      release_date: video.release_date || '',
      source: 'inventory',
      reason: 'inventory_actor_manual_pick'
    })
    ElMessage.success('已加入下载候选')
  } catch (e) {
    ElMessage.error('加入候选失败')
  }
}

const viewInventoryCandidates = () => {
  router.push({ path: '/downloads', query: { tab: 'candidates', source: 'inventory', status: 'candidate' } })
}

onMounted(async () => {
  await fetchActor()
  // 同时加载 Emby 数据以显示统计
  await loadEmbyVideos()
})
</script>

<style scoped>
.actor-page {}
.actor-header {
  display: flex; flex-direction: column; align-items: center;
  gap: 12px; margin-bottom: 24px;
}
.back-btn {
  align-self: flex-start;
  min-height: 44px;
  border: 1px solid var(--glass-control-border);
  border-radius: 999px;
  background: var(--surface-specular-edge), var(--surface-noise), var(--material-glass-control);
  color: var(--text-primary);
  box-shadow: var(--glass-control-shadow);
  backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
  -webkit-backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
  cursor: pointer;
  font-size: 14px;
  padding: 0 14px;
  transition: transform var(--motion-fast), background var(--motion-fast), border-color var(--motion-fast), box-shadow var(--motion-fast), color var(--motion-fast);
}
.back-btn:hover {
  border-color: var(--glass-control-border-hover);
  background: var(--surface-specular-edge-strong), var(--surface-noise), var(--material-glass-control-hover);
  box-shadow: var(--glass-control-shadow-hover);
  transform: translateY(-1px);
}
.back-btn:focus-visible {
  outline: none;
  border-color: var(--glass-control-border-hover);
  background: var(--surface-specular-edge-strong), var(--surface-noise), var(--material-glass-control-hover);
  box-shadow: var(--glass-control-shadow-hover), 0 0 0 3px rgba(var(--accent-rgb), 0.12);
  transform: translateY(-1px);
}
.stats { color: var(--text-secondary); font-size: 14px; }
.mapping-banner {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  max-width: min(680px, 100%);
  padding: 8px 12px;
  border-radius: var(--radius-md);
  border: 1px solid var(--badge-success-border);
  background: var(--surface-specular-edge), var(--surface-noise), var(--badge-success-bg);
  color: var(--badge-success-text);
  font-size: 13px;
  box-shadow: var(--glass-inner-shadow);
}
.mapping-banner.unmapped {
  border-color: var(--badge-warning-border);
  background: var(--surface-specular-edge), var(--surface-noise), var(--badge-warning-bg);
  color: var(--badge-warning-text);
}
.mapping-link {
  border: 1px solid var(--glass-control-border);
  border-radius: 999px;
  background: var(--surface-specular-edge), var(--surface-noise), var(--material-glass-control);
  color: var(--link-text);
  box-shadow: var(--glass-control-shadow);
  backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
  -webkit-backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
  cursor: pointer;
  text-decoration: underline;
  text-decoration-color: var(--link-underline);
  text-underline-offset: 3px;
  min-height: 44px;
  padding: 0 12px;
  transition: background var(--motion-fast), border-color var(--motion-fast), box-shadow var(--motion-fast), color var(--motion-fast);
}
.mapping-link:hover {
  border-color: var(--glass-control-border-hover);
  background: var(--surface-specular-edge-strong), var(--surface-noise), var(--material-glass-control-hover);
  box-shadow: var(--glass-control-shadow-hover);
  text-decoration-color: var(--link-underline-hover);
}
.mapping-link:focus-visible {
  outline: none;
  border-color: var(--glass-control-border-hover);
  background: var(--surface-specular-edge-strong), var(--surface-noise), var(--material-glass-control-hover);
  box-shadow: var(--glass-control-shadow-hover), 0 0 0 3px rgba(var(--accent-rgb), 0.12);
  text-decoration-color: var(--link-underline-hover);
}

/* Tab 样式 */
.tab-bar {
  display: inline-flex;
  gap: 4px;
  padding: 4px;
  border: 1px solid var(--glass-control-border);
  border-radius: var(--radius-md);
  background: var(--surface-specular-edge-strong), var(--surface-noise), var(--material-glass-sheet);
  box-shadow: var(--glass-inner-shadow);
  backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
  -webkit-backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
  margin-bottom: 20px;
}
.tab-btn {
  min-height: 44px;
  padding: 8px 20px;
  border: 1px solid var(--glass-control-border);
  border-radius: 10px;
  background: var(--surface-specular-edge), var(--surface-noise), var(--material-glass-control);
  color: var(--text-secondary);
  box-shadow: var(--glass-control-shadow);
  backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
  -webkit-backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
  cursor: pointer;
  font-size: 14px;
  transition: transform var(--motion-fast), background var(--motion-fast), border-color var(--motion-fast), box-shadow var(--motion-fast), color var(--motion-fast), font-weight var(--motion-fast);
}
.tab-btn:hover {
  color: var(--text-primary);
  border-color: var(--glass-control-border-hover);
  background: var(--surface-specular-edge-strong), var(--surface-noise), var(--material-glass-control-hover);
  box-shadow: var(--glass-control-shadow-hover);
  transform: translateY(-1px);
}
.tab-btn:focus-visible {
  outline: none;
  color: var(--text-primary);
  border-color: var(--glass-control-border-hover);
  background: var(--surface-specular-edge-strong), var(--surface-noise), var(--material-glass-control-hover);
  box-shadow: var(--glass-control-shadow-hover), 0 0 0 3px rgba(var(--accent-rgb), 0.12);
  transform: translateY(-1px);
}
.tab-btn.active {
  color: var(--text-primary);
  border-color: var(--glass-active-border);
  background: var(--surface-specular-edge-strong), var(--surface-noise), var(--glass-active-material);
  box-shadow: var(--glass-active-shadow);
  font-weight: 600;
}

/* 影片卡片 */
.year-section { margin-bottom: 24px; }
.year-title {
  font-size: 18px; font-weight: bold; margin-bottom: 12px;
  padding-bottom: 8px; border-bottom: 1px solid var(--glass-edge);
}
.videos-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: 12px;
}
.video-card {
  border: 1px solid var(--glass-control-border);
  border-radius: var(--radius-md);
  background: var(--surface-specular-edge), var(--surface-noise), var(--material-glass-control);
  box-shadow: var(--glass-control-shadow);
  backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
  -webkit-backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
  overflow: hidden;
  cursor: pointer;
  transition: transform var(--motion-fast), background var(--motion-fast), border-color var(--motion-fast), box-shadow var(--motion-fast);
}
.video-card:hover {
  transform: translateY(-2px);
  border-color: var(--glass-control-border-hover);
  background: var(--surface-specular-edge-strong), var(--surface-noise), var(--material-glass-control-hover);
  box-shadow: var(--glass-control-shadow-hover);
}
.video-card:focus-visible {
  outline: none;
  transform: translateY(-2px);
  border-color: var(--glass-control-border-hover);
  background: var(--surface-specular-edge-strong), var(--surface-noise), var(--material-glass-control-hover);
  box-shadow: var(--glass-control-shadow-hover), 0 0 0 3px rgba(var(--accent-rgb), 0.12);
}
.video-cover {
  aspect-ratio: 3/4;
  background: var(--surface-specular-edge), var(--surface-noise), var(--material-glass-subtle);
  box-shadow: var(--glass-inner-shadow);
  overflow: hidden;
}
.video-cover img { width: 100%; height: 100%; object-fit: cover; }
.no-cover {
  width: 100%; height: 100%; display: flex; align-items: center;
  justify-content: center; color: var(--text-muted); font-size: 12px;
}
.video-info { padding: 8px; }
.video-code {
  font-size: 12px; font-weight: bold; color: var(--text-primary);
  margin-bottom: 4px;
}
.video-title {
  font-size: 11px; color: var(--text-secondary); overflow: hidden;
  text-overflow: ellipsis; white-space: nowrap;
}
.video-meta { font-size: 11px; color: var(--text-muted); }
.missing-card-wrap { position: relative; }
.candidate-btn {
  width: 100%;
  margin-top: 6px;
  border: 1px solid var(--glass-control-border);
  border-radius: 10px;
  background: var(--surface-specular-edge), var(--surface-noise), var(--material-glass-control);
  color: var(--text-primary);
  box-shadow: var(--glass-control-shadow);
  backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
  -webkit-backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
  padding: 7px 10px;
  min-height: 44px;
  cursor: pointer;
  font-size: 12px;
  transition: transform var(--motion-fast), background var(--motion-fast), border-color var(--motion-fast), box-shadow var(--motion-fast);
}
.candidate-btn:hover {
  transform: translateY(-1px);
  border-color: var(--glass-control-border-hover);
  background: var(--surface-specular-edge-strong), var(--surface-noise), var(--material-glass-control-hover);
  box-shadow: var(--glass-control-shadow-hover);
}
.candidate-btn:focus-visible {
  outline: none;
  transform: translateY(-1px);
  border-color: var(--glass-control-border-hover);
  background: var(--surface-specular-edge-strong), var(--surface-noise), var(--material-glass-control-hover);
  box-shadow: var(--glass-control-shadow-hover), 0 0 0 3px rgba(var(--accent-rgb), 0.12);
}
.candidate-link { text-align: center; margin: 20px 0; }

.loading, .empty {
  text-align: center;
  padding: 40px;
  border: 1px solid var(--glass-control-border);
  border-radius: var(--radius-lg);
  background: var(--surface-specular-edge), var(--surface-noise), var(--material-glass-subtle);
  color: var(--text-secondary);
}

@media (max-width: 768px) {
  .videos-grid {
    grid-template-columns: repeat(auto-fit, minmax(var(--video-grid-min-mobile), 1fr));
    gap: var(--video-grid-gap-mobile);
  }
}
</style>
