import axios from 'axios'
import { ElMessage } from 'element-plus'

const api = axios.create({
  baseURL: '/api'
})

const ERROR_TOAST_COOLDOWN_MS = 3000
let lastErrorToast = { key: '', ts: 0 }

// ========== 全局错误拦截 ==========
api.interceptors.response.use(
  response => response,
  error => {
    if (!error.config?.silentError) {
      const errMsg = error.response?.data?.detail
        || error.response?.data?.message
        || error.message
        || '网络错误'
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
  // ========== 视频搜索 & 详情 (JavInfoApi) ==========

  searchVideos(params = {}) {
    return api.get('/v1/videos/search', { params })
  },

  checkLibrary(code) {
    return api.get(`/v1/videos/${code}`)
  },

  listVideos(page = 1, page_size = 20) {
    return api.get('/v1/videos', { params: { page, page_size } })
  },

  getVideo(contentId) {
    return api.get(`/v1/videos/${contentId}`)
  },

  // ========== 演员 ==========

  listActresses(page = 1, page_size = 20, options = {}) {
    return api.get('/v1/actresses', { params: { page, page_size, ...options } })
  },

  getActress(actressId) {
    return api.get(`/v1/actresses/${actressId}`)
  },

  getActressVideos(actressId, page = 1, page_size = 20, options = {}) {
    return api.get(`/v1/actresses/${actressId}/videos`, {
      params: { page, page_size, ...options },
    })
  },

  batchGetActressVideos(ids, page = 1, page_size = 5) {
    return api.post('/v1/actresses/batch_videos', { ids, page, page_size })
  },

  // ========== 枚举数据 ==========

  listMakers() {
    return api.get('/v1/makers')
  },

  listSeries(page = 1, page_size = 20) {
    return api.get('/v1/series', { params: { page, page_size } })
  },

  listCategories() {
    return api.get('/v1/categories', { silentError: true })
  },

  listLabels() {
    return api.get('/v1/labels')
  },

  listDirectors(params = {}) {
    return api.get('/v1/directors', { params })
  },

  listActors(params = {}) {
    return api.get('/v1/actors', { params })
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

  getNewMovies() {
    return api.get('/v1/subscriptions/new_movies')
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

  getLogs(limit = 100, level = '') {
    return api.get('/v1/logs', { params: { limit, level } })
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

  testTranslation(text) {
    return api.post('/v1/translations/test', { text })
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

  getFavorites(entity_type) {
    return api.get('/v1/favorites', { params: { entity_type } })
  },

  getFavoriteVideos() {
    return api.get('/v1/favorites/videos')
  },

  toggleFavorite(data) {
    return api.post('/v1/favorites/toggle', data)
  },

  getCollections() {
    return api.get('/v1/favorites/collections')
  },

  // ========== 补全管理 ==========

  getSupplementStats() {
    return api.get('/v1/supplement/stats')
  },

  getSupplementActressStatus(actressId) {
    return api.get(`/v1/supplement/actresses/${actressId}/status`)
  },

  startSupplementFilmographyJob(actressId) {
    return api.post(`/v1/supplement/actresses/${actressId}/filmography/jobs`)
  },

  refreshSupplementActressResolved(actressId) {
    return api.post(`/v1/supplement/actresses/${actressId}/resolved/refresh`)
  },

  listSupplementJobs(params = {}) {
    return api.get('/v1/supplement/jobs', { params })
  },

  getSupplementJob(jobId) {
    return api.get(`/v1/supplement/jobs/${jobId}`)
  },

  retrySupplementJob(jobId) {
    return api.post(`/v1/supplement/jobs/${jobId}/retry`)
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
    return api.post('/v1/supplement/movies/detail', null, {
      params: { source, source_movie_id: sourceMovieId },
    })
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
    return api.get('/health')
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

  runCandidateProcessingNow() {
    return api.post('/v1/operations/candidate-processing/run')
  }
}
