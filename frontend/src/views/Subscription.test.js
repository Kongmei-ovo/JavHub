import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

const source = readFileSync(new URL('./Subscription.vue', import.meta.url), 'utf8')

function cssBlock(selector) {
  const escaped = selector.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  const match = source.match(new RegExp(`${escaped}\\s*\\{([^}]*)\\}`))
  assert.ok(match, `${selector} should exist`)
  return match[1]
}

test('subscription chrome and sheets use shared Apple glass controls', () => {
  const pageBlock = cssBlock('.sub-page')
  const sheetOverlayBlock = cssBlock('.sheet-overlay')
  const sheetBlock = cssBlock('.sheet')
  const sheetTopBarBlock = cssBlock('.sheet-top-bar')

  assert.match(pageBlock, /--subscription-control-bg:\s*var\(--material-glass-control\)/)
  assert.match(pageBlock, /--subscription-control-bg-hover:\s*var\(--material-glass-control-hover\)/)
  assert.match(pageBlock, /--subscription-control-border:\s*var\(--glass-control-border\)/)
  assert.match(pageBlock, /--subscription-control-shadow:\s*var\(--glass-control-shadow\)/)
  assert.match(pageBlock, /--subscription-sheet-bg:\s*var\(--material-glass-sheet\)/)
  assert.match(sheetOverlayBlock, /--subscription-control-bg:\s*var\(--material-glass-control\)/)
  assert.match(sheetOverlayBlock, /--subscription-sheet-bg:\s*var\(--material-glass-sheet\)/)
  assert.match(sheetOverlayBlock, /--subscription-sticky-bg:\s*var\(--material-glass-elevated\)/)

  for (const selector of [
    '.hero-metrics span',
    '.search-bar',
    '.skel-card',
    '.pill-btn',
    '.top-action-btn',
    '.name-pill',
    '.toggle-pill',
    '.action-btn',
  ]) {
    const block = cssBlock(selector)
    assert.match(block, /background:\s*var\(--subscription-control-bg\)/, `${selector} should use shared glass background`)
    assert.match(block, /border:\s*1px solid var\(--subscription-control-border\)/, `${selector} should use shared glass border`)
    assert.match(block, /box-shadow:\s*var\(--subscription-control-shadow\)/, `${selector} should use shared glass shadow`)
    assert.match(block, /backdrop-filter:\s*blur\(var\(--glass-blur-control\)\)\s*saturate\(var\(--glass-saturate-control\)\)/, `${selector} should use shared control blur`)
    assert.doesNotMatch(block, /rgba\(255,\s*255,\s*255,\s*0\.(?:03|04|05|06|08|1|12)\)|blur\((?:40|80)px\)/, `${selector} should not keep legacy flat white glass`)
  }

  for (const selector of ['.pill-btn', '.top-action-btn', '.toggle-pill', '.action-btn']) {
    const block = cssBlock(selector)
    assert.doesNotMatch(block, /transition:\s*all\b/, `${selector} should avoid transition-all so theme glass tokens settle correctly`)
    assert.doesNotMatch(block, /transition:[^;]*(?:border-color|box-shadow)/, `${selector} should not transition tokenized glass edges across theme changes`)
  }

  for (const selector of [
    '.pill-btn:hover',
    '.top-action-btn:hover',
    '.toggle-pill:hover',
    '.action-btn:hover',
  ]) {
    const block = cssBlock(selector)
    assert.match(block, /background:\s*var\(--subscription-control-bg-hover\)/, `${selector} should use shared hover material`)
    assert.match(block, /border-color:\s*var\(--subscription-control-border-hover\)/, `${selector} should use shared hover border`)
    assert.match(block, /box-shadow:\s*var\(--subscription-control-shadow-hover\)/, `${selector} should use shared hover shadow`)
  }

  assert.match(sheetBlock, /background:\s*var\(--subscription-sheet-bg\)/)
  assert.match(sheetBlock, /border:\s*1px solid var\(--subscription-sheet-border\)/)
  assert.match(sheetBlock, /box-shadow:\s*var\(--shadow-sheet\)/)
  assert.match(sheetBlock, /backdrop-filter:\s*blur\(var\(--glass-blur-sheet\)\)\s*saturate\(var\(--glass-saturate-surface\)\)/)
  assert.doesNotMatch(sheetBlock, /rgba\(22,\s*22,\s*24,\s*0\.85\)|blur\(80px\)/)

  assert.match(sheetTopBarBlock, /background:\s*var\(--subscription-sticky-bg\)/)
  assert.match(sheetTopBarBlock, /backdrop-filter:\s*blur\(var\(--glass-blur-surface\)\)\s*saturate\(var\(--glass-saturate-surface\)\)/)
  assert.doesNotMatch(sheetTopBarBlock, /rgba\(22,\s*22,\s*24,\s*0\.7\)|blur\(20px\)/)
})

test('subscription primary actions use active glass instead of solid accent fills', () => {
  for (const selector of ['.pill-btn-primary', '.top-action-btn.primary', '.action-btn.primary']) {
    const block = cssBlock(selector)
    assert.match(block, /background:\s*var\(--glass-active-material\)/, `${selector} should use active glass material`)
    assert.match(block, /color:\s*var\(--text-primary\)/, `${selector} should keep text on glass`)
    assert.match(block, /border-color:\s*var\(--glass-active-border\)/, `${selector} should use active glass border`)
    assert.match(block, /box-shadow:\s*var\(--glass-active-shadow\)/, `${selector} should use active glass shadow`)
    assert.doesNotMatch(block, /background:\s*var\(--accent\)|color:\s*var\(--text-on-accent\)|border-color:\s*transparent/, `${selector} should not keep legacy solid primary styles`)
  }

  for (const selector of ['.pill-btn-primary:hover', '.top-action-btn.primary:hover', '.action-btn.primary:hover']) {
    const block = cssBlock(selector)
    assert.match(block, /background:\s*var\(--material-glass-control-hover\)/, `${selector} should use shared hover material`)
    assert.match(block, /border-color:\s*var\(--glass-control-border-hover\)/, `${selector} should use shared hover border`)
    assert.match(block, /box-shadow:\s*var\(--glass-control-shadow-hover\)/, `${selector} should use shared hover shadow`)
    assert.doesNotMatch(block, /background:\s*var\(--accent-light\)|color:\s*var\(--text-on-accent\)/, `${selector} should not keep legacy solid hover styles`)
  }
})
