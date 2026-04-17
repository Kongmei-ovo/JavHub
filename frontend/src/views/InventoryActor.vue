<template>
  <div class="actor-page">
    <div class="actor-header">
      <button class="back-btn" @click="$router.back()">← 返回</button>
      <ActressAvatar :name="actor.display_name || actor.actress_name" :size="100" />
      <h2>{{ actor.display_name || actor.actress_name }}</h2>
      <div class="stats">
        共 {{ actor.total_videos }} 部 / 缺失 {{ missingVideos.length }} 部
      </div>
      <div class="actions">
        <button @click="triggerActorJob" class="btn-primary" :disabled="running">
          {{ running ? '对比中...' : '增量对比' }}
        </button>
        <button @click="fillAll" class="btn-secondary">一键补全</button>
      </div>
    </div>

    <div v-if="loading" class="loading">加载中...</div>

    <div v-for="(videos, year) in groupedByYear" :key="year" class="year-section">
      <h3 class="year-title">{{ year }}</h3>
      <div class="videos-grid">
        <VideoCard
          v-for="video in videos"
          :key="video.content_id"
          :video="video"
          @click="showDetail(video)"
        />
      </div>
    </div>

    <div v-if="!loading && Object.keys(groupedByYear).length === 0" class="empty">
      暂无影片数据
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import axios from 'axios'
import ActressAvatar from '../components/ActressAvatar.vue'
import VideoCard from '../components/VideoCard.vue'

const route = useRoute()
const actorId = parseInt(route.params.id)
const actor = ref({})
const videos = ref([])
const missingVideos = ref([])
const loading = ref(false)
const running = ref(false)

const groupedByYear = computed(() => {
  const groups = {}
  for (const v of videos.value) {
    const year = v.release_date ? v.release_date.slice(0, 4) : '未知'
    if (!groups[year]) groups[year] = []
    groups[year].push(v)
  }
  return Object.keys(groups)
    .sort((a, b) => b.localeCompare(a))
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
    videos.value = res.data.videos || []
    missingVideos.value = res.data.missing_videos || []
  } finally {
    loading.value = false
  }
}

const triggerActorJob = async () => {
  running.value = true
  try {
    await axios.post('/api/inventory/jobs/trigger', { job_type: 'actor', actor_id: actorId })
    setTimeout(() => { running.value = false; fetchActor() }, 5000)
  } catch {
    running.value = false
  }
}

const fillAll = async () => {
  for (const v of missingVideos.value) {
    try {
      await axios.post(`/api/inventory/fill/${v.content_id}`)
    } catch {}
  }
  await fetchActor()
}

const showDetail = (video) => {
  // 详情卡片复用逻辑暂省略
}

onMounted(fetchActor)
</script>

<style scoped>
.actor-page { padding: 16px; }
.actor-header {
  display: flex; flex-direction: column; align-items: center;
  gap: 12px; margin-bottom: 24px;
}
.back-btn {
  align-self: flex-start; background: none; border: none;
  color: #1890ff; cursor: pointer; font-size: 14px;
}
.stats { color: #666; }
.actions { display: flex; gap: 8px; }
.btn-primary {
  background: #1890ff; color: #fff; border: none;
  padding: 8px 16px; border-radius: 4px; cursor: pointer;
}
.btn-secondary {
  background: #fff; color: #1890ff; border: 1px solid #1890ff;
  padding: 8px 16px; border-radius: 4px; cursor: pointer;
}
.year-section { margin-bottom: 24px; }
.year-title {
  font-size: 18px; font-weight: bold; margin-bottom: 12px;
  padding-bottom: 8px; border-bottom: 1px solid #eee;
}
.videos-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 12px;
}
.loading, .empty { text-align: center; padding: 40px; }
</style>
