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

    <!-- Tabs -->
    <div class="tabs">
      <button
        :class="{ active: activeTab === 'actors' }"
        @click="activeTab = 'actors'"
      >对比概览</button>
      <button
        :class="{ active: activeTab === 'missing' }"
        @click="activeTab = 'missing'"
      >缺失详情</button>
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

    <!-- 缺失详情 Tab -->
    <div v-if="activeTab === 'missing'" class="tab-content">
      <div class="page-header" style="margin-bottom: 12px;">
        <button @click="fillAll" class="btn-primary" :disabled="fillingAll">
          {{ fillingAll ? '补全中...' : '一键补全全部' }}
        </button>
      </div>

      <div v-if="loadingMissing" class="loading">加载中...</div>
      <div v-if="errorMissing" class="error">{{ errorMissing }}</div>

      <div class="missing-list">
        <div
          v-for="item in missingVideos"
          :key="item.content_id"
          class="missing-item"
        >
          <div class="missing-info">
            <div class="missing-id">{{ item.content_id }}</div>
            <div class="missing-title">{{ item.title || item.content_id }}</div>
            <div class="missing-actress">{{ item.actress_name }}</div>
          </div>
          <div class="missing-actions">
            <button @click="fillOne(item.content_id)" class="btn-small">补全</button>
            <button @click="exempt(item.content_id)" class="btn-danger-small">豁免</button>
          </div>
        </div>
      </div>

      <div v-if="!loadingMissing && missingVideos.length === 0" class="empty">
        暂无缺失影片
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
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

// 缺失详情
const missingVideos = ref([])
const loadingMissing = ref(false)
const errorMissing = ref('')
const fillingAll = ref(false)

const fetchMissing = async () => {
  loadingMissing.value = true
  errorMissing.value = ''
  try {
    const res = await axios.get('/api/inventory/missing')
    missingVideos.value = res.data.data || []
  } catch (e) {
    errorMissing.value = '加载失败: ' + e.message
  } finally {
    loadingMissing.value = false
  }
}

const fillOne = async (contentId) => {
  try {
    await axios.post(`/api/inventory/fill/${contentId}`)
    await fetchMissing()
  } catch (e) {
    alert('补全失败: ' + e.message)
  }
}

const fillAll = async () => {
  if (!confirm('确定要补全所有缺失影片吗？')) return
  fillingAll.value = true
  try {
    await axios.post('/api/inventory/fill-all')
    await fetchMissing()
  } catch (e) {
    alert('补全失败: ' + e.message)
  } finally {
    fillingAll.value = false
  }
}

const exempt = async (contentId) => {
  if (!confirm('确定要豁免此影片吗？')) return
  try {
    await axios.delete(`/api/inventory/missing/${contentId}`)
    await fetchMissing()
  } catch (e) {
    alert('豁免失败: ' + e.message)
  }
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

/* 缺失列表 */
.missing-list { display: flex; flex-direction: column; gap: 8px; }
.missing-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: #fff;
  border-radius: 8px;
}
.missing-id { font-weight: bold; font-size: 14px; }
.missing-title { font-size: 13px; color: #666; margin-top: 2px; }
.missing-actress { font-size: 12px; color: #999; margin-top: 2px; }
.missing-actions { display: flex; gap: 8px; }
.btn-small {
  background: #1890ff; color: #fff; border: none;
  padding: 4px 12px; border-radius: 4px; cursor: pointer; font-size: 12px;
}
.btn-danger-small {
  background: #ff4d4f; color: #fff; border: none;
  padding: 4px 12px; border-radius: 4px; cursor: pointer; font-size: 12px;
}
</style>
