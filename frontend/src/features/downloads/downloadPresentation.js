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

export function formatDownloadTime(time) {
  if (!time) return ''
  const d = new Date(time)
  return `${d.getMonth() + 1}/${d.getDate()} ${d.getHours().toString().padStart(2, '0')}:${d.getMinutes().toString().padStart(2, '0')}`
}
