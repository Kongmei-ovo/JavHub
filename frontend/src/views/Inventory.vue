<template>
  <div class="inventory-page">
    <div class="page-header">
      <h1>库存对比</h1>
      <div class="header-actions">
        <!-- 圆形进度指示器 -->
        <div v-if="running || collecting" class="progress-ring-container">
          <svg class="progress-ring" width="40" height="40">
            <circle
              class="progress-ring-bg"
              cx="20" cy="20" r="16"
              fill="none"
              stroke="#eee"
              stroke-width="3"
            />
            <circle
              class="progress-ring-fill"
              cx="20" cy="20" r="16"
              fill="none"
              stroke="#1890ff"
              stroke-width="3"
              :stroke-dasharray="100"
              :stroke-dashoffset="100 - currentProgress"
              transform="rotate(-90 20 20)"
            />
          </svg>
          <span class="progress-text">{{ currentProgress }}%</span>
        </div>
        <button @click="triggerCollect" class="btn-primary" :disabled="collecting || running">
          {{ collecting ? '采集中...' : '采集Emby数据' }}
        </button>
        <button @click="triggerFullJob" class="btn-secondary" :disabled="running || collecting" :class="{ 'btn-disabled': !snapshotKey }">
          {{ running ? '对比中...' : '全量对比' }}
        </button>
        <button @click="showJobs = true; fetchJobs()" class="btn-ghost">作业历史</button>
      </div>
    </div>

    <!-- 快照信息 -->
    <div v-if="snapshotKey" class="snapshot-info">
      当前快照：{{ snapshotKey }} · {{ actorCount }} 位演员
    </div>
    <div v-else class="snapshot-warn">
      尚未采集 Emby 数据，请先点击「采集Emby数据」
    </div>

    <!-- 对比概览 -->
    <div class="tab-content">
      <div v-if="loadingActors" class="loading">加载中...</div>
      <div v-if="errorActors" class="error">{{ errorActors }}</div>

      <div class="actors-grid">
        <div
          v-for="actor in actors"
          :key="actor.actress_id"
          class="actor-card"
          @click="$router.push(`/inventory/actors/${actor.actress_id}`)"
        >
          <div class="actor-cover">
            <img :src="actor.avatar_url || ''" :alt="actor.display_name" @error="$event.target.style.display='none'" />
          </div>
          <div class="actor-info">
            <div class="actor-name">{{ actor.display_name }}</div>
            <div class="actor-stats">
              {{ actor.total_videos }} 部
              <span v-if="actor.missing_count > 0" class="missing-tag"> · {{ actor.missing_count }} 缺失</span>
            </div>
          </div>
        </div>
      </div>

      <div v-if="!loadingActors && actors.length === 0" class="empty">
        暂无演员数据，请先采集 Emby 数据
      </div>
    </div>

    <!-- 作业历史弹窗 -->
    <div v-if="showJobs" class="dialog-overlay" @click.self="showJobs = false">
      <div class="dialog jobs-dialog">
        <div class="dialog-header">
          <h3>作业历史</h3>
          <button @click="showJobs = false" class="close-btn">×</button>
        </div>
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
        <div v-if="!loadingJobs && jobs.length === 0" class="empty">暂无作业记录</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import axios from 'axios'

const showJobs = ref(false)

// 对比概览
const actors = ref([])
const loadingActors = ref(false)
const errorActors = ref('')
const running = ref(false)
const collecting = ref(false)
const snapshotKey = ref('')
const actorCount = ref(0)
const currentProgress = ref(0)

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

const fetchSnapshotInfo = async () => {
  try {
    const res = await axios.get('/api/inventory/snapshots/latest')
    snapshotKey.value = res.data.snapshot_key || ''
    actorCount.value = res.data.actors ? res.data.actors.length : 0
  } catch (e) {
    snapshotKey.value = ''
    actorCount.value = 0
  }
}

const triggerCollect = async () => {
  if (!confirm('确定要采集 Emby 数据吗？这会拉取全量媒体库信息。')) return
  collecting.value = true
  try {
    await axios.post('/api/inventory/jobs/trigger', { job_type: 'collect' })
    pollJobStatus('collect')
  } catch (e) {
    alert('触发失败: ' + e.message)
    collecting.value = false
  }
}

const triggerFullJob = async () => {
  if (!snapshotKey.value) {
    alert('请先采集 Emby 数据')
    return
  }
  running.value = true
  try {
    await axios.post('/api/inventory/jobs/trigger', { job_type: 'full', snapshot_key: snapshotKey.value })
    pollJobStatus('full')
  } catch (e) {
    errorActors.value = '触发失败: ' + e.message
    running.value = false
  }
}

const pollJobStatus = async (type) => {
  setTimeout(async () => {
    try {
      const res = await axios.get('/api/inventory/jobs')
      const jobs = res.data.data || []
      const latest = jobs[0]
      if (latest && latest.status === 'running') {
        currentProgress.value = latest.progress || 0
        await pollJobStatus(type)
      } else {
        running.value = false
        collecting.value = false
        currentProgress.value = latest && latest.status === 'completed' ? 100 : 0
        await fetchActors()
        await fetchSnapshotInfo()
      }
    } catch {
      running.value = false
      collecting.value = false
      currentProgress.value = 0
    }
  }, 1500)
}

onMounted(() => { fetchActors(); fetchSnapshotInfo() })

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
.btn-secondary:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-ghost {
  background: none; color: #666; border: 1px solid #ddd;
  padding: 8px 16px; border-radius: 4px; cursor: pointer;
}
.progress-ring-container {
  position: relative;
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.progress-ring { position: absolute; top: 0; left: 0; }
.progress-ring-fill {
  transition: stroke-dashoffset 0.3s ease;
}
.progress-text {
  position: relative;
  z-index: 1;
  font-size: 9px;
  font-weight: bold;
  color: #1890ff;
}
.btn-disabled { opacity: 0.5; cursor: not-allowed; }
.snapshot-info {
  background: #f6ffed; border: 1px solid #b7eb8f;
  padding: 8px 16px; border-radius: 4px; margin-bottom: 16px;
  font-size: 13px; color: #52c41a;
}
.snapshot-warn {
  background: #fff2e8; border: 1px solid #ffbb96;
  padding: 8px 16px; border-radius: 4px; margin-bottom: 16px;
  font-size: 13px; color: #fa8c16;
}
.actors-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
  gap: 16px;
}
.actor-card {
  background: #fff;
  border-radius: 8px;
  overflow: hidden;
  cursor: pointer;
  transition: transform 0.2s;
}
.actor-card:hover { transform: translateY(-2px); }
.actor-cover img {
  width: 100%;
  aspect-ratio: 3/4;
  object-fit: cover;
}
.actor-info {
  padding: 8px;
}
.actor-name {
  font-weight: bold;
  margin-bottom: 4px;
}
.actor-stats {
  font-size: 12px;
  color: #666;
  margin-bottom: 4px;
}
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

/* 作业历史弹窗 */
.dialog-overlay {
  position: fixed; top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(0,0,0,0.5); display: flex; align-items: center; justify-content: center;
  z-index: 1000;
}
.jobs-dialog {
  background: #fff; border-radius: 8px; width: 600px; max-height: 80vh;
  display: flex; flex-direction: column;
}
.dialog-header {
  display: flex; justify-content: space-between; align-items: center;
  padding: 16px 20px; border-bottom: 1px solid #eee;
}
.dialog-header h3 { margin: 0; }
.close-btn {
  background: none; border: none; font-size: 24px; cursor: pointer; color: #999;
}
.jobs-dialog .jobs-list { max-height: 60vh; overflow-y: auto; padding: 12px 20px; }
</style>
