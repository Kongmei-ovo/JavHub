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

function backgroundIncludes(block, token) {
  const match = block.match(/background:\s*([^;]+);/)
  return Boolean(match && match[1].includes(token))
}

function assertLayeredBackground(block, token, name) {
  assert.ok(backgroundIncludes(block, token), `${name} should include ${token}`)
  assert.match(block, /var\(--surface-specular-edge/, `${name} should include a specular edge layer`)
  assert.match(block, /var\(--surface-noise\)/, `${name} should include the shared noise layer`)
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
  const smokeRunFocus = cssBlock('.provider-smoke-run:focus-visible')
  const healthCard = cssBlock('.source-health-card')
  const budgetMeter = cssBlock('.source-budget-meter')
  const miniSpinner = cssBlock('.mini-spinner')
  const largeSpinner = cssBlock('.spinner-large')

  assert.doesNotMatch(source, /var\(--surface-card\)|var\(--surface-control\)|var\(--surface-control-hover\)|var\(--surface-input-focus\)|var\(--white-20\)|rgba\(255,\s*107,\s*135/)

  assertLayeredBackground(filterInput, '--material-glass-control', 'source health filter input')
  assert.match(filterInput, /border:\s*1px solid var\(--glass-control-border\)/)
  assert.match(filterInput, /box-shadow:\s*var\(--glass-control-shadow\)/)
  assert.match(filterInput, /backdrop-filter:\s*blur\(var\(--glass-blur-control\)\)\s*saturate\(var\(--glass-saturate-control\)\)/)
  assert.match(filterFocus, /border-color:\s*var\(--glass-active-border\)/)
  assertLayeredBackground(filterFocus, '--glass-active-material', 'source health focused filter input')
  assert.match(filterFocus, /box-shadow:\s*var\(--glass-active-shadow\)/)
  assert.doesNotMatch([filterInput, filterFocus].join('\n'), /^.*background:\s*var\(--(?:material-glass-control|glass-active-material)\);.*$/gm)

  for (const block of [avatarPanel, smokeSummary, smokeHistory, healthCard]) {
    assertLayeredBackground(block, '--material-glass-sheet', 'source health sheet')
    assert.match(block, /border:\s*1px solid var\(--glass-control-border\)/)
    assert.match(block, /box-shadow:\s*var\(--glass-surface-shadow\)/)
    assert.match(block, /backdrop-filter:\s*blur\(var\(--glass-blur-surface\)\)\s*saturate\(var\(--glass-saturate-surface\)\)/)
  }
  assert.doesNotMatch([avatarPanel, smokeSummary, smokeHistory, healthCard].join('\n'), /^.*background:\s*var\(--material-glass-sheet\);.*$/gm)

  for (const block of [avatarMetric, smokeCard, smokeRun, budgetMeter]) {
    assertLayeredBackground(block, '--material-glass-control', 'source health control')
    assert.match(block, /border:\s*1px solid var\(--glass-control-border\)/)
    assert.match(block, /box-shadow:\s*var\(--glass-control-shadow\)/)
    assert.match(block, /backdrop-filter:\s*blur\(var\(--glass-blur-control\)\)\s*saturate\(var\(--glass-saturate-control\)\)/)
  }
  assert.doesNotMatch([avatarMetric, smokeCard, smokeRun, budgetMeter].join('\n'), /^.*background:\s*var\(--material-glass-control\);.*$/gm)

  assertLayeredBackground(smokeRunHover, '--material-glass-control-hover', 'source health hovered run')
  assert.match(smokeRunHover, /border-color:\s*var\(--glass-control-border-hover\)/)
  assert.match(smokeRunHover, /box-shadow:\s*var\(--glass-control-shadow-hover\)/)
  assert.doesNotMatch(smokeRunHover, /^.*background:\s*var\(--material-glass-control-hover\);.*$/gm)
  assertLayeredBackground(smokeRunFocus, '--material-glass-control-hover', 'source health focused run')
  assert.match(smokeRunFocus, /outline:\s*none/)
  assert.match(smokeRunFocus, /border-color:\s*var\(--glass-control-border-hover\)/)
  assert.match(smokeRunFocus, /box-shadow:\s*var\(--glass-control-shadow-hover\),\s*var\(--focus-ring\)/)
  assert.match(smokeRunFocus, /transform:\s*translateY\(-1px\)/)
  assert.doesNotMatch(smokeRunFocus, /^.*background:\s*var\(--material-glass-control-hover\);.*$/gm)
  assert.match(smokeCardFailed, /border-color:\s*var\(--badge-error-border\)/)

  for (const block of [miniSpinner, largeSpinner]) {
    assert.match(block, /border:\s*2px solid var\(--glass-control-border\)/)
    assert.match(block, /border-top-color:\s*var\(--badge-info-text\)/)
  }
})
