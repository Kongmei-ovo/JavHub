import test from 'node:test'
import assert from 'node:assert/strict'
import { existsSync, readFileSync } from 'node:fs'

const vueSource = readFileSync(new URL('./Operations.vue', import.meta.url), 'utf8')
const externalStyle = readFileSync(new URL('../features/operations/operations.css', import.meta.url), 'utf8')
const source = `${vueSource}\n${externalStyle}`
const operationsCardPaths = [
  '../features/operations/PipelineCard.vue',
  '../features/operations/CacheCard.vue',
  '../features/operations/SchedulerCard.vue',
  '../features/operations/DataQualityCard.vue',
  '../features/operations/CandidateAutoCard.vue',
  '../features/operations/SnapshotCard.vue',
  '../features/operations/MappingCard.vue',
]

function readFeatureSource(path) {
  const url = new URL(path, import.meta.url)
  return existsSync(url) ? readFileSync(url, 'utf8') : ''
}

const operationsCardSources = operationsCardPaths.map(path => ({
  path,
  source: readFeatureSource(path),
}))
const operationsCardsSource = operationsCardSources.map(({ source }) => source).join('\n')
const operationsFeatureSource = `${vueSource}\n${operationsCardsSource}`

function cssBlocks(content, selector) {
  const blocks = [...content.matchAll(/([^{}]+)\{([^{}]*)\}/g)]
    .filter(([, selectors]) => selectors
      .split(',')
      .map(part => part.trim())
      .includes(selector))
    .map(([, , block]) => block)
  assert.ok(blocks.length, `${selector} block should exist`)
  return blocks
}

function lastCssBlock(content, selector) {
  const blocks = cssBlocks(content, selector)
  return blocks.at(-1)
}

function backgroundIncludes(token) {
  return new RegExp(`background:[\\s\\S]*var\\(--${token}\\)`)
}

function singleLayerGlassBackgrounds(css) {
  return css
    .split('\n')
    .map((line, index) => ({ line: index + 1, text: line.trim() }))
    .filter(({ text }) => /^background:\s*var\(--(?:material-glass-subtle|material-glass-control|material-glass-control-hover|material-glass-sheet|glass-active-material)\);$/.test(text))
}

test('operations page keeps heavyweight styles in an external scoped stylesheet', () => {
  assert.match(vueSource, /<style scoped src="\.\.\/features\/operations\/operations\.css"><\/style>/)
  assert.ok(externalStyle.length > 18000, 'external operations stylesheet should carry the moved workspace CSS')
  assert.ok(vueSource.split('\n').length < 900, 'Operations.vue should stay small enough to review and parse quickly')
})

test('operations page is split into self-loading feature cards', () => {
  for (const { path, source: cardSource } of operationsCardSources) {
    assert.ok(cardSource, `${path} should exist`)
    assert.match(cardSource, /import api from ['"]\.\.\/\.\.\/api['"]/, `${path} should fetch its own data`)
    assert.match(cardSource, /mounted\(\)\s*\{[\s\S]*this\.load/, `${path} should load on mount`)
    assert.match(cardSource, /<style scoped src="\.\/operations\.css"><\/style>/, `${path} should reuse operations styles`)
  }

  for (const component of ['PipelineCard', 'CacheCard', 'SchedulerCard', 'DataQualityCard', 'CandidateAutoCard', 'SnapshotCard', 'MappingCard']) {
    assert.match(vueSource, new RegExp(`import ${component} from ['"]\\.\\.\\/features\\/operations\\/${component}\\.vue['"]`))
    assert.match(vueSource, new RegExp(`<${component}\\b`))
  }

  assert.ok(vueSource.split('\n').length < 350, 'Operations.vue should only own page layout after card extraction')
  assert.doesNotMatch(vueSource, /api\.(getOperationsOverview|getCacheStats|readiness|runCandidateProcessingNow|purgeCache|refreshMissingCache|startVideoVariantIndexJob)/)
  assert.doesNotMatch(vueSource, /requestConfirm/)
})

test('operations cards use focused APIs so one failed overview does not blank every card', () => {
  const sourcesByName = Object.fromEntries(
    operationsCardSources.map(({ path, source: cardSource }) => [
      path.match(/([^/]+)\.vue$/)?.[1] || path,
      cardSource,
    ])
  )

  assert.doesNotMatch(sourcesByName.SchedulerCard, /getOperationsOverview/)
  assert.match(sourcesByName.SchedulerCard, /api\.readiness\(\)/)
  assert.match(sourcesByName.CacheCard, /api\.getCacheStats\(\)/)
  assert.match(sourcesByName.CacheCard, /api\.purgeCache\(this\.selectedCachePurgeScope\)/)

  assert.doesNotMatch(sourcesByName.CandidateAutoCard, /getOperationsOverview/)
  assert.match(sourcesByName.CandidateAutoCard, /api\.getDownloadCandidateSummary\(\{ status: 'candidate', include_sources: true \}\)/)
  assert.match(sourcesByName.CandidateAutoCard, /api\.listDownloadCandidateRuns\(5\)/)

  assert.doesNotMatch(sourcesByName.SnapshotCard, /getOperationsOverview/)
  assert.match(sourcesByName.SnapshotCard, /api\.getInventorySnapshotLatest\(\)/)
  assert.match(sourcesByName.SnapshotCard, /api\.getMissingActresses\(\)/)
  assert.match(sourcesByName.SnapshotCard, /api\.listInventoryJobs\(\)/)
  assert.match(sourcesByName.SnapshotCard, /api\.getVideoVariantIndexStats\(\)/)

  assert.doesNotMatch(sourcesByName.MappingCard, /getOperationsOverview/)
  assert.match(sourcesByName.MappingCard, /api\.getActorMappingSummary\(\)/)
})

test('operations workbench controls use shared Apple glass tokens', () => {
  const segmentButton = lastCssBlock(source, '.operations-segments button')
  const segmentHover = lastCssBlock(source, '.operations-segments button:hover')
  const segmentActive = lastCssBlock(source, '.operations-segments button.active')
  const blockHeadButton = cssBlocks(source, '.block-head button').find(block => /border:\s*1px solid var\(--glass-control-border\)/.test(block)) || ''
  const operationsPage = lastCssBlock(source, '.operations-page')
  const actionCard = cssBlocks(source, '.action-card').join('\n')
  const actionCardHover = cssBlocks(source, '.action-card:hover').join('\n')
  const queueFocus = cssBlocks(source, '.queue-focus').join('\n')
  const sharedHover = cssBlocks(source, '.queue-focus:hover').join('\n')
  const compactList = cssBlocks(source, '.compact-list').join('\n')
  const runList = cssBlocks(source, '.run-list').join('\n')
  const compactRow = cssBlocks(source, '.compact-row').join('\n')
  const runRow = cssBlocks(source, '.run-row').join('\n')
  const stateItem = cssBlocks(source, '.state-item').join('\n')
  const miniStat = cssBlocks(source, '.mini-stats > div').join('\n')
  const backendPill = lastCssBlock(source, '.backend-pill')
  const warningBlocks = cssBlocks(source, '.state-item.warning')

  assert.doesNotMatch(source, /var\(--surface-card\)|var\(--surface-card-hover\)|var\(--surface-control\)|var\(--surface-control-hover\)|var\(--surface-input-focus\)|var\(--border\)|var\(--border-light\)/)

  assert.match(operationsPage, /--operations-line:\s*var\(--glass-control-border\)/)
  assert.match(operationsPage, /--operations-soft-line:\s*var\(--glass-control-border\)/)

  assert.match(segmentButton, /border:\s*1px solid var\(--glass-control-border\)/)
  assert.match(segmentButton, backgroundIncludes('material-glass-control'))
  assert.match(segmentButton, /box-shadow:\s*var\(--glass-control-shadow\)/)
  assert.match(segmentButton, /backdrop-filter:\s*blur\(var\(--glass-blur-control\)\)\s*saturate\(var\(--glass-saturate-control\)\)/)
  assert.match(segmentHover, backgroundIncludes('material-glass-control-hover'))
  assert.match(segmentHover, /box-shadow:\s*var\(--glass-control-shadow-hover\)/)
  assert.match(segmentActive, backgroundIncludes('glass-active-material'))
  assert.match(segmentActive, /box-shadow:\s*var\(--glass-active-shadow\)/)

  assert.match(blockHeadButton, /border:\s*1px solid var\(--glass-control-border\)/)
  assert.match(blockHeadButton, backgroundIncludes('material-glass-control'))
  assert.match(blockHeadButton, /box-shadow:\s*var\(--glass-control-shadow\)/)

  for (const block of [actionCard, queueFocus, compactList, runList, compactRow, runRow]) {
    assert.match(block, /border:\s*1px solid var\(--operations-soft-line\)/)
    assert.match(block, backgroundIncludes('material-glass-control'))
  }

  for (const block of [compactRow, runRow]) {
    assert.match(block, /box-shadow:\s*var\(--glass-inner-shadow\)/)
  }

  for (const block of [stateItem, miniStat, backendPill]) {
    assert.match(block, /border:\s*1px solid var\(--operations-line\)/)
    assert.match(block, backgroundIncludes('material-glass-control'))
    assert.match(block, /box-shadow:\s*var\(--glass-inner-shadow\)/)
    assert.match(block, /backdrop-filter:\s*blur\(var\(--glass-blur-control\)\)\s*saturate\(var\(--glass-saturate-control\)\)/)
  }

  for (const block of [actionCardHover, sharedHover]) {
    assert.match(block, /border-color:\s*var\(--glass-control-border-hover\)/)
    assert.match(block, backgroundIncludes('material-glass-control-hover'))
  }

  for (const block of warningBlocks) {
    assert.match(block, /background:\s*var\(--operations-warning-material\)/)
    assert.doesNotMatch(block, /rgba\(255,\s*255,\s*255|rgba\(255,255,255/i)
  }
  assert.match(source, /--operations-warning-material:\s*var\(--surface-specular-edge\),\s*var\(--surface-noise\),\s*linear-gradient/)

  for (const block of [segmentButton, blockHeadButton, actionCard, queueFocus, compactList, runList, compactRow, runRow, stateItem, miniStat, backendPill]) {
    assert.doesNotMatch(block, /border:\s*(?:0|none|1px solid transparent)/)
    assert.doesNotMatch(block, /background:\s*(?:transparent|none)/)
  }
})

test('operations keyboard focus mirrors hover glass control treatment', () => {
  const segmentFocus = lastCssBlock(source, '.operations-segments button:focus-visible')
  const heroFocus = lastCssBlock(source, '.hero-stat:focus-visible')
  const actionFocus = cssBlocks(source, '.action-card:focus-visible').join('\n')
  const queueFocus = cssBlocks(source, '.queue-focus:focus-visible').join('\n')
  const compactFocus = cssBlocks(source, '.compact-row:focus-visible').join('\n')
  const stateFocus = cssBlocks(source, '.state-item:is(button):focus-visible').join('\n')
  const blockHeadFocus = cssBlocks(source, '.block-head button:focus-visible').join('\n')
  const scopeFocus = cssBlocks(source, '.scope-chip:focus-visible').join('\n')

  for (const [block, label] of [
    [segmentFocus, 'operations segment focus'],
    [heroFocus, 'operations hero metric focus'],
    [actionFocus, 'operations action card focus'],
    [queueFocus, 'operations queue focus'],
    [compactFocus, 'operations compact row focus'],
    [stateFocus, 'operations state item focus'],
    [blockHeadFocus, 'operations block head focus'],
    [scopeFocus, 'operations scope chip focus'],
  ]) {
    assert.match(block, /outline:\s*none/, `${label} should replace the default outline`)
    assert.match(block, /border-color:\s*var\(--glass-control-border-hover\)/, `${label} should use hover border`)
    assert.match(block, backgroundIncludes('material-glass-control-hover'), `${label} should use hover glass material`)
    assert.match(block, /box-shadow:\s*var\(--glass-control-shadow-hover\),\s*var\(--focus-ring\)/, `${label} should expose a subtle focus ring`)
  }

  for (const block of [heroFocus, actionFocus, queueFocus, compactFocus, stateFocus, scopeFocus]) {
    assert.match(block, /transform:\s*translateY\(-1px\)/)
  }
  assert.match(segmentFocus, /color:\s*var\(--text-primary\)/)
  assert.match(blockHeadFocus, /color:\s*var\(--text-primary\)/)
})

test('operations dense dashboard surfaces expose liquid glass edge refraction', () => {
  const hero = cssBlocks(source, '.operations-hero').join('\n')
  const heroBefore = lastCssBlock(source, '.operations-hero::before')
  const heroChildren = lastCssBlock(source, '.operations-hero > *')
  const panel = cssBlocks(source, '.workbench-panel').join('\n')
  const panelBefore = lastCssBlock(source, '.workbench-panel::before')
  const panelChildren = lastCssBlock(source, '.workbench-panel > *')
  const segments = cssBlocks(source, '.operations-segments').join('\n')

  for (const [block, label] of [[hero, 'hero'], [panel, 'panel'], [segments, 'segments']]) {
    assert.match(block, /position:\s*relative/, `${label} should anchor the inner refraction layer`)
    assert.match(block, /isolation:\s*isolate/, `${label} should isolate glass highlights`)
    assert.match(block, /overflow:\s*hidden/, `${label} should clip liquid glass edges`)
  }

  for (const [block, label] of [[heroBefore, 'hero edge'], [panelBefore, 'panel edge']]) {
    assert.match(block, /content:\s*""/, `${label} should render a pseudo layer`)
    assert.match(block, /position:\s*absolute/, `${label} should cover the surface`)
    assert.match(block, /inset:\s*0/, `${label} should cover the whole surface`)
    assert.match(block, /border-radius:\s*inherit/, `${label} should preserve concentric corners`)
    assert.match(block, backgroundIncludes('surface-specular-edge-strong'), `${label} should use shared specular highlights`)
    assert.match(block, backgroundIncludes('surface-noise'), `${label} should keep material texture`)
    assert.match(block, /opacity:\s*0\.[34]8/, `${label} should stay subtle`)
    assert.match(block, /pointer-events:\s*none/, `${label} should not block controls`)
    assert.match(block, /z-index:\s*0/, `${label} should sit behind content`)
  }

  for (const block of [heroChildren, panelChildren]) {
    assert.match(block, /position:\s*relative/)
    assert.match(block, /z-index:\s*1/)
  }
}
)

test('operations rows and segments add pressed feedback with stable tabular metrics', () => {
  const segmentButton = lastCssBlock(source, '.operations-segments button')
  const segmentActive = lastCssBlock(source, '.operations-segments button:active')
  const heroStrong = lastCssBlock(source, '.hero-stat strong')
  const stateStrong = lastCssBlock(source, '.state-item strong')
  const miniStatsStrong = lastCssBlock(source, '.mini-stats strong')
  const actionActive = cssBlocks(source, '.action-card:active').join('\n')
  const queueActive = cssBlocks(source, '.queue-focus:active').join('\n')
  const compactActive = cssBlocks(source, '.compact-row:active').join('\n')
  const scopeActive = cssBlocks(source, '.scope-chip:active').join('\n')

  assert.match(segmentButton, /transition:[\s\S]*transform var\(--motion-fast\)/)
  assert.match(segmentActive, /transform:\s*scale\(0\.99\)/)
  for (const block of [heroStrong, stateStrong, miniStatsStrong]) {
    assert.match(block, /font-variant-numeric:\s*tabular-nums/)
  }
  for (const block of [actionActive, queueActive, compactActive, scopeActive]) {
    assert.match(block, /transform:\s*translateY\(0\)\s*scale\(0\.99\)/)
  }
})

test('operations top chrome stays console-dense instead of campaign-like', () => {
  const hero = cssBlocks(source, '.operations-hero').join('\n')
  const heroTitle = lastCssBlock(source, '.operations-hero h1')
  const heroCopy = lastCssBlock(source, '.operations-hero p')
  const heroStatGrid = cssBlocks(source, '.hero-stat-grid').join('\n')
  const heroStat = lastCssBlock(source, '.hero-stat')
  const heroStatStrong = lastCssBlock(source, '.hero-stat strong')

  assert.match(hero, /min-height:\s*92px/)
  assert.match(hero, /padding:\s*12px/)
  assert.match(hero, /border-radius:\s*var\(--radius-lg\)/)
  assert.doesNotMatch(hero, /100vh|148px|clamp\(22px/)
  assert.match(heroTitle, /font-size:\s*var\(--type-workbench-title\)/)
  assert.match(heroCopy, /white-space:\s*nowrap/)
  assert.match(heroStatGrid, /grid-template-columns:\s*repeat\(auto-fit,\s*minmax\(108px,\s*1fr\)\)/)
  assert.match(heroStat, /min-height:\s*52px/)
  assert.match(heroStat, /padding:\s*8px 10px/)
  // WAVE-4 D4: hero stat font-size moved to --type-section-title token.
  assert.match(heroStatStrong, /font-size:\s*(?:20px|var\(--type-section-title,\s*20px\))/)
})

test('operations hero metrics expose compact hints and urgency markers', () => {
  const heroStat = lastCssBlock(source, '.hero-stat')
  const urgentStat = cssBlocks(source, '.hero-stat.urgent').join('\n')
  const urgentBefore = cssBlocks(source, '.hero-stat.urgent::before').join('\n')
  const hint = cssBlocks(source, '.hero-stat small').join('\n')

  assert.match(vueSource, /:class="\{ urgent: metric\.urgent \}"/)
  assert.match(vueSource, /<small>\{\{\s*metric\.hint\s*\}\}<\/small>/)
  assert.match(heroStat, /position:\s*relative/)
  assert.match(heroStat, /overflow:\s*hidden/)
  assert.match(urgentStat, /border-color:\s*var\(--badge-warning-border\)/)
  assert.match(urgentStat, /box-shadow:\s*inset 2px 0 0 var\(--badge-warning-border\),\s*var\(--glass-inner-shadow\)/)
  assert.match(urgentBefore, /content:\s*""/)
  assert.match(urgentBefore, /inset:\s*7px auto 7px 6px/)
  assert.match(urgentBefore, /background:\s*var\(--badge-warning-border\)/)
  assert.match(hint, /display:\s*block/)
  assert.match(hint, /font-size:\s*var\(--type-micro\)/)
  assert.match(hint, /text-overflow:\s*ellipsis/)
})

test('operations diagnostic rows use table-like tracks for fast scanning', () => {
  const compactList = cssBlocks(source, '.compact-list').join('\n')
  const runList = cssBlocks(source, '.run-list').join('\n')
  const compactRow = cssBlocks(source, '.compact-row').join('\n')
  const runRow = cssBlocks(source, '.run-row').join('\n')
  const runRowSmall = cssBlocks(source, '.run-row small').join('\n')

  for (const block of [compactList, runList]) {
    assert.match(block, /gap:\s*4px/)
    assert.match(block, /padding:\s*4px/)
  }
  assert.match(compactRow, /display:\s*grid/)
  assert.match(compactRow, /grid-template-columns:\s*minmax\(0,\s*1fr\)\s*auto/)
  assert.match(compactRow, /min-height:\s*32px/)
  assert.match(runRow, /display:\s*grid/)
  assert.match(runRow, /grid-template-columns:\s*minmax\(0,\s*1fr\)\s*auto/)
  assert.match(runRow, /min-height:\s*36px/)
  assert.match(runRowSmall, /font-family:\s*var\(--font-mono\)/)
  assert.match(runRowSmall, /font-variant-numeric:\s*tabular-nums/)
})

test('operations compact diagnostic rows reserve a second-line metadata track', () => {
  const compactRowWithMeta = cssBlocks(source, '.compact-row:has(small)').join('\n')
  const compactRowSmall = cssBlocks(source, '.compact-row small').join('\n')
  const qualityProgressMeta = cssBlocks(source, '.quality-progress-meta').join('\n')
  const qualityProgress = cssBlocks(source, '.quality-progress').join('\n')
  const qualityProgressActions = cssBlocks(source, '.quality-progress-actions').join('\n')
  const qualityProgressAction = cssBlocks(source, '.quality-progress-action').join('\n')
  const qualityIssueRow = cssBlocks(source, '.quality-issue-row').join('\n')

  assert.match(operationsFeatureSource, /class="quality-progress-meta"/)
  assert.match(operationsFeatureSource, /issue\?\.priority_reason/)
  assert.match(operationsFeatureSource, /issueRepairMetaItems\(issue\)/)
  assert.match(operationsFeatureSource, /class="quality-progress-separator"/)
  assert.match(operationsFeatureSource, /class="quality-progress-separator"[^>]*>\s*·\s*<\/span>/)
  assert.match(operationsFeatureSource, /<small>\s*\{\{\s*issue\.summary\s*\}\}\s*<\/small>/)
  assert.match(operationsFeatureSource, /issueRepairMetaItems\(issue\)/)
  assert.match(operationsFeatureSource, /class="quality-progress"/)
  assert.match(operationsFeatureSource, /class="quality-progress-actions"/)
  assert.match(operationsFeatureSource, /class="compact-row quality-issue-row"/)
  assert.match(operationsFeatureSource, /issue\?\.action/)
  assert.match(operationsFeatureSource, /issueRepairActions\(issue\)/)
  assert.match(operationsFeatureSource, /seen\.has\(key\)/)
  assert.match(operationsFeatureSource, /seen\.add\(key\)/)
  assert.match(operationsFeatureSource, /openDataQualityRepairAction\(action, \$event\)/)
  assert.doesNotMatch(operationsFeatureSource, /role="button" tabindex="0" @click="openDataQualityIssueFromRow/)
  assert.match(operationsFeatureSource, /issueRepairReasonActions\(issue\)/)
  assert.match(operationsFeatureSource, /issueRepairEventLabel\(issue\)/)
  assert.match(operationsFeatureSource, /issueRepairEventActions\(issue\)/)
  assert.match(operationsFeatureSource, /issueRepairLocalLabel\(issue\)/)
  assert.match(operationsFeatureSource, /issueRepairLocalSourceLabel\(issue\)/)
  assert.match(operationsFeatureSource, /issueRepairLocalActions\(issue\)/)
  assert.match(operationsFeatureSource, /@click\.stop="openDataQualityRepairAction\(action, \$event\)"/)
  assert.doesNotMatch(operationsFeatureSource, /openDataQualityRepairAction\(issue\.repair_progress\.action, \$event\)/)
  assert.doesNotMatch(operationsFeatureSource, /openDataQualityRepairAction\(issue\.repair_progress\.reason_action, \$event\)/)
  assert.match(operationsFeatureSource, /repair_progress\?\.event_label/)
  assert.match(operationsFeatureSource, /repair_progress\?\.event_actions/)
  assert.match(operationsFeatureSource, /repair_progress\?\.reason_actions/)
  assert.match(operationsFeatureSource, /repair_progress\?\.local_label/)
  assert.match(operationsFeatureSource, /repair_progress\?\.local_source_label/)
  assert.match(operationsFeatureSource, /repair_progress\?\.local_actions/)
  assert.match(compactRowWithMeta, /align-content:\s*center/)
  assert.match(compactRowWithMeta, /gap:\s*2px 8px/)
  assert.match(compactRowWithMeta, /min-height:\s*44px/)
  assert.match(compactRowSmall, /grid-column:\s*1 \/ -1/)
  assert.match(compactRowSmall, /color:\s*var\(--text-secondary\)/)
  // WAVE-4 D4: compact row small font-size moved to --type-caption-2 token.
  assert.match(compactRowSmall, /font-size:\s*(?:11px|var\(--type-caption-2,\s*11px\))/)
  assert.match(compactRowSmall, /line-height:\s*1\.25/)
  assert.match(compactRowSmall, /white-space:\s*nowrap/)
  assert.match(compactRowSmall, /text-overflow:\s*ellipsis/)
  assert.match(qualityProgressMeta, /grid-column:\s*1 \/ -1/)
  assert.match(qualityProgressMeta, /display:\s*flex/)
  assert.match(qualityProgressMeta, /flex-wrap:\s*wrap/)
  assert.match(qualityProgressMeta, /white-space:\s*normal/)
  assert.match(qualityProgress, /min-width:\s*0/)
  assert.match(qualityProgress, /white-space:\s*normal/)
  assert.doesNotMatch(qualityProgress, /text-overflow:\s*ellipsis/)
  assert.match(qualityProgressActions, /grid-column:\s*1 \/ -1/)
  assert.match(qualityProgressActions, /display:\s*flex/)
  assert.match(qualityProgressActions, /flex-wrap:\s*wrap/)
  assert.match(qualityProgressAction, /white-space:\s*nowrap/)
  assert.match(qualityIssueRow, /content-visibility:\s*visible/)
  assert.match(qualityIssueRow, /contain-intrinsic-size:\s*auto/)
  assert.match(qualityIssueRow, /cursor:\s*default/)
  assert.match(source, /@media \(max-width: 560px\)[\s\S]*\.quality-progress\s*\{[\s\S]*grid-column:\s*1 \/ -1/)
})

test('operations layout leaves loading error and empty states to self-loading cards', () => {
  const shell = cssBlocks(source, '.console-state-shell').join('\n')
  const ledger = cssBlocks(source, '.state-ledger').join('\n')
  const ledgerSpan = cssBlocks(source, '.state-ledger span').join('\n')
  const consoleState = cssBlocks(source, '.console-state').join('\n')

  assert.doesNotMatch(vueSource, /class="console-state-shell operations-state-shell"/)
  assert.doesNotMatch(vueSource, /AppleSkeleton/)
  assert.doesNotMatch(vueSource, /AppleErrorState/)
  assert.doesNotMatch(vueSource, /AppleEmptyState/)
  assert.match(operationsFeatureSource, /加载失败/)
  assert.match(operationsFeatureSource, /暂不可用/)

  assert.match(shell, /display:\s*grid/)
  assert.match(shell, /gap:\s*6px/)
  assert.match(shell, /margin-bottom:\s*var\(--operations-panel-gap\)/)
  assert.match(ledger, /display:\s*grid/)
  assert.match(ledger, /grid-template-columns:\s*repeat\(3,\s*minmax\(0,\s*1fr\)\)/)
  assert.match(ledger, /font-family:\s*var\(--font-mono\)/)
  assert.match(ledger, /font-variant-numeric:\s*tabular-nums/)
  assert.match(ledger, backgroundIncludes('material-glass-control'))
  assert.match(ledgerSpan, /overflow:\s*hidden/)
  assert.match(ledgerSpan, /text-overflow:\s*ellipsis/)
  assert.match(consoleState, /max-width:\s*none/)
  assert.match(consoleState, /margin:\s*0/)
  assert.match(consoleState, /text-align:\s*left/)
})

test('operations mobile state and metric surfaces keep stable scan tracks', () => {
  assert.match(source, /@media \(max-width: 900px\)[\s\S]*\.state-ledger\s*\{[\s\S]*grid-template-columns:\s*repeat\(3,\s*minmax\(0,\s*1fr\)\)/)
  assert.match(source, /@media \(max-width: 560px\)[\s\S]*\.state-ledger\s*\{[\s\S]*grid-template-columns:\s*1fr/)
  assert.match(source, /@media \(max-width: 560px\)[\s\S]*\.hero-stat-grid\s*\{[\s\S]*grid-template-columns:\s*repeat\(2,\s*minmax\(0,\s*1fr\)\)/)
  assert.match(source, /@media \(max-width: 560px\)[\s\S]*\.state-item\s*\{[\s\S]*min-height:\s*46px/)
  assert.match(source, /@media \(max-width: 560px\)[\s\S]*\.compact-row:has\(small\)\s*\{[\s\S]*min-height:\s*42px/)
})

test('operations glass backgrounds are layered with specular and noise surfaces', () => {
  assert.deepEqual(singleLayerGlassBackgrounds(externalStyle), [])
})
