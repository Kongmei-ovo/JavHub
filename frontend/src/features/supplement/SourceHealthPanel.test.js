import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

const source = readFileSync(new URL('./SourceHealthPanel.vue', import.meta.url), 'utf8')

function cssBlocks(selector) {
  const blocks = [...source.matchAll(/([^{}]+)\{([^{}]*)\}/g)]
    .filter(([, selectors]) => selectors
      .split(',')
      .map(part => part.trim())
      .includes(selector))
    .map(([, , block]) => block)
  assert.ok(blocks.length, `${selector} block should exist`)
  return blocks
}

function cssBlock(selector) {
  return cssBlocks(selector).at(0)
}

test('source health diagnostics use shared Apple glass materials', () => {
  const filterInput = cssBlock('.filter-input')
  const filterFocus = cssBlock('.filter-input:focus')
  const avatarPanel = cssBlock('.avatar-sync-panel')
  const avatarMetric = cssBlock('.avatar-sync-metrics div')
  const smokeSummary = cssBlock('.provider-smoke-summary')
  const smokeCard = cssBlock('.provider-smoke-card')
  const smokeCardFailed = cssBlock('.provider-smoke-card.failed')
  const smokeHistory = cssBlock('.provider-smoke-history')
  const smokeRun = cssBlock('.provider-smoke-run')
  const smokeRunHover = cssBlock('.provider-smoke-run:hover')
  const healthCard = cssBlock('.source-health-card')
  const budgetMeter = cssBlock('.source-budget-meter')
  const miniSpinner = cssBlock('.mini-spinner')
  const largeSpinner = cssBlock('.spinner-large')

  assert.doesNotMatch(source, /var\(--surface-card\)|var\(--surface-control\)|var\(--surface-control-hover\)|var\(--surface-input-focus\)|var\(--white-20\)|rgba\(255,\s*107,\s*135/)

  assert.match(filterInput, /background:\s*var\(--material-glass-control\)/)
  assert.match(filterInput, /border:\s*1px solid var\(--glass-control-border\)/)
  assert.match(filterInput, /box-shadow:\s*var\(--glass-control-shadow\)/)
  assert.match(filterInput, /backdrop-filter:\s*blur\(var\(--glass-blur-control\)\)\s*saturate\(var\(--glass-saturate-control\)\)/)
  assert.match(filterFocus, /border-color:\s*var\(--glass-active-border\)/)
  assert.match(filterFocus, /background:\s*var\(--glass-active-material\)/)
  assert.match(filterFocus, /box-shadow:\s*var\(--glass-active-shadow\)/)

  for (const block of [avatarPanel, smokeSummary, smokeHistory, healthCard]) {
    assert.match(block, /background:\s*var\(--material-glass-sheet\)/)
    assert.match(block, /border:\s*1px solid var\(--glass-control-border\)/)
    assert.match(block, /box-shadow:\s*var\(--glass-surface-shadow\)/)
    assert.match(block, /backdrop-filter:\s*blur\(var\(--glass-blur-surface\)\)\s*saturate\(var\(--glass-saturate-surface\)\)/)
  }

  for (const block of [avatarMetric, smokeCard, smokeRun, budgetMeter]) {
    assert.match(block, /background:\s*var\(--material-glass-control\)/)
    assert.match(block, /border:\s*1px solid var\(--glass-control-border\)/)
    assert.match(block, /box-shadow:\s*var\(--glass-control-shadow\)/)
    assert.match(block, /backdrop-filter:\s*blur\(var\(--glass-blur-control\)\)\s*saturate\(var\(--glass-saturate-control\)\)/)
  }

  assert.match(smokeRunHover, /background:\s*var\(--material-glass-control-hover\)/)
  assert.match(smokeRunHover, /border-color:\s*var\(--glass-control-border-hover\)/)
  assert.match(smokeRunHover, /box-shadow:\s*var\(--glass-control-shadow-hover\)/)
  assert.match(smokeCardFailed, /border-color:\s*var\(--badge-error-border\)/)

  for (const block of [miniSpinner, largeSpinner]) {
    assert.match(block, /border:\s*2px solid var\(--glass-control-border\)/)
    assert.match(block, /border-top-color:\s*var\(--badge-info-text\)/)
  }
})
