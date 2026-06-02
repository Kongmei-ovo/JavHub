import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

const vueSource = readFileSync(new URL('./Home.vue', import.meta.url), 'utf8')
const externalStyle = readFileSync(new URL('../features/home/home.css', import.meta.url), 'utf8')
const source = `${vueSource}\n${externalStyle}`

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

function singleLayerGlassBackgrounds(css) {
  return css
    .split('\n')
    .map((line, index) => ({ line: index + 1, text: line.trim() }))
    .filter(({ text }) => /^background:\s*var\(--(?:material-glass-control|material-glass-control-hover|material-glass-sheet|glass-active-material)\);$/.test(text))
}

test('home lazy-loads downloader management outside the base downloads chunk', () => {
  assert.match(source, /import \{ defineAsyncComponent \} from 'vue'/)
  assert.match(source, /const DownloaderManagementPanel = defineAsyncComponent\(\(\) => import\('\.\.\/features\/downloaders\/DownloaderManagementPanel\.vue'\)\)/)
  assert.match(source, /components:\s*\{ CandidateRunPanel, DownloaderManagementPanel \}/)
  assert.match(source, /<DownloaderManagementPanel[\s\S]*v-else-if="activeTab === 'downloaders'"/)
  assert.doesNotMatch(source, /<div\s+v-else-if="activeTab === 'downloaders'"\s+class="downloaders-panel apple-reveal"/)
})

test('home page keeps heavyweight styles in an external scoped stylesheet', () => {
  assert.match(vueSource, /<style scoped src="\.\.\/features\/home\/home\.css"><\/style>/)
  assert.ok(externalStyle.length > 20000, 'external home stylesheet should carry the moved workspace CSS')
  assert.ok(vueSource.split('\n').length < 1500, 'Home.vue should stay small enough to review and parse quickly')
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

  for (const block of [candidateSearchFocus]) {
    assert.match(block, backgroundIncludes('material-glass-control-hover'))
    assert.match(block, /border-color:\s*var\(--glass-control-border-hover\)/)
  }

  assert.match(tabBadge, /background:\s*var\(--badge-error-bg\)/)
  assert.match(tabBadge, /color:\s*var\(--badge-error-text\)/)
  assert.match(tabBadgeSubtle, /background:\s*var\(--badge-success-bg\)/)
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

test('home dashboard and task surfaces use shared Apple glass materials', () => {
  const statCard = cssBlock(source, '.stat-card')
  const statCardHover = cssBlock(source, '.stat-card:hover')
  const candidateMetric = cssBlock(source, '.candidate-metric')
  const candidateMetricHover = cssBlock(source, '.candidate-metric:hover')
  const filterBar = cssBlock(source, '.filter-bar')
  const filterBarHover = cssBlock(source, '.filter-bar:hover')
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
  assert.match(detailError, /background:\s*var\(--badge-error-bg\)/)
  assert.match(detailError, /color:\s*var\(--badge-error-text\)/)
  assert.doesNotMatch(`${taskError}\n${detailError}`, /#ef5350|#EF5350/)
})

test('home glass backgrounds are layered with specular and noise surfaces', () => {
  assert.deepEqual(singleLayerGlassBackgrounds(externalStyle), [])
})
