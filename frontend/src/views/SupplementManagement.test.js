import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

const vueSource = readFileSync(new URL('./SupplementManagement.vue', import.meta.url), 'utf8')
const externalStyle = readFileSync(new URL('../features/supplement/supplementManagement.css', import.meta.url), 'utf8')
const actorPicker = readFileSync(new URL('../features/supplement/ActorPickerView.vue', import.meta.url), 'utf8')
const jobList = readFileSync(new URL('../features/supplement/SupplementJobList.vue', import.meta.url), 'utf8')
const sourceHealthPanelVue = readFileSync(new URL('../features/supplement/SourceHealthPanel.vue', import.meta.url), 'utf8')
const sourceHealthStyle = readFileSync(new URL('../features/supplement/sourceHealthPanel.css', import.meta.url), 'utf8')
const sourceHealthPanel = `${sourceHealthPanelVue}\n${sourceHealthStyle}`
const moviesPanel = readFileSync(new URL('../features/supplement/SupplementMoviesPanel.vue', import.meta.url), 'utf8')
const diagnosticsDialog = readFileSync(new URL('../features/supplement/SupplementSourceDiagnosticsDialog.vue', import.meta.url), 'utf8')
const moviesStyle = [
  readFileSync(new URL('../features/supplement/supplementMoviesPanel.css', import.meta.url), 'utf8'),
  readFileSync(new URL('../features/supplement/supplementMovieRepair.css', import.meta.url), 'utf8'),
].join('\n')
const diagnosticsStyle = [
  readFileSync(new URL('../features/supplement/supplementSourceDiagnosticsDialog.css', import.meta.url), 'utf8'),
  readFileSync(new URL('../features/supplement/supplementDiagnosticsFields.css', import.meta.url), 'utf8'),
].join('\n')
const jobsTab = readFileSync(new URL('../features/supplement/JobsTab.vue', import.meta.url), 'utf8')
const moviesTab = readFileSync(new URL('../features/supplement/MoviesTab.vue', import.meta.url), 'utf8')
const sourcesHealthTab = readFileSync(new URL('../features/supplement/SourcesHealthTab.vue', import.meta.url), 'utf8')
const repairLaneTab = readFileSync(new URL('../features/supplement/RepairLaneTab.vue', import.meta.url), 'utf8')
const useSupplementApi = readFileSync(new URL('../features/supplement/useSupplementApi.js', import.meta.url), 'utf8')
const supplementFeatureSource = [vueSource, actorPicker, jobList, sourceHealthPanel, moviesPanel, diagnosticsDialog, jobsTab, moviesTab, sourcesHealthTab, repairLaneTab, useSupplementApi].join('\n')

function cssBlock(content, selector) {
  const blocks = [...content.matchAll(/([^{}]+)\{([^{}]*)\}/g)]
  const match = blocks.find(([, selectors]) => selectors
    .split(',')
    .map(part => part.trim())
    .includes(selector))
  assert.ok(match, `${selector} block should exist`)
  return match[2]
}

function backgroundIncludes(block, token) {
  const match = block.match(/background:\s*([^;]+);/)
  return Boolean(match && match[1].includes(token))
}

function assertLayeredBackground(block, token, name) {
  assert.ok(backgroundIncludes(block, token), `${name} should include ${token}`)
  assert.match(block, /var\(--surface-specular-edge/, `${name} should include a specular edge layer`)
  assert.match(block, /var\(--surface-noise\)/, `${name} should include the shared noise layer`)
}

test('supplement management is a tab shell under the task line budget', () => {
  assert.ok(vueSource.split('\n').length < 400, 'SupplementManagement.vue should stay below 400 lines')
  assert.match(vueSource, /activeTab/)
  assert.match(vueSource, /tabItems/)
  assert.match(vueSource, /JobsTab/)
  assert.match(vueSource, /MoviesTab/)
  assert.match(vueSource, /SourcesHealthTab/)
  assert.match(vueSource, /RepairLaneTab/)
  assert.match(vueSource, /<component\s*:is="activeTabComponent"/)
  assert.match(vueSource, /@jobs-requested="setActiveTab\('jobs'\)"/)
  assert.match(vueSource, /@movies-requested="setActiveTab\('movies'\)"/)
  assert.match(vueSource, /@sources-opened="openSourcesFromMovie"/)
  assert.doesNotMatch(vueSource, /SupplementMoviesPanel/)
  assert.doesNotMatch(vueSource, /SourceHealthPanel/)
  assert.doesNotMatch(vueSource, /SupplementSourceDiagnosticsDialog/)
})

test('supplement management preserves actor context and route coordination', () => {
  assert.match(vueSource, /v-if="showActorPicker"/)
  assert.match(vueSource, /actorPickerError:\s*''/)
  assert.match(vueSource, /actorPickerLoadFailed\(\)/)
  assert.match(vueSource, /api\.searchActors\(keyword\)/)
  assert.match(vueSource, /api\.listSupplementJobs\(\{ page: 1, page_size: 16 \}\)/)
  assert.match(vueSource, /api\.getActress\(normalized\)/)
  assert.match(vueSource, /api\.getSupplementActressStatus\(this\.actorContext\.id\)/)
  assert.match(vueSource, /api\.startSupplementFilmographyJob\(this\.actorContext\.id\)/)
  assert.match(vueSource, /api\.refreshSupplementActressResolved\(this\.actorContext\.id\)/)
  assert.match(vueSource, /replaceSupplementRoute/)
  assert.match(vueSource, /supplementRouteTab/)
  assert.match(vueSource, /this\.\$route\.path\.startsWith\('\/supplement\/'\)/)
  assert.match(vueSource, /openGlobalQueue/)
  assert.match(vueSource, /openSourceHealth/)
  assert.match(vueSource, /viewGfriendsAvatarJobs/)
})

test('supplement management keeps heavyweight behavior inside supplement feature tabs', () => {
  assert.match(useSupplementApi, /export function useSupplementApi/)
  assert.match(jobsTab, /SupplementJobList/)
  assert.match(jobsTab, /loadJobs/)
  assert.match(jobsTab, /retryJob/)
  assert.match(moviesTab, /SupplementMoviesPanel/)
  assert.match(moviesTab, /loadMovies/)
  assert.match(moviesTab, /createDownloadCandidates/)
  assert.match(sourcesHealthTab, /SourceHealthPanel/)
  assert.match(sourcesHealthTab, /loadSourceHealth/)
  assert.match(sourcesHealthTab, /requestConfirm/)
  assert.match(repairLaneTab, /SupplementSourceDiagnosticsDialog/)
  assert.match(repairLaneTab, /openMovieSources/)
  assert.match(repairLaneTab, /manualMatchMovie/)
})

test('supplement management keeps heavyweight styles in external scoped stylesheets', () => {
  assert.match(vueSource, /<style scoped src="\.\.\/features\/supplement\/supplementManagement\.css"><\/style>/)
  assert.match(moviesPanel, /<style scoped src="\.\/supplementMoviesPanel\.css"><\/style>/)
  assert.match(moviesPanel, /<style scoped src="\.\/supplementMovieRepair\.css"><\/style>/)
  assert.match(sourceHealthPanelVue, /<style scoped src="\.\/sourceHealthPanel\.css"><\/style>/)
  assert.match(diagnosticsDialog, /<style scoped src="\.\/supplementSourceDiagnosticsDialog\.css"><\/style>/)
  assert.match(diagnosticsDialog, /<style scoped src="\.\/supplementDiagnosticsFields\.css"><\/style>/)
  assert.ok(`${externalStyle}\n${moviesStyle}\n${sourceHealthStyle}\n${diagnosticsStyle}`.length > 15000)
})

test('supplement actor picker stays actor-first and avoids raw actor id entry', () => {
  assert.match(vueSource, /补全演员/)
  assert.match(actorPicker, /class="actor-search-panel apple-surface"/)
  assert.match(actorPicker, /class="actor-choice-grid"/)
  assert.match(actorPicker, /ActorPortraitCard/)
  assert.match(actorPicker, /density="compact"/)
  assert.match(actorPicker, /action-label="选择"/)
  assert.match(actorPicker, /title: '补全队列不可用'/)
  assert.match(actorPicker, /title: '暂无可选演员'/)
  assert.doesNotMatch(supplementFeatureSource, /placeholder="演员 ID"/)
})

test('supplement movie panel presents the field-gap ledger and field-chip rows', () => {
  // Wave A redesign: only the toolbar + 字段缺口 ledger + 影片行 (field-chip grid + 匹配 pill + 补详情/诊断)
  // remain on screen. The earlier 优先级 / 分拣台 / 修复队列 / 处理线 dense layers are intentionally dropped
  // until the v2 visual language is finalized.
  assert.match(moviesPanel, /class="movies-panel-toolbar"/)
  assert.match(moviesPanel, /class="movie-field-ledger"/)
  assert.match(moviesPanel, /class="field-card"/)
  assert.match(moviesPanel, /class="fc-fieldgrid"/)
  assert.match(moviesPanel, /v-model="movieFilters\.matched"[\s\S]*matchFilterOptions/)
  assert.match(moviesPanel, /@change="\$emit\('apply-filters'\)"/)
  assert.match(moviesPanel, /@keyup\.enter="\$emit\('apply-filters'\)"/)
  assert.match(moviesPanel, /movieFieldSummaryRows/)
  assert.match(moviesPanel, /movieFieldChips\(movie\)/)
  assert.match(moviesPanel, /movieMatchLabel\(movie\)/)
  assert.match(moviesPanel, /当前页字段缺口/)
  assert.match(moviesPanel, /批量补详情/)
  assert.match(moviesPanel, /生成下载候选/)
  assert.match(moviesStyle, /\.movie-field-ledger/)
  assert.match(moviesStyle, /\.field-card/)
  assert.match(moviesStyle, /\.field-chip/)
})

test('supplement source health tab exposes diagnostics and gfriends controls', () => {
  assert.match(sourceHealthPanel, /来源状态/)
  assert.match(sourceHealthPanel, /当前预算/)
  assert.match(sourceHealthPanel, /运行诊断/)
  assert.match(sourceHealthPanel, /最近诊断/)
  assert.match(sourceHealthPanel, /头像覆盖作业/)
  assert.match(sourceHealthPanel, /同步演员头像/)
  assert.match(sourceHealthPanel, /查看头像任务/)
  assert.match(useSupplementApi, /startGfriendsAvatarSyncJob/)
  assert.match(useSupplementApi, /runSupplementProviderSmoke\(payload\)/)
  assert.match(useSupplementApi, /listSupplementProviderSmokeRuns\(5, providerSmokeForm\.value\.source\)/)
  assert.match(useSupplementApi, /listSupplementSourcesHealth\(\)/)
  assert.match(useSupplementApi, /listSupplementSourcesBudgets\(\)/)
  assert.match(useSupplementApi, /pauseSupplementSource/)
  assert.match(useSupplementApi, /resumeSupplementSource/)
})

test('supplement repair lane exposes diagnostics launchpad and manual correction controls', () => {
  assert.match(repairLaneTab, /class="diagnostics-launchpad"/)
  assert.match(repairLaneTab, /class="diagnostics-launchpad-grid"/)
  assert.match(repairLaneTab, /diagnosticsLaunchpadRows/)
  assert.match(repairLaneTab, /diagnosticsFocusMovie/)
  assert.match(repairLaneTab, /openDiagnosticsFocusMovie/)
  assert.match(repairLaneTab, /manualMatchMovie/)
  assert.match(repairLaneTab, /manualIgnoreMovie/)
  assert.match(repairLaneTab, /manualUnmatchMovie/)
  assert.match(useSupplementApi, /api\.getSupplementMovieSources/)
  assert.match(useSupplementApi, /api\.matchSupplementMovie/)
  assert.match(useSupplementApi, /api\.ignoreSupplementMovie/)
  assert.match(useSupplementApi, /api\.unmatchSupplementMovie/)
  assert.match(diagnosticsDialog, /manual-match-bar/)
  assert.match(diagnosticsDialog, /manual_actions/)
  assert.match(diagnosticsDialog, /人工校正记录/)
})

test('supplement embedded panels use shared state components with next actions', () => {
  for (const [name, panel] of [
    ['SupplementMoviesPanel', moviesPanel],
    ['SupplementJobList', jobList],
    ['ActorPickerView', actorPicker],
    ['SourceHealthPanel', sourceHealthPanel],
  ]) {
    assert.doesNotMatch(panel, /<div[^>]+class="loading-wrap"[\s\S]{0,120}<div class="spinner-large"><\/div>/, `${name} should not show an isolated spinner`)
    assert.doesNotMatch(panel, />加载中\.\.\.</, `${name} should use skeleton copy instead of bare loading text`)
    assert.doesNotMatch(panel, /class="(?:empty-inline|empty-panel)[^"]*"[^>]*>暂无[^<]*<\/(?:div|small)>/, `${name} should not leave a one-line empty state`)
  }
  assert.match(moviesPanel, /AppleSkeleton/)
  assert.match(moviesPanel, /AppleEmptyState/)
  assert.match(jobList, /AppleSkeleton/)
  assert.match(jobList, /AppleEmptyState/)
  assert.match(sourceHealthPanel, /AppleSkeleton/)
  assert.match(sourceHealthPanel, /AppleEmptyState/)
})

test('supplement workspace segmented controls use shared Apple glass materials', () => {
  const segmented = cssBlock(externalStyle, '.segmented-control')
  assertLayeredBackground(segmented, '--material-glass-control', 'supplement segmented control')
  assert.match(segmented, /border:\s*1px solid var\(--glass-control-border\)/)
  assert.match(segmented, /box-shadow:\s*var\(--glass-control-shadow\)/)

  const segmentButton = cssBlock(externalStyle, '.segmented-control button')
  assertLayeredBackground(segmentButton, '--material-glass-subtle', 'supplement segmented button')
  assert.match(segmentButton, /border:\s*1px solid transparent/)

  const activeButton = cssBlock(externalStyle, '.segmented-control button.active')
  assertLayeredBackground(activeButton, '--glass-active-material', 'supplement segmented active button')
  assert.match(activeButton, /border-color:\s*var\(--glass-active-border\)/)
})

test('supplement status and source badges use semantic layered glass tokens', () => {
  const defaultStatus = cssBlock(externalStyle, '.status-pill')
  const succeeded = cssBlock(externalStyle, '.status-succeeded')
  const running = cssBlock(externalStyle, '.status-running')
  const failed = cssBlock(externalStyle, '.status-failed')
  const movieDefault = cssBlock(moviesStyle, '.status-pill')
  const matched = cssBlock(moviesStyle, '.match-matched')
  const candidate = cssBlock(moviesStyle, '.match-candidate')
  const sourceHealthy = cssBlock(sourceHealthStyle, '.health-healthy')
  const sourceDegraded = cssBlock(sourceHealthStyle, '.health-degraded')

  for (const [block, label] of [[defaultStatus, 'default'], [movieDefault, 'movie']]) {
    assertLayeredBackground(block, '--badge-info-bg', label)
  }
  for (const [block, label] of [[succeeded, 'succeeded'], [matched, 'matched'], [sourceHealthy, 'healthy']]) {
    assertLayeredBackground(block, '--badge-success-bg', label)
  }
  for (const [block, label] of [[running, 'running'], [candidate, 'candidate'], [sourceDegraded, 'degraded']]) {
    assertLayeredBackground(block, '--badge-warning-bg', label)
  }
  for (const [block, label] of [[failed, 'failed']]) {
    assertLayeredBackground(block, '--badge-error-bg', label)
  }
})
