import test from 'node:test'
import assert from 'node:assert/strict'
import { existsSync, readFileSync } from 'node:fs'

const downloadsUrl = new URL('./Downloads.vue', import.meta.url)
const downloadsSource = existsSync(downloadsUrl) ? readFileSync(downloadsUrl, 'utf8') : ''
const routerSource = readFileSync(new URL('../router/index.js', import.meta.url), 'utf8')

function bracedSource(source, openingBrace) {
  let depth = 0
  for (let index = openingBrace; index < source.length; index += 1) {
    if (source[index] === '{') depth += 1
    if (source[index] === '}') depth -= 1
    if (depth === 0) return source.slice(openingBrace, index + 1)
  }
  assert.fail('expected a balanced source block')
}

function exportedFunctionSource(name) {
  const start = downloadsSource.indexOf(`export function ${name}(`)
  assert.notEqual(start, -1, `${name} should be exported for source orchestration tests`)
  const openingBrace = downloadsSource.indexOf(') {', start) + 2
  assert.ok(openingBrace > 1, `${name} should have a function body`)
  return downloadsSource.slice(start, openingBrace) + bracedSource(downloadsSource, openingBrace)
}

function methodSource(name) {
  const match = downloadsSource.match(new RegExp(`\\n\\s+(?:async\\s+)?${name}\\(`))
  assert.ok(match, `${name} method should exist`)
  const start = match.index + 1
  const openingBrace = downloadsSource.indexOf(') {', start) + 2
  assert.ok(openingBrace > 1, `${name} should have a method body`)
  return downloadsSource.slice(start, openingBrace) + bracedSource(downloadsSource, openingBrace)
}

function evaluateExportedFunction(name) {
  const declaration = exportedFunctionSource(name).replace(/^export\s+/, '')
  return Function(`"use strict"; ${declaration}; return ${name}`)()
}

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

test('download workspace distinguishes downloader clients from download sources', () => {
  assert.match(downloadsSource, /activeTab === 'downloaders'[\s\S]*?openDownloaderTab">\s*下载器\s*<span/)
  assert.match(downloadsSource, /activeTab === 'indexer'[\s\S]*?openIndexerTab">\s*下载源\s*<span/)
  assert.match(downloadsSource, /下载器已保存/)
  assert.doesNotMatch(downloadsSource, /下载源已保存/)
})

test('downloads source management includes AVDB setup and return workflow', () => {
  assert.match(downloadsSource, /下载源/)
  assert.match(downloadsSource, /api\.getAvdbStatus\(\)/)
  assert.match(downloadsSource, /api\.createSource\(/)
  assert.match(downloadsSource, /job:\s*'avdb_sync'/)
  assert.match(downloadsSource, /return_to:\s*'\/downloads\?tab=indexer&source=avdb'/)
  assert.match(downloadsSource, /@save-editor="saveSourceEditor"/)
  assert.match(downloadsSource, /@view-avdb-job="viewAvdbJob"/)
})

test('downloads polls running AVDB syncs without overlapping requests', () => {
  assert.match(downloadsSource, /setInterval\(this\.pollAvdbStatus, 5000\)/)
  assert.match(downloadsSource, /avdbStatusRequestPending/)
  assert.match(downloadsSource, /if \(this\.avdbStatusRequestPending\) return null/)
  assert.match(downloadsSource, /this\.avdbStatusKnown = true/)

  const poll = methodSource('pollAvdbStatus')
  assert.match(poll, /this\.activeTab !== 'indexer'/)
  assert.match(poll, /this\.sourceSnapshot\.sources/)
  assert.match(poll, /item\.id === 'avdb'/)
  assert.match(poll, /shouldPollAvdb\(this\.avdbStatus\)/)
  assert.match(poll, /shouldPollAvdb\(avdbRow\)/)
  assert.match(poll, /this\.sourceBusyId/)
  assert.match(poll, /api\.getSourceConfig\(\)/)
})

test('source config failures stay retryable on tab re-entry', () => {
  const load = methodSource('loadSources')
  assert.match(load, /Promise\.allSettled/)
  assert.match(load, /api\.getSourceConfig\(\)/)
  assert.match(load, /this\.fetchAvdbStatus\(\)/)
  assert.match(load, /snapshotResult\.status === 'fulfilled'/)
  assert.match(load, /requestId === this\.sourceSnapshotRequestId/)
  assert.match(load, /finally[\s\S]*this\.sourceLoading = false/)
  assert.doesNotMatch(load, /this\.sourceSnapshot\s*=\s*\{\s*builtins:\s*\[\]/)
  assert.doesNotMatch(load, /this\.sourceEditor\s*=/)
  assert.doesNotMatch(load, /this\.sourceEditorError\s*=/)
})

test('downloads wires the dedicated snapshot source panel contract', () => {
  for (const binding of [
    ':snapshot="sourceSnapshot"',
    ':loading="sourceLoading"',
    ':busy-source-id="sourceBusyId"',
    ':editor="sourceEditor"',
    ':editor-error="sourceEditorError"',
    ':avdb-status="avdbStatus"',
    '@refresh="loadSources"',
    '@create="openNewSource"',
    '@edit="editSource"',
    '@toggle="toggleSource"',
    '@remove="removeSource"',
    '@save-editor="saveSourceEditor"',
    '@close-editor="closeSourceEditor"',
    '@view-avdb-job="viewAvdbJob"',
  ]) {
    assert.ok(downloadsSource.includes(binding), `missing source panel binding: ${binding}`)
  }

  assert.match(downloadsSource, /sourceSnapshot:\s*\{\s*builtins:\s*\[\],\s*sources:\s*\[\],\s*types:\s*\[\]\s*\}/)
  assert.match(downloadsSource, /sourceEditor:\s*\{\s*open:\s*false,\s*mode:\s*'new',\s*draft:\s*null\s*\}/)
  assert.doesNotMatch(downloadsSource, /:model-value="torznab"|@save="saveTorznab"|@save-avdb|@setup-avdb/)
  assert.doesNotMatch(downloadsSource, /DEFAULT_TORZNAB|DEFAULT_AVDB|api\.getConfig\(\)|api\.updateConfig\(/)
})

test('source payloads whitelist backend fields and never leak management metadata', () => {
  const sourcePayload = evaluateExportedFunction('sourcePayload')
  const draft = {
    id: 'source-1',
    type: 'torznab',
    kind: 'jackett',
    name: 'Jackett',
    enabled: true,
    base_url: 'https://jackett.test',
    api_key: '',
    api_key_configured: true,
    indexer: 'all',
    categories: '5000',
    limit: '30',
    timeout: 12,
    internal_only: 'must not pass',
  }

  assert.deepEqual(sourcePayload(draft), {
    type: 'torznab',
    kind: 'jackett',
    name: 'Jackett',
    enabled: true,
    base_url: 'https://jackett.test',
    api_key: '',
    indexer: 'all',
    categories: '5000',
    limit: 30,
    timeout: 12,
  })
  assert.deepEqual(sourcePayload({ id: 'avdb', type: 'avdb', enabled: true }, true), { type: 'avdb' })
  assert.deepEqual(sourcePayload({ id: 'avdb', type: 'avdb', enabled: false }), {
    type: 'avdb',
    enabled: false,
  })
})

test('enabled source count comes entirely from the backend snapshot', () => {
  const countEnabledSources = evaluateExportedFunction('countEnabledSources')
  assert.equal(countEnabledSources({
    builtins: [{ id: 'm3u8', enabled: true }],
    sources: [
      { id: 'one', enabled: true },
      { id: 'two', enabled: false },
      { id: 'avdb', enabled: true },
    ],
  }), 3)
  assert.equal(countEnabledSources(), 0)
})

test('source editor adopts the server snapshot before closing or navigating', () => {
  const save = methodSource('saveSourceEditor')
  const snapshotIndex = save.indexOf('this.sourceSnapshot = nextSnapshot')
  const closeIndex = save.indexOf('this.closeSourceEditor')
  const navigateIndex = save.indexOf('this.viewAvdbJob')

  assert.match(save, /api\.createSource\(sourcePayload\(draft, true\)\)/)
  assert.match(save, /api\.updateSource\(draft\.id, sourcePayload\(draft\)\)/)
  assert.match(save, /nextSnapshot\.sources\.find\(item => item\.id === 'avdb'\)/)
  assert.match(save, /isNewAvdb && !createdAvdb\?\.available/)
  assert.ok(snapshotIndex >= 0 && closeIndex > snapshotIndex, 'snapshot should be adopted before closing')
  assert.ok(navigateIndex > closeIndex, 'AVDB navigation should happen after the editor closes')

  const catchStart = save.indexOf('catch (error)')
  const finallyStart = save.indexOf('finally', catchStart)
  const failure = save.slice(catchStart, finallyStart)
  assert.match(failure, /this\.sourceEditorError\s*=/)
  assert.doesNotMatch(failure, /this\.sourceSnapshot\s*=|this\.closeSourceEditor|this\.sourceEditor\s*=/)
})

test('source row mutations are confirmed and never update the list optimistically', () => {
  const toggle = methodSource('toggleSource')
  const removeSource = methodSource('removeSource')

  assert.match(toggle, /await api\.updateSource\(item\.id,/)
  assert.ok(
    toggle.indexOf('this.sourceSnapshot = nextSnapshot') > toggle.indexOf('await api.updateSource'),
    'toggle should adopt only the server response',
  )
  assert.match(removeSource, /await requestConfirm\(/)
  assert.match(removeSource, /await api\.deleteSource\(item\.id\)/)
  assert.ok(
    removeSource.indexOf('this.sourceSnapshot = nextSnapshot') > removeSource.indexOf('await api.deleteSource'),
    'remove should adopt only the server response',
  )
  assert.doesNotMatch(toggle, /\.map\(|item\.enabled\s*=/)
  assert.doesNotMatch(removeSource, /\.filter\(/)
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
