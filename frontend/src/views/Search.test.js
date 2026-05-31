import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

const source = readFileSync(new URL('./Search.vue', import.meta.url), 'utf8')

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
  const sortLabelBlock = source.match(/\.sort-strip-label\s*\{[^}]*\}/)?.[0] || ''
  const panelLabelBlock = source.match(/\.panel-field label\s*\{[^}]*\}/)?.[0] || ''
  const appliedChipBlock = source.match(/\.applied-chip\s*\{[^}]*\}/)?.[0] || ''
  const variantButtonBlock = source.match(/\.variant-expand-btn\s*\{[^}]*\}/)?.[0] || ''
  const variantRowBlock = source.match(/\.variant-inline-item\s*\{[^}]*\}/)?.[0] || ''
  const mobileBlock = source.match(/@media \(max-width:\s*768px\)\s*\{[\s\S]*\n\}/)?.[0] || ''

  assert.match(sortLabelBlock, /letter-spacing:\s*0/)
  assert.doesNotMatch(sortLabelBlock, /text-transform:\s*uppercase/)
  assert.match(panelLabelBlock, /letter-spacing:\s*0/)
  assert.doesNotMatch(panelLabelBlock, /text-transform:\s*uppercase/)
  assert.match(appliedChipBlock, /background:\s*var\(--surface-control\)/)
  assert.match(appliedChipBlock, /box-shadow:\s*var\(--glass-control-shadow\)/)
  assert.match(appliedChipBlock, /backdrop-filter:\s*blur\(var\(--glass-blur-control\)\)\s*saturate\(var\(--glass-saturate-control\)\)/)
  assert.match(variantButtonBlock, /box-shadow:\s*var\(--glass-control-shadow\)/)
  assert.match(variantButtonBlock, /backdrop-filter:\s*blur\(var\(--glass-blur-control\)\)/)
  assert.match(variantRowBlock, /background:\s*var\(--surface-control\)/)
  assert.match(variantRowBlock, /box-shadow:\s*var\(--glass-control-shadow\)/)
  assert.match(variantRowBlock, /backdrop-filter:\s*blur\(var\(--glass-blur-control\)\)/)
  assert.match(mobileBlock, /\.variant-inline-item\s*\{[\s\S]*grid-template-columns:\s*1fr/)
  assert.doesNotMatch(source, /\.variant-inline-item\s*\{[^}]*background:\s*rgba\(255,\s*255,\s*255,\s*0\.04\)/)
})
