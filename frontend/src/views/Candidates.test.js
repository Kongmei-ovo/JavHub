import test from 'node:test'
import assert from 'node:assert/strict'
import { existsSync, readFileSync } from 'node:fs'

// Wave P1-1 smoke: the new /candidates page is a thin shell that consumes the
// shared useDownloadCandidates composable and mounts DownloadCandidatePanel.
// The truth source for behavior is the composable; here we just verify the
// integration contract (composable wiring, panel mount, panel prop/event surface).

const candidatesView = readFileSync(new URL('./Candidates.vue', import.meta.url), 'utf8')
const composableUrl = new URL('../features/candidates/useDownloadCandidates.js', import.meta.url)
const composable = existsSync(composableUrl) ? readFileSync(composableUrl, 'utf8') : ''
const router = readFileSync(new URL('../router/index.js', import.meta.url), 'utf8')
const navigation = readFileSync(new URL('../appNavigation.js', import.meta.url), 'utf8')
const panel = readFileSync(new URL('../features/candidates/DownloadCandidatePanel.vue', import.meta.url), 'utf8')
const panelStyle = readFileSync(new URL('../features/candidates/downloadCandidatePanel.css', import.meta.url), 'utf8')

function cssBlock(selector) {
  const blocks = [...panelStyle.matchAll(/([^{}]+)\{([^{}]*)\}/g)]
  const match = blocks.find(([, selectors]) => selectors
    .split(',')
    .map(part => part.trim())
    .includes(selector))
  assert.ok(match, `${selector} block should exist`)
  return match[2]
}

test('Candidates view mounts the shared candidate workspace', () => {
  assert.match(candidatesView, /class="candidates-page page-shell page-shell--gallery"/)
  assert.match(candidatesView, /<h1>候选确认<\/h1>/)
  assert.match(candidatesView, /<DownloadCandidatePanel/)
  assert.match(candidatesView, /import { useDownloadCandidates } from '\.\.\/features\/candidates\/useDownloadCandidates\.js'/)
  assert.match(candidatesView, /useDownloadCandidates\(\{[\s\S]*routePath:\s*'\/candidates'[\s\S]*syncRoute:\s*true[\s\S]*\}\)/)
})

test('Candidates view forwards every DownloadCandidatePanel emit', () => {
  // The shell forwards the complete panel event surface.
  const emits = [...panel.matchAll(/\$emit\('([^']+)'/g)].map((m) => m[1])
  assert.ok(emits.length >= 25, 'panel should declare a complete emit surface')
  const unique = [...new Set(emits)]
  for (const emit of unique) {
    const attr = `@${emit}=`
    assert.ok(
      candidatesView.includes(attr),
      `Candidates.vue should forward emit "${emit}" from DownloadCandidatePanel`,
    )
  }
})

test('Candidates view exposes composable state to the panel template', () => {
  // Each prop the panel requires should resolve from the composable's return.
  for (const prop of [
    'candidate-filter',
    'candidate-stats',
    'selecting-candidates',
    'selected-candidate-ids',
    'candidate-batch-processing',
    'bulk-candidate-loading',
    'candidate-runs',
    'candidate-runs-loading',
    'candidate-total-pages',
    'candidate-page',
    'candidate-total',
    'candidate-repair-scope',
    'filtered-candidates',
    'candidate-mutations',
    'magnet-editor',
    'candidate-detail',
  ]) {
    assert.match(
      candidatesView,
      new RegExp(`:${prop}="`),
      `Candidates.vue should bind panel prop ${prop}`,
    )
  }
})

test('Candidates view loads + reacts to route query changes', () => {
  assert.match(candidatesView, /onMounted\(\(\) => \{[\s\S]*applyRouteQuery\(route\.query\)[\s\S]*reload\(\)[\s\S]*\}\)/)
  assert.match(candidatesView, /watch\(\(\) => route\.query/)
  assert.match(candidatesView, /c\.loadCandidates\(\)/)
  assert.match(candidatesView, /c\.loadCandidateRuns\(\)/)
})

test('Candidates route is registered and reachable from navigation', () => {
  assert.match(router, /path:\s*'\/candidates',\s*name:\s*'Candidates',\s*component:\s*\(\) => import\('\.\.\/views\/Candidates\.vue'\)/)
  assert.match(navigation, /path:\s*'\/candidates',\s*label:\s*'候选确认'/)
  assert.match(navigation, /'\/candidates':\s*\['\/candidates'\]/)
})

test('candidate detail data uses solid content surfaces', () => {
  for (const selector of [
    '.candidate-repair-scope-grid span',
    '.candidate-detail-grid > div',
    '.candidate-detail-magnet',
  ]) {
    const block = cssBlock(selector)
    assert.match(block, /border:\s*1px solid var\(--hairline\)/)
    assert.match(block, /background:\s*var\(--card-2\)/)
    assert.doesNotMatch(block, /material-glass|surface-specular-edge|surface-noise|backdrop-filter/)
  }
})

test('useDownloadCandidates composable preserves all candidate API endpoints', () => {
  // API calls must stay verbatim (no endpoint renames during the move).
  for (const fn of [
    'listDownloadCandidates',
    'getDownloadCandidateSummary',
    'listDownloadCandidateRuns',
    'approveDownloadCandidate',
    'rejectDownloadCandidate',
    'processDownloadCandidate',
    'enrichDownloadCandidateMagnet',
    'bulkRejectDownloadCandidates',
    'bulkRestoreDownloadCandidates',
    'updateDownloadCandidateMagnet',
    'processDownloadCandidates',
    'retryDownloadCandidateRunFailed',
    'getDownloadCandidate',
  ]) {
    assert.ok(composable.includes(`api.${fn}`), `composable should still call api.${fn}`)
  }
})

test('candidate confirmations describe the dispatch target as a downloader', () => {
  assert.match(composable, /发送到当前默认下载器/)
  assert.match(composable, /下发到下载器/)
  assert.doesNotMatch(composable, /默认下载源|下发到下载源/)
})

test('useDownloadCandidates composable exposes the full panel emit surface', () => {
  // Every panel handler must remain exported by the composable.
  for (const exported of [
    'loadCandidates',
    'loadCandidateSummary',
    'loadCandidateRuns',
    'approveCandidate',
    'rejectCandidate',
    'processCandidate',
    'enrichCandidateMagnet',
    'bulkRejectCandidates',
    'bulkRestoreCandidates',
    'enrichVisibleCandidateMagnets',
    'processVisibleCandidates',
    'retryFailedCandidateRun',
    'updateCandidateSearch',
    'submitCandidateSearch',
    'setCandidateStatus',
    'setNeedsMagnet',
    'setCandidateSource',
    'setCandidateLatestEvent',
    'goCandidatePage',
    'applyCandidateRunFilters',
    'toggleCandidateSelection',
    'toggleCandidateSelected',
    'selectAllVisibleCandidates',
    'clearCandidateSelection',
    'editCandidateMagnet',
    'closeMagnetEditor',
    'updateMagnetEditorValue',
    'submitMagnetEditor',
    'openCandidateDetail',
    'closeCandidateDetail',
    'goCandidateActor',
  ]) {
    assert.ok(
      new RegExp(`(?:^|\\s|,)\\s*${exported}(?:\\s*,|\\s*\\}|\\s*$)`, 'm').test(composable),
      `composable should expose ${exported} in its return object`,
    )
  }
})
