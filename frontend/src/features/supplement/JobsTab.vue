<template>
  <section class="workspace-panel apple-surface">
    <div class="panel-header">
      <div>
        <h2>{{ title }}</h2>
        <p v-if="contextLabel" class="panel-subtitle">{{ contextLabel }}</p>
      </div>
      <div class="filter-bar compact">
        <GlassSelect v-model="jobFilters.status" :options="jobStatusOptions" size="compact" :aria-label="statusFilterLabel" @change="applyJobFilters" />
        <button v-if="globalQueue" class="btn btn-ghost btn-sm" type="button" :disabled="recovering" @click="recoverStaleJobs">
          {{ recovering ? '恢复中...' : '恢复卡住任务' }}
        </button>
        <button class="btn btn-ghost btn-sm" type="button" @click="loadJobs">刷新</button>
      </div>
    </div>
    <div v-if="contextItems.length" class="queue-filter-summary" aria-label="全局队列筛选上下文">
      <span v-for="item in contextItems" :key="item.label" class="queue-filter-chip">
        <b>{{ item.label }}</b>
        <em>{{ item.value }}</em>
      </span>
    </div>
    <SupplementJobList
      :jobs="jobs"
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
import GlassSelect from '../../components/GlassSelect.vue'
import SupplementJobList from './SupplementJobList.vue'
import { useSupplementApi } from './useSupplementApi.js'

export default {
  name: 'JobsTab',
  components: { GlassSelect, SupplementJobList },
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
    const jobFilters = reactive({ status: '', actress_id: '', source: '', error_provider: '', error_reason: '' })
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
    const title = computed(() => (props.globalQueue ? '全局队列' : '任务队列'))
    const statusFilterLabel = computed(() => (props.globalQueue ? '全局队列状态筛选' : '任务状态筛选'))

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
    }

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
    onBeforeUnmount(closeJobStream)

    return {
      ...supplement,
      emit,
      jobPage,
      jobFilters,
      jobStatusOptions,
      title,
      statusFilterLabel,
      jobActorLabel,
      loadJobs,
      applyJobFilters,
      goJobPage,
      recoverStaleJobs,
    }
  },
}
</script>
