<template>
  <section class="workspace-panel apple-surface">
    <!-- 恢复卡住任务 / 刷新 挪到菜单行右侧；下面一行搜索 + 筛选(状态)，与「作品目录」一致。
         状态走服务端(跨页准确)；搜索按演员/番号在已载入任务里本地过滤。 -->
    <Teleport to="#supplement-tab-actions" :disabled="!canTeleport">
      <button v-if="globalQueue" class="btn btn-ghost btn-sm" type="button" :disabled="recovering" @click="recoverStaleJobs">
        {{ recovering ? '恢复中...' : '恢复卡住任务' }}
      </button>
      <button class="btn btn-ghost btn-sm" type="button" @click="loadJobs">刷新</button>
    </Teleport>

    <!-- 任务队列 hero(始终显示，与作品目录同构)：选中演员时头像露出在顶部，未选则只剩
         四枚状态胶囊(运行中/排队中/已完成/失败)。计数跨页(含全局队列)。 -->
    <SupplementActorHero :actor="actorContext" :subtitle="`任务队列 ${jobsTotalCount} 个`">
      <template #meters>
        <div class="job-stat is-running"><b>{{ jobStatusCounts.running }}</b><span>运行中</span></div>
        <div class="job-stat is-queued"><b>{{ jobStatusCounts.queued }}</b><span>排队中</span></div>
        <div class="job-stat is-succeeded"><b>{{ jobStatusCounts.succeeded }}</b><span>已完成</span></div>
        <div class="job-stat is-failed"><b>{{ jobStatusCounts.failed }}</b><span>失败</span></div>
      </template>
    </SupplementActorHero>

    <div class="sup-toolbar">
      <label class="sup-search">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" aria-hidden="true">
          <circle cx="11" cy="11" r="7" /><path d="M21 21l-4.3-4.3" />
        </svg>
        <input v-model="jobKeyword" type="search" placeholder="搜索演员 / 番号" aria-label="搜索任务" />
        <button v-if="jobKeyword" type="button" class="sup-search-clear" aria-label="清除搜索" @click="jobKeyword = ''">×</button>
      </label>
      <div ref="filterRoot" class="sup-filter">
        <button
          type="button" class="filter-trigger"
          :class="{ on: filterOpen, active: activeJobFilterCount > 0 }"
          :aria-expanded="filterOpen" :aria-label="statusFilterLabel" @click="filterOpen = !filterOpen"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" aria-hidden="true">
            <path d="M3 6h11M3 12h7M3 18h13" /><circle cx="17.5" cy="6" r="2.2" /><circle cx="13.5" cy="12" r="2.2" /><circle cx="19" cy="18" r="2.2" />
          </svg>
          <span>筛选</span>
          <span v-if="activeJobFilterCount" class="ft-count">{{ activeJobFilterCount }}</span>
          <svg class="ft-chev" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><polyline points="6 9 12 15 18 9" /></svg>
        </button>
        <transition name="fp">
          <div v-if="filterOpen" class="filter-panel" role="dialog" :aria-label="statusFilterLabel">
            <div class="fp-row">
              <span class="fp-label">状态</span>
              <div class="fp-seg" role="group" aria-label="任务状态筛选">
                <button v-for="opt in jobStatusOptions" :key="String(opt.value)" type="button" :class="{ active: jobFilters.status === opt.value }" @click="setJobStatus(opt.value)">{{ opt.label }}</button>
              </div>
            </div>
          </div>
        </transition>
      </div>
    </div>

    <SupplementJobList
      :jobs="filteredJobs"
      :loading="jobsLoading"
      :actor-context="actorContext"
      :job-label="jobActorLabel"
      :status-label="statusLabel"
      :context-label="contextLabel"
      :total-count="jobsTotalCount"
      @retry="retryJob"
      @cancel="cancelJob"
      @actor="emit('actor', $event)"
      @refresh="loadJobs"
      @start-supplement="emit('start-supplement')"
    />
    <div v-if="jobsTotalPages > 1" class="pagination">
      <button class="btn btn-ghost btn-sm" :disabled="jobPage <= 1" @click="goJobPage(jobPage - 1)">上一页</button>
      <span>{{ jobPage }} / {{ jobsTotalPages }}</span>
      <button class="btn btn-ghost btn-sm" :disabled="jobPage >= jobsTotalPages" @click="goJobPage(jobPage + 1)">下一页</button>
    </div>
  </section>
</template>

<script>
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import api from '../../api'
import SupplementJobList from './SupplementJobList.vue'
import SupplementActorHero from './SupplementActorHero.vue'
import { useSupplementApi } from './useSupplementApi.js'

export default {
  name: 'JobsTab',
  components: { SupplementJobList, SupplementActorHero },
  props: {
    actorContext: { type: Object, default: null },
    actorName: { type: String, default: '' },
    initialFilters: { type: Object, default: () => ({}) },
    globalQueue: { type: Boolean, default: false },
    contextLabel: { type: String, default: '' },
    contextItems: { type: Array, default: () => [] },
    refreshNonce: { type: Number, default: 0 },
  },
  emits: ['actor', 'start-supplement', 'filters-change'],
  setup(props, { emit }) {
    const supplement = useSupplementApi()
    const jobPage = ref(1)
    const jobKeyword = ref('')
    const filterOpen = ref(false)
    const filterRoot = ref(null)
    // 仅当父级菜单行的 Teleport 目标存在时才传送（隔离单测/无父级时就地渲染，避免目标缺失报错）。
    const canTeleport = typeof document !== 'undefined' && !!document.getElementById('supplement-tab-actions')
    const jobFilters = reactive({ status: '', actress_id: '', source: '', error_provider: '', error_reason: '' })
    // 选中演员时 hero 卡显示的四种任务状态总数(跨页)。
    const jobStatusCounts = reactive({ running: 0, queued: 0, succeeded: 0, failed: 0 })
    const jobStreamRetryDelays = [1000, 3000, 9000]
    let jobStream = null
    let jobStreamRetryTimer = null
    let jobStreamRetryAttempt = 0
    const jobStatusOptions = [
      { value: '', label: '全部状态' },
      { value: 'queued', label: '排队中' },
      { value: 'running', label: '运行中' },
      { value: 'succeeded', label: '已完成' },
      { value: 'failed', label: '失败' },
    ]
    const statusFilterLabel = computed(() => (props.globalQueue ? '全局队列状态筛选' : '任务状态筛选'))
    // 「筛选」徽标只数下拉里的维度（状态）；搜索是独立输入，不计入。
    const activeJobFilterCount = computed(() => (jobFilters.status ? 1 : 0))
    // 搜索按演员/番号在「已载入任务」里本地过滤（jobs 无文本搜索接口，故只作用于当前页）。
    const filteredJobs = computed(() => {
      const kw = jobKeyword.value.trim().toLowerCase()
      if (!kw) return supplement.jobs.value
      return supplement.jobs.value.filter((job) => {
        const hay = [job.source_actor_name, job.source_movie_id, job.local_actress_id, job.id, jobActorLabel(job)]
          .filter((v) => v != null).join(' ').toLowerCase()
        return hay.includes(kw)
      })
    })

    // hero 四枚胶囊的跨页状态总数。每个状态发一次 page_size=1 探针读 total_count(服务端
     // 计数,跨页准确,不受 100 行上限影响)；选中演员则带 actress_id,全局队列则不带。
    const STATUS_KEYS = ['running', 'queued', 'succeeded', 'failed']
    async function loadJobStatusCounts() {
      const actressId = props.actorContext?.id || ''
      try {
        const results = await Promise.all(STATUS_KEYS.map(status =>
          api.listSupplementJobs(actressId
            ? { page: 1, page_size: 1, status, actress_id: actressId }
            : { page: 1, page_size: 1, status })
            .then(resp => {
              const data = (resp && Object.prototype.hasOwnProperty.call(resp, 'data')) ? resp.data : resp
              return Number((data && data.total_count) || 0)
            })
            .catch(() => 0),
        ))
        STATUS_KEYS.forEach((status, i) => { jobStatusCounts[status] = results[i] })
      } catch {
        /* hero 计数尽力而为 */
      }
    }

    function syncFilters() {
      Object.assign(jobFilters, {
        status: props.initialFilters.status || '',
        source: props.initialFilters.source || '',
        error_provider: props.initialFilters.error_provider || '',
        error_reason: props.initialFilters.error_reason || '',
        actress_id: props.actorContext?.id ? String(props.actorContext.id) : '',
      })
    }

    function jobLabel(job) {
      if (job.job_type === 'movie_detail') return job.source_movie_id ? `影片 ${job.source_movie_id}` : '影片详情'
      return job.source_actor_name || (job.local_actress_id ? `演员 ${job.local_actress_id}` : '演员任务')
    }

    function jobActorLabel(job) {
      const base = jobLabel(job)
      const actorName = props.actorName || job.source_actor_name || ''
      const actorId = job.local_actress_id || props.actorContext?.id
      if (!actorName && !actorId) return base
      const actor = actorName || `演员 ${actorId}`
      return base.includes(actor) ? base : `${actor} · ${base}`
    }

    async function loadJobs(options = {}) {
      await supplement.loadJobs({ page: jobPage.value, pageSize: 20, filters: jobFilters, ...options })
      await loadJobStatusCounts()
    }

    // retry/cancel route through the composable's refreshJobs (not this wrapper), so
    // refresh the hero counts explicitly after each so 运行中/失败 stay accurate.
    async function retryJob(jobId) {
      await supplement.retryJob(jobId)
      await loadJobStatusCounts()
    }
    async function cancelJob(jobId) {
      await supplement.cancelJob(jobId)
      await loadJobStatusCounts()
    }

    function normalizeJobStatus(job) {
      if (job?.status === 'completed') return { ...job, status: 'succeeded', progress: 100 }
      return { ...job, progress: Math.max(0, Math.min(100, Number(job?.progress || 0))) }
    }

    function mergeStreamJob(rawJob) {
      if (rawJob?.kind && rawJob.kind !== 'supplement') return
      const job = normalizeJobStatus(rawJob)
      const index = supplement.jobs.value.findIndex(item => item.id === job.id)
      if (index >= 0) {
        supplement.jobs.value = supplement.jobs.value.map(item => (item.id === job.id ? { ...item, ...job } : item))
      } else {
        supplement.jobs.value = [job, ...supplement.jobs.value].slice(0, 20)
        supplement.jobsTotalCount.value = Math.max(supplement.jobsTotalCount.value || 0, supplement.jobs.value.length)
      }
    }

    function handleJobStreamMessage(event) {
      try {
        mergeStreamJob(JSON.parse(event.data))
      } catch {
        // Ignore malformed stream frames.
      }
    }

    function scheduleJobStreamReconnect() {
      if (jobStreamRetryTimer) return
      const delay = jobStreamRetryDelays[Math.min(jobStreamRetryAttempt, jobStreamRetryDelays.length - 1)]
      jobStreamRetryAttempt += 1
      jobStreamRetryTimer = setTimeout(() => {
        jobStreamRetryTimer = null
        openJobStream()
      }, delay)
    }

    function openJobStream() {
      if (typeof EventSource === 'undefined' || jobStream) return
      jobStream = new EventSource('/api/v1/jobs/stream?kind=supplement')
      jobStream.addEventListener('open', () => { jobStreamRetryAttempt = 0 })
      jobStream.addEventListener('message', handleJobStreamMessage)
      jobStream.addEventListener('error', () => {
        jobStream?.close()
        jobStream = null
        scheduleJobStreamReconnect()
      })
    }

    function closeJobStream() {
      if (jobStreamRetryTimer) clearTimeout(jobStreamRetryTimer)
      jobStreamRetryTimer = null
      jobStream?.close()
      jobStream = null
    }

    async function applyJobFilters() {
      jobPage.value = 1
      emit('filters-change', { ...jobFilters })
      await loadJobs()
    }

    async function goJobPage(page) {
      jobPage.value = page
      await loadJobs()
    }

    async function recoverStaleJobs() {
      await supplement.recoverStale(30)
      await loadJobStatusCounts()
    }

    async function setJobStatus(value) {
      jobFilters.status = value
      await applyJobFilters()
    }

    // 下拉外点 / Esc 收起。
    function onDocPointer(event) {
      const root = filterRoot.value
      if (root && !root.contains(event.target)) filterOpen.value = false
    }
    function onKeydown(event) {
      if (event.key === 'Escape') filterOpen.value = false
    }
    watch(filterOpen, (open) => {
      if (open) {
        document.addEventListener('mousedown', onDocPointer)
        document.addEventListener('keydown', onKeydown)
      } else {
        document.removeEventListener('mousedown', onDocPointer)
        document.removeEventListener('keydown', onKeydown)
      }
    })

    watch(
      () => [props.actorContext?.id || '', JSON.stringify(props.initialFilters), props.refreshNonce],
      async () => {
        jobPage.value = 1
        syncFilters()
        await loadJobs()
      },
      { immediate: true }
    )
    onMounted(openJobStream)
    onBeforeUnmount(() => {
      closeJobStream()
      if (typeof document !== 'undefined') {
        document.removeEventListener('mousedown', onDocPointer)
        document.removeEventListener('keydown', onKeydown)
      }
    })

    return {
      ...supplement,
      emit,
      jobPage,
      jobKeyword,
      filterOpen,
      filterRoot,
      canTeleport,
      jobFilters,
      jobStatusOptions,
      statusFilterLabel,
      activeJobFilterCount,
      filteredJobs,
      jobActorLabel,
      jobStatusCounts,
      loadJobs,
      applyJobFilters,
      goJobPage,
      recoverStaleJobs,
      setJobStatus,
      // local wrappers that refresh hero counts; must come AFTER ...supplement to win.
      retryJob,
      cancelJob,
    }
  },
}
</script>

<style scoped src="./supplementPanel.css"></style>
<style scoped src="./supplementHero.css"></style>
