import test from 'node:test'
import assert from 'node:assert/strict'
import { existsSync, readFileSync } from 'node:fs'

const vueSource = readFileSync(new URL('./Home.vue', import.meta.url), 'utf8')
const candidatePanelUrl = new URL('../features/candidates/DownloadCandidatePanel.vue', import.meta.url)
const candidatePanelSource = existsSync(candidatePanelUrl) ? readFileSync(candidatePanelUrl, 'utf8') : ''
const externalStyle = readFileSync(new URL('../features/home/home.css', import.meta.url), 'utf8')
const candidateStyleUrl = new URL('../features/candidates/downloadCandidatePanel.css', import.meta.url)
const candidateStyle = existsSync(candidateStyleUrl) ? readFileSync(candidateStyleUrl, 'utf8') : ''
const source = `${vueSource}\n${candidatePanelSource}\n${externalStyle}\n${candidateStyle}`

function cssBlocks(content, selector) {
  const searchable = content.replace(/\/\*[\s\S]*?\*\//g, '')
  const blocks = [...searchable.matchAll(/([^{}]+)\{([^{}]*)\}/g)]
    .filter(([, selectors]) => selectors
      .split(',')
      .map(part => part.trim())
      .includes(selector))
    .map(([, , block]) => block)
  assert.ok(blocks.length, `${selector} block should exist`)
  return blocks
}

function cssBlock(content, selector) {
  return cssBlocks(content, selector).join('\n')
}

function backgroundIncludes(token) {
  return new RegExp(`background:[\\s\\S]*var\\(--${token}\\)`)
}

function layeredSemanticBackground(token) {
  return new RegExp(`background:\\s*var\\(--surface-specular-edge\\),\\s*var\\(--surface-noise\\),\\s*var\\(--${token}\\)`)
}

function assertGlassControl(block, label) {
  assert.match(block, /border:\s*1px solid var\(--glass-control-border\)/, `${label} should use the shared glass border`)
  assert.match(block, backgroundIncludes('material-glass-control'), `${label} should use the shared glass control material`)
  assert.match(block, /box-shadow:\s*var\(--glass-control-shadow\)/, `${label} should use the shared control shadow`)
  assert.match(block, /backdrop-filter:\s*blur\(var\(--glass-blur-control\)\)\s*saturate\(var\(--glass-saturate-control\)\)/, `${label} should use shared control blur`)
}

function assertGlassControlHover(block, label) {
  assert.match(block, backgroundIncludes('material-glass-control-hover'), `${label} should use the shared hover material`)
  assert.match(block, /border-color:\s*var\(--glass-control-border-hover\)/, `${label} should use the shared hover border`)
  assert.match(block, /box-shadow:\s*var\(--glass-control-shadow-hover\)/, `${label} should use the shared hover shadow`)
}

function assertGlassSubtle(block, label) {
  assert.match(block, backgroundIncludes('material-glass-subtle'), `${label} should use the shared subtle material`)
  assert.match(block, /var\(--surface-specular-edge/, `${label} should include a specular edge layer`)
  assert.match(block, /var\(--surface-noise\)/, `${label} should include the shared noise layer`)
}

function singleLayerGlassBackgrounds(css) {
  return css
    .split('\n')
    .map((line, index) => ({ line: index + 1, text: line.trim() }))
    .filter(({ text }) => /^background:\s*var\(--(?:material-glass-subtle|material-glass-control|material-glass-control-hover|material-glass-sheet|glass-active-material)\);$/.test(text))
}

test('home lazy-loads downloader management outside the base downloads chunk', () => {
  assert.match(source, /import \{ defineAsyncComponent \} from 'vue'/)
  assert.match(source, /const DownloaderManagementPanel = defineAsyncComponent\(\(\) => import\('\.\.\/features\/downloaders\/DownloaderManagementPanel\.vue'\)\)/)
  assert.match(source, /components:\s*\{[^}]*DownloadStatsBar[^}]*TaskList[^}]*DownloadCandidatePanel[^}]*DownloaderManagementPanel[^}]*\}/)
  assert.match(source, /<DownloaderManagementPanel[\s\S]*v-else-if="activeTab === 'downloaders'"/)
  assert.doesNotMatch(source, /<div\s+v-else-if="activeTab === 'downloaders'"\s+class="downloaders-panel apple-reveal"/)
})

test('home delegates task empty state actions through the task list component', () => {
  assert.match(vueSource, /import TaskList from '\.\.\/features\/home\/TaskList\.vue'/)
  assert.match(vueSource, /<TaskList[\s\S]*v-else-if="activeTab === 'tasks'"/)
  assert.match(vueSource, /:task-empty-primary-label="taskEmptyPrimaryLabel"/)
  assert.match(vueSource, /@empty-action="handleTaskEmptyAction"/)
  assert.match(vueSource, /@parse="\$router\.push\('\/parse'\)"/)
  assert.match(vueSource, /taskEmptyPrimaryLabel\(\)/)
  assert.match(vueSource, /handleTaskEmptyAction\(\)[\s\S]*this\.clearTaskStatus\(\)[\s\S]*this\.openCandidatePreset\(\{ status: 'candidate', source: '' \}\)[\s\S]*this\.\$router\.push\('\/search'\)/)
})

test('home lazy-loads download candidate workspace outside the base downloads chunk', () => {
  assert.match(vueSource, /const DownloadCandidatePanel = defineAsyncComponent\(\(\) => import\('\.\.\/features\/candidates\/DownloadCandidatePanel\.vue'\)\)/)
  assert.match(vueSource, /<DownloadCandidatePanel\s+v-if="activeTab === 'candidates'"/)
  assert.doesNotMatch(vueSource, /搜索番号、标题、演员/)
  assert.doesNotMatch(vueSource, /JavInfo 数据库导入/)
  assert.match(candidatePanelSource, /搜索番号、标题、演员/)
  assert.match(candidatePanelSource, /<CandidateRunPanel/)
  assert.match(candidatePanelSource, /<style scoped src="\.\/downloadCandidatePanel\.css"><\/style>/)
  assert.ok(candidateStyle.length > 10000, 'candidate lazy chunk should carry its own workspace CSS')
})

test('home composes the download dashboard from focused home feature components', () => {
  assert.match(vueSource, /import DownloadStatsBar from '\.\.\/features\/home\/DownloadStatsBar\.vue'/)
  assert.match(vueSource, /import TaskList from '\.\.\/features\/home\/TaskList\.vue'/)
  assert.match(vueSource, /components:\s*\{[^}]*DownloadStatsBar[^}]*TaskList[^}]*DownloadCandidatePanel[^}]*DownloaderManagementPanel[^}]*\}/)
  assert.match(vueSource, /<DownloadStatsBar[\s\S]*:stats="stats"[\s\S]*:candidate-stats="candidateStats"[\s\S]*@select-status="setTaskStatus"[\s\S]*@open-preset="openCandidatePreset"/)
  assert.match(vueSource, /<TaskList[\s\S]*v-else-if="activeTab === 'tasks'"[\s\S]*:tasks="filteredTasks"[\s\S]*@retry="retry"[\s\S]*@remove="remove"/)
  assert.doesNotMatch(vueSource, /class="stats-bar"/)
  assert.doesNotMatch(vueSource, /class="candidate-overview"/)
  assert.doesNotMatch(vueSource, /v-for="task in filteredTasks"/)
})

test('download candidate panel exposes latest event filters from summary counts', () => {
  assert.match(candidatePanelSource, /candidate-event-toolbar/)
  assert.match(candidatePanelSource, /v-for="filter in candidateLatestEventFilters"/)
  assert.match(candidatePanelSource, /candidateStats\.latest_event_by_action/)
  assert.match(candidatePanelSource, /candidateFilter\.latest_event_action === filter\.action/)
  assert.match(candidatePanelSource, /\$emit\('set-latest-event', filter\.action\)/)
  assert.match(vueSource, /@set-latest-event="setCandidateLatestEvent"/)
  assert.match(vueSource, /setCandidateLatestEvent\(action\)/)
  assert.match(vueSource, /latest_event_action: action/)
  assert.match(vueSource, /without_event:\s*'未处理'/)
  assert.match(vueSource, /missing_cover: this\.\$route\.query\.missing_cover === '1'/)
  assert.match(vueSource, /params\.missing_cover = this\.candidateFilter\.missing_cover/)
  assert.match(vueSource, /if \(filter\.missing_cover\) query\.missing_cover = '1'/)
  assert.match(vueSource, /缺封面/)
})

test('download candidate panel exposes repair scope for data quality routes', () => {
  assert.match(vueSource, /:candidate-repair-scope="candidateRepairScope"/)
  assert.match(vueSource, /candidateRepairScope\(\)/)
  assert.match(vueSource, /const visibleMagnetTargets = this\.visibleMagnetTargetCount/)
  assert.match(vueSource, /visibleMagnetTargetCount\(\)/)
  assert.match(vueSource, /this\.filteredCandidates\.filter\(candidate =>/)
  assert.match(vueSource, /total:\s*this\.candidateTotal/)
  assert.match(vueSource, /scopeLabel:\s*this\.candidateRepairScopeLabel/)
  assert.match(vueSource, /candidateRepairScopeLabel\(\)/)
  assert.match(candidatePanelSource, /candidateRepairScope/)
  assert.match(candidatePanelSource, /class="candidate-repair-scope"/)
  assert.match(candidatePanelSource, /candidateRepairScope\.total/)
  assert.match(candidatePanelSource, /candidateRepairScope\.visibleMagnetTargets/)
  assert.match(candidatePanelSource, /当前页可补磁力/)
  assert.match(candidatePanelSource, /筛选总量/)
  assert.match(candidateStyle, /\.candidate-repair-scope/)
  assert.match(candidateStyle, /\.candidate-repair-scope-grid/)
})

test('home page keeps heavyweight styles in external scoped stylesheets', () => {
  assert.match(vueSource, /<style scoped src="\.\.\/features\/home\/home\.css"><\/style>/)
  assert.ok(externalStyle.length > 8000, 'external home stylesheet should carry the base workspace CSS')
  assert.ok(candidateStyle.length > 10000, 'candidate workspace stylesheet should travel with the lazy chunk')
  assert.ok(vueSource.split('\n').length < 400, 'Home.vue should stay small enough to review and parse quickly')
})

test('home candidate controls use shared Apple glass tokens', () => {
  const downloadTabs = cssBlock(source, '.download-tabs')
  const tabButton = cssBlock(source, '.tab-btn')
  const tabHover = cssBlock(source, '.tab-btn:hover')
  const tabActive = cssBlock(source, '.tab-btn.active')
  const tabBadge = cssBlock(source, '.tab-badge')
  const tabBadgeSubtle = cssBlock(source, '.tab-badge.subtle')
  const candidateSearch = cssBlock(source, '.candidate-search-input')
  const candidateSearchFocus = cssBlock(source, '.candidate-search-input:focus')
  const bulkToolbar = cssBlock(source, '.bulk-toolbar')
  const chip = cssBlock(source, '.chip')
  const chipActive = cssBlock(source, '.chip.active')
  const dangerLink = cssBlock(source, '.link-btn.danger')
  const dangerLinkHover = cssBlock(source, '.link-btn.danger:hover')

  assert.match(downloadTabs, /border:\s*1px solid var\(--glass-control-border\)/)
  assert.match(downloadTabs, backgroundIncludes('material-glass-sheet'))
  assert.match(downloadTabs, /box-shadow:\s*var\(--glass-inner-shadow\)/)

  for (const block of [tabButton, candidateSearch, bulkToolbar, chip]) {
    assert.match(block, /border:\s*1px solid var\(--glass-control-border\)/)
    assert.match(block, backgroundIncludes('material-glass-control'))
    assert.match(block, /box-shadow:\s*var\(--glass-control-shadow\)/)
    assert.match(block, /backdrop-filter:\s*blur\(var\(--glass-blur-control\)\)\s*saturate\(var\(--glass-saturate-control\)\)/)
    assert.doesNotMatch(block, /border:\s*(?:0|none|1px solid transparent)/)
    assert.doesNotMatch(block, /background:\s*(?:transparent|none)/)
  }

  for (const block of [tabHover]) {
    assert.match(block, backgroundIncludes('material-glass-control-hover'))
    assert.match(block, /border-color:\s*var\(--glass-control-border-hover\)/)
    assert.match(block, /box-shadow:\s*var\(--glass-control-shadow-hover\)/)
  }

  for (const block of [tabActive, chipActive]) {
    assert.match(block, backgroundIncludes('glass-active-material'))
    assert.match(block, /border-color:\s*var\(--glass-active-border\)/)
    assert.match(block, /box-shadow:\s*var\(--glass-active-shadow\)/)
  }

  assert.match(dangerLink, backgroundIncludes('badge-error-bg'))
  assert.match(dangerLink, /var\(--surface-specular-edge\)/)
  assert.match(dangerLink, /var\(--surface-noise\)/)
  assert.match(dangerLink, /border-color:\s*var\(--badge-error-border\)/)
  assert.match(dangerLink, /color:\s*var\(--badge-error-text\)/)
  assert.match(dangerLinkHover, backgroundIncludes('badge-error-bg'))
  assert.match(dangerLinkHover, /var\(--surface-specular-edge-strong\)/)
  assert.match(dangerLinkHover, /var\(--surface-noise\)/)
  assert.match(dangerLinkHover, /border-color:\s*var\(--badge-error-border\)/)

  for (const block of [candidateSearchFocus]) {
    assert.match(block, backgroundIncludes('material-glass-control-hover'))
    assert.match(block, /border-color:\s*var\(--glass-control-border-hover\)/)
  }

  assert.match(tabBadge, layeredSemanticBackground('badge-error-bg'))
  assert.match(tabBadge, /color:\s*var\(--badge-error-text\)/)
  assert.match(tabBadge, /box-shadow:\s*var\(--glass-control-shadow\)/)
  assert.match(tabBadge, /backdrop-filter:\s*blur\(var\(--glass-blur-control\)\)\s*saturate\(var\(--glass-saturate-control\)\)/)
  assert.match(tabBadgeSubtle, layeredSemanticBackground('badge-success-bg'))
  assert.match(tabBadgeSubtle, /color:\s*var\(--badge-success-text\)/)

  for (const block of [
    downloadTabs,
    tabButton,
    tabActive,
    tabBadge,
    tabBadgeSubtle,
    candidateSearch,
    bulkToolbar,
    chip
  ]) {
    assert.doesNotMatch(block, /rgba\(255,\s*255,\s*255|rgba\(255,255,255|#fff|#ffffff/i)
  }
})

test('home candidate controls mirror hover glass treatment for keyboard focus', () => {
  const tabFocus = cssBlock(source, '.tab-btn:focus-visible')
  const chipFocus = cssBlock(source, '.chip:focus-visible:not(:disabled)')
  const linkFocus = cssBlock(source, '.link-btn:focus-visible')
  const dangerLinkFocus = cssBlock(source, '.link-btn.danger:focus-visible')
  const pageFocus = cssBlock(source, '.page-btn:focus-visible:not(:disabled)')

  for (const [block, label] of [
    [tabFocus, 'download tab focus'],
    [chipFocus, 'candidate chip focus'],
    [linkFocus, 'candidate link focus'],
    [pageFocus, 'candidate pagination focus'],
  ]) {
    assert.match(block, /outline:\s*none/, `${label} should replace the default outline`)
    assert.match(block, backgroundIncludes('material-glass-control-hover'), `${label} should use hover glass material`)
    assert.match(block, /border-color:\s*var\(--glass-control-border-hover\)/, `${label} should use hover border`)
    assert.match(block, /box-shadow:\s*var\(--glass-control-shadow-hover\),\s*var\(--focus-ring\)/, `${label} should expose a subtle focus ring`)
  }

  assert.match(tabFocus, /color:\s*var\(--text-primary\)/)
  assert.match(chipFocus, /color:\s*var\(--text-primary\)/)
  assert.match(pageFocus, /transform:\s*translateY\(-1px\)/)
  assert.match(linkFocus, /text-decoration-color:\s*var\(--link-underline-hover\)/)
  assert.match(dangerLinkFocus, /outline:\s*none/)
  assert.match(dangerLinkFocus, backgroundIncludes('badge-error-bg'))
  assert.match(dangerLinkFocus, /var\(--surface-specular-edge-strong\)/)
  assert.match(dangerLinkFocus, /var\(--surface-noise\)/)
  assert.match(dangerLinkFocus, /border-color:\s*var\(--badge-error-border\)/)
  assert.match(dangerLinkFocus, /box-shadow:\s*var\(--glass-control-shadow-hover\),\s*0 0 0 3px color-mix\(in srgb,\s*var\(--badge-error-text\) 18%,\s*transparent\)/)
  assert.doesNotMatch(dangerLinkFocus, /rgba\(var\(--accent-rgb\)|rgba\(var\(--error-rgb\)/)
})

test('home dashboard and task surfaces use shared Apple glass materials', () => {
  const statCard = cssBlock(source, '.stat-card')
  const statCardHover = cssBlock(source, '.stat-card:hover')
  const candidateMetric = cssBlock(source, '.candidate-metric')
  const candidateMetricHover = cssBlock(source, '.candidate-metric:hover')
  const candidateFilterLedger = cssBlock(source, '.candidate-filter-ledger')
  const filterBar = cssBlock(source, '.filter-bar')
  const filterBarHover = cssBlock(source, '.filter-bar:hover')
  const statIcon = cssBlock(source, '.stat-icon')
  const pageButton = cssBlock(source, '.page-btn')
  const pageButtonHover = cssBlock(source, '.page-btn:hover:not(:disabled)')
  const taskCover = cssBlock(source, '.task-cover')
  const coverPlaceholder = cssBlock(source, '.cover-placeholder')
  const coverOverlay = cssBlock(source, '.cover-overlay')
  const coverCode = cssBlock(source, '.cover-code')
  const actionChipPrimary = cssBlock(source, '.action-chip.primary')
  const taskActions = cssBlock(source, '.task-actions')
  const inlineDialogOverlay = cssBlock(source, '.inline-dialog-overlay')
  const inlineDialog = cssBlock(source, '.inline-dialog')
  const magnetInput = cssBlock(source, '.magnet-editor-input')
  const magnetInputFocus = cssBlock(source, '.magnet-editor-input:focus')
  const detailGridItem = cssBlock(source, '.candidate-detail-grid > div')
  const detailMagnet = cssBlock(source, '.candidate-detail-magnet')
  const eventDot = cssBlock(source, '.event-dot')
  const taskError = cssBlock(source, '.task-error')
  const detailError = cssBlock(source, '.candidate-detail-error')

  for (const [block, label] of [
    [statCard, 'stat cards'],
    [candidateMetric, 'candidate metrics'],
    [candidateFilterLedger, 'candidate filter ledger'],
    [filterBar, 'filter bar'],
    [pageButton, 'pagination buttons'],
    [taskCover, 'task covers'],
    [coverPlaceholder, 'cover placeholders'],
    [magnetInput, 'magnet editor input'],
    [detailGridItem, 'candidate detail tiles'],
    [detailMagnet, 'candidate detail magnet']
  ]) {
    assertGlassControl(block, label)
    assert.doesNotMatch(block, /var\(--surface-control\)|var\(--bg-card\)|var\(--bg-secondary\)|var\(--border-light\)|rgba\(255,\s*255,\s*255|#fff|#ffffff/i)
  }

  for (const [block, label] of [
    [statCardHover, 'stat card hover'],
    [candidateMetricHover, 'candidate metric hover'],
    [filterBarHover, 'filter bar hover'],
    [pageButtonHover, 'pagination button hover']
  ]) {
    assertGlassControlHover(block, label)
    assert.doesNotMatch(block, /var\(--surface-control-hover\)|var\(--border-light\)/)
  }

  assertGlassSubtle(statIcon, 'stat icon')
  assert.match(statIcon, /border:\s*1px solid var\(--glass-control-border\)/)
  assert.match(statIcon, /box-shadow:\s*var\(--glass-control-shadow\)/)

  assert.match(inlineDialog, /border:\s*1px solid var\(--glass-control-border\)/)
  assert.match(inlineDialog, backgroundIncludes('material-glass-sheet'))
  assert.match(inlineDialog, /box-shadow:\s*var\(--shadow-sheet\)/)
  assert.doesNotMatch(inlineDialog, /var\(--border-light\)/)

  assert.match(coverOverlay, /--home-cover-scrim-clear:\s*var\(--media-caption-scrim-clear\)/)
  assert.match(coverOverlay, /--home-cover-scrim-strong:\s*var\(--media-caption-scrim-strong\)/)
  assert.match(coverOverlay, /background:\s*linear-gradient\(180deg,\s*var\(--home-cover-scrim-clear\),\s*var\(--home-cover-scrim-strong\)\)/)
  assert.doesNotMatch(coverOverlay, /rgba\(0,\s*0,\s*0|rgba\(0,0,0|#000|#000000/i)
  assert.match(coverCode, /color:\s*var\(--media-caption-text\)/)
  assert.doesNotMatch(coverCode, /color:\s*white|#fff|#ffffff/i)

  assert.match(actionChipPrimary, backgroundIncludes('glass-active-material'))
  assert.match(actionChipPrimary, /border-color:\s*var\(--glass-active-border\)/)
  assert.match(actionChipPrimary, /color:\s*var\(--text-primary\)/)
  assert.match(actionChipPrimary, /box-shadow:\s*var\(--glass-active-shadow\)/)
  assert.doesNotMatch(actionChipPrimary, /background:\s*var\(--accent\)|color:\s*var\(--text-on-accent\)|border-color:\s*var\(--accent\)/)

  assert.match(taskActions, /border-top:\s*1px solid var\(--glass-control-border\)/)
  assert.doesNotMatch(taskActions, /var\(--border\)/)

  assert.match(inlineDialogOverlay, /z-index:\s*var\(--z-modal\)/)
  assert.match(inlineDialogOverlay, /background:\s*var\(--surface-scrim\)/)
  assert.match(inlineDialogOverlay, /backdrop-filter:\s*blur\(var\(--glass-blur-control\)\)\s*saturate\(var\(--glass-saturate-control\)\)/)
  assert.doesNotMatch(inlineDialogOverlay, /z-index:\s*\d+|rgba\(0,\s*0,\s*0/)

  assert.match(eventDot, backgroundIncludes('glass-active-material'))
  assert.match(eventDot, /border:\s*1px solid var\(--glass-active-border\)/)
  assert.match(eventDot, /box-shadow:\s*var\(--glass-active-shadow\)/)
  assert.doesNotMatch(eventDot, /background:\s*var\(--accent\)/)

  assert.match(magnetInputFocus, /border-color:\s*var\(--glass-active-border\)/)
  assert.match(magnetInputFocus, /box-shadow:\s*var\(--glass-active-shadow\)/)
  assert.match(taskError, /color:\s*var\(--badge-error-text\)/)
  assert.match(detailError, layeredSemanticBackground('badge-error-bg'))
  assert.match(detailError, /color:\s*var\(--badge-error-text\)/)
  assert.match(detailError, /box-shadow:\s*var\(--glass-control-shadow\)/)
  assert.match(detailError, /backdrop-filter:\s*blur\(var\(--glass-blur-control\)\)\s*saturate\(var\(--glass-saturate-control\)\)/)
  assert.doesNotMatch(`${taskError}\n${detailError}`, /#ef5350|#EF5350/)
})

test('home glass backgrounds are layered with specular and noise surfaces', () => {
  assert.deepEqual(singleLayerGlassBackgrounds(externalStyle), [])
})
