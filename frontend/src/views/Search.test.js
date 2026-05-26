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
  assert.match(source, /variant_group_items/)
  assert.match(source, /另 \{\{ item\.variant_group_count - 1 \}\} 个版本/)
  assert.match(source, /toggleVariantGroup\(item\)/)
})

test('search cards pass backend display code and variant labels into MovieCard', () => {
  assert.match(source, /:contentId="item\.display_code \|\| item\.dvd_id \|\| item\.content_id"/)
  assert.match(source, /:dvdId="item\.display_code \|\| item\.dvd_id \|\| item\.content_id"/)
  assert.match(source, /:variantLabels="item\.variant_labels \|\| \[\]"/)
  assert.match(source, /:variantExplanations="item\.variant_explanations \|\| \[\]"/)
})
