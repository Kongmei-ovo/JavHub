import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

const source = readFileSync(new URL('./Search.vue', import.meta.url), 'utf8')

function sourceBlock(selector) {
  const escaped = selector.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  const match = source.match(new RegExp(`${escaped}\\s*\\{([^}]*)\\}`))
  assert.ok(match, `${selector} should exist`)
  return match[1]
}

test('search page requests grouped variants with explanations by default', () => {
  assert.match(source, /variant_mode:\s*'grouped'/)
  assert.match(source, /include_variant_explanations:\s*1/)
  assert.doesNotMatch(source, /variant_scope:\s*'indexed'/)
})

test('search page can expand backend-provided variant groups inline', () => {
  assert.match(source, /expandedVariantGroups/)
  assert.match(source, /variantGroupItems\(item\)/)
  assert.match(source, /另 \{\{ item\.variant_group_count - 1 \}\} 个版本/)
  assert.match(source, /toggleVariantGroup\(item\)/)
})

test('search page reuses shared video variant presentation helpers', () => {
  assert.match(source, /import \{ variantGroupKey, visibleVariantItems \} from '\.\.\/utils\/videoVariantPresentation\.js'/)
  assert.doesNotMatch(source, /variantGroupKey\(item\) \{\s*return item\.canonical_code/)
  assert.doesNotMatch(source, /const keyOf = \(value\) => value\?\.content_id/)
})

test('search cards pass backend display code and variant labels into MovieCard', () => {
  assert.match(source, /:contentId="item\.display_code \|\| item\.dvd_id \|\| item\.content_id"/)
  assert.match(source, /:dvdId="item\.display_code \|\| item\.dvd_id \|\| item\.content_id"/)
  assert.match(source, /:variantLabels="item\.variant_labels \|\| \[\]"/)
  assert.match(source, /:variantExplanations="item\.variant_explanations \|\| \[\]"/)
})

test('search filter chrome uses shared liquid glass controls without uppercase microcopy', () => {
  const sortLabelBlock = sourceBlock('.sort-strip-label')
  const panelLabelBlock = sourceBlock('.panel-field label')
  const appliedChipBlock = sourceBlock('.applied-chip')
  const mobileBlock = source.match(/@media \(max-width:\s*768px\)\s*\{[\s\S]*\n\}/)?.[0] || ''

  assert.match(sortLabelBlock, /letter-spacing:\s*0/)
  assert.doesNotMatch(sortLabelBlock, /text-transform:\s*uppercase/)
  assert.match(panelLabelBlock, /letter-spacing:\s*0/)
  assert.doesNotMatch(panelLabelBlock, /text-transform:\s*uppercase/)
  assert.match(appliedChipBlock, /background:\s*var\(--surface-control\)/)
  assert.match(appliedChipBlock, /box-shadow:\s*var\(--glass-control-shadow\)/)
  assert.match(appliedChipBlock, /backdrop-filter:\s*blur\(var\(--glass-blur-control\)\)\s*saturate\(var\(--glass-saturate-control\)\)/)
  assert.match(mobileBlock, /\.variant-inline-item\s*\{[\s\S]*grid-template-columns:\s*1fr/)
  assert.doesNotMatch(source, /\.variant-inline-item\s*\{[^}]*background:\s*rgba\(255,\s*255,\s*255,\s*0\.04\)/)
})

test('search inline variant controls use shared glass materials and explicit motion', () => {
  const variantButtonBlock = sourceBlock('.variant-expand-btn')
  const variantButtonHoverBlock = sourceBlock('.variant-expand-btn:hover')
  const variantButtonActiveBlock = sourceBlock('.variant-expand-btn:active')
  const variantRowBlock = sourceBlock('.variant-inline-item')
  const variantRowHoverBlock = sourceBlock('.variant-inline-item:hover')

  for (const [block, name] of [[variantButtonBlock, 'variant button'], [variantRowBlock, 'variant row']]) {
    assert.match(block, /border:\s*1px solid var\(--glass-control-border\)/, `${name} should use shared glass border`)
    assert.match(block, /background:\s*var\(--material-glass-control\)/, `${name} should use shared glass material`)
    assert.match(block, /box-shadow:\s*var\(--glass-control-shadow\)/, `${name} should use shared glass shadow`)
    assert.match(block, /backdrop-filter:\s*blur\(var\(--glass-blur-control\)\)\s*saturate\(var\(--glass-saturate-control\)\)/, `${name} should use control blur`)
    assert.match(block, /transition:\s*transform var\(--motion-standard\),\s*background var\(--motion-standard\),\s*border-color var\(--motion-standard\),\s*box-shadow var\(--motion-standard\),\s*color var\(--motion-fast\),\s*opacity var\(--motion-fast\)/, `${name} should use explicit motion tokens`)
    assert.doesNotMatch(block, /transition:\s*var\(--transition-pro\)|background:\s*var\(--surface-control\)/, `${name} should not keep legacy flat controls`)
  }

  for (const [block, name] of [[variantButtonHoverBlock, 'variant button hover'], [variantRowHoverBlock, 'variant row hover']]) {
    assert.match(block, /background:\s*var\(--material-glass-control-hover\)/, `${name} should use shared hover material`)
    assert.match(block, /border-color:\s*var\(--glass-control-border-hover\)/, `${name} should use shared hover border`)
    assert.match(block, /box-shadow:\s*var\(--glass-control-shadow-hover\)/, `${name} should use shared hover shadow`)
    assert.match(block, /transform:\s*translateY\(-1px\)/, `${name} should lightly lift`)
  }

  assert.match(variantButtonActiveBlock, /transform:\s*translateY\(0\)\s*scale\(0\.99\)/)
  assert.doesNotMatch(source, /\.variant-expand-btn\s*\{[^}]*transition:\s*var\(--transition-pro\)/)
})
