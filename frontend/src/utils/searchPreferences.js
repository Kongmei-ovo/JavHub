export const SEARCH_PREFERENCES_KEY = 'javhub_search_preferences'

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
