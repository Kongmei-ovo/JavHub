<template>
  <div class="inventory-page page-shell page-shell--workspace">
    <div class="page-header">
      <h1>库存对比</h1>
      <div class="header-actions">
        <div v-if="running || collecting" class="progress-ring-container">
          <svg class="progress-ring" width="40" height="40">
            <circle
              class="progress-ring-bg"
              cx="20" cy="20" r="16"
              fill="none"
              stroke="var(--glass-control-border)"
              stroke-width="3"
            />
            <circle
              class="progress-ring-fill"
              cx="20" cy="20" r="16"
              fill="none"
              stroke="var(--glass-active-border)"
              stroke-width="3"
              :stroke-dasharray="100"
              :stroke-dashoffset="100 - currentProgress"
              transform="rotate(-90 20 20)"
            />
          </svg>
          <span class="progress-text">{{ currentProgress }}%</span>
        </div>
        <button type="button" @click="triggerCollect" class="btn btn-primary" :disabled="collecting || running">
          {{ collecting ? '采集中...' : '采集Emby数据' }}
        </button>
        <button type="button" @click="triggerFullJob" class="btn btn-ghost" :disabled="running || collecting" :class="{ 'btn-disabled': !snapshotKey }">
          {{ running ? '对比中...' : '全量对比' }}
        </button>
        <button type="button" @click="showJobs = true; fetchJobs()" class="btn btn-ghost">作业历史</button>
      </div>
    </div>

    <!-- 快照信息 -->
    <div v-if="snapshotKey" class="snapshot-info">
      当前快照：{{ snapshotKey }} · {{ total }} 位演员
      <span v-if="mappingSummary.total">
        · 映射覆盖率 {{ mappingCoverageText }}
        · 未映射 {{ mappingSummary.unmapped || 0 }}
        · 映射建议 {{ mappingSummary.candidate || 0 }}
        · 候选 {{ candidateStats.candidate || 0 }}
      </span>
      <button type="button" class="inline-link" @click="$router.push('/normalize')">处理未映射演员</button>
      <button type="button" class="inline-link" @click="$router.push({ path: '/downloads', query: { tab: 'candidates', source: 'inventory' } })">查看候选</button>
    </div>
    <div v-else class="snapshot-warn">
      尚未采集 Emby 数据，请先点击「采集Emby数据」
    </div>

    <!-- 搜索过滤栏 -->
    <div class="filter-bar">
      <div class="search-box">
        <svg class="search-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
          <circle cx="11" cy="11" r="8"/>
          <path d="m21 21-4.35-4.35"/>
        </svg>
        <input
          v-model="searchKeyword"
          placeholder="搜索演员..."
          class="search-input"
          @input="onSearchInput"
        />
        <button v-if="searchKeyword" type="button" class="search-clear" @click="clearSearch">×</button>
      </div>
      <div class="filter-controls">
        <div class="sort-control">
          <label>排序：</label>
          <GlassSelect
            v-model="sortBy"
            :options="sortOptions"
            size="regular"
            aria-label="库存演员排序"
            @change="doSearch"
          />
        </div>
        <div class="page-size-control">
          <label>每页：</label>
          <GlassSelect
            v-model="pageSize"
            :options="pageSizeOptions"
            size="regular"
            placement="right"
            aria-label="库存每页数量"
            @change="onPageSizeChange"
          />
        </div>
      </div>
    </div>

    <!-- 结果信息 -->
    <div v-if="!loadingActors && actors.length > 0" class="result-bar">
      <span class="result-count">共 {{ total }} 位演员</span>
    </div>

    <!-- 顶部分页 -->
    <div v-if="!loadingActors && totalPages > 1" class="pagination-bar pagination-bar-top">
      <button type="button" class="page-btn" :disabled="page <= 1" @click="goPage(1)">«</button>
      <button type="button" class="page-btn" :disabled="page <= 1" @click="goPage(page - 1)">‹</button>
      <span class="page-indicator">{{ page }} / {{ totalPages }}</span>
      <button type="button" class="page-btn" :disabled="page >= totalPages" @click="goPage(page + 1)">›</button>
      <button type="button" class="page-btn" :disabled="page >= totalPages" @click="goPage(totalPages)">»</button>
      <div class="jump-wrap">
        <input
          v-model.number="jumpPage"
          class="jump-input"
          type="number"
          min="1"
          :max="totalPages"
          @keyup.enter="doJumpPage"
        />
        <button type="button" class="jump-btn" @click="doJumpPage">跳转</button>
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
          role="button"
          tabindex="0"
          @click="openActor(actor)"
          @keydown.enter.prevent="openActor(actor)"
          @keydown.space.prevent="openActor(actor)"
        >
          <div class="actor-cover">
            <img
              :src="actor.avatar_url || ''"
              :alt="actor.display_name"
              loading="lazy"
              decoding="async"
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
      <button type="button" class="page-btn" :disabled="page <= 1" @click="goPage(1)">«</button>
      <button type="button" class="page-btn" :disabled="page <= 1" @click="goPage(page - 1)">‹</button>
      <span class="page-indicator">{{ page }} / {{ totalPages }}</span>
      <button type="button" class="page-btn" :disabled="page >= totalPages" @click="goPage(page + 1)">›</button>
      <button type="button" class="page-btn" :disabled="page >= totalPages" @click="goPage(totalPages)">»</button>
      <div class="jump-wrap">
        <input
          v-model.number="jumpPage"
          class="jump-input"
          type="number"
          min="1"
          :max="totalPages"
          @keyup.enter="doJumpPage"
        />
        <button type="button" class="jump-btn" @click="doJumpPage">跳转</button>
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
              <span v-if="job.result.candidates">候选 {{ job.result.candidates }}</span>
              <span v-if="job.result.unmapped" class="unmapped-tag">未映射 {{ job.result.unmapped }}</span>
              <span v-if="job.result.failed" class="failed-tag">失败 {{ job.result.failed }}</span>
              <span v-if="job.result.actors && !job.result.scanned">演员 {{ job.result.actors }}</span>
            </div>
            <div v-else-if="job.error_msg" class="job-error">{{ job.error_msg }}</div>
          </div>
        </div>
        <div v-if="!loadingJobs && jobs.length === 0" class="empty">暂无作业记录</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'
import { ElMessage } from '../utils/message.js'
import api from '../api'
import { requestConfirm } from '../utils/confirmDialog'
import GlassSelect from '../components/GlassSelect.vue'

const router = useRouter()
const showJobs = ref(false)

// 对比概览
const actors = ref([])
const loadingActors = ref(false)
const errorActors = ref('')
const running = ref(false)
const collecting = ref(false)
const snapshotKey = ref('')
const currentProgress = ref(0)
const mappingSummary = ref({})
const candidateStats = ref({})
const mappingCoverageText = ref('0%')

// 分页 & 搜索 & 排序
const searchKeyword = ref('')
const sortBy = ref('actress_name')
const page = ref(1)
const pageSize = ref(48)
const total = ref(0)
const totalPages = ref(1)
const jumpPage = ref(null)
let searchTimer = null

const sortOptions = [
  { value: 'actress_name', label: '名称 A→Z' },
  { value: 'actress_name_desc', label: '名称 Z→A' },
  { value: 'total_videos', label: '影片数 多→少' },
  { value: 'total_videos_asc', label: '影片数 少→多' },
  { value: 'missing_count', label: '缺失 多→少' },
  { value: 'missing_count_asc', label: '缺失 少→多' },
]

const pageSizeOptions = [24, 48, 72, 100].map(size => ({ value: size, label: String(size) }))

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
    await fetchMappingSummary()
  } catch (e) {
    snapshotKey.value = ''
  }
}

const fetchMappingSummary = async () => {
  try {
    const summary = await api.getActorMappingSummary()
    mappingSummary.value = summary.data || {}
    mappingCoverageText.value = `${Math.round((mappingSummary.value.coverage || 0) * 100)}%`
    const candidates = await api.getDownloadCandidateSummary({ status: 'candidate', source: 'inventory' })
    candidateStats.value = candidates.data || {}
  } catch (e) {
    mappingSummary.value = {}
    candidateStats.value = {}
    mappingCoverageText.value = '0%'
  }
}

const triggerCollect = async () => {
  const confirmed = await requestConfirm({
    title: '采集 Emby 数据',
    message: '确定要采集 Emby 数据吗？',
    details: '这会拉取全量媒体库信息，期间库存对比按钮会暂时不可用。',
    confirmText: '开始采集'
  })
  if (!confirmed) return
  collecting.value = true
  try {
    await axios.post('/api/inventory/jobs/trigger', { job_type: 'collect' })
    pollJobStatus('collect')
  } catch (e) {
    ElMessage.error('触发失败: ' + e.message)
    collecting.value = false
  }
}

const triggerFullJob = async () => {
  if (!snapshotKey.value) {
    ElMessage.warning('请先采集 Emby 数据')
    return
  }
  const confirmed = await requestConfirm({
    title: '全量库存对比',
    message: '确认开始全量库存对比？',
    details: '会读取最近一次 Emby 采集快照并生成缺失/映射结果，运行期间相关操作会暂时不可用。',
    confirmText: '开始对比',
  })
  if (!confirmed) return
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

const openActor = (actor) => {
  if (!actor?.actress_id) return
  router.push(`/inventory/actors/${actor.actress_id}`)
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

<style scoped src="../features/inventory/inventory.css"></style>
