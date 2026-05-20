import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

const source = readFileSync(new URL('./Actor.vue', import.meta.url), 'utf8')

test('actor page treats supplement as part of the default catalog', () => {
  assert.equal(source.includes('包含补全'), false)
  assert.equal(source.includes('supplement-toggle'), false)
  assert.equal(source.includes('includeSupplement'), false)
  assert.equal(source.includes('查看补全影片'), false)
  assert.match(source, /getActressVideos\(this\.actressId,\s*page,\s*MOVIE_PAGE_SIZE,\s*\{\s*include_supplement:\s*'1',\s*include_total:\s*false\s*\}\)/)
  assert.match(source, /:serviceCode="displayServiceCode\(movie\)"/)
  assert.match(source, /if \(movie\._raw\?\.data_origin === 'supplement'\) return ''/)
})

test('actor page keeps loading more when totals are unknown', () => {
  assert.match(source, /if \(this\.totalCount < 0 \|\| this\.movieTotalPages < 0\)/)
  assert.match(source, /return this\.movies\.length >= this\.moviePage \* MOVIE_PAGE_SIZE/)
  assert.match(source, /Number\.isInteger\(data\.total_count\) \? data\.total_count : this\.movies\.length/)
  assert.match(source, /Number\.isInteger\(data\.total_pages\) \? data\.total_pages : 1/)
})

test('actor page surfaces download candidate handoff', () => {
  assert.match(source, /candidateSummary/)
  assert.match(source, /下载候选/)
  assert.match(source, /待补磁力/)
  assert.match(source, /api\.getDownloadCandidateSummary/)
  assert.doesNotMatch(source, /api\.listDownloadCandidates/)
  assert.doesNotMatch(source, /limit:\s*100000/)
  assert.match(source, /goDownloadCandidates/)
  assert.match(source, /path: '\/downloads'/)
  assert.match(source, /tab: 'candidates'/)
})
