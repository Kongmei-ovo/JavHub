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

export function candidateStatusLabel(status) {
  return CANDIDATE_STATUS_LABELS[status] || status
}

export function candidateSourceLabel(source) {
  return CANDIDATE_SOURCE_LABELS[source] || source || '未知来源'
}
