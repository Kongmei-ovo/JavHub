const KNOWN_PROVIDERS = ['avbase', 'fanza', 'fc2', 'jav321', 'javbus', 'javlibrary', 'mgstage']

export function supplementJobProviderSummary(providers = [], visibleLimit = 4) {
  const unique = [...new Set((providers || []).map(provider => String(provider || '').trim()).filter(Boolean))]
  if (!unique.length) return ''
  const visible = unique.slice(0, visibleLimit)
  const folded = unique.length - visible.length
  return folded > 0 ? `${visible.join(' · ')} · 另 ${folded} 个来源` : visible.join(' · ')
}

export function supplementJobFailureDiagnostics(job = {}) {
  const lastError = String(job?.last_error || '').trim()
  if (!lastError) {
    return {
      hasError: false,
      reasonKey: '',
      reasonLabel: '无',
      summary: '无',
      providers: [],
      providerSummary: '',
      nextActionLabel: '刷新队列',
      nextActionDetail: '同步最新状态',
    }
  }

  const providers = supplementJobProviderNames(lastError, job?.source)
  const reasonKey = supplementJobReasonKey(lastError)
  const reasonLabel = supplementJobReasonLabel(reasonKey)
  const providerSummary = supplementJobProviderSummary(providers)

  return {
    hasError: true,
    reasonKey,
    reasonLabel,
    summary: reasonLabel,
    providers,
    providerSummary,
    nextActionLabel: supplementJobNextActionLabel(reasonKey),
    nextActionDetail: providerSummary || '查看来源',
  }
}

export function supplementJobFailureSummary(job = {}) {
  const diagnostics = supplementJobFailureDiagnostics(job)
  if (!diagnostics.hasError) return diagnostics.summary
  return diagnostics.providerSummary
    ? `${diagnostics.summary} · ${diagnostics.providerSummary}`
    : diagnostics.summary
}

export function supplementJobProviderNames(lastError = '', source = '') {
  const text = String(lastError || '').toLowerCase()
  const prefix = text.match(/^\s*([a-z0-9_.-]+)\s*:/)
  const providers = new Set()
  if (prefix && KNOWN_PROVIDERS.includes(prefix[1])) providers.add(prefix[1])
  for (const provider of KNOWN_PROVIDERS) {
    if (text.includes(provider)) providers.add(provider)
  }
  const sourceName = String(source || '').trim().toLowerCase()
  if (!providers.size && KNOWN_PROVIDERS.includes(sourceName)) providers.add(sourceName)
  return [...providers].sort((left, right) => (
    supplementJobProviderFailureWeight(text, right)
    - supplementJobProviderFailureWeight(text, left)
  ) || KNOWN_PROVIDERS.indexOf(left) - KNOWN_PROVIDERS.indexOf(right))
}

export function supplementJobReasonKey(lastError = '') {
  const text = String(lastError || '').toLowerCase()
  if (text.includes('concurrency limit')) return 'concurrency_limit'
  if (text.includes('cannot unmarshal') || text.includes('low quality detail')) return 'source_schema'
  if (text.includes('sqlstate') || text.includes('not-null constraint') || text.includes('null value in column')) return 'write_error'
  if (text.includes('temporarily unavailable') || text.includes('source health control') || text.includes('cloudflare')) return 'source_unavailable'
  if (text.includes('no high-confidence') || text.includes('identity_unknown')) return 'low_confidence'
  if (text.includes('request failed') || text.includes('not found') || text.includes('forbidden') || text.includes('403') || text.includes('404')) return 'request_failed'
  return 'other'
}

function supplementJobReasonLabel(reasonKey) {
  const labels = {
    concurrency_limit: '并发限制',
    source_schema: '来源数据结构异常',
    write_error: '写入异常',
    source_unavailable: '来源暂不可用',
    low_confidence: '低置信匹配',
    request_failed: '请求失败',
    other: '其他失败',
  }
  return labels[reasonKey] || labels.other
}

function supplementJobNextActionLabel(reasonKey) {
  const labels = {
    concurrency_limit: '等待冷却',
    source_schema: '检查解析',
    write_error: '检查写入',
    source_unavailable: '检查来源',
    low_confidence: '人工匹配',
    request_failed: '检查来源',
    other: '查看详情',
  }
  return labels[reasonKey] || labels.other
}

function supplementJobProviderFailureWeight(lastError, provider) {
  const fragment = supplementJobProviderErrorFragment(lastError, provider)
  if (/cloudflare|temporarily unavailable|source health control/.test(fragment)) return 70
  if (/forbidden|403/.test(fragment)) return 60
  if (/request failed|not found|404/.test(fragment)) return 40
  if (/concurrency limit/.test(fragment)) return 30
  if (/cannot unmarshal|low quality detail/.test(fragment)) return 25
  if (/no high-confidence|identity_unknown/.test(fragment)) return 10
  return fragment ? 1 : 0
}

function supplementJobProviderErrorFragment(lastError, provider) {
  const text = String(lastError || '').toLowerCase()
  const start = text.indexOf(`${provider}:`)
  if (start < 0) {
    return text.includes(provider) ? text : ''
  }
  const rest = text.slice(start)
  const nextProviderIndexes = KNOWN_PROVIDERS
    .filter(name => name !== provider)
    .map(name => rest.indexOf(`; ${name}:`))
    .filter(index => index >= 0)
  const end = nextProviderIndexes.length ? Math.min(...nextProviderIndexes) : rest.length
  return rest.slice(0, end)
}
