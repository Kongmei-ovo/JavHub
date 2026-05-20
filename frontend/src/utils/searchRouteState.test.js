import test from 'node:test'
import assert from 'node:assert/strict'
import {
  buildSearchApiParams,
  canonicalizeSearchState,
  cycleSearchSort,
  filterChipsFromSearchState,
  parseSearchQuery,
  searchQueryEquals,
  searchHasUserConditions,
  searchQueryFromState,
  sortStateFromSortValue,
  sortValueFromSortState,
} from './searchRouteState.js'

test('parseSearchQuery restores every canonical search field', () => {
  assert.deepEqual(parseSearchQuery({
    content_id: 'cme-001',
    q: '制服',
    service_code: 'digital',
    year: '2024',
    maker: 'MOODYZ',
    actress: '小湊よつ葉',
    series: '企画',
    category_name: '制服 巨乳',
    sort: 'release_date_asc',
    page: '3',
  }), {
    contentId: 'CME-001',
    keyword: '制服',
    serviceCode: 'digital',
    year: 2024,
    makerName: 'MOODYZ',
    actressName: '小湊よつ葉',
    seriesName: '企画',
    categoryTags: ['制服', '巨乳'],
    sort: 'release_date_asc',
    page: 3,
  })
})

test('searchQueryFromState serializes a canonical refreshable URL query', () => {
  assert.deepEqual(searchQueryFromState({
    contentId: 'CME-001',
    keyword: '',
    serviceCode: 'rental',
    year: 2023,
    makerName: '',
    actressName: '演员',
    seriesName: '',
    categoryTags: ['剧情', '4K'],
    sort: 'runtime_mins_desc',
    page: 5,
  }), {
    content_id: 'CME-001',
    service_code: 'rental',
    year: '2023',
    actress: '演员',
    category_name: '剧情 4K',
    sort: 'runtime_mins_desc',
    page: '5',
  })
})

test('searchQueryEquals ignores query key order but not value changes', () => {
  assert.equal(searchQueryEquals(
    { page: '1', sort: 'random', service_code: 'mono' },
    { service_code: 'mono', sort: 'random', page: '1' },
  ), true)
  assert.equal(searchQueryEquals(
    { page: '1', sort: 'random', service_code: 'mono' },
    { page: '1', sort: 'random', service_code: 'digital' },
  ), false)
  assert.equal(searchQueryEquals(
    { page: '1', sort: 'random' },
    { page: '1', sort: 'random', returnTo: 'video' },
  ), false)
})

test('empty random search is valid and maps to random API params', () => {
  const state = parseSearchQuery({ sort: 'random', page: '1' })
  assert.equal(state.sort, 'random')
  assert.deepEqual(searchQueryFromState(state), { sort: 'random', page: '1' })
  assert.deepEqual(buildSearchApiParams(state, { pageSize: 30 }), {
    page: 1,
    page_size: 30,
    random: '1',
    include_total: false,
  })
})

test('searchHasUserConditions distinguishes random exploration from filtered search', () => {
  assert.equal(searchHasUserConditions({ sort: 'random', page: 1 }), false)
  assert.equal(searchHasUserConditions({ contentId: 'CME-001', sort: 'random', page: 1 }), true)
  assert.equal(searchHasUserConditions({ categoryTags: ['剧情'], sort: 'random', page: 1 }), true)
})

test('canonicalizeSearchState returns empty searches to random exploration', () => {
  assert.deepEqual(searchQueryFromState(canonicalizeSearchState({
    keyword: '',
    categoryTags: [],
    sort: 'release_date_desc',
    page: 3,
  })), { sort: 'random', page: '1' })
  assert.deepEqual(searchQueryFromState(canonicalizeSearchState({
    keyword: '制服',
    sort: 'release_date_desc',
    page: 3,
  })), { q: '制服', sort: 'release_date_desc', page: '3' })
})

test('cycleSearchSort keeps exactly one active sort', () => {
  assert.equal(cycleSearchSort('random', 'release_date'), 'release_date_desc')
  assert.equal(cycleSearchSort('release_date_desc', 'release_date'), 'release_date_asc')
  assert.equal(cycleSearchSort('release_date_asc', 'release_date'), 'random')
  assert.equal(cycleSearchSort('title_ja_desc', 'runtime_mins'), 'runtime_mins_desc')
  assert.equal(cycleSearchSort('runtime_mins_desc', 'random'), 'random')
})

test('sort helpers convert between route sort values and legacy pill state', () => {
  const state = sortStateFromSortValue('title_ja_asc')
  assert.deepEqual(state, {
    release_date: null,
    title_ja: 'asc',
    runtime_mins: null,
    random: false,
  })
  assert.equal(sortValueFromSortState(state), 'title_ja_asc')
  assert.equal(sortValueFromSortState({ release_date: 'desc', title_ja: 'asc', runtime_mins: null, random: false }), 'release_date_desc')
})

test('filterChipsFromSearchState describes removable user conditions', () => {
  assert.deepEqual(filterChipsFromSearchState({
    contentId: 'CME-001',
    keyword: '制服',
    serviceCode: 'digital',
    year: 2025,
    makerName: 'Maker',
    actressName: '',
    seriesName: '',
    categoryTags: ['剧情'],
    sort: 'random',
    page: 1,
  }).map(chip => chip.label), [
    '番号: CME-001',
    '关键词: 制服',
    '版本: 数字',
    '年份: 2025',
    '工作室: Maker',
    '题材: 剧情',
  ])
})
