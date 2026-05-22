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
            @click="openEmbyItem(video)"
          >
            <div class="video-cover">
              <img
                v-if="video.image_tag"
                :src="embyImageUrl(video.item_id, video.image_tag)"
                :alt="video.title"
                @error="$event.target.style.display='none'"
              />
              <div v-else class="no-cover">无封面</div>
            </div>
            <div class="video-info">
              <div class="video-code" :title="video.title">{{ video._code || extractCode(video.title) }}</div>
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
import api from '../api'

const route = useRoute()
const router = useRouter()
const actorId = parseInt(route.params.id)
const actor = ref({})
const embyVideos = ref([])
const missingVideos = ref([])
const loading = ref(false)
const activeTab = ref('emby')

// 从 title 提取番号（去除时间戳等后缀）
function extractCode(title) {
  if (!title) return ''
  // 匹配常见番号格式：ABC-123, ABC-123-hack, ABC123 等
  const match = title.match(/([A-Z]+-\d+)/i)
  return match ? match[1].toUpperCase() : ''
}

// 从 title 提取年份（用于年份为空的情况）
function extractYearFromTitle(title) {
  if (!title) return null
  // 匹配 4 位年份数字
  const match = title.match(/\b(19\d{2}|20\d{2})\b/)
  return match ? parseInt(match[1]) : null
}

// 获取影片年份（优先字段值，其次从 title 提取）
function getVideoYear(video, yearField, dateField) {
  let year
  if (yearField === 'release_date') {
    // 缺失影片用 release_date 字段
    year = video[yearField] ? parseInt(video[yearField].slice(0, 4)) : null
    if (!year) year = extractYearFromTitle(video.title)
  } else {
    // Emby 影片优先用 production_year，否则用 premiere_date
    year = video[yearField] || (video[dateField] ? new Date(video[dateField]).getFullYear() : null)
    if (!year || isNaN(year)) year = extractYearFromTitle(video.title)
  }
  return year || null
}

// Emby 已有影片按年分组（编年正序：最早的在前）
const groupedEmbyByYear = computed(() => {
  const groups = {}
  for (const v of embyVideos.value) {
    const year = getVideoYear(v, 'production_year', 'premiere_date')
    const yearKey = year ? String(year) : '未知'
    if (!groups[yearKey]) groups[yearKey] = []
    // 附加提取的番号
    v._code = v._code || extractCode(v.title)
    groups[yearKey].push(v)
  }
  // 编年正序：最早的年份在前
  return Object.keys(groups)
    .sort((a, b) => {
      if (a === '未知') return 1
      if (b === '未知') return -1
      return a.localeCompare(b)
    })
    .reduce((acc, key) => {
      acc[key] = groups[key]
      return acc
    }, {})
})

// 缺失影片按年分组（编年正序）
const groupedMissingByYear = computed(() => {
  const groups = {}
  for (const v of missingVideos.value) {
    const year = getVideoYear(v, 'release_date', null)
    const yearKey = year ? String(year) : '未知'
    if (!groups[yearKey]) groups[yearKey] = []
    groups[yearKey].push(v)
  }
  // 编年正序：最早的年份在前
  return Object.keys(groups)
    .sort((a, b) => {
      if (a === '未知') return 1
      if (b === '未知') return -1
      return a.localeCompare(b)
    })
    .reduce((acc, key) => {
      acc[key] = groups[key]
      return acc
    }, {})
})

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
  align-self: flex-start; min-height: 44px; background: none; border: none;
  color: var(--text-primary); cursor: pointer; font-size: 14px;
  padding: 0 8px;
}
.stats { color: #666; font-size: 14px; }
.mapping-banner {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  max-width: min(680px, 100%);
  padding: 8px 12px;
  border-radius: 8px;
  border: 1px solid rgba(82, 196, 26, 0.28);
  background: rgba(82, 196, 26, 0.08);
  color: #52c41a;
  font-size: 13px;
}
.mapping-banner.unmapped {
  border-color: rgba(250, 140, 22, 0.28);
  background: rgba(250, 140, 22, 0.08);
  color: #fa8c16;
}
.mapping-link {
  border: 0;
  background: transparent;
  color: var(--link-text);
  cursor: pointer;
  text-decoration: underline;
  text-decoration-color: var(--link-underline);
  text-underline-offset: 3px;
  min-height: 44px;
  padding: 0 6px;
}

/* Tab 样式 */
.tab-bar {
  display: flex; gap: 4px; border-bottom: 2px solid var(--border);
  margin-bottom: 20px;
}
.tab-btn {
  min-height: 44px; padding: 8px 20px; background: none; border: none;
  border-bottom: 2px solid transparent; margin-bottom: -2px;
  cursor: pointer; font-size: 14px; color: var(--text-secondary);
  transition: all 0.2s;
}
.tab-btn:hover { color: var(--text-primary); }
.tab-btn.active {
  color: var(--text-primary); border-bottom-color: var(--active-indicator); font-weight: 600;
}

/* 影片卡片 */
.year-section { margin-bottom: 24px; }
.year-title {
  font-size: 18px; font-weight: bold; margin-bottom: 12px;
  padding-bottom: 8px; border-bottom: 1px solid var(--border);
}
.videos-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: 12px;
}
.video-card {
  background: var(--bg-card); border-radius: 8px; overflow: hidden;
  cursor: pointer; transition: transform 0.2s;
}
.video-card:hover { transform: translateY(-2px); }
.video-cover {
  aspect-ratio: 3/4; background: var(--bg-secondary); overflow: hidden;
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
  border: 1px solid var(--border);
  border-radius: 6px;
  background: var(--bg-card);
  color: var(--text-primary);
  padding: 7px 10px;
  min-height: 44px;
  cursor: pointer;
  font-size: 12px;
}
.candidate-link { text-align: center; margin: 20px 0; }

.loading, .empty { text-align: center; padding: 40px; color: var(--text-secondary); }

@media (max-width: 768px) {
  .videos-grid {
    grid-template-columns: repeat(auto-fit, minmax(var(--video-grid-min-mobile), 1fr));
    gap: var(--video-grid-gap-mobile);
  }
}
</style>
