export const PROVIDER_META = {
  google_free: { label: 'Google 免费接口', hint: '无密钥，适合标题和短名称批量翻译。' },
  baidu: { label: '百度翻译', hint: '使用百度通用文本翻译 API，适合已有免费 key 的低成本翻译。' },
  deepl: { label: 'DeepL', hint: '质量更高，需要配置密钥。' },
  microsoft: { label: 'Microsoft 翻译', hint: 'Azure 翻译接口，需要密钥和可选区域。' },
  ai: { label: '智能兜底', hint: '使用设置页当前公共智能模型，适合低成本源效果不好时补充。' },
}

export const PROVIDER_KEYS = Object.keys(PROVIDER_META)

const PROVIDER_LABELS = {
  cache: '缓存',
  mapping: '映射',
  google_free: 'Google 免费接口',
  baidu: '百度翻译',
  deepl: 'DeepL',
  microsoft: 'Microsoft 翻译',
  ai: '智能兜底',
  openai_compatible: '智能兜底',
  translation_service: '批量源',
  import: '导入',
  manual: '人工',
}

export function providerLabel(key) {
  return PROVIDER_LABELS[key] || key || ''
}

export function providerOrderLabel(order) {
  const labels = (order || []).map(key => providerLabel(key)).filter(Boolean)
  return labels.length ? labels.join(' -> ') : '未记录'
}

export function normalizeProvider(provider) {
  const key = provider === 'openai_compatible' ? 'ai' : provider
  return PROVIDER_META[key] ? key : 'google_free'
}

export function firstNetworkProvider(order) {
  if (!Array.isArray(order)) return ''
  const found = order.find(key => PROVIDER_META[key === 'openai_compatible' ? 'ai' : key])
  return found ? normalizeProvider(found) : ''
}
