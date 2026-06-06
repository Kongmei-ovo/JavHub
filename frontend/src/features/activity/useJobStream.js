import { computed, getCurrentInstance, onMounted, onUnmounted, ref } from 'vue'
import api from '../../api/index.js'

const RETRY_DELAYS_MS = [1000, 3000, 9000]
const STREAM_URL = '/api/v1/jobs/stream'
const RUNNING_STATUSES = new Set(['queued', 'running'])

function normalizeJob(rawJob) {
  const id = Number(rawJob?.id)
  if (!Number.isFinite(id)) return null
  return {
    ...rawJob,
    id,
    progress: Math.max(0, Math.min(100, Number(rawJob.progress || 0))),
  }
}

function jobsFromRows(rows) {
  const next = new Map()
  for (const rawJob of Array.isArray(rows) ? rows : []) {
    const job = normalizeJob(rawJob)
    if (job) next.set(job.id, job)
  }
  return next
}

function eventSourceUrl(params = {}) {
  const search = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== '') {
      search.set(key, String(value))
    }
  }
  const query = search.toString()
  return query ? `${STREAM_URL}?${query}` : STREAM_URL
}

export function useJobStream(options = {}) {
  const {
    autoStart = true,
    eventSourceFactory = (url) => new EventSource(url),
    loadInitial = false,
    params = {},
  } = options
  const jobs = ref(new Map())
  const connected = ref(false)
  const lastError = ref('')
  const nextRetryDelayMs = ref(0)
  let source = null
  let retryTimer = null
  let retryIndex = 0
  let stopped = true

  const orderedJobs = computed(() => Array.from(jobs.value.values()).sort((a, b) => {
    const left = Date.parse(a.created_at || a.started_at || a.finished_at || '') || 0
    const right = Date.parse(b.created_at || b.started_at || b.finished_at || '') || 0
    return right - left || Number(b.id || 0) - Number(a.id || 0)
  }))
  const runningJobs = computed(() => orderedJobs.value.filter(job => RUNNING_STATUSES.has(job.status)))

  const upsertJob = (rawJob) => {
    const job = normalizeJob(rawJob)
    if (!job) return
    const next = new Map(jobs.value)
    next.set(job.id, job)
    jobs.value = next
  }

  const closeSource = () => {
    if (!source) return
    source.close()
    source = null
    connected.value = false
  }

  const clearRetry = () => {
    if (retryTimer) clearTimeout(retryTimer)
    retryTimer = null
    nextRetryDelayMs.value = 0
  }

  const connect = () => {
    clearRetry()
    closeSource()
    source = eventSourceFactory(eventSourceUrl(params))
    source.onopen = () => {
      connected.value = true
      lastError.value = ''
      retryIndex = 0
      nextRetryDelayMs.value = 0
    }
    source.onmessage = (event) => {
      try {
        upsertJob(JSON.parse(event.data))
      } catch (error) {
        lastError.value = error?.message || 'Job stream parse failed'
      }
    }
    source.onerror = () => {
      connected.value = false
      closeSource()
      if (stopped) return
      const delay = RETRY_DELAYS_MS[Math.min(retryIndex, RETRY_DELAYS_MS.length - 1)]
      retryIndex += 1
      nextRetryDelayMs.value = delay
      retryTimer = setTimeout(connect, delay)
    }
  }

  const loadSnapshot = async () => {
    try {
      const response = await api.getJobs({ limit: params.limit || 50 })
      jobs.value = jobsFromRows(response?.data?.data)
    } catch (error) {
      lastError.value = error?.message || 'Jobs snapshot failed'
    }
  }

  const start = async () => {
    if (!stopped) return
    stopped = false
    if (loadInitial) await loadSnapshot()
    if (!stopped) connect()
  }

  const stop = () => {
    stopped = true
    clearRetry()
    closeSource()
  }

  if (autoStart) {
    if (getCurrentInstance()) {
      onMounted(start)
    } else {
      start()
    }
  }
  if (getCurrentInstance()) onUnmounted(stop)

  return {
    jobs,
    orderedJobs,
    runningJobs,
    connected,
    lastError,
    nextRetryDelayMs,
    start,
    stop,
  }
}

export { RETRY_DELAYS_MS, STREAM_URL }
