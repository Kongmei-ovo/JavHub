export const SEARCH_PREFERENCES_KEY = 'javhub_search_preferences'
export const SEARCH_HISTORY_PREFERENCES_KEY = 'javhub_search_history_preferences'
const HISTORY_LIMIT = 24
const PREFERENCE_PARAM_LIMIT = 4

export const DEFAULT_SEARCH_PREFERENCES = {
  defaultSort: 'random',
  defaultServiceCode: '',
}

export function normalizeSearchPreferences(value = {}) {
  const prefs = value && typeof value === 'object' && !Array.isArray(value) ? value : {}
  const sortValues = new Set(['random', 'none', 'release_date_desc', 'release_date_asc', 'title_ja_desc', 'title_ja_asc', 'runtime_mins_desc', 'runtime_mins_asc'])
  const serviceValues = new Set(['', 'digital', 'mono', 'rental', 'ebook'])
  const defaultSort = sortValues.has(prefs.defaultSort) ? prefs.defaultSort : DEFAULT_SEARCH_PREFERENCES.defaultSort
  const defaultServiceCode = serviceValues.has(prefs.defaultServiceCode) ? prefs.defaultServiceCode : DEFAULT_SEARCH_PREFERENCES.defaultServiceCode
  return { defaultSort, defaultServiceCode }
}

export function loadSearchPreferences() {
  try {
    return normalizeSearchPreferences(JSON.parse(localStorage.getItem(SEARCH_PREFERENCES_KEY) || '{}'))
  } catch {
    return { ...DEFAULT_SEARCH_PREFERENCES }
  }
}

export function saveSearchPreferences(preferences) {
  const normalized = normalizeSearchPreferences(preferences)
  localStorage.setItem(SEARCH_PREFERENCES_KEY, JSON.stringify(normalized))
  return normalized
}

function safeStorageRead(key) {
  try {
    return JSON.parse(localStorage.getItem(key) || '{}')
  } catch {
    return {}
  }
}

function compactText(value) {
  const text = value == null ? '' : String(value).trim().replace(/\s+/g, ' ')
  return text.slice(0, 48)
}

function entityListFromVideo(video = {}, key) {
  const direct = compactText(video[key])
  if (direct) return [direct]
  const collection = key === 'actress_name'
    ? video.actresses
    : key === 'category_name'
      ? video.categories
      : null
  if (!Array.isArray(collection)) return []
  return collection
    .map(item => compactText(item?.name_ja || item?.name || item?.actress_name || item?.display_name))
    .filter(Boolean)
}

function bumpCounts(counts = {}, values = []) {
  const next = { ...counts }
  for (const value of values) {
    const key = compactText(value)
    if (key) next[key] = (Number(next[key]) || 0) + 1
  }
  return Object.fromEntries(
    Object.entries(next)
      .sort((a, b) => b[1] - a[1] || (a[0] < b[0] ? -1 : a[0] > b[0] ? 1 : 0))
      .slice(0, HISTORY_LIMIT),
  )
}

function topValues(counts = {}) {
  return Object.entries(counts)
    .sort((a, b) => b[1] - a[1] || (a[0] < b[0] ? -1 : a[0] > b[0] ? 1 : 0))
    .slice(0, PREFERENCE_PARAM_LIMIT)
    .map(([key]) => key)
}

function normalizeCounts(counts = {}) {
  return Object.fromEntries(
    Object.entries(counts || {})
      .map(([key, value]) => [compactText(key), Math.max(1, Math.min(Number(value) || 1, 999))])
      .filter(([key]) => Boolean(key))
      .sort((a, b) => b[1] - a[1] || (a[0] < b[0] ? -1 : a[0] > b[0] ? 1 : 0))
      .slice(0, HISTORY_LIMIT),
  )
}

export function normalizeSearchHistoryPreferences(value = {}) {
  const prefs = value && typeof value === 'object' && !Array.isArray(value) ? value : {}
  return {
    actresses: normalizeCounts(prefs.actresses),
    makers: normalizeCounts(prefs.makers),
    series: normalizeCounts(prefs.series),
    categories: normalizeCounts(prefs.categories),
  }
}

export function loadSearchHistoryPreferences() {
  return normalizeSearchHistoryPreferences(safeStorageRead(SEARCH_HISTORY_PREFERENCES_KEY))
}

export function recordSearchHistoryPreference(video = {}) {
  const current = loadSearchHistoryPreferences()
  const next = {
    actresses: bumpCounts(current.actresses, entityListFromVideo(video, 'actress_name')),
    makers: bumpCounts(current.makers, entityListFromVideo(video, 'maker_name')),
    series: bumpCounts(current.series, entityListFromVideo(video, 'series_name')),
    categories: bumpCounts(current.categories, entityListFromVideo(video, 'category_name')),
  }
  localStorage.setItem(SEARCH_HISTORY_PREFERENCES_KEY, JSON.stringify(next))
  return next
}

export function buildSearchPreferenceParams(preferences = loadSearchHistoryPreferences()) {
  const params = {}
  const actresses = topValues(preferences.actresses)
  const makers = topValues(preferences.makers)
  const series = topValues(preferences.series)
  const categories = topValues(preferences.categories)
  if (actresses.length) params.preferred_actresses = actresses.join(',')
  if (makers.length) params.preferred_makers = makers.join(',')
  if (series.length) params.preferred_series = series.join(',')
  if (categories.length) params.preferred_categories = categories.join(',')
  return params
}
