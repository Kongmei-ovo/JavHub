import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

const source = readFileSync(new URL('./LibraryOrganize.vue', import.meta.url), 'utf8')

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

test('library organize top chrome uses the shared Apple glass material', () => {
  assert.match(source, /class="organize-header apple-surface"/)
  assert.match(source, /class="status-strip organize-status apple-surface"/)
  assert.match(source, /class="organize-tabs apple-surface"/)

  const headerRule = cssRule('.organize-header')
  const headerBeforeRule = cssRule('.organize-header::before')
  const statusRule = cssRule('.organize-status')
  const tabActiveRule = cssRule('.tab-btn.active')

  assert.match(headerRule, /min-height: 148px/)
  assert.match(headerRule, /radial-gradient/)
  assert.match(headerRule, /overflow: hidden/)
  assert.match(headerBeforeRule, /background-image/)
  assert.match(headerBeforeRule, /mask-image/)
  assert.match(statusRule, /background: var\(--material-glass-sheet\)/)
  assert.match(statusRule, /backdrop-filter: blur\(var\(--glass-blur-surface\)\)/)
  assert.match(tabActiveRule, /background: var\(--glass-active-material\)/)
  assert.match(tabActiveRule, /box-shadow: var\(--glass-active-shadow\)/)
})

test('library organize workbench cards use liquid glass depth instead of flat white cards', () => {
  const panelRule = cssGroupedRule('.workbench-panel,')
  const rowRule = cssGroupedRule('.priority-row,')
  const inputRule = cssGroupedRule('.mini-check-form input,')

  assert.match(panelRule, /border: 1px solid var\(--glass-edge\)/)
  assert.match(panelRule, /background: var\(--material-glass-elevated\)/)
  assert.match(panelRule, /backdrop-filter: blur\(var\(--glass-blur-surface\)\)/)
  assert.match(rowRule, /box-shadow: var\(--glass-inner-shadow\)/)
  assert.match(rowRule, /transition:/)
  assert.match(inputRule, /background: var\(--material-glass-control\)/)
  assert.match(inputRule, /box-shadow: var\(--glass-control-shadow\)/)
})

test('library organize nested controls keep glass treatment across light and dark themes', () => {
  const detailRule = cssRule('.actor-detail-head')
  const chipRule = cssGroupedRule('.candidate-pills button,')
  const chipActiveRule = cssRule('.chip.active')
  const autoMatchRule = cssRule('.auto-match-panel')

  assert.match(detailRule, /border: 1px solid var\(--glass-control-border\)/)
  assert.match(detailRule, /background: var\(--material-glass-control\)/)
  assert.match(chipRule, /box-shadow: var\(--glass-inner-shadow\)/)
  assert.match(chipActiveRule, /background: var\(--glass-active-material\)/)
  assert.match(autoMatchRule, /background: var\(--material-glass-control\)/)
  assert.match(source, /:global\(:root\[data-theme="dark"\] \.organize-header\)/)
  assert.match(source, /:global\(:root\[data-theme="dark"\] \.organize-status\)/)
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
