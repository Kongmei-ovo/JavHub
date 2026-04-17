<template>
  <div class="inventory-page">
    <div class="page-header">
      <h1>库存对比</h1>
      <div class="header-actions">
        <button @click="triggerFullJob" class="btn-primary" :disabled="running">
          {{ running ? '对比中...' : '全量对比' }}
        </button>
      </div>
    </div>

    <!-- Tabs -->
    <div class="tabs">
      <button
        :class="{ active: activeTab === 'actors' }"
        @click="activeTab = 'actors'"
      >对比概览</button>
      <button
        :class="{ active: activeTab === 'jobs' }"
        @click="activeTab = 'jobs'"
      >作业历史</button>
    </div>

    <!-- 对比概览 Tab -->
    <div v-if="activeTab === 'actors'" class="tab-content">
      <div v-if="loadingActors" class="loading">加载中...</div>
      <div v-if="errorActors" class="error">{{ errorActors }}</div>

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

      <div v-if="!loadingActors && actors.length === 0" class="empty">
        暂无演员数据，请先执行全量对比
      </div>
    </div>

    <!-- 作业历史 Tab -->
    <div v-if="activeTab === 'jobs'" class="tab-content">
      <div v-if="loadingJobs" class="loading">加载中...</div>
      <div v-if="errorJobs" class="error">{{ errorJobs }}</div>

      <div class="jobs-list">
        <div
          v-for="job in jobs"
          :key="job.id"
          class="job-item"
        >
          <div class="job-info">
            <div class="job-type">{{ job.job_type }}</div>
            <div class="job-meta">
              <span v-if="job.actor_id">演员ID: {{ job.actor_id }}</span>
              <span>状态: {{ job.status }}</span>
              <span>{{ job.created_at }}</span>
            </div>
          </div>
          <div class="job-stats" v-if="job.result">
            <span v-if="job.result.scanned">已扫描 {{ job.result.scanned }}</span>
            <span v-if="job.result.missing" class="missing-tag">缺失 {{ job.result.missing }}</span>
          </div>
        </div>
      </div>

      <div v-if="!loadingJobs && jobs.length === 0" class="empty">
        暂无作业记录
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import axios from 'axios'
import ActressAvatar from '../components/ActressAvatar.vue'

const activeTab = ref('actors')

// 对比概览
const actors = ref([])
const loadingActors = ref(false)
const errorActors = ref('')
const running = ref(false)

const fetchActors = async () => {
  loadingActors.value = true
  errorActors.value = ''
  try {
    const res = await axios.get('/api/inventory/actors')
    actors.value = res.data.data || []
  } catch (e) {
    errorActors.value = '加载失败: ' + e.message
  } finally {
    loadingActors.value = false
  }
}

const triggerFullJob = async () => {
  running.value = true
  try {
    await axios.post('/api/inventory/jobs/trigger', { job_type: 'full' })
    pollJobStatus()
  } catch (e) {
    errorActors.value = '触发失败: ' + e.message
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

// 作业历史
const jobs = ref([])
const loadingJobs = ref(false)
const errorJobs = ref('')

const fetchJobs = async () => {
  loadingJobs.value = true
  errorJobs.value = ''
  try {
    const res = await axios.get('/api/inventory/jobs')
    jobs.value = res.data.data || []
  } catch (e) {
    errorJobs.value = '加载失败: ' + e.message
  } finally {
    loadingJobs.value = false
  }
}

// Watch tab changes to load data
watch(activeTab, (tab) => {
  if (tab === 'jobs' && jobs.value.length === 0) fetchJobs()
})
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
.tabs {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
  border-bottom: 1px solid #eee;
  padding-bottom: 8px;
}
.tabs button {
  background: none;
  border: none;
  padding: 8px 16px;
  cursor: pointer;
  font-size: 14px;
  color: #666;
  border-radius: 4px;
}
.tabs button.active {
  background: #1890ff;
  color: #fff;
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

/* 作业历史 */
.jobs-list { display: flex; flex-direction: column; gap: 8px; }
.job-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: #fff;
  border-radius: 8px;
}
.job-type { font-weight: bold; }
.job-meta { font-size: 12px; color: #999; margin-top: 4px; display: flex; gap: 12px; }
.job-stats { display: flex; gap: 12px; font-size: 13px; }
</style>
