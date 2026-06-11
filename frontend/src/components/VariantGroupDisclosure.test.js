import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

const source = readFileSync(new URL('./VariantGroupDisclosure.vue', import.meta.url), 'utf8')

function sourceBlock(selector) {
  const escaped = selector.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  const match = source.match(new RegExp(`${escaped}\\s*\\{([^}]*)\\}`))
  assert.ok(match, `${selector} should exist`)
  return match[1]
}

function assertLayeredSemanticBackground(block, token, label) {
  assert.match(
    block,
    new RegExp(`background:\\s*var\\(--surface-specular-edge\\),\\s*var\\(--surface-noise\\),\\s*var\\(${token}\\)`),
    `${label} should layer semantic fill with shared glass highlights`
  )
}

test('VariantGroupDisclosure declares the required props and emits', () => {
  assert.match(source, /variantGroupCount/)
  assert.match(source, /variantGroupItems/)
  assert.match(source, /expanded/)
  assert.match(source, /itemKey/)
  assert.match(source, /defineEmits\(\['toggle', 'openVariant'\]\)/)
})

test('VariantGroupDisclosure toggles labels between collapsed and expanded states', () => {
  assert.match(source, /收起版本/)
  assert.match(source, /另 \{\{ hiddenCount \}\} 个版本/)
})

test('VariantGroupDisclosure renders backend-provided variant rows without fetching or opening modals', () => {
  assert.match(source, /v-for="variant in visibleItems"/)
  assert.match(source, /:key="variantKey\(variant\)"/)
  assert.match(source, /displayCode\(variant\)/)
  assert.match(source, /variantLabels\(variant\)/)
  assert.match(source, /\$emit\('openVariant', variant\)/)
  assert.doesNotMatch(source, /api\./)
  assert.doesNotMatch(source, /openVideoModal/)
})

test('VariantGroupDisclosure separates glass toggle chrome from solid variant rows', () => {
  const toggleBlock = sourceBlock('.variant-group-disclosure__toggle')
  const toggleHoverBlock = sourceBlock('.variant-group-disclosure__toggle:hover')
  const toggleActiveBlock = sourceBlock('.variant-group-disclosure__toggle:active')
  const rowBlock = sourceBlock('.variant-group-disclosure__row')
  const rowHoverBlock = sourceBlock('.variant-group-disclosure__row:hover')
  const labelBlock = sourceBlock('.variant-group-disclosure__labels span')

  assert.match(toggleBlock, /border:\s*1px solid var\(--glass-control-border\)/)
  assert.match(toggleBlock, /background:\s*var\(--surface-specular-edge\),\s*var\(--surface-noise\),\s*var\(--material-glass-control\)/)
  assert.match(toggleBlock, /box-shadow:\s*var\(--glass-control-shadow\)/)
  assert.match(toggleBlock, /backdrop-filter:\s*blur\(var\(--glass-blur-control\)\)\s*saturate\(var\(--glass-saturate-control\)\)/)

  assert.match(toggleHoverBlock, /background:\s*var\(--surface-specular-edge-strong\),\s*var\(--surface-noise\),\s*var\(--material-glass-control-hover\)/)
  assert.match(toggleHoverBlock, /border-color:\s*var\(--glass-control-border-hover\)/)
  assert.match(toggleHoverBlock, /box-shadow:\s*var\(--glass-control-shadow-hover\)/)

  assert.match(rowBlock, /border:\s*1px solid var\(--hairline\)/)
  assert.match(rowBlock, /background:\s*var\(--card-2\)/)
  assert.match(rowBlock, /box-shadow:\s*none/)
  assert.doesNotMatch(rowBlock, /material-glass|surface-specular-edge|surface-noise|backdrop-filter/)
  assert.match(rowHoverBlock, /background:\s*var\(--card-hover\)/)
  assert.match(rowHoverBlock, /border-color:\s*var\(--hairline-strong\)/)
  assert.match(rowHoverBlock, /box-shadow:\s*var\(--shadow-card\)/)
  assert.doesNotMatch(rowHoverBlock, /material-glass|surface-specular-edge|surface-noise|backdrop-filter/)

  for (const [block, name] of [[toggleBlock, 'toggle'], [rowBlock, 'row']]) {
    assert.match(block, /transition:\s*transform var\(--motion-standard\),\s*opacity var\(--motion-fast\)/, `${name} should use lightweight motion tokens`)
    assert.doesNotMatch(block, /transition:[^;]*(?:background|border-color|box-shadow|filter|backdrop-filter)/, `${name} should keep material changes out of transitions`)
  }

  assert.match(toggleActiveBlock, /transform:\s*translateY\(0\)\s*scale\(0\.99\)/)
  assertLayeredSemanticBackground(labelBlock, '--badge-info-bg', 'variant label')
  assert.match(labelBlock, /border:\s*1px solid var\(--badge-info-border\)/)
  assert.match(labelBlock, /color:\s*var\(--badge-info-text\)/)
  assert.match(labelBlock, /box-shadow:\s*var\(--glass-control-shadow\)/)
  assert.match(labelBlock, /backdrop-filter:\s*blur\(var\(--glass-blur-control\)\)\s*saturate\(var\(--glass-saturate-control\)\)/)
  assert.doesNotMatch(source, /transition:\s*var\(--transition-pro\)/)
})
