const SORT_FIELDS = new Set(['release_date', 'title_ja', 'runtime_mins'])
const SORT_VALUES = new Set([
  'random',
  'release_date_desc',
  'release_date_asc',
  'title_ja_desc',
  'title_ja_asc',
  'runtime_mins_desc',
  'runtime_mins_asc',
])

function firstValue(value) {
  return Array.isArray(value) ? value[0] : value
}

function stringValue(value) {
  const text = firstValue(value)
  return text == null ? '' : String(text).trim()
}

function numberValue(value, fallback = null) {
  const number = Number(stringValue(value))
  return Number.isFinite(number) && number > 0 ? number : fallback
}

export function normalizeSearchSort(sort) {
  const value = stringValue(sort)
  return SORT_VALUES.has(value) ? value : 'random'
}

export function sortStateFromSortValue(sort = 'random') {
  const state = {
    release_date: null,
    title_ja: null,
    runtime_mins: null,
    random: false,
  }
  const value = normalizeSearchSort(sort)
  if (value === 'random') {
    state.random = true
    return state
  }
  const [field, direction] = value.match(/^(release_date|title_ja|runtime_mins)_(asc|desc)$/)?.slice(1) || []
  if (field && direction) state[field] = direction
  return state
}

export function sortValueFromSortState(sortState = {}) {
  if (sortState.random) return 'random'
  for (const field of ['release_date', 'title_ja', 'runtime_mins']) {
    if (sortState[field] === 'desc' || sortState[field] === 'asc') {
      return `${field}_${sortState[field]}`
    }
  }
  return 'random'
}

export function cycleSearchSort(currentSort = 'random', key = 'random') {
  if (key === 'random') return 'random'
  if (!SORT_FIELDS.has(key)) return normalizeSearchSort(currentSort)
  const value = normalizeSearchSort(currentSort)
  const currentField = value.match(/^(release_date|title_ja|runtime_mins)_(asc|desc)$/)?.[1]
  const currentDirection = value.match(/^(release_date|title_ja|runtime_mins)_(asc|desc)$/)?.[2]
  if (currentField !== key) return `${key}_desc`
  if (currentDirection === 'desc') return `${key}_asc`
  return 'random'
}

export function parseSearchQuery(query = {}) {
  const categoryName = stringValue(query.category_name)
  return {
    contentId: stringValue(query.content_id).toUpperCase(),
    keyword: stringValue(query.q || query.keyword),
    year: numberValue(query.year, null),
    makerName: stringValue(query.maker),
    actressName: stringValue(query.actress),
    seriesName: stringValue(query.series),
    categoryTags: categoryName.split(/\s+/).filter(Boolean),
    sort: normalizeSearchSort(query.sort),
    page: numberValue(query.page, 1),
  }
}

export function searchQueryFromState(state = {}) {
  const query = {}
  const contentId = stringValue(state.contentId).toUpperCase()
  const keyword = stringValue(state.keyword)
  const makerName = stringValue(state.makerName)
  const actressName = stringValue(state.actressName)
  const seriesName = stringValue(state.seriesName)
  const year = numberValue(state.year, null)
  const categoryTags = Array.isArray(state.categoryTags)
    ? state.categoryTags.map(tag => String(tag).trim()).filter(Boolean)
    : []
  const sort = normalizeSearchSort(state.sort)
  const page = numberValue(state.page, 1)

  if (contentId) query.content_id = contentId
  if (keyword) query.q = keyword
  if (year) query.year = String(year)
  if (makerName) query.maker = makerName
  if (actressName) query.actress = actressName
  if (seriesName) query.series = seriesName
  if (categoryTags.length) query.category_name = categoryTags.join(' ')
  query.sort = sort
  query.page = String(page)
  return query
}

export function searchQueryEquals(a = {}, b = {}) {
  const normalize = (query) => {
    const result = {}
    for (const key of Object.keys(query || {}).sort()) {
      const value = firstValue(query[key])
      if (value !== undefined && value !== null) result[key] = String(value)
    }
    return JSON.stringify(result)
  }
  return normalize(a) === normalize(b)
}

export function searchHasUserConditions(state = {}) {
  const query = searchQueryFromState({ ...state, sort: 'random', page: 1 })
  return ['content_id', 'q', 'year', 'maker', 'actress', 'series', 'category_name']
    .some(key => Boolean(query[key]))
}

export function canonicalizeSearchState(state = {}) {
  const next = parseSearchQuery(searchQueryFromState(state))
  if (!searchHasUserConditions(next)) {
    next.sort = 'random'
    next.page = 1
  }
  return next
}

export function buildSearchApiParams(state = {}, { pageSize = 30 } = {}) {
  const normalized = {
    ...parseSearchQuery(searchQueryFromState(state)),
    page: numberValue(state.page, 1),
  }
  const params = {
    page: normalized.page,
    page_size: pageSize,
  }
  if (normalized.contentId) params.content_id = normalized.contentId
  if (normalized.keyword) params.q = normalized.keyword
  if (normalized.year) params.year = normalized.year
  if (normalized.makerName) params.maker_name = normalized.makerName
  if (normalized.actressName) params.actress_name = normalized.actressName
  if (normalized.seriesName) params.series_name = normalized.seriesName
  if (normalized.categoryTags.length) params.category_name = normalized.categoryTags.join(' ')

  if (normalized.sort === 'random') {
    params.random = '1'
    params.include_total = false
    return params
  }

  const [field, direction] = normalized.sort.match(/^(release_date|title_ja|runtime_mins)_(asc|desc)$/)?.slice(1) || []
  if (field && direction) params.sort_by = `${field}:${direction}`
  return params
}

export function filterChipsFromSearchState(state = {}) {
  const chips = []
  const add = (key, label, value) => {
    const text = stringValue(value)
    if (text) chips.push({ key, label: `${label}: ${text}` })
  }
  add('contentId', '番号', state.contentId)
  add('keyword', '关键词', state.keyword)
  if (state.year) chips.push({ key: 'year', label: `年份: ${state.year}` })
  add('makerName', '工作室', state.makerName)
  add('actressName', '演员', state.actressName)
  add('seriesName', '系列', state.seriesName)
  for (const tag of state.categoryTags || []) {
    if (tag) chips.push({ key: 'categoryTags', value: tag, label: `题材: ${tag}` })
  }
  return chips
}
