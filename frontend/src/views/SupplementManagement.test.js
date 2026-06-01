import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

const source = readFileSync(new URL('./SupplementManagement.vue', import.meta.url), 'utf8')
const actorPicker = readFileSync(new URL('../features/supplement/ActorPickerView.vue', import.meta.url), 'utf8')
const jobList = readFileSync(new URL('../features/supplement/SupplementJobList.vue', import.meta.url), 'utf8')
const sourceHealthPanel = readFileSync(new URL('../features/supplement/SourceHealthPanel.vue', import.meta.url), 'utf8')
const supplementFeatureSource = [source, actorPicker, jobList, sourceHealthPanel].join('\n')
const app = readFileSync(new URL('../App.vue', import.meta.url), 'utf8')

function cssBlock(content, selector) {
  const blocks = [...content.matchAll(/([^{}]+)\{([^{}]*)\}/g)]
  const match = blocks.find(([, selectors]) => selectors
    .split(',')
    .map(part => part.trim())
    .includes(selector))
  assert.ok(match, `${selector} block should exist`)
  return match[2]
}

test('supplement management shows and controls actor context when routed from an actor', () => {
  assert.match(source, /v-if="actorContext"/)
  assert.match(source, /class="actor-context-card"/)
  assert.match(source, /api\.getActress\(normalized\)/)
  assert.match(source, /clearActorContext\(\)/)
  assert.match(source, /goActorContext\(\)/)
  assert.match(source, /applyJobActorContext\(job\)/)
})

test('supplement management keeps jobs and movies scoped to actor context', () => {
  assert.match(source, /applyActorContext\(actressId\)/)
  assert.match(source, /this\.jobFilters\.actress_id = normalized/)
  assert.match(source, /this\.movieFilters\.actress_id = normalized/)
  assert.match(source, /jobActorLabel\(job\)/)
})

test('supplement management lets users search and select an actor instead of typing ids', () => {
  assert.match(source, /v-model:keyword="actorSearchKeyword"/)
  assert.match(source, /searchActorContext\(\)/)
  assert.match(source, /selectActorContext/)
  assert.match(source, /api\.searchActors\(keyword\)/)
  assert.match(actorPicker, /v-for="actor in actors"/)
  assert.match(source, /actorChoiceCards/)
  assert.match(actorPicker, /ActorPortraitCard/)
  assert.match(actorPicker, /density="compact"/)
  assert.match(actorPicker, /action-label="选择"/)
  assert.doesNotMatch(actorPicker, /class="actor-choice-card apple-surface"/)
  assert.doesNotMatch(actorPicker, /class="select-orb"/)
  assert.doesNotMatch(supplementFeatureSource, /placeholder="演员 ID"/)
})

test('supplement management defaults to an actor-first selection view', () => {
  assert.match(source, /补全演员/)
  assert.match(source, /v-if="showActorPicker"/)
  assert.match(actorPicker, /class="actor-search-panel apple-surface"/)
  assert.match(actorPicker, /class="actor-choice-grid"/)
  assert.match(source, /recentActorJobs/)
})

test('supplement management builds recent actor cards without fanout actor detail requests', () => {
  const loadRecentActorJobsBlock = source.match(/async loadRecentActorJobs\(\{ silent = false \} = \{\}\) \{[\s\S]*?\n    \},/)?.[0] || ''

  assert.match(loadRecentActorJobsBlock, /api\.listSupplementJobs\(\{ page: 1, page_size: 16 \}\)/)
  assert.match(loadRecentActorJobsBlock, /this\.recentActors = this\.recentActorJobs\.map\(this\.recentActorFromJob\)/)
  assert.match(source, /recentActorFromJob\(job\)/)
  assert.doesNotMatch(loadRecentActorJobsBlock, /loadRecentActors|api\.getActress/)
  assert.doesNotMatch(source, /api\.getActress\(job\.local_actress_id\)/)
})

test('supplement management uses an actor workspace with segmented panels', () => {
  assert.match(source, /class="actor-workspace-hero apple-surface"/)
  assert.match(source, /workspaceSegments/)
  assert.match(source, /activeWorkspaceSegment/)
  assert.match(source, /作品字段/)
  assert.match(source, /任务队列/)
  assert.match(source, /来源诊断/)
  assert.match(sourceHealthPanel, /来源状态/)
  assert.match(jobList, /jobAttemptMeta/)
  assert.match(jobList, /next_run_at/)
  assert.match(source, /getSupplementActressStatus\(normalized\)/)
  assert.match(source, /startSupplementFilmographyJob\(this\.actorContext\.id\)/)
  assert.match(source, /refreshSupplementActressResolved\(this\.actorContext\.id\)/)
  assert.match(source, /生成下载候选/)
  assert.match(source, /createDownloadCandidates/)
  assert.match(source, /api\.createSupplementDownloadCandidates\(params\)/)
  assert.match(source, /path: '\/downloads'/)
  assert.match(source, /source: 'supplement'/)
})

test('supplement management exposes source health and manual correction controls', () => {
  assert.match(source, /api\.listSupplementSourcesHealth\(\)/)
  assert.match(source, /api\.listSupplementSourcesBudgets\(\)/)
  assert.match(source, /sourceHealthRows/)
  assert.match(sourceHealthPanel, /当前预算/)
  assert.match(source, /api\.pauseSupplementSource/)
  assert.match(source, /api\.resumeSupplementSource/)
  assert.match(source, /已暂停/)
  assert.match(source, /manual-match-bar/)
  assert.match(source, /manualMatchMovie/)
  assert.match(source, /api\.matchSupplementMovie/)
  assert.match(source, /api\.ignoreSupplementMovie/)
  assert.match(source, /api\.unmatchSupplementMovie/)
  assert.match(source, /manual_actions/)
  assert.match(source, /人工校正记录/)
})

test('supplement management exposes global gfriends avatar sync controls', () => {
  assert.match(source, /openSourceHealth\(\)/)
  assert.match(source, /showSourceHealthGlobal/)
  assert.match(source, /requestConfirm/)
  assert.match(source, /syncGfriendsAvatars/)
  assert.match(source, /api\.startGfriendsAvatarSyncJob\(\)/)
  assert.match(source, /loadGfriendsAvatarJob/)
  assert.match(source, /_startGfriendsAvatarPolling/)
  assert.match(source, /source: 'gfriends'/)
  assert.match(sourceHealthPanel, /头像覆盖作业/)
  assert.match(sourceHealthPanel, /同步演员头像/)
  assert.match(sourceHealthPanel, /查看头像任务/)
  assert.match(sourceHealthPanel, /匹配头像/)
  assert.match(sourceHealthPanel, /写入覆盖/)
  assert.match(sourceHealthPanel, /已校验/)
  assert.match(sourceHealthPanel, /有效头像/)
  assert.match(sourceHealthPanel, /拉取 gfriends Filetree/)
  assert.match(sourceHealthPanel, /校验图片健康/)
})

test('supplement job list names gfriends avatar sync jobs explicitly', () => {
  assert.match(jobList, /actress_avatar_sync/)
  assert.match(jobList, /gfriends 头像同步/)
})

test('supplement management exposes provider smoke diagnostics', () => {
  assert.match(sourceHealthPanel, /运行诊断/)
  assert.match(source, /runProviderSmoke/)
  assert.match(source, /api\.runSupplementProviderSmoke\(payload\)/)
  assert.match(source, /providerSmokeForm/)
  assert.match(sourceHealthPanel, /source_movie_id/)
  assert.match(source, /自定义样本需要先选择来源/)
  assert.match(sourceHealthPanel, /最近诊断/)
  assert.match(source, /api\.listSupplementProviderSmokeRuns\(5, this\.providerSmokeForm\.source\)/)
  assert.match(supplementFeatureSource, /smokeRunLabel/)
  assert.match(source, /providerSmokeReport/)
  assert.match(sourceHealthPanel, /字段分/)
})

test('source health styles stay in the lazy child chunk', () => {
  assert.match(source, /const SourceHealthPanel = defineAsyncComponent/)
  assert.doesNotMatch(source, /\.avatar-sync-panel\s*\{/)
  assert.doesNotMatch(source, /\.provider-smoke-summary\s*\{/)
  assert.doesNotMatch(source, /\.provider-smoke-card\s*\{/)
  assert.doesNotMatch(source, /\.provider-smoke-history\s*\{/)
  assert.doesNotMatch(source, /\.provider-smoke-run\s*\{/)
  assert.doesNotMatch(source, /\.source-health-card\s*\{/)
  assert.doesNotMatch(source, /\.source-budget-meter\s*\{/)
})

test('supplement management preserves a global queue entry point', () => {
  assert.match(source, /showGlobalQueue/)
  assert.match(source, /openGlobalQueue\(\)/)
  assert.match(source, /全局队列/)
  assert.match(source, /applyJobActorContext\(job\)/)
})

test('supplement management applies routed movie search and resets filtered pages', () => {
  assert.match(source, /const q = typeof this\.\$route\.query\.q === 'string'/)
  assert.match(source, /this\.movieFilters\.q = q/)
  assert.match(source, /this\.moviePage = 1/)
  assert.match(source, /@change="applyMovieFilters"/)
  assert.match(source, /@keyup\.enter="applyMovieFilters"/)
  assert.match(source, /async applyMovieFilters\(\)[\s\S]*this\.moviePage = 1[\s\S]*await this\.loadMovies\(\)/)
  assert.match(source, /@change="applyJobFilters"/)
  assert.match(source, /async applyJobFilters\(\)[\s\S]*this\.jobPage = 1[\s\S]*await this\.loadJobs\(\)/)
  assert.match(source, /if \(this\.movieFilters\.q\) query\.q = this\.movieFilters\.q/)
})

test('supplement management refreshes workspace data when supplement polling finishes', () => {
  assert.match(source, /async refreshSupplementWorkspaceAfterPolling\(\)/)
  assert.match(source, /await this\.refreshSupplementWorkspaceAfterPolling\(\)/)
  assert.match(source, /Promise\.all\(\[[\s\S]*this\.loadJobs\(\{ silent: true \}\)[\s\S]*this\.loadMovies\(\{ silent: true \}\)[\s\S]*this\.loadSupplementStatus\(\{ poll: false \}\)/)
})

test('supplement management creates download candidates from current movie filters', () => {
  assert.match(source, /buildMovieFilterParams\(/)
  assert.match(source, /if \(this\.movieFilters\.matched !== null\) params\.matched = this\.movieFilters\.matched/)
  assert.match(source, /if \(this\.movieFilters\.quality === 'missing_cover'\) params\.missing_cover = true/)
  assert.match(source, /if \(this\.movieFilters\.quality === 'missing_runtime'\) params\.missing_runtime = true/)
  assert.match(source, /if \(this\.movieFilters\.quality === 'missing_maker'\) params\.missing_maker = true/)
  assert.match(source, /if \(this\.movieFilters\.quality === 'missing_categories'\) params\.missing_categories = true/)
  assert.match(source, /if \(this\.movieFilters\.quality === 'low_completeness'\) params\.max_completeness = 2/)
  assert.match(source, /const params = this\.buildMovieFilterParams\(\)/)
  assert.doesNotMatch(source, /buildMovieFilterParams\(\{ limit: 100 \}\)/)
  assert.match(source, /if \(this\.actorContextName\) params\.actress_name = this\.actorContextName/)
})

test('supplement management avoids a remount-style refresh when re-entered', () => {
  assert.match(app, /'SupplementManagement'/)
  assert.match(source, /activated\(\)/)
  assert.match(source, /wasDeactivated/)
  assert.match(source, /lastAppliedRouteKey/)
  assert.match(source, /replaceSupplementRoute/)
  assert.doesNotMatch(source, /class="supplement-page apple-reveal"/)
})

test('supplement actor picker keeps search glass in the lazy child', () => {
  const pickerSearch = cssBlock(actorPicker, '.search-shell')

  assert.match(pickerSearch, /background:\s*var\(--surface-control\)/)
  assert.match(pickerSearch, /border:\s*1px solid var\(--glass-control-border\)/)
  assert.match(pickerSearch, /box-shadow:\s*var\(--glass-control-shadow\)/)
  assert.match(pickerSearch, /backdrop-filter:\s*blur\(var\(--glass-blur-control\)\)\s*saturate\(var\(--glass-saturate-control\)\)/)

  assert.doesNotMatch(source, /\.supplement-hero\s*\{/)
  assert.doesNotMatch(source, /\.actor-filter-bar\s*\{/)
  assert.doesNotMatch(source, /\.compact-search\s*\{/)
  assert.doesNotMatch(source, /\.actor-result-card\s*,/)
  assert.doesNotMatch(source, /\.recent-actor-row\s*\{/)
  assert.doesNotMatch(source, /\.recent-actor-list\s*\{/)
})

test('supplement workspace rows and filters use shared Apple glass controls', () => {
  const input = cssBlock(source, '.filter-input')
  const inputFocus = cssBlock(source, '.filter-input:focus')
  const movieRow = cssBlock(source, '.ios-row')
  const deepJobRow = cssBlock(source, '.workspace-panel :deep(.ios-row)')
  const jobRow = cssBlock(jobList, '.ios-row')
  const emptyInner = cssBlock(source, '.empty-panel.inner')

  assert.match(input, /background:\s*var\(--surface-control\)/)
  assert.match(input, /border:\s*1px solid var\(--glass-control-border\)/)
  assert.match(input, /box-shadow:\s*var\(--glass-control-shadow\)/)
  assert.match(input, /backdrop-filter:\s*blur\(var\(--glass-blur-control\)\)\s*saturate\(var\(--glass-saturate-control\)\)/)
  assert.match(inputFocus, /background:\s*var\(--surface-input-focus\)/)
  assert.match(inputFocus, /box-shadow:\s*var\(--glass-active-shadow\)/)

  for (const block of [movieRow, deepJobRow, jobRow, emptyInner]) {
    assert.match(block, /background:\s*var\(--surface-control\)/)
    assert.match(block, /border:\s*1px solid var\(--glass-control-border\)/)
    assert.match(block, /box-shadow:\s*var\(--glass-control-shadow\)/)
    assert.match(block, /backdrop-filter:\s*blur\(var\(--glass-blur-control\)\)\s*saturate\(var\(--glass-saturate-control\)\)/)
  }
})

test('supplement diagnostics modal avoids legacy flat surfaces', () => {
  const header = cssBlock(source, '.diagnostics-header')
  const table = cssBlock(source, '.diagnostics-table')
  const row = cssBlock(source, '.diagnostics-row')
  const headRow = cssBlock(source, '.diagnostics-row-head')
  const identityChip = cssBlock(source, '.identity-chip')
  const manualAction = cssBlock(source, '.manual-action-item')

  assert.match(header, /background:\s*var\(--surface-card\)/)
  assert.match(header, /border-bottom:\s*1px solid var\(--glass-control-border\)/)
  assert.match(header, /box-shadow:\s*var\(--glass-surface-shadow\)/)
  assert.match(header, /backdrop-filter:\s*blur\(var\(--glass-blur-surface\)\)\s*saturate\(var\(--glass-saturate-surface\)\)/)

  assert.match(table, /border:\s*1px solid var\(--glass-control-border\)/)
  assert.match(table, /box-shadow:\s*var\(--glass-control-shadow\)/)
  assert.match(table, /background:\s*var\(--surface-control\)/)

  for (const block of [row, identityChip, manualAction]) {
    assert.match(block, /background:\s*var\(--surface-control\)/)
    assert.match(block, /border:\s*1px solid var\(--glass-control-border\)/)
    assert.match(block, /box-shadow:\s*var\(--glass-control-shadow\)/)
    assert.match(block, /backdrop-filter:\s*blur\(var\(--glass-blur-control\)\)\s*saturate\(var\(--glass-saturate-control\)\)/)
  }

  assert.match(headRow, /background:\s*var\(--glass-active-material\)/)
  assert.match(headRow, /box-shadow:\s*var\(--glass-active-shadow\)/)
})

test('supplement source diagnostics use shared Apple glass materials', () => {
  const input = cssBlock(sourceHealthPanel, '.filter-input')
  const inputFocus = cssBlock(sourceHealthPanel, '.filter-input:focus')
  const avatarPanel = cssBlock(sourceHealthPanel, '.avatar-sync-panel')
  const avatarMetric = cssBlock(sourceHealthPanel, '.avatar-sync-metrics div')
  const smokeSummary = cssBlock(sourceHealthPanel, '.provider-smoke-summary')
  const smokeHistory = cssBlock(sourceHealthPanel, '.provider-smoke-history')
  const smokeRun = cssBlock(sourceHealthPanel, '.provider-smoke-run')
  const smokeRunHover = cssBlock(sourceHealthPanel, '.provider-smoke-run:hover')
  const smokeCard = cssBlock(sourceHealthPanel, '.provider-smoke-card')
  const sourceCard = cssBlock(sourceHealthPanel, '.source-health-card')
  const budgetMeter = cssBlock(sourceHealthPanel, '.source-budget-meter')

  assert.match(input, /background:\s*var\(--surface-control\)/)
  assert.match(input, /border:\s*1px solid var\(--glass-control-border\)/)
  assert.match(input, /box-shadow:\s*var\(--glass-control-shadow\)/)
  assert.match(input, /backdrop-filter:\s*blur\(var\(--glass-blur-control\)\)\s*saturate\(var\(--glass-saturate-control\)\)/)
  assert.match(inputFocus, /background:\s*var\(--surface-input-focus\)/)
  assert.match(inputFocus, /box-shadow:\s*var\(--glass-active-shadow\)/)

  for (const block of [avatarPanel, smokeSummary, smokeHistory, sourceCard]) {
    assert.match(block, /background:\s*var\(--surface-card\)/)
    assert.match(block, /border:\s*1px solid var\(--glass-control-border\)/)
    assert.match(block, /box-shadow:\s*var\(--glass-surface-shadow\)/)
    assert.match(block, /backdrop-filter:\s*blur\(var\(--glass-blur-surface\)\)\s*saturate\(var\(--glass-saturate-surface\)\)/)
  }

  for (const block of [avatarMetric, smokeRun, smokeCard, budgetMeter]) {
    assert.match(block, /background:\s*var\(--surface-control\)/)
    assert.match(block, /border:\s*1px solid var\(--glass-control-border\)/)
    assert.match(block, /box-shadow:\s*var\(--glass-control-shadow\)/)
    assert.match(block, /backdrop-filter:\s*blur\(var\(--glass-blur-control\)\)\s*saturate\(var\(--glass-saturate-control\)\)/)
  }

  assert.match(smokeRunHover, /background:\s*var\(--surface-control-hover\)/)
  assert.match(smokeRunHover, /border-color:\s*var\(--glass-control-border-hover\)/)
  assert.match(smokeRunHover, /box-shadow:\s*var\(--glass-control-shadow-hover\)/)
})
