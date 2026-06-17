// 115 网盘文件管理 / 离线下载 / 影片资源的 API 方法集合。
// 以工厂形式导出，由 src/api/index.js 注入共享的 axios 实例后 spread 进默认导出，
// 让主 api 文件保持在 large-file 行数上限内（见 visualContract.test.js）。
export function open115Api(api) {
  return {
    listOpen115Files({ cid = '0', offset = 0, limit = 100, keyword = '', order = '', asc = null } = {}) {
      const params = { cid, offset, limit }
      if (keyword) params.keyword = keyword
      if (order) params.order = order
      if (asc !== null && asc !== undefined) params.asc = asc ? 1 : 0
      return api.get('/v1/open115/files', { params, silentError: true })
    },

    getOpen115Quota() {
      return api.get('/v1/open115/offline/quota', { silentError: true })
    },

    listOpen115OfflineTasks(page = 1) {
      return api.get('/v1/open115/offline/tasks', { params: { page }, silentError: true })
    },

    addOpen115Offline({ urls, cid = '0' }) {
      return api.post('/v1/open115/offline/add', { urls, cid: String(cid) })
    },

    deleteOpen115OfflineTask({ infoHash, delSource = false }) {
      return api.post('/v1/open115/offline/delete', { info_hash: String(infoHash), del_source: Boolean(delSource) })
    },

    clearOpen115OfflineTasks(flag = 0) {
      return api.post('/v1/open115/offline/clear', { flag })
    },

    createOpen115Folder(pid, name) {
      return api.post('/v1/open115/files/folder', { pid: String(pid), name })
    },

    renameOpen115File(fileId, name) {
      return api.post('/v1/open115/files/rename', { file_id: String(fileId), name })
    },

    moveOpen115Files(fileIds, toCid) {
      return api.post('/v1/open115/files/move', { file_ids: fileIds.map(String), to_cid: String(toCid) })
    },

    copyOpen115Files(fileIds, toCid) {
      return api.post('/v1/open115/files/copy', { file_ids: fileIds.map(String), to_cid: String(toCid) })
    },

    deleteOpen115Files(fileIds, parentId) {
      return api.post('/v1/open115/files/delete', { file_ids: fileIds.map(String), parent_id: parentId ? String(parentId) : null })
    },

    getOpen115VideoSources(pickCode) {
      return api.get('/v1/open115/files/video', { params: { pick_code: pickCode }, silentError: true })
    },

    open115ImageUrl(pickCode, ext = '') {
      const suffix = ext ? `&ext=${encodeURIComponent(ext)}` : ''
      return `/api/v1/open115/files/image?pick_code=${encodeURIComponent(pickCode)}${suffix}`
    },

    open115StreamUrl(pickCode) {
      return `/api/v1/open115/files/stream?pick_code=${encodeURIComponent(pickCode)}`
    },
  }
}
