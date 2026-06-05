import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

const vueSource = readFileSync(new URL('./Subscription.vue', import.meta.url), 'utf8')
const externalStyle = readFileSync(new URL('../features/subscription/subscription.css', import.meta.url), 'utf8')
const source = `${vueSource}\n${externalStyle}`

function cssBlock(selector) {
  const escaped = selector.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  const match = source.match(new RegExp(`${escaped}\\s*\\{([^}]*)\\}`))
  assert.ok(match, `${selector} should exist`)
  return match[1]
}

test('subscription page keeps large scoped styles in a feature stylesheet', () => {
  assert.match(vueSource, /<style scoped src="\.\.\/features\/subscription\/subscription\.css"><\/style>/)
  assert.ok(vueSource.split('\n').length < 600, 'Subscription.vue should stay below 600 lines')
  assert.ok(externalStyle.split('\n').length > 530, 'external stylesheet should contain the moved subscription styles')
})

test('subscription chrome and sheets use shared Apple glass controls', () => {
  const pageBlock = cssBlock('.sub-page')
  const sheetOverlayBlock = cssBlock('.sheet-overlay')
  const sheetBlock = cssBlock('.sheet')
  const sheetTopBarBlock = cssBlock('.sheet-top-bar')

  for (const block of [pageBlock, sheetOverlayBlock]) {
    assert.match(block, /--subscription-control-bg:\s*var\(--surface-specular-edge\),\s*var\(--surface-noise\),\s*var\(--material-glass-control\)/)
    assert.match(block, /--subscription-control-bg-hover:\s*var\(--surface-specular-edge-strong\),\s*var\(--surface-noise\),\s*var\(--material-glass-control-hover\)/)
    assert.match(block, /--subscription-active-bg:\s*var\(--surface-specular-edge-strong\),\s*var\(--surface-noise\),\s*var\(--glass-active-material\)/)
    assert.match(block, /--subscription-active-bg-hover:\s*var\(--surface-specular-edge-strong\),\s*var\(--surface-noise\),\s*var\(--material-glass-control-hover\)/)
    assert.match(block, /--subscription-sheet-bg:\s*var\(--surface-specular-edge\),\s*var\(--surface-noise\),\s*var\(--material-glass-sheet\)/)
    assert.match(block, /--subscription-sticky-bg:\s*var\(--surface-specular-edge\),\s*var\(--surface-noise\),\s*var\(--material-glass-elevated\)/)
  }
  assert.match(pageBlock, /--subscription-control-border:\s*var\(--glass-control-border\)/)
  assert.match(pageBlock, /--subscription-control-shadow:\s*var\(--glass-control-shadow\)/)

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

  for (const selector of [
    '.clear-btn:focus-visible',
    '.pill-btn:focus-visible',
    '.top-action-btn:focus-visible',
    '.toggle-pill:focus-visible',
    '.action-btn:focus-visible',
  ]) {
    const block = cssBlock(selector)
    assert.match(block, /outline:\s*none/, `${selector} should avoid native focus outlines over glass`)
    assert.match(block, /box-shadow:\s*var\(--subscription-control-shadow-hover\),\s*0 0 0 4px rgba\(var\(--accent-rgb\),\s*0\.12\)/, `${selector} should use a restrained glass focus ring`)
  }

  for (const selector of [
    '.clear-btn:active',
    '.pill-btn:active',
    '.toggle-pill:active',
  ]) {
    const block = cssBlock(selector)
    assert.match(block, /transform:\s*translateY\(0\)\s*scale\(0\.97\)/, `${selector} should use compact pressed feedback`)
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
    assert.match(block, /background:\s*var\(--subscription-active-bg\)/, `${selector} should use active glass material`)
    assert.match(block, /color:\s*var\(--text-primary\)/, `${selector} should keep text on glass`)
    assert.match(block, /border-color:\s*var\(--glass-active-border\)/, `${selector} should use active glass border`)
    assert.match(block, /box-shadow:\s*var\(--glass-active-shadow\)/, `${selector} should use active glass shadow`)
    assert.doesNotMatch(block, /background:\s*var\(--accent\)|color:\s*var\(--text-on-accent\)|border-color:\s*transparent/, `${selector} should not keep legacy solid primary styles`)
  }

  for (const selector of ['.pill-btn-primary:hover', '.top-action-btn.primary:hover', '.action-btn.primary:hover']) {
    const block = cssBlock(selector)
    assert.match(block, /background:\s*var\(--subscription-active-bg-hover\)/, `${selector} should use shared hover material`)
    assert.match(block, /border-color:\s*var\(--glass-control-border-hover\)/, `${selector} should use shared hover border`)
    assert.match(block, /box-shadow:\s*var\(--glass-control-shadow-hover\)/, `${selector} should use shared hover shadow`)
    assert.doesNotMatch(block, /background:\s*var\(--accent-light\)|color:\s*var\(--text-on-accent\)/, `${selector} should not keep legacy solid hover styles`)
  }
})

test('subscription badges and discovery clear control use semantic glass tokens', () => {
  const badge = cssBlock('.inline-badge')
  const clearButton = cssBlock('.clear-btn')
  const clearButtonHover = cssBlock('.clear-btn:hover')

  assert.match(badge, /border:\s*1px solid var\(--badge-error-border\)/)
  assert.match(badge, /background:\s*var\(--badge-error-bg\)/)
  assert.match(badge, /color:\s*var\(--badge-error-text\)/)
  assert.doesNotMatch(badge, /#fff|#ffffff|#ff375f/i)

  assert.match(clearButton, /border:\s*1px solid var\(--subscription-control-border\)/)
  assert.match(clearButton, /background:\s*var\(--subscription-control-bg\)/)
  assert.match(clearButton, /box-shadow:\s*var\(--subscription-control-shadow\)/)
  assert.match(clearButton, /backdrop-filter:\s*blur\(var\(--glass-blur-control\)\)\s*saturate\(var\(--glass-saturate-control\)\)/)
  assert.doesNotMatch(clearButton, /background:\s*(?:none|transparent)|border:\s*(?:none|0)/)

  assert.match(clearButtonHover, /background:\s*var\(--subscription-control-bg-hover\)/)
  assert.match(clearButtonHover, /border-color:\s*var\(--subscription-control-border-hover\)/)
  assert.match(clearButtonHover, /box-shadow:\s*var\(--subscription-control-shadow-hover\)/)
})

test('subscription danger actions use semantic error tokens', () => {
  const pageBlock = cssBlock('.sub-page')
  const sheetOverlayBlock = cssBlock('.sheet-overlay')
  const dangerButton = cssBlock('.top-action-btn.danger')
  const dangerHover = cssBlock('.top-action-btn.danger:hover')

  for (const block of [pageBlock, sheetOverlayBlock]) {
    assert.match(block, /--subscription-danger-bg:\s*var\(--badge-error-bg\)/)
    assert.match(block, /--subscription-danger-border:\s*var\(--badge-error-border\)/)
    assert.doesNotMatch(block, /#ff375f/i)
  }

  assert.match(dangerButton, /color:\s*var\(--badge-error-text\)/)
  assert.match(dangerButton, /border-color:\s*var\(--badge-error-border\)/)
  assert.doesNotMatch(dangerButton, /#ff375f/i)
  assert.match(dangerHover, /background:\s*var\(--badge-error-bg\)/)
})

test('subscription loading spinners use shared glass border tokens', () => {
  const spinnerSmall = cssBlock('.spinner-small')
  const spinnerTiny = cssBlock('.spinner-tiny')

  assert.match(spinnerSmall, /border:\s*2px solid var\(--glass-control-border\)/)
  assert.match(spinnerTiny, /border:\s*1\.5px solid var\(--glass-control-border\)/)
  for (const block of [spinnerSmall, spinnerTiny]) {
    assert.match(block, /border-top-color:\s*var\(--text-primary\)/)
    assert.doesNotMatch(block, /var\(--border\)/)
  }
})
