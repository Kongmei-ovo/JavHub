const ACTIVE_IMPORT_STATUSES = [
  'pending',
  'uploading',
  'uploaded',
  'restoring',
  'stopping',
  'swapping',
  'restarting',
  'migrating',
]

const IMPORT_STATUS_LABELS = {
  pending: '等待上传',
  uploading: '上传中',
  uploaded: '已上传',
  restoring: '恢复中',
  stopping: '停止 JavInfoApi',
  swapping: '切换数据库',
  restarting: '重启 JavInfoApi',
  migrating: '更新 JavInfoApi',
  completed: '已完成',
  failed: '失败',
  canceled: '已取消',
}

function boundedPercent(value) {
  return Math.max(0, Math.min(100, Math.round(Number(value) || 0)))
}

export function isJavInfoImportActive(job) {
  return ACTIVE_IMPORT_STATUSES.includes(job?.status)
}

export function javinfoImportStatusLabel(job) {
  const status = job?.status || 'pending'
  const stage = job?.stage || status
  return IMPORT_STATUS_LABELS[stage] || IMPORT_STATUS_LABELS[status] || status
}

export function javinfoImportProgress({
  job = {},
  uploading = false,
  uploadProgress = 0,
  fileSize = 0,
} = {}) {
  const currentJob = job || {}
  if (currentJob.status === 'completed') return 100
  if (uploading) return boundedPercent(uploadProgress)
  const total = Number(currentJob.file_size || fileSize || 0)
  const uploaded = Number(currentJob.uploaded_bytes || 0)
  if (total > 0) return boundedPercent(uploaded * 100 / total)
  if (isJavInfoImportActive(currentJob)) return 10
  return 0
}

export function formatBytes(value) {
  const size = Number(value || 0)
  if (size >= 1024 ** 3) return `${(size / 1024 ** 3).toFixed(2)} GB`
  if (size >= 1024 ** 2) return `${(size / 1024 ** 2).toFixed(1)} MB`
  if (size >= 1024) return `${(size / 1024).toFixed(1)} KB`
  return `${size} B`
}
