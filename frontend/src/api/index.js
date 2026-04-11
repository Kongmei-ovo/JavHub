import axios from 'axios'

const api = axios.create({
  baseURL: '/api'
})

export default {
  // ========== 视频搜索 & 详情 (JavInfoApi) ==========

  /**
   * 搜索视频
   * @param {Object} params - 搜索参数
   * @param {string} params.q - 关键词搜索
   * @param {string} params.content_id - 番号精确匹配
   * @param {number} params.maker_id - 厂商ID
   * @param {number} params.series_id - 系列ID
   * @param {number} params.actress_id - 演员ID
   * @param {number} params.category_id - 题材ID
   * @param {number} params.page - 页码
   * @param {number} params.page_size - 每页数量
   */
  searchVideos(params = {}) {
    return api.get('/v1/videos/search', { params })
  },

  /**
   * 获取视频列表
   */
  listVideos(page = 1, page_size = 20) {
    return api.get('/v1/videos', { params: { page, page_size } })
  },

  /**
   * 获取视频详情
   */
  getVideo(contentId) {
    return api.get(`/v1/videos/${contentId}`)
  },

  // ========== 演员 ==========

  /**
   * 获取演员列表
   */
  listActresses(page = 1, page_size = 20) {
    return api.get('/v1/actresses', { params: { page, page_size } })
  },

  /**
   * 获取演员详情
   */
  getActress(actressId) {
    return api.get(`/v1/actresses/${actressId}`)
  },

  /**
   * 获取演员作品列表
   */
  getActressVideos(actressId, page = 1, page_size = 20) {
    return api.get(`/v1/actresses/${actressId}/videos`, { params: { page, page_size } })
  },

  // ========== 枚举数据 ==========

  /**
   * 获取所有厂商
   */
  listMakers() {
    return api.get('/v1/makers')
  },

  /**
   * 获取所有系列
   */
  listSeries() {
    return api.get('/v1/series')
  },

  /**
   * 获取所有题材
   */
  listCategories() {
    return api.get('/v1/categories')
  },

  /**
   * 获取题材统计（含影片数量，用于金色传说稀有度）
   */
  categoryStats() {
    return api.get('/v1/categories/stats')
  },

  /**
   * 获取所有品牌
   */
  listLabels() {
    return api.get('/v1/labels')
  },

  /**
   * 获取统计数据
   */
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

  // ========== 图片代理 ==========

  proxyImage(url) {
    return `/api/proxy/image?url=${encodeURIComponent(url)}`
  },

  // ========== 健康检查 ==========

  health() {
    return api.get('/health')
  }
}
