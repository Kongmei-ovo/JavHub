import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

const source = readFileSync(new URL('./VariantGroupDisclosure.vue', import.meta.url), 'utf8')

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
