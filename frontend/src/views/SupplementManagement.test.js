import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

const vueSource = readFileSync(new URL('./SupplementManagement.vue', import.meta.url), 'utf8')
const externalStyle = readFileSync(new URL('../features/supplement/supplementManagement.css', import.meta.url), 'utf8')
const actorPicker = readFileSync(new URL('../features/supplement/ActorPickerView.vue', import.meta.url), 'utf8')
const jobList = readFileSync(new URL('../features/supplement/SupplementJobList.vue', import.meta.url), 'utf8')
const sourceHealthPanel = readFileSync(new URL('../features/supplement/SourceHealthPanel.vue', import.meta.url), 'utf8')
const moviesPanel = readFileSync(new URL('../features/supplement/SupplementMoviesPanel.vue', import.meta.url), 'utf8')
const diagnosticsDialog = readFileSync(new URL('../features/supplement/SupplementSourceDiagnosticsDialog.vue', import.meta.url), 'utf8')
const moviesStyle = readFileSync(new URL('../features/supplement/supplementMoviesPanel.css', import.meta.url), 'utf8')
const diagnosticsStyle = readFileSync(new URL('../features/supplement/supplementSourceDiagnosticsDialog.css', import.meta.url), 'utf8')
const source = `${vueSource}\n${externalStyle}\n${moviesPanel}\n${moviesStyle}\n${diagnosticsDialog}\n${diagnosticsStyle}`
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

function backgroundIncludes(block, token) {
  const match = block.match(/background:\s*([^;]+);/)
  return Boolean(match && match[1].includes(token))
}

function assertLayeredBackground(block, token, name) {
  assert.ok(backgroundIncludes(block, token), `${name} should include ${token}`)
  assert.match(block, /var\(--surface-specular-edge/, `${name} should include a specular edge layer`)
  assert.match(block, /var\(--surface-noise\)/, `${name} should include the shared noise layer`)
}

test('supplement management shows and controls actor context when routed from an actor', () => {
  assert.match(source, /v-if="actorContext"/)
  assert.match(source, /class="actor-context-card"/)
  assert.match(source, /api\.getActress\(normalized\)/)
  assert.match(source, /clearActorContext\(\)/)
  assert.match(source, /goActorContext\(\)/)
  assert.match(source, /applyJobActorContext\(job\)/)
})

test('supplement management keeps heavyweight styles in an external scoped stylesheet', () => {
  assert.match(vueSource, /<style scoped src="\.\.\/features\/supplement\/supplementManagement\.css"><\/style>/)
  assert.match(moviesPanel, /<style scoped src="\.\/supplementMoviesPanel\.css"><\/style>/)
  assert.match(diagnosticsDialog, /<style scoped src="\.\/supplementSourceDiagnosticsDialog\.css"><\/style>/)
  assert.ok(`${externalStyle}\n${moviesStyle}\n${diagnosticsStyle}`.length > 15000, 'external supplement stylesheets should carry the moved workspace CSS')
  assert.ok(vueSource.split('\n').length < 1500, 'SupplementManagement.vue should stay small enough to review and parse quickly')
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
  assert.match(source, /const SupplementMoviesPanel = defineAsyncComponent/)
  assert.match(source, /const SupplementSourceDiagnosticsDialog = defineAsyncComponent/)
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

test('supplement workspace segmented controls use shared Apple glass materials', () => {
  const segmented = cssBlock(source, '.segmented-control')
  assertLayeredBackground(segmented, '--material-glass-control', 'supplement segmented control')
  assert.match(segmented, /border:\s*1px solid var\(--glass-control-border\)/)
  assert.match(segmented, /box-shadow:\s*var\(--glass-control-shadow\)/)
  assert.match(segmented, /backdrop-filter:\s*blur\(var\(--glass-blur-control\)\)\s*saturate\(var\(--glass-saturate-control\)\)/)

  const segmentButton = cssBlock(source, '.segmented-control button')
  assertLayeredBackground(segmentButton, '--material-glass-subtle', 'supplement segmented button')
  assert.match(segmentButton, /border:\s*1px solid transparent/)
  assert.match(segmentButton, /transition:\s*background var\(--motion-fast\)/)
  assert.doesNotMatch(segmentButton, /background:\s*transparent|border:\s*0|transition:\s*all/)

  const hoverButton = cssBlock(source, '.segmented-control button:hover')
  assertLayeredBackground(hoverButton, '--material-glass-control-hover', 'supplement segmented hovered button')
  assert.match(hoverButton, /border-color:\s*var\(--glass-control-border-hover\)/)

  const activeButton = cssBlock(source, '.segmented-control button.active')
  assertLayeredBackground(activeButton, '--glass-active-material', 'supplement segmented active button')
  assert.match(activeButton, /border-color:\s*var\(--glass-active-border\)/)
  assert.match(activeButton, /box-shadow:\s*var\(--glass-active-shadow\)/)
  assert.doesNotMatch(activeButton, /inset 0 -2px 0/)
  assert.doesNotMatch([segmented, segmentButton, hoverButton, activeButton].join('\n'), /^.*background:\s*var\(--(?:material-glass-control|material-glass-subtle|material-glass-control-hover|glass-active-material)\);.*$/gm)
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

test('supplement job status pills use semantic layered glass tokens', () => {
  const base = cssBlock(jobList, '.status-pill')
  const succeeded = cssBlock(jobList, '.status-succeeded')
  const running = cssBlock(jobList, '.status-running')
  const queued = cssBlock(jobList, '.status-queued')
  const failed = cssBlock(jobList, '.status-failed')

  assert.match(base, /color:\s*var\(--badge-info-text\)/)
  assertLayeredBackground(base, '--badge-info-bg', 'supplement job default status')
  assert.match(base, /border:\s*1px solid var\(--badge-info-border\)/)

  assert.match(succeeded, /color:\s*var\(--badge-success-text\)/)
  assertLayeredBackground(succeeded, '--badge-success-bg', 'supplement job succeeded status')
  assert.match(succeeded, /border-color:\s*var\(--badge-success-border\)/)

  for (const [block, name] of [
    [running, 'supplement job running status'],
    [queued, 'supplement job queued status'],
  ]) {
    assert.match(block, /color:\s*var\(--badge-warning-text\)/, `${name} should keep warning text`)
    assertLayeredBackground(block, '--badge-warning-bg', name)
    assert.match(block, /border-color:\s*var\(--badge-warning-border\)/, `${name} should keep warning border`)
  }

  assert.match(failed, /color:\s*var\(--badge-error-text\)/)
  assertLayeredBackground(failed, '--badge-error-bg', 'supplement job failed status')
  assert.match(failed, /border-color:\s*var\(--badge-error-border\)/)

  for (const block of [base, succeeded, running, queued, failed]) {
    assert.doesNotMatch(block, /rgba\(255,\s*255,\s*255|#[0-9a-f]{3,6}/i)
  }
})

test('supplement workspace status badges use semantic layered glass tokens', () => {
  const defaultStatus = cssBlock(externalStyle, '.status-pill')
  const succeeded = cssBlock(externalStyle, '.status-succeeded')
  const running = cssBlock(externalStyle, '.status-running')
  const queued = cssBlock(externalStyle, '.status-queued')
  const failed = cssBlock(externalStyle, '.status-failed')
  const idle = cssBlock(externalStyle, '.status-idle')
  const movieDefault = cssBlock(moviesStyle, '.status-pill')
  const matched = cssBlock(moviesStyle, '.match-matched')
  const candidate = cssBlock(moviesStyle, '.match-candidate')
  const supplementOnly = cssBlock(moviesStyle, '.match-supplement-only')
  const ignored = cssBlock(moviesStyle, '.match-ignored')

  for (const [block, label] of [
    [defaultStatus, 'workspace default status'],
    [movieDefault, 'workspace movie default status'],
    [supplementOnly, 'workspace supplement-only match'],
    [idle, 'workspace idle status'],
  ]) {
    assertLayeredBackground(block, '--badge-info-bg', label)
    assert.match(block, /color:\s*var\(--badge-info-text\)/, `${label} should keep info text`)
    assert.match(block, /border(?:-color)?:\s*(?:1px solid )?var\(--badge-info-border\)/, `${label} should keep info border`)
  }

  for (const [block, label] of [
    [succeeded, 'workspace succeeded status'],
    [matched, 'workspace matched status'],
  ]) {
    assertLayeredBackground(block, '--badge-success-bg', label)
    assert.match(block, /color:\s*var\(--badge-success-text\)/, `${label} should keep success text`)
    assert.match(block, /border-color:\s*var\(--badge-success-border\)/, `${label} should keep success border`)
  }

  for (const [block, label] of [
    [running, 'workspace running status'],
    [queued, 'workspace queued status'],
    [candidate, 'workspace candidate match'],
  ]) {
    assertLayeredBackground(block, '--badge-warning-bg', label)
    assert.match(block, /color:\s*var\(--badge-warning-text\)/, `${label} should keep warning text`)
    assert.match(block, /border-color:\s*var\(--badge-warning-border\)/, `${label} should keep warning border`)
  }

  assertLayeredBackground(failed, '--badge-error-bg', 'workspace failed status')
  assert.match(failed, /color:\s*var\(--badge-error-text\)/)
  assert.match(failed, /border-color:\s*var\(--badge-error-border\)/)

  assertLayeredBackground(ignored, '--badge-pending-bg', 'workspace ignored match')
  assert.match(ignored, /color:\s*var\(--badge-pending-text\)/)
  assert.match(ignored, /border-color:\s*var\(--badge-pending-border\)/)
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
  assert.match(source, /@apply-filters="applyMovieFilters"/)
  assert.match(moviesPanel, /@change="\$emit\('apply-filters'\)"/)
  assert.match(moviesPanel, /@keyup\.enter="\$emit\('apply-filters'\)"/)
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
  const pickerSearchFocus = cssBlock(actorPicker, '.search-shell:focus-within')

  assert.doesNotMatch(actorPicker, /var\(--surface-control\)|var\(--surface-input-focus\)|var\(--active-border\)/)
  assertLayeredBackground(pickerSearch, '--material-glass-control', 'actor picker search')
  assert.match(pickerSearch, /border:\s*1px solid var\(--glass-control-border\)/)
  assert.match(pickerSearch, /box-shadow:\s*var\(--glass-control-shadow\)/)
  assert.match(pickerSearch, /backdrop-filter:\s*blur\(var\(--glass-blur-control\)\)\s*saturate\(var\(--glass-saturate-control\)\)/)
  assert.match(pickerSearchFocus, /border-color:\s*var\(--glass-active-border\)/)
  assertLayeredBackground(pickerSearchFocus, '--glass-active-material', 'actor picker focused search')
  assert.match(pickerSearchFocus, /box-shadow:\s*var\(--glass-active-shadow\)/)
  assert.doesNotMatch(actorPicker, /^.*background:\s*var\(--(?:material-glass-control|glass-active-material)\);.*$/gm)

  assert.doesNotMatch(source, /\.supplement-hero\s*\{/)
  assert.doesNotMatch(source, /\.actor-filter-bar\s*\{/)
  assert.doesNotMatch(source, /\.compact-search\s*\{/)
  assert.doesNotMatch(source, /\.actor-result-card\s*,/)
  assert.doesNotMatch(source, /\.recent-actor-row\s*\{/)
  assert.doesNotMatch(source, /\.recent-actor-list\s*\{/)
})

test('supplement workspace rows and filters use shared Apple glass controls', () => {
  const input = cssBlock(moviesStyle, '.filter-input')
  const inputFocus = cssBlock(moviesStyle, '.filter-input:focus')
  const movieRow = cssBlock(moviesStyle, '.ios-row')
  const jobRow = cssBlock(jobList, '.ios-row')
  const jobRowHover = cssBlock(jobList, '.ios-row:hover')
  const jobRowFocusWithin = cssBlock(jobList, '.ios-row:focus-within')
  const workspaceAvatar = cssBlock(externalStyle, '.workspace-avatar')
  const jobAvatar = cssBlock(jobList, '.job-avatar')
  const emptyInner = cssBlock(externalStyle, '.empty-panel.inner')
  const movieSpinner = cssBlock(moviesStyle, '.spinner-large')
  const jobSpinner = cssBlock(jobList, '.spinner-large')

  assert.doesNotMatch(source, /var\(--surface-card\)|var\(--surface-control\)|var\(--surface-control-hover\)|var\(--surface-input-focus\)|var\(--bg-secondary\)|var\(--white-20\)|rgba\(255,\s*107,\s*135|#ff6b87|var\(--active-border\)/)
  assert.doesNotMatch(jobList, /var\(--surface-control\)|var\(--bg-secondary\)|var\(--white-20\)/)

  assertLayeredBackground(input, '--material-glass-control', 'supplement filter input')
  assert.match(input, /border:\s*1px solid var\(--glass-control-border\)/)
  assert.match(input, /box-shadow:\s*var\(--glass-control-shadow\)/)
  assert.match(input, /backdrop-filter:\s*blur\(var\(--glass-blur-control\)\)\s*saturate\(var\(--glass-saturate-control\)\)/)
  assert.match(inputFocus, /border-color:\s*var\(--glass-active-border\)/)
  assertLayeredBackground(inputFocus, '--glass-active-material', 'supplement focused filter input')
  assert.match(inputFocus, /box-shadow:\s*var\(--glass-active-shadow\)/)
  assert.doesNotMatch([input, inputFocus].join('\n'), /^.*background:\s*var\(--(?:material-glass-control|glass-active-material)\);.*$/gm)

  for (const block of [movieRow, jobRow]) {
    assertLayeredBackground(block, '--material-glass-control', 'supplement workspace row')
    assert.match(block, /border:\s*1px solid var\(--glass-control-border\)/)
    assert.match(block, /box-shadow:\s*var\(--glass-control-shadow\)/)
    assert.match(block, /backdrop-filter:\s*blur\(var\(--glass-blur-control\)\)\s*saturate\(var\(--glass-saturate-control\)\)/)
  }
  assertLayeredBackground(emptyInner, '--material-glass-control', 'supplement inner empty panel')
  assert.match(emptyInner, /border:\s*1px solid var\(--glass-control-border\)/)
  assert.match(emptyInner, /box-shadow:\s*var\(--glass-control-shadow\)/)
  assert.match(emptyInner, /backdrop-filter:\s*blur\(var\(--glass-blur-control\)\)\s*saturate\(var\(--glass-saturate-control\)\)/)
  assert.doesNotMatch([movieRow, jobRow, emptyInner].join('\n'), /^.*background:\s*var\(--material-glass-control\);.*$/gm)

  assertLayeredBackground(jobRow, '--material-glass-control', 'supplement job row')
  assert.match(jobRow, /border:\s*1px solid var\(--glass-control-border\)/)
  assert.match(jobRow, /box-shadow:\s*var\(--glass-control-shadow\)/)
  assert.match(jobRow, /transition:\s*transform var\(--motion-fast\), background var\(--motion-fast\), border-color var\(--motion-fast\), box-shadow var\(--motion-fast\)/)
  assert.match(jobRow, /backdrop-filter:\s*blur\(var\(--glass-blur-control\)\)\s*saturate\(var\(--glass-saturate-control\)\)/)
  assert.doesNotMatch(jobList, /^.*background:\s*var\(--material-glass-control\);.*$/gm)

  assertLayeredBackground(jobRowHover, '--material-glass-control-hover', 'supplement hovered job row')
  assert.match(jobRowHover, /border-color:\s*var\(--glass-control-border-hover\)/)
  assert.match(jobRowHover, /box-shadow:\s*var\(--glass-control-shadow-hover\)/)
  assert.match(jobRowHover, /transform:\s*translateY\(-1px\)/)
  assertLayeredBackground(jobRowFocusWithin, '--material-glass-control-hover', 'supplement focused job row')
  assert.match(jobRowFocusWithin, /border-color:\s*var\(--glass-control-border-hover\)/)
  assert.match(jobRowFocusWithin, /box-shadow:\s*var\(--glass-control-shadow-hover\),\s*var\(--focus-ring\)/)
  assert.match(jobRowFocusWithin, /transform:\s*translateY\(-1px\)/)
  assert.doesNotMatch([jobRowHover, jobRowFocusWithin].join('\n'), /^.*background:\s*var\(--material-glass-control-hover\);.*$/gm)

  const avatarBlocks = [workspaceAvatar, jobAvatar]
  for (const block of avatarBlocks) {
    assertLayeredBackground(block, '--material-glass-subtle', 'supplement workspace avatar')
    assert.match(block, /border:\s*1px solid var\(--glass-control-border\)/)
    assert.match(block, /box-shadow:\s*var\(--glass-inner-shadow\)/)
    assert.match(block, /backdrop-filter:\s*blur\(var\(--glass-blur-control\)\)\s*saturate\(var\(--glass-saturate-control\)\)/)
  }
  assert.doesNotMatch(avatarBlocks.join('\n'), /^.*background:\s*var\(--material-glass-subtle\);.*$/gm)

  for (const block of [movieSpinner, jobSpinner]) {
    assert.match(block, /border:\s*2px solid var\(--glass-control-border\)/)
    assert.match(block, /border-top-color:\s*var\(--badge-info-text\)/)
  }
})

test('supplement diagnostics modal avoids legacy flat surfaces', () => {
  const header = cssBlock(source, '.diagnostics-header')
  const table = cssBlock(source, '.diagnostics-table')
  const row = cssBlock(source, '.diagnostics-row')
  const headRow = cssBlock(source, '.diagnostics-row-head')
  const identityChip = cssBlock(source, '.identity-chip')
  const detailSourceItem = cssBlock(source, '.detail-source-item')
  const manualAction = cssBlock(source, '.manual-action-item')

  assertLayeredBackground(header, '--material-glass-sheet', 'supplement diagnostics header')
  assert.match(header, /border-bottom:\s*1px solid var\(--glass-control-border\)/)
  assert.match(header, /box-shadow:\s*var\(--glass-surface-shadow\)/)
  assert.match(header, /backdrop-filter:\s*blur\(var\(--glass-blur-surface\)\)\s*saturate\(var\(--glass-saturate-surface\)\)/)

  assert.match(table, /border:\s*1px solid var\(--glass-control-border\)/)
  assert.match(table, /box-shadow:\s*var\(--glass-control-shadow\)/)
  assertLayeredBackground(table, '--material-glass-control', 'supplement diagnostics table')
  assert.doesNotMatch([header, table].join('\n'), /^.*background:\s*var\(--(?:material-glass-sheet|material-glass-control)\);.*$/gm)

  const diagnosticsItemBlocks = [row, identityChip, detailSourceItem, manualAction]
  for (const block of diagnosticsItemBlocks) {
    assertLayeredBackground(block, '--material-glass-control', 'supplement diagnostics item')
    assert.match(block, /border:\s*1px solid var\(--glass-control-border\)/)
    assert.match(block, /box-shadow:\s*var\(--glass-control-shadow\)/)
    assert.match(block, /backdrop-filter:\s*blur\(var\(--glass-blur-control\)\)\s*saturate\(var\(--glass-saturate-control\)\)/)
  }
  assert.doesNotMatch(diagnosticsItemBlocks.join('\n'), /^.*background:\s*var\(--material-glass-control\);.*$/gm)

  assertLayeredBackground(headRow, '--glass-active-material', 'supplement diagnostics header row')
  assert.match(headRow, /box-shadow:\s*var\(--glass-active-shadow\)/)
  assert.doesNotMatch(headRow, /^.*background:\s*var\(--glass-active-material\);.*$/gm)
  assert.doesNotMatch(diagnosticsStyle, /\.btn\.danger\s*\{/, 'danger buttons should use the global glass button treatment')
  assert.doesNotMatch(diagnosticsStyle, /#ff6b87|rgba\(255,\s*107,\s*135/i)
})

test('supplement source diagnostics use shared Apple glass materials', () => {
  const diagnosticsOverlay = cssBlock(diagnosticsStyle, '.diagnostics-overlay')
  const input = cssBlock(sourceHealthPanel, '.filter-input')
  const inputFocus = cssBlock(sourceHealthPanel, '.filter-input:focus')
  const avatarPanel = cssBlock(sourceHealthPanel, '.avatar-sync-panel')
  const avatarMetric = cssBlock(sourceHealthPanel, '.avatar-sync-metrics div')
  const smokeSummary = cssBlock(sourceHealthPanel, '.provider-smoke-summary')
  const smokeHistory = cssBlock(sourceHealthPanel, '.provider-smoke-history')
  const smokeRun = cssBlock(sourceHealthPanel, '.provider-smoke-run')
  const smokeRunHover = cssBlock(sourceHealthPanel, '.provider-smoke-run:hover')
  const smokeCard = cssBlock(sourceHealthPanel, '.provider-smoke-card')
  const smokeCardFailed = cssBlock(sourceHealthPanel, '.provider-smoke-card.failed')
  const sourceCard = cssBlock(sourceHealthPanel, '.source-health-card')
  const budgetMeter = cssBlock(sourceHealthPanel, '.source-budget-meter')
  const miniSpinner = cssBlock(sourceHealthPanel, '.mini-spinner')
  const largeSpinner = cssBlock(sourceHealthPanel, '.spinner-large')

  assert.doesNotMatch(sourceHealthPanel, /var\(--surface-card\)|var\(--surface-control\)|var\(--surface-control-hover\)|var\(--surface-input-focus\)|var\(--white-20\)|rgba\(255,\s*107,\s*135/)
  assert.match(diagnosticsOverlay, /z-index:\s*var\(--z-modal\)/)
  assert.match(diagnosticsOverlay, /background:\s*var\(--surface-scrim\)/)
  assert.match(diagnosticsOverlay, /backdrop-filter:\s*blur\(var\(--glass-blur-control\)\)\s*saturate\(var\(--glass-saturate-control\)\)/)
  assert.doesNotMatch(diagnosticsOverlay, /z-index:\s*\d+|rgba\(0,\s*0,\s*0/)

  assertLayeredBackground(input, '--material-glass-control', 'supplement source filter input')
  assert.match(input, /border:\s*1px solid var\(--glass-control-border\)/)
  assert.match(input, /box-shadow:\s*var\(--glass-control-shadow\)/)
  assert.match(input, /backdrop-filter:\s*blur\(var\(--glass-blur-control\)\)\s*saturate\(var\(--glass-saturate-control\)\)/)
  assert.match(inputFocus, /border-color:\s*var\(--glass-active-border\)/)
  assertLayeredBackground(inputFocus, '--glass-active-material', 'supplement source focused filter input')
  assert.match(inputFocus, /box-shadow:\s*var\(--glass-active-shadow\)/)
  assert.doesNotMatch([input, inputFocus].join('\n'), /^.*background:\s*var\(--(?:material-glass-control|glass-active-material)\);.*$/gm)

  for (const block of [avatarPanel, smokeSummary, smokeHistory, sourceCard]) {
    assertLayeredBackground(block, '--material-glass-sheet', 'supplement source sheet')
    assert.match(block, /border:\s*1px solid var\(--glass-control-border\)/)
    assert.match(block, /box-shadow:\s*var\(--glass-surface-shadow\)/)
    assert.match(block, /backdrop-filter:\s*blur\(var\(--glass-blur-surface\)\)\s*saturate\(var\(--glass-saturate-surface\)\)/)
  }
  assert.doesNotMatch([avatarPanel, smokeSummary, smokeHistory, sourceCard].join('\n'), /^.*background:\s*var\(--material-glass-sheet\);.*$/gm)

  for (const block of [avatarMetric, smokeRun, smokeCard, budgetMeter]) {
    assertLayeredBackground(block, '--material-glass-control', 'supplement source control')
    assert.match(block, /border:\s*1px solid var\(--glass-control-border\)/)
    assert.match(block, /box-shadow:\s*var\(--glass-control-shadow\)/)
    assert.match(block, /backdrop-filter:\s*blur\(var\(--glass-blur-control\)\)\s*saturate\(var\(--glass-saturate-control\)\)/)
  }
  assert.doesNotMatch([avatarMetric, smokeRun, smokeCard, budgetMeter].join('\n'), /^.*background:\s*var\(--material-glass-control\);.*$/gm)

  assertLayeredBackground(smokeRunHover, '--material-glass-control-hover', 'supplement source hovered run')
  assert.match(smokeRunHover, /border-color:\s*var\(--glass-control-border-hover\)/)
  assert.match(smokeRunHover, /box-shadow:\s*var\(--glass-control-shadow-hover\)/)
  assert.doesNotMatch(smokeRunHover, /^.*background:\s*var\(--material-glass-control-hover\);.*$/gm)
  assert.match(smokeCardFailed, /border-color:\s*var\(--badge-error-border\)/)

  for (const block of [miniSpinner, largeSpinner]) {
    assert.match(block, /border:\s*2px solid var\(--glass-control-border\)/)
    assert.match(block, /border-top-color:\s*var\(--badge-info-text\)/)
  }
})

test('supplement source status pills use shared semantic badge tokens', () => {
  const idle = cssBlock(sourceHealthPanel, '.status-idle')
  const healthy = cssBlock(sourceHealthPanel, '.health-healthy')
  const degraded = cssBlock(sourceHealthPanel, '.health-degraded')
  const coolingDown = cssBlock(sourceHealthPanel, '.health-cooling_down')
  const paused = cssBlock(sourceHealthPanel, '.health-paused')

  assert.match(idle, /color:\s*var\(--badge-pending-text\)/)
  assertLayeredBackground(idle, '--badge-pending-bg', 'source idle status')
  assert.match(idle, /border-color:\s*var\(--badge-pending-border\)/)

  assert.match(healthy, /color:\s*var\(--badge-success-text\)/)
  assertLayeredBackground(healthy, '--badge-success-bg', 'source healthy status')
  assert.match(healthy, /border-color:\s*var\(--badge-success-border\)/)

  assert.match(degraded, /color:\s*var\(--badge-warning-text\)/)
  assertLayeredBackground(degraded, '--badge-warning-bg', 'source degraded status')
  assert.match(degraded, /border-color:\s*var\(--badge-warning-border\)/)

  assert.match(coolingDown, /color:\s*var\(--badge-error-text\)/)
  assertLayeredBackground(coolingDown, '--badge-error-bg', 'source cooling down status')
  assert.match(coolingDown, /border-color:\s*var\(--badge-error-border\)/)

  assert.match(paused, /color:\s*var\(--badge-pending-text\)/)
  assertLayeredBackground(paused, '--badge-pending-bg', 'source paused status')
  assert.match(paused, /border-color:\s*var\(--badge-pending-border\)/)

  for (const block of [idle, healthy, degraded, coolingDown, paused]) {
    assert.doesNotMatch(block, /rgba\(255,\s*255,\s*255|#[0-9a-f]{3,6}/i)
  }
})
