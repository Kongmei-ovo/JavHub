import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

const source = readFileSync(new URL('./Actor.vue', import.meta.url), 'utf8')

test('actor page treats supplement as part of the default catalog', () => {
  assert.equal(source.includes('包含补全'), false)
  assert.equal(source.includes('supplement-toggle'), false)
  assert.equal(source.includes('includeSupplement'), false)
  assert.equal(source.includes('查看补全影片'), false)
  assert.match(source, /getActressVideos\(this\.actressId,\s*page,\s*pageSize,\s*\{\s*include_supplement:\s*'1'\s*\}\)/)
  assert.match(source, /:serviceCode="displayServiceCode\(movie\)"/)
  assert.match(source, /if \(movie\._raw\?\.data_origin === 'supplement'\) return ''/)
})

test('actor page surfaces download candidate handoff', () => {
  assert.match(source, /candidateSummary/)
  assert.match(source, /下载候选/)
  assert.match(source, /待补磁力/)
  assert.match(source, /api\.listDownloadCandidates/)
  assert.match(source, /goDownloadCandidates/)
  assert.match(source, /path: '\/downloads'/)
  assert.match(source, /tab: 'candidates'/)
})
