import test from 'node:test'
import assert from 'node:assert/strict'
import { existsSync, readFileSync } from 'node:fs'

const downloadsUrl = new URL('./Downloads.vue', import.meta.url)
const downloadsSource = existsSync(downloadsUrl) ? readFileSync(downloadsUrl, 'utf8') : ''
const routerSource = readFileSync(new URL('../router/index.js', import.meta.url), 'utf8')

test('downloads route owns a dedicated v2 view', () => {
  assert.match(routerSource, /path:\s*'\/downloads'[\s\S]*views\/Downloads\.vue/)
  assert.doesNotMatch(routerSource, /views\/Home\.vue/)
  assert.ok(existsSync(downloadsUrl), 'Downloads.vue should exist')
  assert.match(downloadsSource, /name:\s*'Downloads'/)
  assert.doesNotMatch(downloadsSource, /features\/home/)
})

test('downloads page has no candidate workspace dependency', () => {
  assert.doesNotMatch(
    downloadsSource,
    /candidateStats|getDownloadCandidateSummary|CandidateOverview|openCandidatePreset/,
  )
  assert.doesNotMatch(downloadsSource, /待确认候选|待补磁力|可批准/)
})

test('downloads page keeps real task and downloader responsibilities', () => {
  assert.match(downloadsSource, /api\.getDownloads\(\)/)
  assert.match(downloadsSource, /api\.createDownload\(/)
  assert.match(downloadsSource, /api\.deleteDownload\(/)
  assert.match(downloadsSource, /api\.listDownloaders\(\)/)
  assert.match(downloadsSource, /api\.updateDownloaders\(/)
  assert.match(downloadsSource, /api\.testDownloader\(/)
})

test('legacy candidate deep links remain compatible', () => {
  assert.match(downloadsSource, /query\.tab === 'candidates'/)
  assert.match(downloadsSource, /path:\s*'\/candidates'/)
  assert.match(downloadsSource, /delete next\.tab/)
})

test('download empty state only points to download entry paths', () => {
  assert.match(downloadsSource, /taskEmptyPrimaryLabel\(\)/)
  assert.match(downloadsSource, /浏览影库/)
  assert.match(downloadsSource, /this\.\$router\.push\('\/search'\)/)
  assert.doesNotMatch(downloadsSource, /查看 \$\{.*\} 个候选|处理候选/)
})
