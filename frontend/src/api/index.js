import axios from 'axios'

const api = axios.create({
  baseURL: '/api'
})

// ==============================================
// 全局缓存：题材统计数据（启动时拉取，所有页面共享）
// ==============================================
const STATS_CACHE_KEY = 'javhub_category_stats'
const STATS_TTL_MS = 60 * 60 * 1000  // 1小时过期

let _cachedStats = null

/**
 * 获取题材统计（含影片数量）
 * 优先从内存缓存返回，避免重复请求
 * forceRefresh=true 时强制从 API 重新拉取
 */
async function getCategoryStats(forceRefresh = false) {
  if (!forceRefresh && _cachedStats) {
    return _cachedStats
  }
  if (!forceRefresh) {
    try {
      const cached = localStorage.getItem(STATS_CACHE_KEY)
      if (cached) {
        const { data, ts } = JSON.parse(cached)
        if (Date.now() - ts < STATS_TTL_MS) {
          _cachedStats = data
          return data
        }
      }
    } catch {}
  }
  const resp = await api.get('/v1/categories/stats')
  const data = Array.isArray(resp.data) ? resp.data : (resp.data || [])
  _cachedStats = data
  try {
    localStorage.setItem(STATS_CACHE_KEY, JSON.stringify({ data, ts: Date.now() }))
  } catch {}
  return data
}

export default {
  // ==============================================
  // 共享 stats 缓存（async，内存+localStorage 双缓存）
  // ==============================================
  getCategoryStats,

  // ========== 视频搜索 & 详情 (JavInfoApi) ==========

  searchVideos(params = {}) {
    return api.get('/v1/videos/search', { params })
  },

  listVideos(page = 1, page_size = 20) {
    return api.get('/v1/videos', { params: { page, page_size } })
  },

  getVideo(contentId) {
    return api.get(`/v1/videos/${contentId}`)
  },

  // ========== 演员 ==========

  listActresses(page = 1, page_size = 20) {
    return api.get('/v1/actresses', { params: { page, page_size } })
  },

  getActress(actressId) {
    return api.get(`/v1/actresses/${actressId}`)
  },

  getActressVideos(actressId, page = 1, page_size = 20) {
    return api.get(`/v1/actresses/${actressId}/videos`, { params: { page, page_size } })
  },

  // ========== 枚举数据 ==========

  listMakers() {
    return api.get('/v1/makers')
  },

  listSeries() {
    return api.get('/v1/series')
  },

  listCategories() {
    return api.get('/v1/categories')
  },

  listLabels() {
    return api.get('/v1/labels')
  },

  getStats() {
    return api.get('/v1/stats')
  },

  // ========== 下载管理 ==========

  getDownloads() {
    return api.get('/downloads')
  },

  createDownload(data) {
    return api.post('/downloads', data)
  },

  deleteDownload(taskId) {
    return api.delete(`/downloads/${taskId}`)
  },

  // ========== 订阅管理 ==========

  getSubscriptions() {
    return api.get('/subscriptions')
  },

  addSubscription(data) {
    return api.post('/subscriptions', data)
  },

  deleteSubscription(id) {
    return api.delete(`/subscriptions/${id}`)
  },

  checkSubscriptions() {
    return api.post('/subscriptions/check')
  },

  // ========== 缺失检测 ==========

  getMissingActresses() {
    return api.get('/missing/actresses')
  },

  getMissingActressDetail(actressId) {
    return api.get(`/missing/actresses/${actressId}`)
  },

  refreshMissingCache() {
    return api.post('/missing/actresses/refresh')
  },

  // ========== 去重 ==========

  getDuplicates() {
    return api.get('/duplicates')
  },

  deleteDuplicate(embyItemId) {
    return api.post(`/duplicates/${embyItemId}/delete`)
  },

  ignoreDuplicate(embyItemId) {
    return api.post(`/duplicates/${embyItemId}/ignore`)
  },

  // ========== 日志 ==========

  getLogs(limit = 100, level = '') {
    return api.get('/logs', { params: { limit, level } })
  },

  // ========== 配置 ==========

  getConfig() {
    return api.get('/config')
  },

  updateConfig(config) {
    return api.put('/config', config)
  },

  purgeCache(scope = 'video') {
    return api.post('/cache/purge', null, { params: { scope } })
  },

  // ========== 图片代理 ==========

  proxyImage(url) {
    return `/api/proxy/image?url=${encodeURIComponent(url)}`
  },

  // ========== 健康检查 ==========

  health() {
    return api.get('/health')
  }
}
