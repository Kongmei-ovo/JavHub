<template>
  <div class="inventory-page">
    <div class="page-header">
      <h1>库存对比</h1>
      <div class="header-actions">
        <button @click="triggerFullJob" class="btn-primary" :disabled="running">
          {{ running ? '对比中...' : '全量对比' }}
        </button>
        <button @click="$router.push('/inventory/jobs')" class="btn-secondary">作业历史</button>
      </div>
    </div>

    <div v-if="loading" class="loading">加载中...</div>
    <div v-if="error" class="error">{{ error }}</div>

    <div class="actors-grid">
      <div
        v-for="actor in actors"
        :key="actor.actress_id"
        class="actor-card"
        @click="$router.push(`/inventory/actors/${actor.actress_id}`)"
      >
        <ActressAvatar :name="actor.display_name" :size="80" :badge="actor.missing_count" />
        <div class="actor-name">{{ actor.display_name }}</div>
        <div class="actor-stats">
          <span>共 {{ actor.total_videos }} 部</span>
          <span v-if="actor.missing_count > 0" class="missing-tag">缺 {{ actor.missing_count }}</span>
        </div>
      </div>
    </div>

    <div v-if="!loading && actors.length === 0" class="empty">
      暂无演员数据，请先执行全量对比
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import axios from 'axios'
import ActressAvatar from '../components/ActressAvatar.vue'

const actors = ref([])
const loading = ref(false)
const error = ref('')
const running = ref(false)

const fetchActors = async () => {
  loading.value = true
  error.value = ''
  try {
    const res = await axios.get('/api/inventory/actors')
    actors.value = res.data.data || []
  } catch (e) {
    error.value = '加载失败: ' + e.message
  } finally {
    loading.value = false
  }
}

const triggerFullJob = async () => {
  running.value = true
  try {
    await axios.post('/api/inventory/jobs/trigger', { job_type: 'full' })
    pollJobStatus()
  } catch (e) {
    error.value = '触发失败: ' + e.message
    running.value = false
  }
}

const pollJobStatus = async () => {
  setTimeout(async () => {
    try {
      const res = await axios.get('/api/inventory/jobs')
      const jobs = res.data.data || []
      const latest = jobs[0]
      if (latest && latest.status === 'running') {
        await pollJobStatus()
      } else {
        running.value = false
        await fetchActors()
      }
    } catch {
      running.value = false
    }
  }, 3000)
}

onMounted(fetchActors)
</script>

<style scoped>
.inventory-page { padding: 16px; }
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}
.header-actions { display: flex; gap: 8px; }
.btn-primary {
  background: #1890ff; color: #fff; border: none;
  padding: 8px 16px; border-radius: 4px; cursor: pointer;
}
.btn-primary:disabled { background: #ccc; cursor: not-allowed; }
.btn-secondary {
  background: #fff; color: #1890ff; border: 1px solid #1890ff;
  padding: 8px 16px; border-radius: 4px; cursor: pointer;
}
.actors-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
  gap: 16px;
}
.actor-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 16px;
  background: #fff;
  border-radius: 8px;
  cursor: pointer;
}
.actor-card:hover { background: #f5f5f5; }
.actor-name { font-weight: bold; text-align: center; }
.actor-stats { font-size: 12px; color: #666; text-align: center; }
.missing-tag { color: #ff4d4f; }
.loading, .error, .empty { text-align: center; padding: 40px; }
.error { color: #ff4d4f; }
</style>
