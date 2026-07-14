// Single source of truth for the download-candidate workspace.
//
// API calls and routing semantics are preserved from the original workspace;
// views/Candidates.vue is now the only UI owner.

import { reactive, ref, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api from '../../api'
import { ElMessage } from '../../utils/message.js'
import { requestConfirm } from '../../utils/confirmDialog'
import * as candidatePresentation from './candidatePresentation'

const cleanObject = (target) => {
  Object.keys(target).forEach(key => {
    if (target[key] === undefined || target[key] === '' || target[key] === null) delete target[key]
  })
  return target
}

const eventLabels = {
  without_event: '未处理',
  magnet_enrich_failed: '补磁力失败',
  magnet_enriched: '已补磁力',
  policy_skipped: '策略跳过',
  process_failed: '处理失败',
  approve_failed: '批准失败',
  supplement_imported: '补全导入',
}

function initialCandidateStats() {
  return {
    candidate: 0,
    approved: 0,
    rejected: 0,
    sent: 0,
    failed: 0,
    needs_magnet: 0,
    by_source: {},
    candidate_by_source: {},
  }
}

function initialFilter(query = {}) {
  return {
    status: query.status || 'candidate',
    source: query.source || '',
    actress_id: query.actress_id || '',
    q: query.q || '',
    needs_magnet: query.needs_magnet === '1' ? true : (query.needs_magnet === '0' ? false : null),
    missing_cover: query.missing_cover === '1',
    latest_event_action: query.latest_event_action || '',
  }
}

export function useDownloadCandidates(options = {}) {
  const {
    routePath = '/candidates',
    syncRoute = true,
    baseQuery = () => ({}),
    enabled = ref(true),
  } = options

  const route = useRoute()
  const router = useRouter()

  // === Reactive state ===
  const candidates = ref([])
  const candidateStats = ref(initialCandidateStats())
  const candidatePage = ref(Number(route.query.page || 1) || 1)
  const candidatePageSize = ref(50)
  const candidateTotal = ref(0)
  const candidateTotalPages = ref(1)
  const selectingCandidates = ref(false)
  const selectedCandidateIds = ref([])
  const bulkCandidateLoading = ref(false)
  const candidateBatchProcessing = ref('')
  const candidateRuns = ref([])
  const candidateRunsLoading = ref(false)
  const candidateMutations = ref({})
  const candidateFilter = reactive(initialFilter(route.query))
  const magnetEditor = reactive({ open: false, candidate: null, value: '' })
  const candidateDetail = reactive({ open: false, loading: false, data: null })

  // === Computed ===
  const filteredCandidates = computed(() => candidates.value)

  const candidateFilterLedger = computed(() => {
    if (!enabled.value) return []
    const items = [{ key: 'status', label: candidatePresentation.candidateStatusLabel(candidateFilter.status || 'candidate') }]
    if (candidateFilter.needs_magnet === true) items.push({ key: 'needs_magnet', label: '待补磁力' })
    if (candidateFilter.needs_magnet === false) items.push({ key: 'ready', label: '可批准' })
    if (candidateFilter.missing_cover) items.push({ key: 'missing_cover', label: '缺封面' })
    if (candidateFilter.source) items.push({ key: 'source', label: `来源 ${candidatePresentation.candidateSourceLabel(candidateFilter.source)}` })
    if (candidateFilter.latest_event_action) items.push({ key: 'event', label: `最近 ${candidateEventActionLabel(candidateFilter.latest_event_action)}` })
    if (candidateFilter.actress_id) items.push({ key: 'actor', label: `演员 ${candidateFilter.actress_id}` })
    if (candidateFilter.q) items.push({ key: 'q', label: `搜索 ${candidateFilter.q}` })
    items.push({ key: 'total', label: `当前 ${candidateTotal.value} 条` })
    return items
  })

  const visibleMagnetTargetCount = computed(() => filteredCandidates.value
    .filter(candidate => (candidate.status === 'candidate' || candidate.status === 'failed') && !candidate.magnet)
    .length)

  const candidateRepairScopeLabel = computed(() => {
    if (candidateFilter.needs_magnet === true) return '待补磁力修复'
    if (candidateFilter.missing_cover) return '缺封面候选修复'
    if (candidateFilter.latest_event_action) return `最近 ${candidateEventActionLabel(candidateFilter.latest_event_action)}`
    return ''
  })

  const candidateRepairScope = computed(() => {
    const scopeLabel = candidateRepairScopeLabel.value
    if (!scopeLabel) return null
    return {
      scopeLabel,
      total: candidateTotal.value,
      visibleCount: filteredCandidates.value.length,
      visibleMagnetTargets: visibleMagnetTargetCount.value,
    }
  })

  const processVisibleLabel = computed(() => {
    if (candidateBatchProcessing.value === 'dry-run') return '预演中...'
    if (candidateBatchProcessing.value === 'process') return '处理中...'
    return '按策略处理当前'
  })

  const candidateLatestEventFilters = computed(() => {
    const counts = candidateStats.value.latest_event_by_action || {}
    return Object.entries(counts)
      .filter(([, count]) => Number(count || 0) > 0)
      .map(([action, count]) => ({
        action,
        count: Number(count || 0),
        label: candidateEventActionLabel(action),
      }))
  })

  // === Helpers ===
  function candidateEventActionLabel(action) {
    return eventLabels[action] || action
  }

  function isCandidateMutating(id) {
    return Boolean(candidateMutations.value[id]) || bulkCandidateLoading.value || Boolean(candidateBatchProcessing.value)
  }

  function setCandidateMutation(id, action) {
    candidateMutations.value = { ...candidateMutations.value, [id]: action }
  }

  function clearCandidateMutation(id) {
    const next = { ...candidateMutations.value }
    delete next[id]
    candidateMutations.value = next
  }

  function candidateFilterPayload(overrides = {}) {
    return cleanObject({
      status: candidateFilter.status || 'candidate',
      source: candidateFilter.source || undefined,
      actress_id: candidateFilter.actress_id ? Number(candidateFilter.actress_id) : undefined,
      q: candidateFilter.q || undefined,
      needs_magnet: candidateFilter.needs_magnet,
      missing_cover: candidateFilter.missing_cover || undefined,
      latest_event_action: candidateFilter.latest_event_action || undefined,
      limit: candidates.value.length || 50,
      ...overrides,
    })
  }

  function processPreviewMessage(preview = {}) {
    const counts = preview.counts || {}
    return `预演 ${preview.total || 0} 个：可直接下发 ${counts.would_send || 0}，需补磁力 ${counts.would_enrich_magnet || 0}，受上限跳过 ${counts.would_skip_limit || 0}。`
  }

  function processPreviewDetails(counts = {}, limits = {}) {
    const skipped = Object.entries(counts)
      .filter(([action]) => action.startsWith('skipped') || action === 'manual_required')
      .reduce((sum, [, value]) => sum + Number(value || 0), 0)
    const remaining = limits.remaining === null || limits.remaining === undefined ? '不限' : limits.remaining
    return `策略跳过 ${skipped}。单次上限 ${limits.per_run || '不限'}，24 小时上限 ${limits.per_24h || '不限'}，当前剩余额度 ${remaining}。`
  }

  // === Route sync ===
  function candidateRouteQuery(overrides = {}) {
    const filter = { ...candidateFilter, page: candidatePage.value, ...overrides }
    const query = { ...baseQuery() }
    if (filter.status) query.status = filter.status
    if (filter.source) query.source = filter.source
    if (filter.actress_id) query.actress_id = filter.actress_id
    if (filter.q) query.q = filter.q
    if (filter.needs_magnet === true) query.needs_magnet = '1'
    if (filter.needs_magnet === false) query.needs_magnet = '0'
    if (filter.missing_cover) query.missing_cover = '1'
    if (filter.latest_event_action) query.latest_event_action = filter.latest_event_action
    if (filter.page && Number(filter.page) > 1) query.page = String(Number(filter.page))
    return query
  }

  function shouldSyncRoute() {
    return syncRoute && enabled.value
  }

  function pushCandidateRoute(overrides = {}) {
    if (!shouldSyncRoute()) return
    const next = cleanObject({ ...candidateRouteQuery(overrides) })
    if (JSON.stringify(next) === JSON.stringify(route.query || {})) return
    router.push({ path: routePath, query: next }).catch(() => {})
  }

  function replaceCandidateRoute(overrides = {}) {
    if (!shouldSyncRoute()) return
    const next = cleanObject({ ...candidateRouteQuery(overrides) })
    if (JSON.stringify(next) === JSON.stringify(route.query || {})) return
    router.replace({ path: routePath, query: next }).catch(() => {})
  }

  function syncCandidateRoute() {
    replaceCandidateRoute()
  }

  function applyRouteQuery(query = {}) {
    let changed = false
    const nextPage = Number(query.page || 1) || 1
    if (candidatePage.value !== nextPage) { candidatePage.value = nextPage; changed = true }
    const nextFilter = initialFilter(query)
    if (JSON.stringify(nextFilter) !== JSON.stringify({ ...candidateFilter })) {
      Object.assign(candidateFilter, nextFilter)
      changed = true
    }
    return changed
  }

  // === Filter mutators ===
  function updateCandidateSearch(value) {
    candidateFilter.q = value
  }

  function submitCandidateSearch() {
    pushCandidateRoute({ q: candidateFilter.q, page: 1 })
  }

  function setCandidateStatus(status) {
    pushCandidateRoute({ status, needs_magnet: null, page: 1 })
  }

  function setNeedsMagnet(needs) {
    pushCandidateRoute({ status: 'candidate', needs_magnet: needs, page: 1 })
  }

  function setCandidateSource(source) {
    pushCandidateRoute({ source, page: 1 })
  }

  function setCandidateLatestEvent(action) {
    pushCandidateRoute({ latest_event_action: action, page: 1 })
  }

  function goCandidatePage(page) {
    const nextPage = Math.max(1, Math.min(candidateTotalPages.value, Number(page) || 1))
    if (nextPage !== candidatePage.value) pushCandidateRoute({ page: nextPage })
  }

  function applyCandidateRunFilters(run, overrides = {}) {
    const filters = { ...(run?.filters || {}), ...overrides }
    pushCandidateRoute({
      status: filters.status || 'candidate',
      source: filters.source || '',
      actress_id: filters.actress_id || '',
      q: filters.q || '',
      needs_magnet: filters.needs_magnet === undefined ? null : filters.needs_magnet,
      missing_cover: Boolean(filters.missing_cover),
      latest_event_action: filters.latest_event_action || '',
      page: 1,
    })
  }

  // === Selection ===
  function toggleCandidateSelection() {
    selectingCandidates.value = !selectingCandidates.value
    if (!selectingCandidates.value) selectedCandidateIds.value = []
  }

  function toggleCandidateSelected(id) {
    selectedCandidateIds.value = selectedCandidateIds.value.includes(id)
      ? selectedCandidateIds.value.filter(item => item !== id)
      : [...selectedCandidateIds.value, id]
  }

  function selectAllVisibleCandidates() {
    selectedCandidateIds.value = [...new Set([...selectedCandidateIds.value, ...candidates.value.map(c => c.id)])]
  }

  function clearCandidateSelection() {
    selectedCandidateIds.value = []
  }

  // === Magnet editor / detail dialogs ===
  function editCandidateMagnet(candidate) {
    if (!isCandidateMutating(candidate.id)) {
      magnetEditor.open = true
      magnetEditor.candidate = candidate
      magnetEditor.value = candidate.magnet || ''
    }
  }

  function closeMagnetEditor() {
    if (!magnetEditor.candidate || !isCandidateMutating(magnetEditor.candidate.id)) {
      magnetEditor.open = false
      magnetEditor.candidate = null
      magnetEditor.value = ''
    }
  }

  function updateMagnetEditorValue(value) {
    magnetEditor.value = value
  }

  async function openCandidateDetail(candidate) {
    candidateDetail.open = true
    candidateDetail.loading = true
    candidateDetail.data = candidate
    try {
      const resp = await api.getDownloadCandidate(candidate.id)
      candidateDetail.loading = false
      candidateDetail.data = resp.data.data
    } catch (e) {
      console.error('Load candidate detail failed:', e)
      candidateDetail.loading = false
      candidateDetail.data = candidate
    }
  }

  function closeCandidateDetail() {
    candidateDetail.open = false
    candidateDetail.loading = false
    candidateDetail.data = null
  }

  // === API-driven methods ===
  async function loadCandidates() {
    try {
      const params = {}
      if (candidateFilter.status) params.status = candidateFilter.status
      if (candidateFilter.source) params.source = candidateFilter.source
      if (candidateFilter.actress_id) params.actress_id = candidateFilter.actress_id
      if (candidateFilter.q) params.q = candidateFilter.q
      if (candidateFilter.needs_magnet !== null) params.needs_magnet = candidateFilter.needs_magnet
      if (candidateFilter.missing_cover) params.missing_cover = candidateFilter.missing_cover
      if (candidateFilter.latest_event_action) params.latest_event_action = candidateFilter.latest_event_action
      params.page = candidatePage.value
      params.page_size = candidatePageSize.value
      params.include_stats = false
      const resp = await api.listDownloadCandidates(params)
      candidates.value = resp.data.data || []
      candidateTotal.value = Number(resp.data.total || candidates.value.length) || 0
      candidateTotalPages.value = Number(resp.data.total_pages || 1) || 1
      selectedCandidateIds.value = selectedCandidateIds.value.filter(id => candidates.value.some(c => c.id === id))
      syncCandidateRoute()
      await loadCandidateSummary()
    } catch (e) {
      console.error('Failed to load candidates:', e)
    }
  }

  async function loadCandidateSummary() {
    try {
      const resp = await api.getDownloadCandidateSummary({ status: 'candidate', include_sources: true })
      candidateStats.value = resp.data || candidateStats.value
    } catch (e) {
      console.error('Failed to load candidate summary:', e)
    }
  }

  async function loadCandidateRuns() {
    candidateRunsLoading.value = true
    try {
      const resp = await api.listDownloadCandidateRuns(5)
      candidateRuns.value = resp.data.data || []
    } catch (e) {
      console.error('Failed to load candidate runs:', e)
    } finally {
      candidateRunsLoading.value = false
    }
  }

  async function approveCandidate(candidate) {
    if (isCandidateMutating(candidate.id)) return
    const confirmed = await requestConfirm({
      title: '批准下载候选',
      message: `确认批准 ${candidate.dvd_id || candidate.content_id} 并下发下载？`,
      details: candidate.magnet
        ? '会创建真实下载任务并发送到当前默认下载器。'
        : '该候选没有磁力链接，批准可能失败或需要先补磁力。',
      confirmText: '批准',
    })
    if (!confirmed) return
    setCandidateMutation(candidate.id, 'approve')
    try {
      await api.approveDownloadCandidate(candidate.id)
      await loadCandidates()
    } catch (e) {
      console.error('Approve candidate failed:', e)
    } finally {
      clearCandidateMutation(candidate.id)
    }
  }

  async function rejectCandidate(candidate) {
    if (isCandidateMutating(candidate.id)) return
    const confirmed = await requestConfirm({
      title: '拒绝下载候选',
      message: `确认拒绝 ${candidate.dvd_id || candidate.content_id}？`,
      details: candidate.title || '',
      confirmText: '拒绝',
      tone: 'danger',
    })
    if (!confirmed) return
    setCandidateMutation(candidate.id, 'reject')
    try {
      await api.rejectDownloadCandidate(candidate.id)
      await loadCandidates()
    } catch (e) {
      console.error('Reject candidate failed:', e)
    } finally {
      clearCandidateMutation(candidate.id)
    }
  }

  async function processCandidate(candidate) {
    if (isCandidateMutating(candidate.id)) return
    const confirmed = await requestConfirm({
      title: '按策略处理候选',
      message: `确认按当前策略处理 ${candidate.dvd_id || candidate.content_id}？`,
      details: '可能会补充磁力并下发到下载器；不满足策略时会保持候选状态。',
      confirmText: '处理',
    })
    if (!confirmed) return
    setCandidateMutation(candidate.id, 'process')
    try {
      const action = (await api.processDownloadCandidate(candidate.id, { enrich: true })).data?.action
      if (action === 'sent') ElMessage?.success?.('候选已下发下载')
      else if (action === 'manual_required') ElMessage?.info?.('当前为人工批准策略')
      else if (action?.startsWith('skipped')) ElMessage?.info?.('候选未满足策略条件')
      else if (action?.startsWith('failed')) ElMessage?.error?.('候选处理失败')
      await loadCandidates()
    } catch (e) {
      console.error('Process candidate failed:', e)
    } finally {
      clearCandidateMutation(candidate.id)
    }
  }

  async function enrichCandidateMagnet(candidate) {
    if (isCandidateMutating(candidate.id)) return
    setCandidateMutation(candidate.id, 'enrich')
    try {
      const action = (await api.enrichDownloadCandidateMagnet(candidate.id)).data?.action
      if (action === 'magnet_enriched') ElMessage?.success?.('已补充 magnet')
      else if (action === 'magnet_not_found') ElMessage?.warning?.('未找到可用 magnet')
      else if (action === 'already_has_magnet') ElMessage?.info?.('候选已有 magnet')
      await loadCandidates()
    } catch (e) {
      console.error('Enrich candidate magnet failed:', e)
    } finally {
      clearCandidateMutation(candidate.id)
    }
  }

  async function bulkRejectCandidates() {
    if (selectedCandidateIds.value.length === 0 || bulkCandidateLoading.value) return
    const confirmed = await requestConfirm({
      title: '批量拒绝候选',
      message: `确认拒绝 ${selectedCandidateIds.value.length} 个下载候选？`,
      details: '拒绝后可在已拒绝筛选中批量恢复。',
      confirmText: '拒绝',
      tone: 'danger',
    })
    if (!confirmed) return
    bulkCandidateLoading.value = true
    try {
      await api.bulkRejectDownloadCandidates(selectedCandidateIds.value)
      selectedCandidateIds.value = []
      await loadCandidates()
    } catch (e) {
      console.error('Bulk reject candidates failed:', e)
    } finally {
      bulkCandidateLoading.value = false
    }
  }

  async function bulkRestoreCandidates() {
    if (selectedCandidateIds.value.length === 0 || bulkCandidateLoading.value) return
    bulkCandidateLoading.value = true
    try {
      await api.bulkRestoreDownloadCandidates(selectedCandidateIds.value)
      selectedCandidateIds.value = []
      await loadCandidates()
    } catch (e) {
      console.error('Bulk restore candidates failed:', e)
    } finally {
      bulkCandidateLoading.value = false
    }
  }

  async function submitMagnetEditor() {
    const candidate = magnetEditor.candidate
    const magnet = magnetEditor.value.trim()
    if (!candidate || !magnet || isCandidateMutating(candidate.id)) return
    setCandidateMutation(candidate.id, 'magnet')
    try {
      await api.updateDownloadCandidateMagnet(candidate.id, magnet)
      closeMagnetEditor()
      await loadCandidates()
    } catch (e) {
      console.error('Update candidate magnet failed:', e)
    } finally {
      clearCandidateMutation(candidate.id)
    }
  }

  async function enrichVisibleCandidateMagnets() {
    if (candidateBatchProcessing.value) return
    const targets = candidates.value.filter(candidate => (candidate.status === 'candidate' || candidate.status === 'failed') && !candidate.magnet)
    if (!targets.length) {
      ElMessage?.info?.('当前列表没有待补磁力的候选')
      return
    }
    const confirmed = await requestConfirm({
      title: '批量补充磁力',
      message: `确认为当前列表中的 ${targets.length} 个下载候选查找并写入磁力？当前筛选总量 ${candidateTotal.value} 个。`,
      details: '会逐个访问候选的磁力来源，并把找到的磁力保存到候选记录。',
      confirmText: '开始补磁力',
    })
    if (!confirmed) return
    candidateBatchProcessing.value = 'enrich'
    try {
      let enriched = 0
      for (const candidate of targets) {
        if ((await api.enrichDownloadCandidateMagnet(candidate.id)).data?.action === 'magnet_enriched') enriched += 1
      }
      ElMessage?.success?.(`已检查 ${targets.length} 个，补磁力 ${enriched} 个`)
      await loadCandidates()
    } catch (e) {
      console.error('Batch enrich candidates failed:', e)
    } finally {
      candidateBatchProcessing.value = ''
    }
  }

  async function processVisibleCandidates() {
    if (candidateBatchProcessing.value) return
    candidateBatchProcessing.value = 'dry-run'
    let preview
    try {
      preview = (await api.processDownloadCandidates(candidateFilterPayload({ enrich: true, dry_run: true }))).data || {}
    } catch (e) {
      console.error('Preview candidate processing failed:', e)
      candidateBatchProcessing.value = ''
      return
    }
    const confirmed = await requestConfirm({
      title: '按策略处理候选',
      message: processPreviewMessage(preview),
      details: processPreviewDetails(preview.counts || {}, preview.limits || {}),
      confirmText: '处理',
    })
    if (!confirmed) {
      candidateBatchProcessing.value = ''
      return
    }
    candidateBatchProcessing.value = 'process'
    try {
      const resp = await api.processDownloadCandidates(candidateFilterPayload({ enrich: true }))
      const counts = resp.data?.counts || {}
      const skipped = (counts.manual_required || 0) + (counts.skipped_source || 0) + (counts.skipped_missing_magnet || 0) + (counts.skipped_status || 0)
      ElMessage?.success?.(`处理 ${resp.data?.total || 0} 个：下发 ${counts.sent || 0}，跳过 ${skipped}`)
      await loadCandidates()
      await loadCandidateRuns()
    } catch (e) {
      console.error('Batch process candidates failed:', e)
    } finally {
      candidateBatchProcessing.value = ''
    }
  }

  async function retryFailedCandidateRun(run) {
    if (!run?.id || candidateBatchProcessing.value) return
    const confirmed = await requestConfirm({
      title: '重试失败候选',
      message: `确认重试本次处理中的 ${run.failed || 0} 个失败候选？`,
      details: '会复用当时策略并重新补磁力/下发，仍失败的候选会留在失败队列。',
      confirmText: '重试',
    })
    if (!confirmed) return
    candidateBatchProcessing.value = 'retry-run'
    try {
      const resp = await api.retryDownloadCandidateRunFailed(run.id, { enrich: true })
      const counts = resp.data?.counts || {}
      ElMessage?.success?.(`已重试 ${resp.data?.total || 0} 个：下发 ${counts.sent || 0}，失败 ${counts.failed_downloader || 0}`)
      await loadCandidates()
      await loadCandidateRuns()
    } catch (e) {
      console.error('Retry failed candidate run failed:', e)
    } finally {
      candidateBatchProcessing.value = ''
    }
  }

  function goCandidateActor(candidate) {
    if (!candidate.actress_id) return
    const name = candidate.actress_name || candidate.actress_id
    router.push({
      path: `/actor/${encodeURIComponent(name)}`,
      query: { name, actress_id: candidate.actress_id },
    })
  }

  return {
    // state
    candidates,
    candidateStats,
    candidatePage,
    candidatePageSize,
    candidateTotal,
    candidateTotalPages,
    selectingCandidates,
    selectedCandidateIds,
    bulkCandidateLoading,
    candidateBatchProcessing,
    candidateRuns,
    candidateRunsLoading,
    candidateMutations,
    candidateFilter,
    magnetEditor,
    candidateDetail,
    // computed
    filteredCandidates,
    candidateFilterLedger,
    visibleMagnetTargetCount,
    candidateRepairScopeLabel,
    candidateRepairScope,
    processVisibleLabel,
    candidateLatestEventFilters,
    // helpers
    candidateEventActionLabel,
    isCandidateMutating,
    setCandidateMutation,
    clearCandidateMutation,
    candidateFilterPayload,
    processPreviewMessage,
    processPreviewDetails,
    // route sync
    candidateRouteQuery,
    pushCandidateRoute,
    replaceCandidateRoute,
    syncCandidateRoute,
    applyRouteQuery,
    // filter mutators
    updateCandidateSearch,
    submitCandidateSearch,
    setCandidateStatus,
    setNeedsMagnet,
    setCandidateSource,
    setCandidateLatestEvent,
    goCandidatePage,
    applyCandidateRunFilters,
    // selection
    toggleCandidateSelection,
    toggleCandidateSelected,
    selectAllVisibleCandidates,
    clearCandidateSelection,
    // magnet editor / detail
    editCandidateMagnet,
    closeMagnetEditor,
    updateMagnetEditorValue,
    openCandidateDetail,
    closeCandidateDetail,
    submitMagnetEditor,
    // API-driven methods
    loadCandidates,
    loadCandidateSummary,
    loadCandidateRuns,
    approveCandidate,
    rejectCandidate,
    processCandidate,
    enrichCandidateMagnet,
    bulkRejectCandidates,
    bulkRestoreCandidates,
    enrichVisibleCandidateMagnets,
    processVisibleCandidates,
    retryFailedCandidateRun,
    goCandidateActor,
  }
}
