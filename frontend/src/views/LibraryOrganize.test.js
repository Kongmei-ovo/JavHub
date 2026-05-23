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
