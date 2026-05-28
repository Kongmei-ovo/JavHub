export function percentValue(item = {}) {
  const total = Number(item.total || 0)
  if (!total) return 0
  const translated = Number(item.translated || 0)
  return Math.max(0, Math.min(100, Math.round((translated / total) * 100)))
}

export function coveragePercent(item = {}) {
  return `${percentValue(item)}%`
}

export function formatNumber(value) {
  return new Intl.NumberFormat('zh-CN').format(Number(value || 0))
}

export function jobTypeLabel(type) {
  return {
    library_titles: '库内影片标题',
    workbench_retry: '工作台重试',
    metadata_names: '全部元数据名称',
    metadata_categories: '题材名称',
    metadata_series: '系列名称',
    metadata_makers: '厂商名称',
    metadata_labels: '厂牌名称',
    metadata_actresses: '演员名称',
  }[type] || type || '未知作业'
}

export function workbenchStatusLabel(status) {
  return {
    untranslated: '未翻译',
    machine_translated: '机翻',
    reviewed: '已校对',
    manual_edited: '人工修改',
    failed: '失败',
    invalid: '无效',
  }[status] || '未翻译'
}

export function workbenchStatusClass(status) {
  return `status-${status || 'untranslated'}`
}

export function statusLabel(status) {
  return {
    pending: '等待中',
    running: '运行中',
    paused: '已暂停',
    completed: '已完成',
    failed: '失败',
    idle: '空闲',
  }[status] || '空闲'
}

export function jobStatusClass(status) {
  return `status-${status || 'idle'}`
}

export function durationText(value) {
  if (value === null || value === undefined) return '—'
  const seconds = Math.max(0, Number(value) || 0)
  if (seconds < 60) return `${seconds}s`
  const minutes = Math.floor(seconds / 60)
  const rest = seconds % 60
  if (minutes < 60) return rest ? `${minutes}m ${rest}s` : `${minutes}m`
  const hours = Math.floor(minutes / 60)
  const minuteRest = minutes % 60
  return minuteRest ? `${hours}h ${minuteRest}m` : `${hours}h`
}

export function jobProgressValue(job = null) {
  const value = Number(job?.progress_percent || 0)
  if (!Number.isFinite(value)) return 0
  return Math.max(0, Math.min(100, Math.round(value)))
}
