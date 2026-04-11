<template>
  <div class="missing-detail-page">
    <div class="page-header">
      <button @click="$router.back()" class="back-btn">← 返回</button>
      <h1>{{ actressName }} ({{ missingCount }} 部缺失)</h1>
      <button @click="downloadAll" class="download-all-btn">一键下载</button>
    </div>

    <div v-for="(videos, year) in videosByYear" :key="year" class="year-section">
      <h2 class="year-title">{{ year }} 年</h2>
      <div class="video-grid">
        <div v-for="video in videos" :key="video.content_id" class="video-card-wrapper">
          <VideoCard
            :contentId="video.content_id"
            :title="video.title"
            :coverUrl="video.jacket_thumb_url"
            :releaseDate="video.release_date"
          />
          <div class="card-actions">
            <button @click="downloadVideo(video)" class="action-btn download">下载</button>
            <button @click="ignoreVideo(video)" class="action-btn ignore">忽略</button>
          </div>
        </div>
      </div>
    </div>

    <div v-if="loading" class="loading">加载中...</div>
    <div v-if="error" class="error">{{ error }}</div>

    <div class="bottom-actions">
      <button @click="downloadAll" class="download-all-btn">一键下载全部</button>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRoute } from 'vue-router'
import axios from 'axios'
import VideoCard from '../components/VideoCard.vue'

const route = useRoute()
const actressId = computed(() => route.params.id)
const actressName = ref('')
const missingCount = ref(0)
const allVideos = ref([])
const loading = ref(false)
const error = ref('')

const videosByYear = computed(() => {
  const grouped = {}
  for (const video of allVideos.value) {
    const year = video.release_date?.slice(0, 4) || '未知'
    if (!grouped[year]) grouped[year] = []
    grouped[year].push(video)
  }
  return grouped
})

const fetchDetail = async () => {
  loading.value = true
  error.value = ''
  try {
    const res = await axios.get(`/api/missing/actresses/${actressId.value}`)
    actressName.value = res.data.actress_name
    missingCount.value = res.data.missing_count
    // flatten videos_by_year back to array
    allVideos.value = Object.values(res.data.videos_by_year).flat()
  } catch (e) {
    error.value = '加载失败: ' + e.message
  } finally {
    loading.value = false
  }
}

const downloadVideo = async (video) => {
  // TODO: 调用下载 API
  console.log('download', video)
}

const ignoreVideo = async (video) => {
  // TODO: 调用忽略 API
  console.log('ignore', video)
}

const downloadAll = async () => {
  // TODO: 批量下载
  console.log('download all')
}

onMounted(fetchDetail)
</script>

<style scoped>
.missing-detail-page {
  padding: 16px;
}
.page-header {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 16px;
}
.back-btn {
  background: none;
  border: none;
  color: #1890ff;
  cursor: pointer;
}
.download-all-btn {
  background: #52c41a;
  color: #fff;
  border: none;
  padding: 8px 16px;
  border-radius: 4px;
  cursor: pointer;
}
.year-section {
  margin-bottom: 24px;
}
.year-title {
  margin-bottom: 12px;
  color: #333;
}
.video-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  gap: 16px;
}
.video-card-wrapper {
  position: relative;
}
.card-actions {
  display: flex;
  gap: 4px;
  margin-top: 4px;
}
.action-btn {
  flex: 1;
  padding: 4px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
}
.action-btn.download {
  background: #1890ff;
  color: #fff;
}
.action-btn.ignore {
  background: #f5f5f5;
  color: #666;
}
.bottom-actions {
  position: fixed;
  bottom: 20px;
  right: 20px;
}
.loading, .error {
  text-align: center;
  padding: 20px;
}
</style>
