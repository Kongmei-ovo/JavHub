<template>
  <div class="inventory-page">
    <div class="page-header">
      <h1>库存对比</h1>
      <div class="header-actions">
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
      当前快照：{{ snapshotKey }} · {{ total }} 位演员
    </div>
    <div v-else class="snapshot-warn">
      尚未采集 Emby 数据，请先点击「采集Emby数据」
    </div>

    <!-- 搜索过滤栏 -->
    <div class="filter-bar">
      <div class="search-box">
        <svg class="search-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="11" cy="11" r="8"/>
          <path d="m21 21-4.35-4.35"/>
        </svg>
        <input
          v-model="searchKeyword"
          placeholder="搜索演员..."
          class="search-input"
          @input="onSearchInput"
        />
        <button v-if="searchKeyword" class="search-clear" @click="clearSearch">×</button>
      </div>
      <div class="filter-controls">
        <div class="sort-control">
          <label>排序：</label>
          <select v-model="sortBy" @change="doSearch" class="filter-select">
            <option value="actress_name">名称 A→Z</option>
            <option value="actress_name_desc">名称 Z→A</option>
            <option value="total_videos">影片数 多→少</option>
            <option value="total_videos_asc">影片数 少→多</option>
            <option value="missing_count">缺失 多→少</option>
            <option value="missing_count_asc">缺失 少→多</option>
          </select>
        </div>
        <div class="page-size-control">
          <label>每页：</label>
          <select v-model="pageSize" @change="onPageSizeChange" class="filter-select">
            <option :value="24">24</option>
            <option :value="48">48</option>
            <option :value="72">72</option>
            <option :value="100">100</option>
          </select>
        </div>
      </div>
    </div>

    <!-- 结果信息 -->
    <div v-if="!loadingActors && actors.length > 0" class="result-bar">
      <span class="result-count">共 {{ total }} 位演员</span>
    </div>

    <!-- 顶部分页 -->
    <div v-if="!loadingActors && totalPages > 1" class="pagination-bar pagination-bar-top">
      <button class="page-btn" :disabled="page <= 1" @click="goPage(1)">«</button>
      <button class="page-btn" :disabled="page <= 1" @click="goPage(page - 1)">‹</button>
      <span class="page-indicator">{{ page }} / {{ totalPages }}</span>
      <button class="page-btn" :disabled="page >= totalPages" @click="goPage(page + 1)">›</button>
      <button class="page-btn" :disabled="page >= totalPages" @click="goPage(totalPages)">»</button>
      <div class="jump-wrap">
        <input
          v-model.number="jumpPage"
          class="jump-input"
          type="number"
          min="1"
          :max="totalPages"
          @keyup.enter="doJumpPage"
        />
        <button class="jump-btn" @click="doJumpPage">跳转</button>
      </div>
    </div>

    <!-- 对比概览 -->
    <div class="tab-content">
      <div v-if="loadingActors" class="loading">加载中...</div>
      <div v-if="errorActors" class="error">{{ errorActors }}</div>

      <!-- 骨架屏 -->
      <div v-if="loadingActors" class="actors-grid">
        <div v-for="n in 12" :key="n" class="actor-card skeleton">
          <div class="actor-cover skeleton-cover"></div>
          <div class="actor-info">
            <div class="skeleton-line w-60"></div>
            <div class="skeleton-line w-40"></div>
          </div>
        </div>
      </div>

      <div v-else class="actors-grid">
        <div
          v-for="actor in actors"
          :key="actor.actress_id"
          class="actor-card"
          @click="$router.push(`/inventory/actors/${actor.actress_id}`)"
        >
          <div class="actor-cover">
            <img
              :src="actor.avatar_url || ''"
              :alt="actor.display_name"
              @error="handleImgError($event)"
            />
            <div v-if="actor.missing_count > 0" class="missing-badge">{{ actor.missing_count }}</div>
          </div>
          <div class="actor-info">
            <div class="actor-name">{{ actor.display_name }}</div>
            <div class="actor-stats">{{ actor.total_videos }} 部</div>
          </div>
        </div>
      </div>

      <div v-if="!loadingActors && actors.length === 0 && snapshotKey" class="empty">
        <template v-if="searchKeyword">未找到匹配「{{ searchKeyword }}」的演员</template>
        <template v-else>暂无演员数据</template>
      </div>
      <div v-if="!loadingActors && !snapshotKey" class="empty">
        请先采集 Emby 数据
      </div>
    </div>

    <!-- 底部分页 -->
    <div v-if="!loadingActors && totalPages > 1" class="pagination-bar pagination-bar-bottom">
      <button class="page-btn" :disabled="page <= 1" @click="goPage(1)">«</button>
      <button class="page-btn" :disabled="page <= 1" @click="goPage(page - 1)">‹</button>
      <span class="page-indicator">{{ page }} / {{ totalPages }}</span>
      <button class="page-btn" :disabled="page >= totalPages" @click="goPage(page + 1)">›</button>
      <button class="page-btn" :disabled="page >= totalPages" @click="goPage(totalPages)">»</button>
      <div class="jump-wrap">
        <input
          v-model.number="jumpPage"
          class="jump-input"
          type="number"
          min="1"
          :max="totalPages"
          @keyup.enter="doJumpPage"
        />
        <button class="jump-btn" @click="doJumpPage">跳转</button>
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
const currentProgress = ref(0)

// 分页 & 搜索 & 排序
const searchKeyword = ref('')
const sortBy = ref('actress_name')
const page = ref(1)
const pageSize = ref(48)
const total = ref(0)
const totalPages = ref(1)
const jumpPage = ref(null)
let searchTimer = null

const fetchActors = async () => {
  loadingActors.value = true
  errorActors.value = ''
  try {
    const params = {
      page: page.value,
      page_size: pageSize.value
    }
    if (searchKeyword.value) {
      params.search = searchKeyword.value
    }
    // 解析排序参数
    if (sortBy.value === 'actress_name_desc') {
      params.sort_by = 'actress_name'
      params.sort_order = 'desc'
    } else if (sortBy.value === 'actress_name') {
      params.sort_by = 'actress_name'
      params.sort_order = 'asc'
    } else if (sortBy.value === 'total_videos') {
      params.sort_by = 'total_videos'
      params.sort_order = 'desc'
    } else if (sortBy.value === 'total_videos_asc') {
      params.sort_by = 'total_videos'
      params.sort_order = 'asc'
    } else if (sortBy.value === 'missing_count') {
      params.sort_by = 'missing_count'
      params.sort_order = 'desc'
    } else if (sortBy.value === 'missing_count_asc') {
      params.sort_by = 'missing_count'
      params.sort_order = 'asc'
    }

    const res = await axios.get('/api/inventory/actors', { params })
    actors.value = res.data.data || []
    total.value = res.data.total || 0
    totalPages.value = res.data.total_pages || 1
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
  } catch (e) {
    snapshotKey.value = ''
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

const onSearchInput = () => {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    page.value = 1
    doSearch()
  }, 300)
}

const clearSearch = () => {
  searchKeyword.value = ''
  page.value = 1
  doSearch()
}

const doSearch = () => {
  page.value = 1
  fetchActors()
}

const onPageSizeChange = () => {
  page.value = 1
  fetchActors()
}

const goPage = (p) => {
  if (p < 1 || p > totalPages.value || p === page.value) return
  page.value = p
  fetchActors()
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

const doJumpPage = () => {
  if (!jumpPage.value) return
  const p = Math.max(1, Math.min(totalPages.value, jumpPage.value))
  jumpPage.value = null
  goPage(p)
}

const handleImgError = (e) => {
  e.target.style.display = 'none'
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
  background: var(--accent); color: #fff; border: none;
  padding: 8px 16px; border-radius: 4px; cursor: pointer;
}
.btn-primary:disabled { background: var(--border); cursor: not-allowed; }
.btn-secondary:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-ghost {
  background: none; color: var(--text-secondary); border: 1px solid var(--border);
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

/* 搜索过滤栏 */
.filter-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}
.search-box {
  display: flex;
  align-items: center;
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 4px;
  padding: 0 12px;
  flex: 1;
  max-width: 320px;
}
.search-box:focus-within {
  border-color: var(--accent);
}
.search-icon {
  width: 18px;
  height: 18px;
  color: #999;
  flex-shrink: 0;
}
.search-input {
  flex: 1;
  border: none;
  outline: none;
  padding: 8px;
  font-size: 14px;
  background: transparent;
  color: var(--text-primary);
}
.search-clear {
  background: none;
  border: none;
  color: #999;
  cursor: pointer;
  font-size: 18px;
  padding: 0 4px;
}
.search-clear:hover { color: var(--text-primary); }
.filter-controls {
  display: flex;
  align-items: center;
  gap: 16px;
}
.sort-control,
.page-size-control {
  display: flex;
  align-items: center;
  gap: 6px;
}
.sort-control label,
.page-size-control label {
  font-size: 13px;
  color: var(--text-secondary);
  white-space: nowrap;
}
.filter-select {
  padding: 6px 10px;
  border: 1px solid var(--border);
  border-radius: 4px;
  background: var(--bg-card);
  color: var(--text-primary);
  font-size: 13px;
  cursor: pointer;
}
.filter-select:focus {
  outline: none;
  border-color: var(--accent);
}

.result-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}
.result-count {
  font-size: 13px;
  color: var(--text-secondary);
}

.actors-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
  gap: 16px;
}
.actor-card {
  background: var(--bg-card);
  border-radius: 8px;
  overflow: hidden;
  cursor: pointer;
  transition: transform 0.2s, box-shadow 0.2s;
}
.actor-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 4px 12px rgba(0,0,0,0.1);
}
.actor-cover {
  position: relative;
  width: 100%;
  aspect-ratio: 3/4;
  overflow: hidden;
  background: var(--bg-secondary);
}
.actor-cover img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 0.3s;
}
.actor-card:hover .actor-cover img {
}
.missing-badge {
  position: absolute;
  top: 6px;
  right: 6px;
  background: #ff4d4f;
  color: #fff;
  font-size: 11px;
  font-weight: bold;
  padding: 2px 6px;
  border-radius: 10px;
  min-width: 20px;
  text-align: center;
}
.actor-info {
  padding: 8px;
}
.actor-name {
  font-weight: bold;
  font-size: 13px;
  margin-bottom: 2px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.actor-stats {
  font-size: 11px;
  color: #999;
}
.missing-tag { color: #ff4d4f; }
.loading, .error, .empty { text-align: center; padding: 40px; color: #666; }
.error { color: #ff4d4f; }

/* 骨架屏 */
.skeleton-cover {
  width: 100%;
  aspect-ratio: 3/4;
  background: var(--bg-card-hover);
  position: relative;
  overflow: hidden;
}
.skeleton-cover::after {
  content: "";
  position: absolute;
  inset: 0;
  background: linear-gradient(90deg, transparent, var(--white-06), transparent);
  transform: translateX(-100%);
  animation: shimmer 2s infinite;
}
.skeleton-line {
  height: 12px;
  background: #f0f0f0;
  border-radius: 6px;
  margin-bottom: 6px;
}
.skeleton-line.w-60 { width: 60%; }
.skeleton-line.w-40 { width: 40%; }
@keyframes shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

/* 分页 */
.pagination-bar {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 8px;
  padding: 16px 0;
}
.pagination-bar-top {
  padding: 12px 0 16px;
}
.page-btn {
  background: var(--bg-card);
  border: 1px solid var(--border);
  color: var(--text-primary);
  padding: 5px 10px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 13px;
  transition: all 0.2s;
}
.page-btn:hover:not(:disabled) {
  border-color: var(--accent);
  color: var(--accent);
}
.page-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}
.page-indicator {
  font-size: 13px;
  color: var(--text-secondary);
  padding: 0 8px;
}
.jump-wrap {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-left: 8px;
}
.jump-input {
  width: 50px;
  padding: 4px 6px;
  border: 1px solid var(--border);
  border-radius: 4px;
  font-size: 12px;
  text-align: center;
  background: var(--bg-card);
  color: var(--text-primary);
}
.jump-input::-webkit-inner-spin-button,
.jump-input::-webkit-outer-spin-button {
  -webkit-appearance: none;
}
.jump-btn {
  background: var(--bg-secondary);
  border: 1px solid var(--border);
  color: var(--text-primary);
  padding: 4px 10px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
  transition: all 0.2s;
}
.jump-btn:hover {
  border-color: var(--accent);
  color: var(--accent);
}

/* 作业历史 */
.jobs-list { display: flex; flex-direction: column; gap: 8px; }
.job-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: var(--bg-card);
  border-radius: 8px;
}
.job-type { font-weight: bold; }
.job-meta { font-size: 12px; color: #999; margin-top: 4px; display: flex; gap: 12px; }
.job-stats { display: flex; gap: 12px; font-size: 13px; }

.dialog-overlay {
  position: fixed; top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(0,0,0,0.5); display: flex; align-items: center; justify-content: center;
  z-index: 1000;
}
.jobs-dialog {
  background: var(--bg-card); border-radius: 8px; width: 600px; max-height: 80vh;
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

@media (max-width: 768px) {
  .filter-bar {
    flex-direction: column;
    align-items: stretch;
  }
  .search-box {
    max-width: none;
  }
  .filter-controls {
    justify-content: space-between;
  }
  .actors-grid {
    grid-template-columns: repeat(auto-fill, minmax(110px, 1fr));
    gap: 12px;
  }
}
</style>
