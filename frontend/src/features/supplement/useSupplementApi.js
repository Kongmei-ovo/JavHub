import { computed, ref } from 'vue'
import defaultApi from '../../api/index.js'
import { ElMessage } from '../../utils/message.js'

function unwrapResponse(resp, fallback = null) {
  if (resp && Object.prototype.hasOwnProperty.call(resp, 'data')) return resp.data
  return resp ?? fallback
}

function errorMessage(error) {
  return error?.message || error?.response?.data?.detail || '请求失败'
}

function assignTruthy(params, filters, keys) {
  for (const key of keys) {
    const value = filters?.[key]
    if (value !== undefined && value !== null && value !== '') params[key] = value
  }
  return params
}

export function buildMovieFilterParams(filters = {}, baseParams = {}) {
  const params = { ...baseParams }
  if (filters.matched !== null && filters.matched !== undefined) params.matched = filters.matched
  assignTruthy(params, filters, ['actress_id', 'q'])
  if (filters.quality === 'missing_cover') params.missing_cover = true
  if (filters.quality === 'missing_runtime') params.missing_runtime = true
  if (filters.quality === 'missing_maker') params.missing_maker = true
  if (filters.quality === 'missing_categories') params.missing_categories = true
  if (filters.quality === 'low_completeness') params.max_completeness = 2
  return params
}

export function useSupplementApi({ api = defaultApi } = {}) {
  const jobs = ref([])
  const jobsLoading = ref(false)
  const jobsError = ref('')
  const jobsTotalCount = ref(0)
  const jobsTotalPages = ref(1)
  const lastJobRequest = ref({ page: 1, pageSize: 20, filters: {} })
  const recovering = ref(false)

  const supplementMovies = ref([])
  const moviesLoading = ref(false)
  const moviesError = ref('')
  const moviesTotalCount = ref(0)
  const moviesTotalPages = ref(1)
  const lastMovieRequest = ref({ page: 1, pageSize: 20, filters: {} })
  const enrichingMovies = ref({})
  const batchEnriching = ref(false)
  const candidateImporting = ref(false)

  const sourceDiagnosticsOpen = ref(false)
  const sourceDiagnosticsLoading = ref(false)
  const sourceDiagnostics = ref(null)
  const manualContentId = ref('')
  const manualActionLoading = ref(false)

  const sourceHealth = ref([])
  const sourceBudgets = ref([])
  const sourceHealthLoading = ref(false)
  const sourceHealthError = ref('')
  const sourceActionLoading = ref('')
  const providerSmokeLoading = ref(false)
  const providerSmokeReport = ref(null)
  const providerSmokeForm = ref({ source: '', sourceMovieId: '' })
  const providerSmokeRuns = ref([])
  const gfriendsAvatarJob = ref(null)
  const gfriendsAvatarSyncing = ref(false)

  async function loadJobs({ page = 1, pageSize = 20, filters = {}, silent = false } = {}) {
    lastJobRequest.value = { page, pageSize, filters: { ...filters } }
    if (!silent) jobsLoading.value = true
    jobsError.value = ''
    try {
      const params = assignTruthy({ page, page_size: pageSize }, filters, [
        'status',
        'actress_id',
        'source',
        'error_provider',
        'error_reason',
      ])
      const data = unwrapResponse(await api.listSupplementJobs(params), {})
      jobs.value = data.data || data || []
      jobsTotalCount.value = data.total_count || 0
      jobsTotalPages.value = data.total_pages || 1
    } catch (error) {
      jobsError.value = errorMessage(error)
      console.error('Load supplement jobs failed:', error)
    } finally {
      if (!silent) jobsLoading.value = false
    }
  }

  async function refreshJobs() {
    await loadJobs(lastJobRequest.value)
  }

  async function retryJob(jobId) {
    try {
      await api.retrySupplementJob(jobId)
      await refreshJobs()
    } catch (error) {
      jobsError.value = errorMessage(error)
      console.error('Retry job failed:', error)
    }
  }

  async function cancelJob(jobId) {
    try {
      await api.cancelSupplementJob(jobId)
      await refreshJobs()
    } catch (error) {
      jobsError.value = errorMessage(error)
      console.error('Cancel job failed:', error)
    }
  }

  async function recoverStale(olderThanMinutes = 30) {
    recovering.value = true
    try {
      await api.recoverStaleSupplementJobs(olderThanMinutes)
      await refreshJobs()
    } catch (error) {
      jobsError.value = errorMessage(error)
      console.error('Recover stale failed:', error)
    } finally {
      recovering.value = false
    }
  }

  async function loadMovies({ page = 1, pageSize = 20, filters = {}, silent = false } = {}) {
    lastMovieRequest.value = { page, pageSize, filters: { ...filters } }
    if (!silent) moviesLoading.value = true
    moviesError.value = ''
    try {
      const params = buildMovieFilterParams(filters, { page, page_size: pageSize })
      const data = unwrapResponse(await api.listSupplementMovies(params), {})
      supplementMovies.value = data.data || data || []
      moviesTotalCount.value = data.total_count || 0
      moviesTotalPages.value = data.total_pages || 1
    } catch (error) {
      moviesError.value = errorMessage(error)
      console.error('Load supplement movies failed:', error)
    } finally {
      if (!silent) moviesLoading.value = false
    }
  }

  async function refreshMovies() {
    await loadMovies(lastMovieRequest.value)
  }

  function movieMatchState(movie) {
    if (movie?.matched_content_id) return 'matched'
    if (movie?.match_status === 'manual_ignored') return 'ignored'
    if (movie?.match_status === 'candidate' || (movie?.match_candidate_count ?? 0) > 0) return 'candidate'
    return 'supplement-only'
  }

  function movieMatchClass(movie) {
    return movieMatchState(movie)
  }

  function movieMatchLabel(movie) {
    const state = movieMatchState(movie)
    if (state === 'matched') return `已匹配 ${movie.matched_content_id}`
    if (state === 'candidate') return (movie.match_candidate_count ?? 0) > 0 ? `待确认 ${movie.match_candidate_count}` : '待确认'
    if (state === 'ignored') return '已忽略'
    return '仅补全'
  }

  function movieCover(movie) {
    return movie?.cover_thumb_url || movie?.cover_url || ''
  }

  function movieCategories(movie) {
    const raw = movie?.category_names
    if (!raw) return ''
    let list = raw
    if (typeof raw === 'string') {
      try { list = JSON.parse(raw) } catch { return raw }
    }
    if (!Array.isArray(list)) return String(raw)
    return list.slice(0, 3).join(' · ')
  }

  function movieFieldChips(movie = {}) {
    return [
      { key: 'cover', label: '封面', missingLabel: '缺封面', value: movieCover(movie) ? '已取' : '', important: true },
      { key: 'runtime', label: '时长', missingLabel: '缺时长', value: movie.runtime_mins ? `${movie.runtime_mins}m` : '', important: true },
      { key: 'maker', label: '厂商', missingLabel: '缺厂商', value: movie.maker_name || '' },
      { key: 'label', label: '厂牌', missingLabel: '缺厂牌', value: movie.label_name || '' },
      { key: 'series', label: '系列', missingLabel: '缺系列', value: movie.series_name || '' },
      { key: 'category', label: '分类', missingLabel: '缺分类', value: movieCategories(movie) || '' },
    ]
  }

  const workspaceMovieFieldGapCount = computed(() => supplementMovies.value.reduce((total, movie) => {
    return total + movieFieldChips(movie).filter(chip => !chip.value).length
  }, 0))

  const workspacePendingCandidateCount = computed(() => {
    return supplementMovies.value.filter(movie => movieMatchClass(movie) === 'candidate').length
  })

  const workspaceDetailTargetCount = computed(() => supplementMovies.value.filter(movie => {
    return Boolean(movie?.source_movie_id) && movieFieldChips(movie).some(chip => !chip.value)
  }).length)

  async function enrichMovie(movie, { actressId = '', onJobsRequested = null } = {}) {
    if (!movie?.source_movie_id || enrichingMovies.value[movie.id]) return
    enrichingMovies.value = { ...enrichingMovies.value, [movie.id]: true }
    try {
      await api.startSupplementMovieDetailJob(movie.source_movie_id, 'all', movie.local_actress_id || actressId || null)
      ElMessage.success('已加入详情任务队列')
      if (onJobsRequested) await onJobsRequested()
    } catch (error) {
      moviesError.value = errorMessage(error)
      console.error('Start movie detail job failed:', error)
    } finally {
      const next = { ...enrichingMovies.value }
      delete next[movie.id]
      enrichingMovies.value = next
    }
  }

  async function batchEnrichMovies({ filters = {}, onJobsRequested = null } = {}) {
    if (batchEnriching.value) return
    batchEnriching.value = true
    try {
      await api.startSupplementMovieDetailBatchJobs(buildMovieFilterParams(filters, { source: 'all', limit: 20 }))
      ElMessage.success('已批量加入详情任务队列')
      if (onJobsRequested) await onJobsRequested()
    } catch (error) {
      moviesError.value = errorMessage(error)
      console.error('Start batch movie detail jobs failed:', error)
    } finally {
      batchEnriching.value = false
    }
  }

  async function createDownloadCandidates({ filters = {}, actressId = '', actressName = '', router = null } = {}) {
    if (candidateImporting.value) return
    candidateImporting.value = true
    try {
      const params = buildMovieFilterParams(filters)
      if (actressId) params.actress_id = actressId
      if (actressName) params.actress_name = actressName
      const data = unwrapResponse(await api.createSupplementDownloadCandidates(params), {})
      ElMessage.success(`已生成 ${data.created || 0} 个下载候选，已有 ${data.existing || 0} 个`)
      if (router) {
        await router.push({
          path: '/candidates',
          query: {
            status: 'candidate',
            source: 'supplement',
            ...(actressId ? { actress_id: actressId } : {}),
            ...(filters.q ? { q: filters.q } : {}),
          },
        })
      }
    } catch (error) {
      moviesError.value = errorMessage(error)
      console.error('Create supplement download candidates failed:', error)
    } finally {
      candidateImporting.value = false
    }
  }

  async function openMovieSources(movie) {
    if (!movie?.id) return
    sourceDiagnosticsOpen.value = true
    sourceDiagnosticsLoading.value = true
    sourceDiagnostics.value = null
    try {
      sourceDiagnostics.value = unwrapResponse(await api.getSupplementMovieSources(movie.id), {})
      manualContentId.value = sourceDiagnostics.value?.movie?.matched_content_id || ''
    } catch (error) {
      moviesError.value = errorMessage(error)
      console.error('Load movie sources failed:', error)
    } finally {
      sourceDiagnosticsLoading.value = false
    }
  }

  function closeMovieSources() {
    sourceDiagnosticsOpen.value = false
    sourceDiagnostics.value = null
    manualContentId.value = ''
  }

  async function reloadCurrentDiagnostics() {
    const movieId = sourceDiagnostics.value?.movie?.id
    if (!movieId) return
    sourceDiagnostics.value = unwrapResponse(await api.getSupplementMovieSources(movieId), {})
    manualContentId.value = sourceDiagnostics.value?.movie?.matched_content_id || ''
    await refreshMovies()
  }

  async function manualMatchMovie(candidateContentId = '') {
    const movieId = sourceDiagnostics.value?.movie?.id
    const contentId = String(candidateContentId || manualContentId.value || '').trim()
    if (!movieId || !contentId || manualActionLoading.value) return
    manualActionLoading.value = true
    try {
      await api.matchSupplementMovie(movieId, contentId, '人工确认匹配')
      ElMessage.success('已确认匹配')
      await reloadCurrentDiagnostics()
    } catch (error) {
      ElMessage.error(`确认匹配失败：${errorMessage(error)}`)
      console.error('Manual match failed:', error)
    } finally {
      manualActionLoading.value = false
    }
  }

  async function manualIgnoreMovie() {
    const movieId = sourceDiagnostics.value?.movie?.id
    if (!movieId || manualActionLoading.value) return
    manualActionLoading.value = true
    try {
      await api.ignoreSupplementMovie(movieId, '人工忽略')
      ElMessage.success('已忽略该补全影片')
      await reloadCurrentDiagnostics()
    } catch (error) {
      ElMessage.error(`忽略失败：${errorMessage(error)}`)
      console.error('Manual ignore failed:', error)
    } finally {
      manualActionLoading.value = false
    }
  }

  async function manualUnmatchMovie() {
    const movieId = sourceDiagnostics.value?.movie?.id
    if (!movieId || manualActionLoading.value) return
    manualActionLoading.value = true
    try {
      await api.unmatchSupplementMovie(movieId, '人工解除匹配')
      ElMessage.success('已解除匹配')
      await reloadCurrentDiagnostics()
    } catch (error) {
      ElMessage.error(`解除匹配失败：${errorMessage(error)}`)
      console.error('Manual unmatch failed:', error)
    } finally {
      manualActionLoading.value = false
    }
  }

  const sourceHealthRows = computed(() => {
    const budgets = new Map((sourceBudgets.value || []).map(item => [item.source, item]))
    return (sourceHealth.value || []).map(source => ({
      ...source,
      budget: budgets.get(source.source) || null,
    }))
  })

  const providerSourceOptions = computed(() => [
    { value: '', label: '默认样本' },
    ...sourceHealthRows.value.map(source => ({
      value: source.source,
      label: source.display_name || source.source,
    })),
  ])

  const isGfriendsAvatarJobRunning = computed(() => {
    const status = gfriendsAvatarJob.value?.status
    return status === 'queued' || status === 'running'
  })

  async function loadGfriendsAvatarJob() {
    try {
      const data = unwrapResponse(await api.listSupplementJobs({ page: 1, page_size: 1, source: 'gfriends' }), {})
      gfriendsAvatarJob.value = (data.data || [])[0] || null
    } catch (error) {
      sourceHealthError.value = errorMessage(error)
      console.error('Load gfriends avatar job failed:', error)
    }
  }

  async function loadProviderSmokeRuns() {
    try {
      providerSmokeRuns.value = unwrapResponse(await api.listSupplementProviderSmokeRuns(5, providerSmokeForm.value.source), [])
    } catch (error) {
      sourceHealthError.value = errorMessage(error)
      console.error('Load provider smoke history failed:', error)
    }
  }

  async function loadSourceHealth({ silent = false } = {}) {
    if (!silent) sourceHealthLoading.value = true
    sourceHealthError.value = ''
    try {
      const [healthResp, budgetResp, smokeRunsResp] = await Promise.all([
        api.listSupplementSourcesHealth(),
        api.listSupplementSourcesBudgets(),
        api.listSupplementProviderSmokeRuns(5, providerSmokeForm.value.source),
      ])
      sourceHealth.value = unwrapResponse(healthResp, [])
      sourceBudgets.value = unwrapResponse(budgetResp, [])
      providerSmokeRuns.value = unwrapResponse(smokeRunsResp, [])
    } catch (error) {
      sourceHealthError.value = errorMessage(error)
      console.error('Load source health failed:', error)
    } finally {
      if (!silent) sourceHealthLoading.value = false
    }
  }

  async function runProviderSmoke() {
    if (providerSmokeLoading.value) return
    const source = (providerSmokeForm.value.source || '').trim()
    const sourceMovieId = (providerSmokeForm.value.sourceMovieId || '').trim()
    if (sourceMovieId && !source) {
      ElMessage.warning('自定义样本需要先选择来源')
      return
    }
    const payload = {}
    if (source) payload.source = source
    if (sourceMovieId) {
      payload.source_movie_id = sourceMovieId
      payload.name = `${source} ${sourceMovieId}`
    }
    providerSmokeLoading.value = true
    try {
      providerSmokeReport.value = unwrapResponse(await api.runSupplementProviderSmoke(payload), {})
      await loadProviderSmokeRuns()
    } catch (error) {
      sourceHealthError.value = errorMessage(error)
      console.error('Run provider smoke failed:', error)
    } finally {
      providerSmokeLoading.value = false
    }
  }

  async function pauseSource(source) {
    if (!source || sourceActionLoading.value) return
    sourceActionLoading.value = source
    try {
      await api.pauseSupplementSource(source, 'manual pause from supplement management', 24 * 60)
      await loadSourceHealth()
    } catch (error) {
      sourceHealthError.value = errorMessage(error)
      console.error('Pause source failed:', error)
    } finally {
      sourceActionLoading.value = ''
    }
  }

  async function resumeSource(source) {
    if (!source || sourceActionLoading.value) return
    sourceActionLoading.value = source
    try {
      await api.resumeSupplementSource(source)
      await loadSourceHealth()
    } catch (error) {
      sourceHealthError.value = errorMessage(error)
      console.error('Resume source failed:', error)
    } finally {
      sourceActionLoading.value = ''
    }
  }

  async function recheckSource(source) {
    if (!source || sourceActionLoading.value) return
    sourceActionLoading.value = source
    try {
      const data = unwrapResponse(await api.checkSupplementSource(source), {})
      if (data.reachable) {
        ElMessage.success(`${source} 可访问，已恢复`)
      } else {
        ElMessage.warning(`${source} 不可用：${data.error_type || data.error || '探活失败'}`)
      }
      await loadSourceHealth()
    } catch (error) {
      sourceHealthError.value = errorMessage(error)
      ElMessage.error(`检查 ${source} 失败：${errorMessage(error)}`)
      console.error('Recheck source failed:', error)
    } finally {
      sourceActionLoading.value = ''
    }
  }

  async function syncGfriendsAvatars() {
    if (gfriendsAvatarSyncing.value || isGfriendsAvatarJobRunning.value) return
    gfriendsAvatarSyncing.value = true
    try {
      const data = unwrapResponse(await api.startGfriendsAvatarSyncJob(), {})
      ElMessage.success(data.existing ? '已有头像同步任务，已切换到任务状态' : '已加入头像同步队列')
      await loadGfriendsAvatarJob()
    } catch (error) {
      sourceHealthError.value = errorMessage(error)
      console.error('Start gfriends avatar sync failed:', error)
    } finally {
      gfriendsAvatarSyncing.value = false
    }
  }

  function sourceHealthLabel(status) {
    const map = { healthy: '健康', degraded: '降级', cooling_down: '冷却中', paused: '已暂停', unknown: '未检测' }
    return map[status] || status || '未检测'
  }

  function sourceHealthDetail(source) {
    if (!source) return ''
    const failures = source.consecutive_failures ? `连续失败 ${source.consecutive_failures}` : '无连续失败'
    if (source.cooldown_until) return `${failures} · 冷却至 ${new Date(source.cooldown_until).toLocaleTimeString()}`
    return `${failures} · 成功 ${source.success_count || 0} / 失败 ${source.failure_count || 0}`
  }

  function sourceBudgetLabel(budget) {
    if (!budget) return '预算状态未加载'
    const lock = budget.global_lock_enabled ? '全局锁已启用' : '仅本进程'
    return `${lock} · 本进程 ${budget.local_active || 0} 个请求`
  }

  function smokeRunLabel(run) {
    const req = run?.request || {}
    if (req.source_movie_id) return `${req.source || '来源'} · ${req.source_movie_id}`
    if (req.source) return `${req.source} 默认样本`
    if (req.samples?.length) return `${req.samples.length} 个样本`
    return '默认样本'
  }

  function fieldLabel(fieldName) {
    const map = {
      title: '标题',
      release_date: '发行日',
      runtime_mins: '时长',
      cover_url: '封面',
      cover_thumb_url: '缩略图',
      maker_name: '厂商',
      label_name: '厂牌',
      series_name: '系列',
      category_names: '分类',
      actor_names: '演员',
      summary: '简介',
      score: '评分',
      sample_image_urls: '样张',
      sample_movie_url: '预告',
      source_url: '来源链接',
      display_number: '展示番号',
      normalized_number: '规范番号',
    }
    return map[fieldName] || fieldName
  }

  function fieldValuePreview(value) {
    if (!value) return ''
    const text = String(value)
    return text.length > 140 ? `${text.slice(0, 140)}...` : text
  }

  function manualActionLabel(action) {
    const map = { match: '确认匹配', ignore: '忽略', unmatch: '解除匹配' }
    return map[action] || action || '人工操作'
  }

  function formatActionTime(value) {
    if (!value) return ''
    return new Date(value).toLocaleString()
  }

  function statusLabel(status) {
    const map = { queued: '排队中', running: '运行中', succeeded: '已完成', failed: '失败', idle: '待开始' }
    return map[status] || status || '待开始'
  }

  return {
    jobs,
    jobsLoading,
    jobsError,
    jobsTotalCount,
    jobsTotalPages,
    recovering,
    loadJobs,
    retryJob,
    cancelJob,
    recoverStale,
    statusLabel,
    supplementMovies,
    moviesLoading,
    moviesTotalCount,
    moviesTotalPages,
    enrichingMovies,
    batchEnriching,
    candidateImporting,
    loadMovies,
    movieMatchClass,
    movieMatchLabel,
    movieCover,
    movieCategories,
    movieFieldChips,
    workspaceMovieFieldGapCount,
    workspacePendingCandidateCount,
    workspaceDetailTargetCount,
    enrichMovie,
    batchEnrichMovies,
    createDownloadCandidates,
    sourceDiagnosticsOpen,
    sourceDiagnosticsLoading,
    sourceDiagnostics,
    manualContentId,
    manualActionLoading,
    openMovieSources,
    closeMovieSources,
    reloadCurrentDiagnostics,
    manualMatchMovie,
    manualIgnoreMovie,
    manualUnmatchMovie,
    sourceHealthRows,
    sourceHealthLoading,
    sourceActionLoading,
    providerSmokeLoading,
    providerSmokeReport,
    providerSmokeForm,
    providerSmokeRuns,
    providerSourceOptions,
    gfriendsAvatarJob,
    gfriendsAvatarSyncing,
    isGfriendsAvatarJobRunning,
    loadGfriendsAvatarJob,
    loadSourceHealth,
    loadProviderSmokeRuns,
    runProviderSmoke,
    pauseSource,
    resumeSource,
    recheckSource,
    syncGfriendsAvatars,
    sourceHealthLabel,
    sourceHealthDetail,
    sourceBudgetLabel,
    smokeRunLabel,
    fieldLabel,
    fieldValuePreview,
    manualActionLabel,
    formatActionTime,
  }
}
