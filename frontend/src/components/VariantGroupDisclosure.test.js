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

test('VariantGroupDisclosure uses shared glass control materials and explicit motion', () => {
  const toggleBlock = sourceBlock('.variant-group-disclosure__toggle')
  const toggleHoverBlock = sourceBlock('.variant-group-disclosure__toggle:hover')
  const toggleActiveBlock = sourceBlock('.variant-group-disclosure__toggle:active')
  const rowBlock = sourceBlock('.variant-group-disclosure__row')
  const rowHoverBlock = sourceBlock('.variant-group-disclosure__row:hover')
  const labelBlock = sourceBlock('.variant-group-disclosure__labels span')

  for (const [block, name] of [[toggleBlock, 'toggle'], [rowBlock, 'row']]) {
    assert.match(block, /border:\s*1px solid var\(--glass-control-border\)/, `${name} should use shared glass border`)
    assert.match(block, /background:\s*var\(--surface-specular-edge\),\s*var\(--surface-noise\),\s*var\(--material-glass-control\)/, `${name} should use shared glass material`)
    assert.match(block, /box-shadow:\s*var\(--glass-control-shadow\)/, `${name} should use shared glass shadow`)
    assert.match(block, /backdrop-filter:\s*blur\(var\(--glass-blur-control\)\)\s*saturate\(var\(--glass-saturate-control\)\)/, `${name} should use control blur`)
    assert.match(block, /transition:\s*transform var\(--motion-standard\),\s*background var\(--motion-standard\),\s*border-color var\(--motion-standard\),\s*box-shadow var\(--motion-standard\),\s*color var\(--motion-fast\),\s*opacity var\(--motion-fast\)/, `${name} should use explicit motion tokens`)
    assert.doesNotMatch(block, /transition:\s*var\(--transition-pro\)|rgba\(255,\s*255,\s*255,\s*0\.04\)|background:\s*var\(--surface-control\)/, `${name} should not keep legacy flat surfaces`)
  }

  for (const [block, name] of [[toggleHoverBlock, 'toggle hover'], [rowHoverBlock, 'row hover']]) {
    assert.match(block, /background:\s*var\(--surface-specular-edge-strong\),\s*var\(--surface-noise\),\s*var\(--material-glass-control-hover\)/, `${name} should use shared hover material`)
    assert.match(block, /border-color:\s*var\(--glass-control-border-hover\)/, `${name} should use shared hover border`)
    assert.match(block, /box-shadow:\s*var\(--glass-control-shadow-hover\)/, `${name} should use shared hover shadow`)
    assert.match(block, /transform:\s*translateY\(-1px\)/, `${name} should add light lift`)
  }

  assert.match(toggleActiveBlock, /transform:\s*translateY\(0\)\s*scale\(0\.99\)/)
  assertLayeredSemanticBackground(labelBlock, '--badge-info-bg', 'variant label')
  assert.match(labelBlock, /border:\s*1px solid var\(--badge-info-border\)/)
  assert.match(labelBlock, /color:\s*var\(--badge-info-text\)/)
  assert.match(labelBlock, /box-shadow:\s*var\(--glass-control-shadow\)/)
  assert.match(labelBlock, /backdrop-filter:\s*blur\(var\(--glass-blur-control\)\)\s*saturate\(var\(--glass-saturate-control\)\)/)
  assert.doesNotMatch(source, /transition:\s*var\(--transition-pro\)/)
})
