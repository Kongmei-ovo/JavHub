const TORZNAB_DRAFT = Object.freeze({
  id: '',
  type: 'torznab',
  kind: 'prowlarr',
  name: '',
  enabled: true,
  base_url: '',
  api_key: '',
  api_key_configured: false,
  indexer: 'all',
  categories: '',
  limit: 20,
  timeout: 15,
})

const TORZNAB_KIND_LABELS = {
  prowlarr: 'Prowlarr',
  jackett: 'Jackett',
  torznab: '通用 Torznab',
}

function asSource(value) {
  if (typeof value === 'string') return { type: value }
  return value && typeof value === 'object' && !Array.isArray(value) ? value : {}
}

function sourceType(value) {
  return String(asSource(value).type || '').trim().toLowerCase()
}

function text(value) {
  return typeof value === 'string' ? value.trim() : ''
}

function validHttpUrl(value) {
  try {
    const parsed = new URL(text(value))
    return ['http:', 'https:'].includes(parsed.protocol.toLowerCase()) && Boolean(parsed.hostname)
  } catch (_) {
    return false
  }
}

function boundedInteger(value, minimum, maximum) {
  if (typeof value !== 'number' && typeof value !== 'string') return false
  if (typeof value === 'string' && !/^-?\d+$/.test(value.trim())) return false
  const number = Number(value)
  return Number.isInteger(number) && number >= minimum && number <= maximum
}

function downloadUri(item) {
  const source = asSource(item)
  for (const key of ['magnet', 'torrent_url', 'download_url']) {
    const value = text(source[key])
    if (value) return value
  }
  return ''
}

function btihFromUri(uri) {
  try {
    const parsed = new URL(uri)
    for (const [key, value] of parsed.searchParams.entries()) {
      if (key.toLowerCase() !== 'xt') continue
      const match = value.trim().match(/^urn:btih:(.+)$/i)
      if (match) return match[1].trim()
    }
  } catch (_) {
    return ''
  }
  return ''
}

function normalizedUri(uri) {
  try {
    const parsed = new URL(uri)
    const pairs = [...parsed.searchParams.entries()]
    pairs.sort((left, right) => {
      const keyOrder = left[0].toLowerCase().localeCompare(right[0].toLowerCase())
      return keyOrder || left[1].localeCompare(right[1])
    })
    parsed.search = ''
    for (const [key, value] of pairs) parsed.searchParams.append(key, value)
    return parsed.toString()
  } catch (_) {
    return ''
  }
}

function magnetIdentity(item) {
  const source = asSource(item)
  const infoHash = text(source.info_hash)
  if (infoHash) return `btih:${infoHash.toLowerCase()}`

  const uri = downloadUri(source)
  if (!uri) return ''
  const btih = btihFromUri(uri)
  if (btih) return `btih:${btih.toLowerCase()}`

  const normalized = normalizedUri(uri)
  return normalized ? `uri:${normalized}` : ''
}

export function createSourceDraft(type = 'torznab', source = {}) {
  const saved = asSource(source)
  if (String(type || '').trim().toLowerCase() === 'avdb') {
    return {
      id: text(saved.id),
      type: 'avdb',
      enabled: Boolean(saved.enabled),
    }
  }
  return {
    id: text(saved.id) || TORZNAB_DRAFT.id,
    type: 'torznab',
    kind: text(saved.kind) || TORZNAB_DRAFT.kind,
    name: typeof saved.name === 'string' ? saved.name : TORZNAB_DRAFT.name,
    enabled: saved.enabled === undefined ? TORZNAB_DRAFT.enabled : Boolean(saved.enabled),
    base_url: typeof saved.base_url === 'string' ? saved.base_url : TORZNAB_DRAFT.base_url,
    api_key: '',
    api_key_configured: Boolean(saved.api_key_configured),
    indexer: typeof saved.indexer === 'string' ? saved.indexer : TORZNAB_DRAFT.indexer,
    categories: typeof saved.categories === 'string' ? saved.categories : TORZNAB_DRAFT.categories,
    limit: saved.limit ?? TORZNAB_DRAFT.limit,
    timeout: saved.timeout ?? TORZNAB_DRAFT.timeout,
  }
}

export function validateSourceDraft(value = {}) {
  const draft = asSource(value)
  if (sourceType(draft) !== 'torznab') return {}

  const errors = {}
  if (!text(draft.name)) errors.name = '请输入来源名称'
  if (!validHttpUrl(draft.base_url)) errors.base_url = '请输入有效的 HTTP(S) URL'
  const canKeepConfiguredKey = Boolean(text(draft.id)) && Boolean(draft.api_key_configured)
  if (!text(draft.api_key) && !canKeepConfiguredKey) errors.api_key = '请输入 API Key'
  if (!boundedInteger(draft.limit, 1, 100)) errors.limit = '返回上限必须是 1–100 的整数'
  if (!boundedInteger(draft.timeout, 1, 60)) errors.timeout = '超时必须是 1–60 的整数'
  return errors
}

export function sourceTypeLabel(value = {}) {
  const source = asSource(value)
  switch (sourceType(source)) {
    case 'm3u8':
      return '在线 M3U8'
    case 'torznab':
      return TORZNAB_KIND_LABELS[text(source.kind).toLowerCase()] || TORZNAB_KIND_LABELS.torznab
    case 'avdb':
      return 'AVDB 公开库'
    default:
      return text(source.name) || '下载源'
  }
}

export function sourceTypeMark(value = {}) {
  switch (sourceType(value)) {
    case 'm3u8':
      return 'HLS'
    case 'torznab':
      return 'BT'
    case 'avdb':
      return 'DB'
    default:
      return 'SRC'
  }
}

export function sourceHost(value) {
  const raw = typeof value === 'string' ? value : asSource(value).base_url
  const address = text(raw)
  if (!address) return '尚未配置'
  try {
    return new URL(address).host || address
  } catch (_) {
    return address
  }
}

export function selectableMagnetSources(snapshot = {}) {
  const options = [{ value: 'auto', label: '自动' }]
  const sources = Array.isArray(snapshot?.sources) ? snapshot.sources : []
  for (const source of sources) {
    const type = sourceType(source)
    const eligible = type === 'torznab'
      ? Boolean(source?.enabled)
      : type === 'avdb' && Boolean(source?.enabled) && Boolean(source?.available)
    const id = text(source?.id)
    if (!eligible || !id) continue
    options.push({
      value: id,
      label: type === 'avdb' ? 'AVDB 公开库' : text(source?.name) || sourceTypeLabel(source),
    })
  }
  return options
}

export function mergeMagnetResults(existing = [], searched = []) {
  const merged = []
  const identities = new Set()
  const items = [
    ...(Array.isArray(existing) ? existing : []),
    ...(Array.isArray(searched) ? searched : []),
  ]

  for (const item of items) {
    const identity = magnetIdentity(item)
    if (identity && identities.has(identity)) continue
    if (identity) identities.add(identity)
    merged.push(item)
  }
  return merged
}
