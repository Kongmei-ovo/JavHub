import axios from 'axios'
import { ElMessage } from '../utils/message.js'
import { apiErrorMessage } from '../utils/apiErrors.js'

const api = axios.create({
  baseURL: '/api'
})

const ERROR_TOAST_COOLDOWN_MS = 3000
const JAVINFO_IMPORT_CHUNK_SIZE = 8 * 1024 * 1024
const JAVINFO_IMPORT_CHUNK_RETRIES = 3
let lastErrorToast = { key: '', ts: 0 }

export function formatApiError(error, { service = '服务', action = '请求', fallback = '请稍后重试。' } = {}) {
  const status = error?.response?.status || 0
  const rawMessage = apiErrorMessage(error, fallback)
  const retryable = !status || status >= 500 || status === 408 || status === 429
  const serviceLabel = service
  return {
    status,
    retryable,
    serviceLabel,
    rawMessage,
    message: `${serviceLabel}${action}失败：${retryable ? fallback : rawMessage}`,
  }
}

function numericPathSegment(value, label) {
  const text = String(value ?? '').trim()
  if (!/^\d+$/.test(text)) {
    throw new TypeError(`${label} must be a numeric id`)
  }
  return encodeURIComponent(text)
}

function pathSegment(value, label) {
  const text = String(value ?? '').trim()
  if (!text) {
    throw new TypeError(`${label} is required`)
  }
  return encodeURIComponent(text)
}

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms))
}

function chunkUploadProgress(onUploadProgress, loaded, total) {
  if (typeof onUploadProgress === 'function') {
    onUploadProgress({ loaded, total })
  }
}

function isUploadCompleteStatus(status) {
  return ['uploaded', 'restoring', 'stopping', 'swapping', 'restarting', 'migrating', 'completed'].includes(status)
}

async function retryChunkUpload(request, refreshUploadedBytes) {
  let lastError = null
  for (let attempt = 1; attempt <= JAVINFO_IMPORT_CHUNK_RETRIES; attempt += 1) {
    try {
      return await request()
    } catch (error) {
      lastError = error
      if (typeof refreshUploadedBytes === 'function') {
        const refreshed = await refreshUploadedBytes()
        if (refreshed !== null && refreshed !== undefined) {
          return { data: { uploaded_bytes: refreshed } }
        }
      }
      if (attempt === JAVINFO_IMPORT_CHUNK_RETRIES) break
      await sleep(250 * attempt)
    }
  }
  throw lastError
}

async function completeChunkedUpload(jobId, total) {
  let lastError = null
  for (let attempt = 1; attempt <= JAVINFO_IMPORT_CHUNK_RETRIES; attempt += 1) {
    try {
      return await api.post(`/v1/javinfo/imports/jobs/${jobId}/upload/complete`, null, { silentError: true })
    } catch (error) {
      lastError = error
      const statusResp = await api.get(`/v1/javinfo/imports/jobs/${jobId}`, { silentError: true })
      const job = statusResp.data || {}
      if (isUploadCompleteStatus(job.status) && Number(job.uploaded_bytes || 0) >= total) {
        return statusResp
      }
      if (attempt === JAVINFO_IMPORT_CHUNK_RETRIES) break
      await sleep(250 * attempt)
    }
  }
  throw lastError
}

// ========== 全局错误拦截 ==========
api.interceptors.response.use(
  response => response,
  error => {
    if (!error.config?.silentError) {
      const errMsg = apiErrorMessage(error)
      const key = `${error.response?.status || 'network'}:${errMsg}`
      const now = Date.now()
      if (key !== lastErrorToast.key || now - lastErrorToast.ts > ERROR_TOAST_COOLDOWN_MS) {
        ElMessage.error(errMsg)
        lastErrorToast = { key, ts: now }
      }
      console.error('API Error:', error.response?.status, errMsg)
    }
    return Promise.reject(error)
  }
)

export default {
  formatApiError,

  // ========== 视频搜索 & 详情 (JavInfoApi) ==========

  searchVideos(params = {}) {
    return api.get('/v1/videos/search', { params })
  },

  checkLibrary(code) {
    return api.get(`/v1/videos/${pathSegment(code, 'code')}`)
  },

  listVideos(page = 1, page_size = 20, options = {}) {
    return api.get('/v1/videos', { params: { page, page_size, include_total: false, ...options } })
  },

  getVideo(contentId, options = {}) {
    const serviceCode = String(options.service_code || '').trim()
    const config = serviceCode ? { params: { service_code: serviceCode } } : undefined
    return api.get(`/v1/videos/${pathSegment(contentId, 'contentId')}`, config)
  },

  // ========== 演员 ==========

  listActresses(page = 1, page_size = 20, options = {}) {
    return api.get('/v1/actresses', { params: { page, page_size, ...options } })
  },

  getActress(actressId) {
    return api.get(`/v1/actresses/${numericPathSegment(actressId, 'actressId')}`)
  },

  getActressVideos(actressId, page = 1, page_size = 20, options = {}) {
    return api.get(`/v1/actresses/${numericPathSegment(actressId, 'actressId')}/videos`, {
      params: { page, page_size, include_total: false, ...options },
    })
  },

  batchGetActressVideos(ids, page = 1, page_size = 5) {
    return api.post('/v1/actresses/batch_videos', { ids, page, page_size })
  },

  // ========== 枚举数据 ==========

  listMakers(params = {}) {
    return api.get('/v1/makers', { params })
  },

  listSeries(page = 1, page_size = 20, options = {}) {
    return api.get('/v1/series', { params: { page, page_size, ...options } })
  },

  listCategories() {
    return api.get('/v1/categories', { silentError: true })
  },

  listLabels(params = {}) {
    return api.get('/v1/labels', { params })
  },

  listDirectors(params = {}) {
    return api.get('/v1/directors', { params })
  },

  listActors(params = {}) {
    return api.get('/v1/actors', { params })
  },

  listInventoryActors(params = {}) {
    return api.get('/inventory/actors', { params })
  },

  getLibraryOrganizeOverview(params = {}) {
    return api.get('/inventory/overview', { params })
  },

  getInventoryActor(actressId) {
    return api.get(`/inventory/actors/${numericPathSegment(actressId, 'actressId')}`)
  },

  getInventorySnapshotLatest() {
    return api.get('/inventory/snapshots/latest')
  },

  triggerInventoryJob(data) {
    return api.post('/inventory/jobs/trigger', data)
  },

  listInventoryJobs() {
    return api.get('/inventory/jobs')
  },

  listInventoryMissing(params = {}) {
    return api.get('/inventory/missing', { params })
  },

  fillInventoryVideo(contentId) {
    return api.post(`/inventory/fill/${pathSegment(contentId, 'contentId')}`)
  },

  fillAllInventoryVideos(params = {}) {
    return api.post('/inventory/fill-all', null, { params })
  },

  listAuthors(params = {}) {
    return api.get('/v1/authors', { params })
  },

  // ========== 下载管理 ==========

  getDownloads() {
    return api.get('/v1/downloads')
  },

  createDownload(data) {
    return api.post('/v1/downloads', data)
  },

  deleteDownload(taskId) {
    return api.delete(`/v1/downloads/${taskId}`)
  },

  listDownloaders() {
    return api.get('/v1/downloads/downloaders')
  },

  updateDownloaders(data) {
    return api.put('/v1/downloads/downloaders', data)
  },

  testDownloader(data) {
    return api.post('/v1/downloads/downloaders/test', data)
  },

  listDownloadCandidates(params = {}) {
    return api.get('/v1/downloads/candidates', { params })
  },

  getDownloadCandidateSummary(params = {}) {
    return api.get('/v1/downloads/candidates/summary', { params })
  },

  getDownloadCandidate(candidateId) {
    return api.get(`/v1/downloads/candidates/${candidateId}`)
  },

  listDownloadCandidateRuns(limit = 20) {
    return api.get('/v1/downloads/candidates/runs', { params: { limit } })
  },

  retryDownloadCandidateRunFailed(runId, payload = {}) {
    return api.post(`/v1/downloads/candidates/runs/${runId}/retry-failed`, payload)
  },

  createDownloadCandidate(data) {
    return api.post('/v1/downloads/candidates', data)
  },

  updateDownloadCandidateMagnet(candidateId, magnet, magnetSource = 'manual') {
    return api.put(`/v1/downloads/candidates/${candidateId}/magnet`, {
      magnet,
      magnet_source: magnetSource,
    })
  },

  enrichDownloadCandidateMagnet(candidateId) {
    return api.post(`/v1/downloads/candidates/${candidateId}/enrich-magnet`)
  },

  processDownloadCandidate(candidateId, payload = {}) {
    return api.post(`/v1/downloads/candidates/${candidateId}/process`, payload)
  },

  processDownloadCandidates(payload = {}) {
    return api.post('/v1/downloads/candidates/process', payload)
  },

  approveDownloadCandidate(candidateId) {
    return api.post(`/v1/downloads/candidates/${candidateId}/approve`)
  },

  rejectDownloadCandidate(candidateId) {
    return api.post(`/v1/downloads/candidates/${candidateId}/reject`)
  },

  bulkRejectDownloadCandidates(ids = []) {
    return api.post('/v1/downloads/candidates/bulk/reject', { ids })
  },

  bulkRestoreDownloadCandidates(ids = []) {
    return api.post('/v1/downloads/candidates/bulk/restore', { ids })
  },

  // ========== 订阅管理 ==========

  getSubscriptions() {
    return api.get('/v1/subscriptions')
  },

  addSubscription(data) {
    return api.post('/v1/subscriptions', data)
  },

  deleteSubscription(id) {
    return api.delete(`/v1/subscriptions/${id}`)
  },

  checkSubscriptions() {
    return api.post('/v1/subscriptions/check')
  },

  searchActors(keyword) {
    return api.get('/v1/subscriptions/search', { params: { q: keyword } })
  },

  checkSubscription(id) {
    return api.post(`/v1/subscriptions/${id}/check`)
  },

  getNewMovies(params = {}) {
    return api.get('/v1/subscriptions/new_movies', { params })
  },

  toggleSubscription(data) {
    return api.post('/v1/subscriptions/toggle', data)
  },

  updateSubscription(id, data) {
    return api.put(`/v1/subscriptions/${id}`, data)
  },

  getSubscriptionStatus(actressId) {
    return api.get(`/v1/subscriptions/status/${actressId}`)
  },

  // ========== 演员映射 ==========

  listActorMappings(params = {}) {
    return api.get('/inventory/actor-mappings', { params })
  },

  getActorMappingSummary() {
    return api.get('/inventory/actor-mappings/summary')
  },

  listUnmappedActors(params = {}) {
    return api.get('/inventory/actor-mappings/unmapped', { params })
  },

  searchActorMappingCandidates(params = {}) {
    return api.get('/inventory/actor-mappings/search', { params })
  },

  reviewActorMappingWithAi(data) {
    return api.post('/inventory/actor-mappings/ai-review', data)
  },

  generateActorMappingCandidates(params = {}) {
    return api.post('/inventory/actor-mappings/candidates/generate', null, { params })
  },

  autoMatchActorMappings(params = {}) {
    return api.post('/inventory/actor-mappings/auto-match', null, { params })
  },

  confirmActorMapping(data) {
    return api.post('/inventory/actor-mappings/confirm', data)
  },

  ignoreActorMapping(data) {
    return api.post('/inventory/actor-mappings/ignore', data)
  },

  deleteActorMapping(mappingId) {
    return api.delete(`/inventory/actor-mappings/${mappingId}`)
  },

  // ========== 缺失检测 ==========

  getMissingActresses() {
    return api.get('/v1/missing/actresses')
  },

  getMissingActressDetail(actressId) {
    return api.get(`/v1/missing/actresses/${actressId}`)
  },

  refreshMissingCache() {
    return api.post('/v1/missing/actresses/refresh')
  },

  // ========== 去重 ==========

  getDuplicates() {
    return api.get('/v1/duplicates')
  },

  deleteDuplicate(embyItemId) {
    return api.post(`/v1/duplicates/${embyItemId}/delete`)
  },

  ignoreDuplicate(embyItemId) {
    return api.post(`/v1/duplicates/${embyItemId}/ignore`)
  },

  // ========== 日志 ==========

  getLogs(limit = 100, level = '', options = {}) {
    return api.get('/v1/logs', { params: { limit, level, ...options } })
  },

  clearLogs() {
    return api.delete('/v1/logs')
  },

  // ========== 配置 ==========

  getConfig() {
    return api.get('/v1/config')
  },

  updateConfig(config) {
    return api.put('/v1/config', config)
  },

  exportConfig() {
    return api.get('/v1/config/export', { responseType: 'blob' })
  },

  testTelegramBot(token) {
    return api.post('/v1/notification/telegram/test', null, { params: { token } })
  },

  testAiModel(ai = {}) {
    return api.post('/v1/ai/test', { provider: ai.provider || 'openai_compatible', ai })
  },

  listAiModels(ai = {}) {
    return api.post('/v1/ai/models', { provider: ai.provider || 'openai_compatible', ai })
  },

  purgeCache(scope = 'video') {
    return api.post('/v1/cache/purge', null, { params: { scope } })
  },

  getCacheStats() {
    return api.get('/v1/cache/stats')
  },

  preflightJavInfoImport(importDb = {}, expectedSize = 0) {
    return api.post('/v1/javinfo/imports/preflight', {
      import_db: importDb,
      expected_size: expectedSize,
    })
  },

  runJavInfoMigrations(dryRun = false) {
    return api.post('/v1/javinfo/imports/migrations', { dry_run: dryRun })
  },

  createJavInfoImportJob(payload = {}) {
    return api.post('/v1/javinfo/imports/jobs', payload)
  },

  async uploadJavInfoImportDump(jobId, file, onUploadProgress, options = {}) {
    const total = Number(file?.size || 0)
    const chunkSize = Number(options.chunkSize || JAVINFO_IMPORT_CHUNK_SIZE)
    const statusResp = await api.get(`/v1/javinfo/imports/jobs/${jobId}`)
    let uploaded = Math.max(0, Math.min(total, Number(statusResp.data?.uploaded_bytes || 0)))
    chunkUploadProgress(onUploadProgress, uploaded, total)

    let chunkIndex = Math.floor(uploaded / chunkSize)
    while (uploaded < total) {
      const end = Math.min(uploaded + chunkSize, total)
      const chunk = file.slice(uploaded, end)
      const offset = uploaded
      const response = await retryChunkUpload(() => api.put(
        `/v1/javinfo/imports/jobs/${jobId}/upload/chunks/${chunkIndex}`,
        chunk,
        {
          headers: {
            'Content-Type': 'application/octet-stream',
            'X-Chunk-Offset': String(offset),
            'X-Chunk-Size': String(chunk.size ?? end - offset),
            'X-Total-Size': String(total),
          },
          transformRequest: [(data) => data],
          silentError: true,
        },
      ), async () => {
        const refreshed = await api.get(`/v1/javinfo/imports/jobs/${jobId}`, { silentError: true })
        const serverUploaded = Math.max(0, Math.min(total, Number(refreshed.data?.uploaded_bytes || 0)))
        return serverUploaded > offset ? serverUploaded : null
      })
      uploaded = Math.max(uploaded, Math.min(total, Number(response.data?.uploaded_bytes || end)))
      chunkUploadProgress(onUploadProgress, uploaded, total)
      chunkIndex = Math.floor(uploaded / chunkSize)
    }

    return completeChunkedUpload(jobId, total)
  },

  getJavInfoImportJob(jobId) {
    return api.get(`/v1/javinfo/imports/jobs/${jobId}`)
  },

  listJavInfoImportJobs(limit = 20) {
    return api.get('/v1/javinfo/imports/jobs', { params: { limit }, silentError: true })
  },

  cancelJavInfoImportJob(jobId) {
    return api.post(`/v1/javinfo/imports/jobs/${jobId}/cancel`)
  },

  startVideoVariantIndexJob() {
    return api.post('/v1/video-variants/index/jobs')
  },

  listVideoVariantIndexJobs(limit = 20) {
    return api.get('/v1/video-variants/index/jobs', { params: { limit }, silentError: true })
  },

  getVideoVariantIndexStats() {
    return api.get('/v1/video-variants/index/stats', { silentError: true })
  },

  // ========== 翻译映射 ==========

  exportTranslations(type) {
    return api.get(`/v1/translations/export/${type}`, { responseType: 'blob' })
  },

  importTranslations(type, file) {
    const form = new FormData()
    form.append('file', file)
    return api.post(`/v1/translations/import/${type}`, form, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
  },

  getTranslationStats() {
    return api.get('/v1/translations/stats')
  },

  testTranslation(text, provider) {
    return api.post('/v1/translations/test', { text, provider })
  },

  startTranslationJob(payload = {}) {
    return api.post('/v1/translations/jobs', payload)
  },

  listTranslationJobs(limit = 20) {
    return api.get('/v1/translations/jobs', { params: { limit } })
  },

  getTranslationJob(jobId) {
    return api.get(`/v1/translations/jobs/${jobId}`)
  },

  pauseTranslationJob(jobId) {
    return api.post(`/v1/translations/jobs/${jobId}/pause`)
  },

  listTranslationItems(params = {}) {
    return api.get('/v1/translations/items', { params })
  },

  updateTranslationItem(type, itemId, payload = {}) {
    return api.patch(`/v1/translations/items/${type}/${itemId}`, payload)
  },

  getTranslationItemHistory(type, itemId, limit = 50) {
    return api.get(`/v1/translations/items/${type}/${itemId}/history`, { params: { limit } })
  },

  retryTranslationItems(payload = {}) {
    return api.post('/v1/translations/items/retry', payload)
  },

  // ========== 收藏管理 ==========

  getFavorites(entity_type, options = {}) {
    return api.get('/v1/favorites', { params: { entity_type, ...options } })
  },

  getFavoriteVideos() {
    return api.get('/v1/favorites/videos')
  },

  getFavoriteVideosPage(params = {}) {
    return api.get('/v1/favorites/videos/page', { params })
  },

  toggleFavorite(data) {
    return api.post('/v1/favorites/toggle', data)
  },

  getCollections() {
    return api.get('/v1/favorites/collections')
  },

  createCollection(data) {
    return api.post('/v1/favorites/collections', data)
  },

  updateCollection(collectionId, data) {
    return api.put(`/v1/favorites/collections/${numericPathSegment(collectionId, 'collectionId')}`, data)
  },

  deleteCollection(collectionId) {
    return api.delete(`/v1/favorites/collections/${numericPathSegment(collectionId, 'collectionId')}`)
  },

  // ========== 补全管理 ==========

  getSupplementStats() {
    return api.get('/v1/supplement/stats')
  },

  getSupplementActressStatus(actressId) {
    return api.get(`/v1/supplement/actresses/${numericPathSegment(actressId, 'actressId')}/status`)
  },

  startSupplementFilmographyJob(actressId) {
    return api.post(`/v1/supplement/actresses/${numericPathSegment(actressId, 'actressId')}/filmography/jobs`)
  },

  startGfriendsAvatarSyncJob() {
    return api.post('/v1/supplement/avatars/gfriends/jobs')
  },

  refreshSupplementActressResolved(actressId) {
    return api.post(`/v1/supplement/actresses/${numericPathSegment(actressId, 'actressId')}/resolved/refresh`)
  },

  listSupplementJobs(params = {}) {
    return api.get('/v1/supplement/jobs', { params })
  },

  getSupplementJob(jobId) {
    return api.get(`/v1/supplement/jobs/${numericPathSegment(jobId, 'jobId')}`)
  },

  retrySupplementJob(jobId) {
    return api.post(`/v1/supplement/jobs/${numericPathSegment(jobId, 'jobId')}/retry`)
  },

  cancelSupplementJob(jobId) {
    return api.post(`/v1/supplement/jobs/${jobId}/cancel`)
  },

  recoverStaleSupplementJobs(olderThanMinutes = 30) {
    return api.post('/v1/supplement/jobs/recover_stale', null, { params: { older_than_minutes: olderThanMinutes } })
  },

  listSupplementMovies(params = {}) {
    return api.get('/v1/supplement/movies', { params })
  },

  getSupplementMovieSources(movieId) {
    return api.get(`/v1/supplement/movies/${movieId}/sources`)
  },

  matchSupplementMovie(movieId, contentId, reason = '') {
    return api.post(`/v1/supplement/movies/${movieId}/match`, { content_id: contentId, reason })
  },

  ignoreSupplementMovie(movieId, reason = '') {
    return api.post(`/v1/supplement/movies/${movieId}/ignore`, { reason })
  },

  unmatchSupplementMovie(movieId, reason = '') {
    return api.post(`/v1/supplement/movies/${movieId}/unmatch`, { reason })
  },

  listSupplementSources() {
    return api.get('/v1/supplement/sources')
  },

  listSupplementSourcesHealth() {
    return api.get('/v1/supplement/sources/health')
  },

  listSupplementSourcesBudgets() {
    return api.get('/v1/supplement/sources/budgets')
  },

  runSupplementProviderSmoke(payload = {}) {
    return api.post('/v1/supplement/providers/smoke', payload)
  },

  listSupplementProviderSmokeRuns(limit = 5, source = '') {
    const params = { limit }
    if (source) params.source = source
    return api.get('/v1/supplement/providers/smoke/runs', { params })
  },

  pauseSupplementSource(source, reason = '', durationMinutes = 1440) {
    return api.post(`/v1/supplement/sources/${source}/pause`, { reason, duration_minutes: durationMinutes })
  },

  resumeSupplementSource(source) {
    return api.post(`/v1/supplement/sources/${source}/resume`)
  },

  enrichSupplementMovieDetail(sourceMovieId, source = 'all') {
    return this.startSupplementMovieDetailJob(sourceMovieId, source)
  },

  startSupplementMovieDetailJob(sourceMovieId, source = 'all', actressId = null) {
    const params = { source, source_movie_id: sourceMovieId }
    if (actressId) params.actress_id = actressId
    return api.post('/v1/supplement/movies/detail/jobs', null, {
      params,
    })
  },

  startSupplementMovieDetailBatchJobs(params = {}) {
    return api.post('/v1/supplement/movies/detail/jobs/batch', null, { params })
  },

  createSupplementDownloadCandidates(params = {}) {
    return api.post('/v1/supplement/movies/candidates', null, { params })
  },

  // ========== 健康检查 ==========

  health() {
    return api.get('/health', { baseURL: '' })
  },

  readiness() {
    return api.get('/health/readiness', { baseURL: '' })
  },

  // ========== 流媒体 ==========

  getStreamUrl(contentId) {
    return api.get(`/v1/stream/${contentId}`)
  },

  transferToCloud(contentId, data) {
    return api.post(`/v1/stream/${contentId}/transfer`, data)
  },

  // ========== 运营总览 ==========

  getOperationsOverview() {
    return api.get('/v1/operations/overview')
  },

  getDataQualityOverview(limit = 8) {
    return api.get('/v1/data-quality/overview', { params: { limit } })
  },

  runCandidateProcessingNow() {
    return api.post('/v1/operations/candidate-processing/run')
  }
}
