const AVDB_SYNC_STATUSES = new Set(['never', 'running', 'success', 'failed'])

function asObject(value) {
  return value && typeof value === 'object' && !Array.isArray(value) ? value : {}
}

export function normalizeAvdbStatus(value = {}) {
  const source = asObject(value)
  const recordCount = Number(source.record_count ?? 0)
  const status = AVDB_SYNC_STATUSES.has(source.status) ? source.status : 'never'

  return {
    enabled: Boolean(source.enabled),
    syncEnabled: Boolean(source.sync_enabled),
    status,
    available: Boolean(source.available),
    release: String(source.current_release || ''),
    generation: String(source.current_generation || ''),
    recordCount: Number.isFinite(recordCount) ? Math.max(0, recordCount) : 0,
    sourceCounts: asObject(source.source_counts),
    lastCheckedAt: source.last_checked_at || '',
    lastStartedAt: source.last_started_at || '',
    lastCompletedAt: source.last_completed_at || '',
    lastError: String(source.last_error || ''),
  }
}

export function avdbState(value = {}, { loading = false, known = true } = {}) {
  const status = normalizeAvdbStatus(value)
  if (loading) return { code: 'loading', label: '读取中', tone: 'is-idle' }
  if (!known) return { code: 'unavailable', label: '状态异常', tone: 'is-failed' }
  if (status.status === 'running') return { code: 'syncing', label: '同步中', tone: 'is-running' }
  if (status.status === 'failed') return { code: 'failed', label: '失败', tone: 'is-failed' }
  if (status.available) return { code: 'available', label: '可用', tone: 'is-success' }
  if (!status.syncEnabled) return { code: 'unconfigured', label: '未配置', tone: 'is-idle' }
  return { code: 'unsynced', label: '未同步', tone: 'is-warn' }
}

export function shouldPollAvdb(value = {}) {
  return normalizeAvdbStatus(value).status === 'running'
}

export function formatAvdbCount(value) {
  const count = Number(value)
  if (!Number.isFinite(count) || count < 0) return '0'
  return Math.trunc(count).toLocaleString('zh-CN')
}

export function avdbSourceCountText(sourceCounts = {}) {
  return Object.entries(asObject(sourceCounts))
    .filter(([, count]) => Number.isFinite(Number(count)))
    .map(([source, count]) => `${source} ${formatAvdbCount(count)}`)
    .join(' · ')
}
