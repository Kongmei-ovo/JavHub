import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

const vueSource = readFileSync(new URL('./LibraryOrganize.vue', import.meta.url), 'utf8')
const externalStyle = readFileSync(new URL('../features/library/libraryOrganize.css', import.meta.url), 'utf8')
const source = `${vueSource}\n${externalStyle}`

function cssRule(selector) {
  const escaped = selector.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  const match = source.match(new RegExp(`${escaped} \\{([\\s\\S]*?)\\n\\}`))
  assert.ok(match, `Expected CSS rule for ${selector}`)
  return match[1]
}

function cssGroupedRule(selector) {
  const escaped = selector.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  const match = source.match(new RegExp(`${escaped}[\\s\\S]*?\\{([\\s\\S]*?)\\n\\}`))
  assert.ok(match, `Expected grouped CSS rule starting at ${selector}`)
  return match[1]
}

function darkRule(selector) {
  return cssGroupedRule(`:global(:root[data-theme="dark"] ${selector}`)
}

function backgroundIncludes(token) {
  return new RegExp(`background:[\\s\\S]*var\\(--${token}\\)`)
}

function singleLayerGlassBackgrounds(css) {
  return css
    .split('\n')
    .map((line, index) => ({ line: index + 1, text: line.trim() }))
    .filter(({ text }) => /^background:\s*var\(--(?:material-glass-subtle|material-glass-control|material-glass-control-hover|material-glass-elevated|material-glass-sheet|glass-active-material)\);$/.test(text))
}

test('library organize keeps large scoped styles in a feature stylesheet', () => {
  assert.match(vueSource, /<style scoped src="\.\.\/features\/library\/libraryOrganize\.css"><\/style>/)
  assert.ok(vueSource.split('\n').length < 1100, 'LibraryOrganize.vue should stay below 1100 lines')
  assert.ok(externalStyle.split('\n').length > 800, 'external stylesheet should contain the moved page styles')
})

test('library organize top chrome uses the shared Apple glass material', () => {
  assert.match(source, /class="organize-header apple-surface"/)
  assert.match(source, /class="status-strip organize-status apple-surface"/)
  assert.match(source, /class="organize-tabs apple-surface"/)

  const headerRule = cssRule('.organize-header')
  const headerBeforeRule = cssRule('.organize-header::before')
  const statusRule = cssRule('.organize-status')
  const tabActiveRule = cssRule('.tab-btn.active')
  const setupBannerRule = cssRule('.setup-banner')

  assert.match(headerRule, /min-height: 148px/)
  assert.match(headerRule, /border:\s*1px solid var\(--glass-edge-strong\)/)
  assert.match(headerRule, backgroundIncludes('material-glass-sheet'))
  assert.match(headerRule, /box-shadow:\s*var\(--glass-surface-shadow\)/)
  assert.match(headerRule, /backdrop-filter:\s*blur\(var\(--glass-blur-surface\)\)\s*saturate\(var\(--glass-saturate-surface\)\)/)
  assert.doesNotMatch(headerRule, /rgba\(255,\s*255,\s*255|rgba\(255,255,255|radial-gradient|linear-gradient\(145deg/)
  assert.match(headerRule, /overflow: hidden/)
  assert.match(headerBeforeRule, backgroundIncludes('material-glass-subtle'))
  assert.match(headerBeforeRule, /--organize-header-mask-start:\s*var\(--media-edge-mask-strong\)/)
  assert.match(headerBeforeRule, /--organize-header-mask-end:\s*var\(--media-edge-mask-clear\)/)
  assert.match(headerBeforeRule, /mask-image:\s*linear-gradient\(90deg,\s*var\(--organize-header-mask-start\),\s*var\(--organize-header-mask-end\) 74%\)/)
  assert.doesNotMatch(headerBeforeRule, /background-image|rgba\(255,\s*255,\s*255|rgba\(255,255,255|rgba\(0,\s*0,\s*0|rgba\(0,0,0|#000|#000000/i)
  assert.match(statusRule, backgroundIncludes('material-glass-sheet'))
  assert.match(statusRule, /backdrop-filter: blur\(var\(--glass-blur-surface\)\)/)
  assert.match(tabActiveRule, backgroundIncludes('glass-active-material'))
  assert.match(tabActiveRule, /box-shadow: var\(--glass-active-shadow\)/)

  assert.match(setupBannerRule, /border:\s*1px solid var\(--glass-edge-strong\)/)
  assert.match(setupBannerRule, backgroundIncludes('material-glass-sheet'))
  assert.match(setupBannerRule, /box-shadow:\s*var\(--glass-surface-shadow\)/)
  assert.match(setupBannerRule, /backdrop-filter:\s*blur\(var\(--glass-blur-surface\)\)\s*saturate\(var\(--glass-saturate-surface\)\)/)
  assert.doesNotMatch(setupBannerRule, /rgba\(255,\s*255,\s*255|rgba\(255,255,255|var\(--surface-card\)/)
})

test('library organize tab controls use shared liquid glass tokens', () => {
  const tabRule = cssRule('.tab-btn')
  const tabHoverRule = cssRule('.tab-btn:hover')
  const tabActiveRule = cssRule('.tab-btn.active')

  assert.match(tabRule, /border:\s*1px solid var\(--glass-control-border\)/)
  assert.match(tabRule, backgroundIncludes('material-glass-control'))
  assert.match(tabRule, /box-shadow:\s*var\(--glass-control-shadow\)/)
  assert.match(tabRule, /backdrop-filter:\s*blur\(var\(--glass-blur-control\)\)\s*saturate\(var\(--glass-saturate-control\)\)/)
  assert.match(tabHoverRule, /border-color:\s*var\(--glass-control-border-hover\)/)
  assert.match(tabHoverRule, backgroundIncludes('material-glass-control-hover'))
  assert.match(tabHoverRule, /box-shadow:\s*var\(--glass-control-shadow-hover\)/)
  assert.match(tabActiveRule, /border-color:\s*var\(--glass-active-border\)/)
  assert.match(tabActiveRule, backgroundIncludes('glass-active-material'))
  assert.doesNotMatch(tabRule, /border:\s*1px solid transparent/)
  assert.doesNotMatch(tabRule, /background:\s*transparent/)
})

test('library organize keyboard focus mirrors hover glass control treatment', () => {
  const statusFocusRule = cssRule('.status-cell:focus-visible')
  const tabFocusRule = cssRule('.tab-btn:focus-visible')
  const workflowFocusRule = cssGroupedRule('.priority-row:focus-visible,')
  const chipFocusRule = cssGroupedRule('.candidate-pills button:focus-visible,')

  for (const [rule, label] of [
    [statusFocusRule, 'status metric focus'],
    [tabFocusRule, 'organize tab focus'],
    [workflowFocusRule, 'workflow action focus'],
    [chipFocusRule, 'candidate chip focus'],
  ]) {
    assert.match(rule, /outline:\s*none/, `${label} should replace the default outline`)
    assert.match(rule, /border-color:\s*var\(--glass-control-border-hover\)/, `${label} should use hover border`)
    assert.match(rule, backgroundIncludes('material-glass-control-hover'), `${label} should use hover glass material`)
    assert.match(rule, /box-shadow:\s*var\(--glass-control-shadow-hover\),\s*0 0 0 3px rgba\(var\(--accent-rgb\),\s*0\.12\)/, `${label} should show a subtle Apple-style focus ring`)
  }

  assert.match(statusFocusRule, /transform:\s*translateY\(-1px\)/)
  assert.match(tabFocusRule, /color:\s*var\(--text-primary\)/)
  assert.match(workflowFocusRule, /transform:\s*translateY\(-1px\)/)
})

test('library organize workbench cards use liquid glass depth instead of flat white cards', () => {
  const panelRule = cssGroupedRule('.workbench-panel,')
  const rowRule = cssGroupedRule('.priority-row,')
  const inputRule = cssGroupedRule('.mini-check-form input,')

  assert.match(panelRule, /border: 1px solid var\(--glass-edge\)/)
  assert.match(panelRule, backgroundIncludes('material-glass-elevated'))
  assert.match(panelRule, /backdrop-filter: blur\(var\(--glass-blur-surface\)\)/)
  assert.match(rowRule, /box-shadow: var\(--glass-inner-shadow\)/)
  assert.match(rowRule, /transition:/)
  assert.match(inputRule, backgroundIncludes('material-glass-control'))
  assert.match(inputRule, /box-shadow: var\(--glass-control-shadow\)/)
  const focusRule = cssGroupedRule('.mini-check-form input:focus,')
  assert.match(focusRule, /border-color:\s*var\(--glass-active-border\)/)
  assert.doesNotMatch(focusRule, /border-color:\s*var\(--accent\)/)
})

test('library organize nested list rows mirror Apple glass hover while child actions are focused', () => {
  const nestedHoverRule = cssGroupedRule('.mapping-item:hover,')
  const nestedFocusRule = cssGroupedRule('.mapping-item:focus-within,')
  const darkNestedHoverRule = cssGroupedRule(':global(:root[data-theme="dark"] .mapping-item:hover),')
  const darkNestedFocusRule = cssGroupedRule(':global(:root[data-theme="dark"] .mapping-item:focus-within),')

  assert.match(source, /\.mapping-item:hover,\s*\.duplicate-group:hover,\s*\.job-row:hover,\s*\.duplicate-entry:hover,\s*\.check-item:hover,\s*\.inventory-candidate:hover,\s*\.missing-video:hover\s*\{/)
  assert.match(source, /\.mapping-item:focus-within,\s*\.duplicate-group:focus-within,\s*\.job-row:focus-within,\s*\.duplicate-entry:focus-within,\s*\.check-item:focus-within,\s*\.inventory-candidate:focus-within,\s*\.missing-video:focus-within\s*\{/)

  assert.match(nestedHoverRule, /border-color:\s*var\(--glass-control-border-hover\)/)
  assert.match(nestedHoverRule, backgroundIncludes('material-glass-control-hover'))
  assert.match(nestedHoverRule, /box-shadow:\s*var\(--glass-control-shadow-hover\)/)
  assert.match(nestedHoverRule, /transform:\s*translateY\(-1px\)/)

  assert.match(nestedFocusRule, /outline:\s*none/)
  assert.match(nestedFocusRule, /border-color:\s*var\(--glass-control-border-hover\)/)
  assert.match(nestedFocusRule, backgroundIncludes('material-glass-control-hover'))
  assert.match(nestedFocusRule, /box-shadow:\s*var\(--glass-control-shadow-hover\),\s*0 0 0 3px rgba\(var\(--accent-rgb\),\s*0\.12\)/)
  assert.match(nestedFocusRule, /transform:\s*translateY\(-1px\)/)

  assert.match(darkNestedHoverRule, /border-color:\s*var\(--glass-control-border-hover\)/)
  assert.match(darkNestedHoverRule, backgroundIncludes('material-glass-control-hover'))
  assert.match(darkNestedHoverRule, /box-shadow:\s*var\(--glass-control-shadow-hover\)/)
  assert.match(darkNestedFocusRule, /border-color:\s*var\(--glass-control-border-hover\)/)
  assert.match(darkNestedFocusRule, backgroundIncludes('material-glass-control-hover'))
  assert.match(darkNestedFocusRule, /box-shadow:\s*var\(--glass-control-shadow-hover\),\s*0 0 0 3px rgba\(var\(--accent-rgb\),\s*0\.12\)/)
  assert.match(darkNestedFocusRule, /transform:\s*translateY\(-1px\)/)
})

test('library organize nested controls keep glass treatment across light and dark themes', () => {
  const detailRule = cssRule('.actor-detail-head')
  const chipRule = cssGroupedRule('.candidate-pills button,')
  const chipActiveRule = cssRule('.chip.active')
  const autoMatchRule = cssRule('.auto-match-panel')

  assert.match(detailRule, /border: 1px solid var\(--glass-control-border\)/)
  assert.match(detailRule, backgroundIncludes('material-glass-control'))
  assert.match(chipRule, /box-shadow: var\(--glass-inner-shadow\)/)
  assert.match(chipActiveRule, backgroundIncludes('glass-active-material'))
  assert.match(autoMatchRule, backgroundIncludes('material-glass-control'))
  assert.match(source, /:global\(:root\[data-theme="dark"\] \.organize-header\)/)
  assert.match(source, /:global\(:root\[data-theme="dark"\] \.organize-status\)/)
})

test('library organize inventory media placeholders use shared subtle glass material', () => {
  const posterRule = cssGroupedRule('.missing-video img,')
  const actorAvatarRule = cssRule('.actor-avatar')

  for (const rule of [posterRule, actorAvatarRule]) {
    assert.match(rule, backgroundIncludes('material-glass-subtle'))
    assert.match(rule, /border:\s*1px solid var\(--glass-control-border\)/)
    assert.match(rule, /box-shadow:\s*var\(--glass-inner-shadow\)/)
    assert.doesNotMatch(rule, /rgba\(255,\s*255,\s*255|linear-gradient\(145deg/)
  }
})

test('library organize dark theme overlays defer to shared material tokens', () => {
  const headerRule = darkRule('.organize-header)')
  const headerBeforeRule = darkRule('.organize-header::before)')
  const surfaceRule = darkRule('.organize-status),')
  const controlRule = darkRule('.status-cell),')
  const hoverRule = darkRule('.status-cell:hover),')
  const focusRule = darkRule('.mini-check-form input:focus),')

  assert.match(headerRule, /border-color:\s*var\(--glass-edge-strong\)/)
  assert.match(headerRule, backgroundIncludes('material-glass-elevated'))
  assert.doesNotMatch(headerRule, /rgba\(255,\s*255,\s*255|rgba\(255,255,255|linear-gradient|radial-gradient/)

  assert.match(headerBeforeRule, backgroundIncludes('material-glass-subtle'))
  assert.doesNotMatch(headerBeforeRule, /background-image|rgba\(255,\s*255,\s*255|rgba\(255,255,255/)

  assert.match(surfaceRule, /border-color:\s*var\(--glass-edge\)/)
  assert.match(surfaceRule, backgroundIncludes('material-glass-elevated'))
  assert.match(surfaceRule, /box-shadow:\s*var\(--glass-surface-shadow\)/)
  assert.doesNotMatch(surfaceRule, /rgba\(255,255,255/)
  assert.doesNotMatch(surfaceRule, /linear-gradient\(145deg/)

  assert.match(controlRule, /border-color:\s*var\(--glass-control-border\)/)
  assert.match(controlRule, backgroundIncludes('material-glass-control'))
  assert.doesNotMatch(controlRule, /rgba\(255,255,255/)
  assert.doesNotMatch(controlRule, /linear-gradient\(145deg/)

  assert.match(hoverRule, /border-color:\s*var\(--glass-control-border-hover\)/)
  assert.match(hoverRule, backgroundIncludes('material-glass-control-hover'))
  assert.match(hoverRule, /box-shadow:\s*var\(--glass-control-shadow-hover\)/)
  assert.doesNotMatch(hoverRule, /rgba\(255,255,255/)
  assert.doesNotMatch(hoverRule, /linear-gradient\(145deg/)

  assert.match(focusRule, /border-color:\s*var\(--glass-control-border-hover\)/)
  assert.match(focusRule, /box-shadow:\s*var\(--glass-control-shadow-hover\),\s*0 0 0 4px rgba\(var\(--accent-rgb\),\s*0\.10\)/)
  assert.doesNotMatch(focusRule, /rgba\(255,255,255/)
})

test('library organize first load uses compact overview instead of eight-way fanout', () => {
  const reloadAllBlock = source.match(/async function reloadAll\(\) \{[\s\S]*?\n\}/)?.[0] || ''

  assert.match(reloadAllBlock, /loadOverview\(\)/)
  assert.doesNotMatch(reloadAllBlock, /Promise\.all\(\[/)
  assert.match(source, /async function loadOverview\(\)/)
  assert.match(source, /api\.getLibraryOrganizeOverview/)
})

test('library organize uses overview totals instead of first page array length for queue metrics', () => {
  assert.match(source, /const missingTotal = ref\(0\)/)
  assert.match(source, /const duplicateTotal = ref\(0\)/)
  assert.match(source, /missingTotal\.value = Number\(data\?\.missing\?\.total \|\| missingVideos\.value\.length \|\| 0\)/)
  assert.match(source, /duplicateTotal\.value = Number\(data\?\.duplicates\?\.total \|\| duplicates\.value\.length \|\| 0\)/)
  assert.match(source, /\{ value: 'inventory', label: '库存对比', count: missingTotal\.value \}/)
  assert.match(source, /\{ value: 'duplicates', label: '重复清理', count: duplicateTotal\.value \}/)
  assert.match(source, /Number\(missingTotal\.value \|\| 0\)/)
  assert.match(source, /Number\(duplicateTotal\.value \|\| 0\)/)
})

test('library organize defers duplicate scan until duplicate tab is opened', () => {
  assert.match(source, /const duplicatesDeferred = ref\(false\)/)
  assert.match(source, /duplicatesDeferred\.value = Boolean\(data\?\.duplicates\?\.deferred\)/)
  assert.match(source, /function ensureDuplicateTabLoaded\(\)/)
  assert.match(source, /activeTab\.value === 'duplicates'[\s\S]*duplicatesDeferred\.value[\s\S]*loadDuplicates\(\)/)
  assert.match(source, /watch\(activeTab, ensureDuplicateTabLoaded\)/)
})

test('library organize requests a bounded missing-video page', () => {
  assert.match(source, /api\.listInventoryMissing\(\{ page: 1, page_size: 80 \}\)/)
})

test('library organize glass backgrounds are layered with specular and noise surfaces', () => {
  assert.deepEqual(singleLayerGlassBackgrounds(externalStyle), [])
})
