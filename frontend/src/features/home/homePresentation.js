const STATUS_BADGES = {
  pending: 'badge-pending',
  downloading: 'badge-info',
  completed: 'badge-success',
  failed: 'badge-error',
}

const STATUS_LABELS = {
  pending: '待处理',
  downloading: '下载中',
  completed: '已完成',
  failed: '失败',
}

const CANDIDATE_BADGES = {
  candidate: 'badge-pending',
  approved: 'badge-info',
  sent: 'badge-success',
  failed: 'badge-error',
  rejected: 'badge-pending',
}

const CANDIDATE_STATUS_LABELS = {
  candidate: '待确认',
  approved: '已批准',
  sent: '已下发',
  failed: '失败',
  rejected: '已拒绝',
}

const CANDIDATE_SOURCE_LABELS = {
  subscription: '订阅',
  inventory: '库存',
  supplement: '补全',
  manual: '手动',
}

export function shortDownloaderAddress(address) {
  const value = String(address || '').trim()
  if (!value) return ''
  try {
    const url = new URL(value)
    return `${url.host}${url.pathname === '/' ? '' : url.pathname}`.replace(/\/$/, '')
  } catch (_) {
    return value.replace(/^https?:\/\//, '').replace(/\/$/, '')
  }
}

export function downloaderPathSummary(client) {
  if (client.default_path) return client.default_path
  if (client.category) return `分类 ${client.category}`
  return '默认路径'
}

export function statusBadge(status) {
  return STATUS_BADGES[status] || 'badge-pending'
}

export function statusLabel(status) {
  return STATUS_LABELS[status] || status
}

export function candidateBadge(status) {
  return CANDIDATE_BADGES[status] || 'badge-pending'
}

export function candidateStatusLabel(status) {
  return CANDIDATE_STATUS_LABELS[status] || status
}

export function candidateSourceLabel(source) {
  return CANDIDATE_SOURCE_LABELS[source] || source || '未知来源'
}

export function formatDownloadTime(time) {
  if (!time) return ''
  const d = new Date(time)
  return `${d.getMonth() + 1}/${d.getDate()} ${d.getHours().toString().padStart(2, '0')}:${d.getMinutes().toString().padStart(2, '0')}`
}
