import test from 'node:test'
import assert from 'node:assert/strict'
import {
  movieCardVariantProps,
  variantGroupKey,
  visibleVariantItems,
} from './videoVariantPresentation.js'

test('movieCardVariantProps centralizes MovieCard variant identifiers and labels', () => {
  const item = {
    content_id: 'cid-784',
    dvd_id: 'MIAA-784',
    display_code: 'MIAA-784',
    canonical_code: 'MIAA-00784',
    variant_labels: [{ key: 'digital', label: '数字版', short_label: '数字' }],
    variant_explanations: [{ label: '数字版', meaning: 'FANZA 配信版' }],
  }

  assert.deepEqual(movieCardVariantProps(item), {
    contentId: 'MIAA-784',
    dvdId: 'MIAA-784',
    displayCode: 'MIAA-784',
    canonicalCode: 'MIAA-00784',
    variantLabels: item.variant_labels,
    variantExplanations: item.variant_explanations,
  })
})

test('movieCardVariantProps falls back to dvd_id and content_id without mutating labels', () => {
  assert.deepEqual(movieCardVariantProps({ content_id: 'cid-1', dvd_id: 'DVD-001' }), {
    contentId: 'DVD-001',
    dvdId: 'DVD-001',
    displayCode: 'DVD-001',
    canonicalCode: '',
    variantLabels: [],
    variantExplanations: [],
  })
})

test('variantGroupKey prefers canonical code for stable expansion state', () => {
  assert.equal(variantGroupKey({
    content_id: 'cid-1',
    dvd_id: 'DVD-001',
    display_code: 'DVD-001',
    canonical_code: 'CANON-001',
  }), 'CANON-001')
})

test('visibleVariantItems hides the primary item from backend variant rows', () => {
  const primary = {
    content_id: 'cid-primary',
    dvd_id: 'DVD-001',
    display_code: 'DVD-001',
    variant_group_items: [
      { content_id: 'cid-primary', dvd_id: 'DVD-001', display_code: 'DVD-001' },
      { content_id: 'cid-digital', dvd_id: 'DVD-001-DIGITAL', display_code: 'DVD-001-DIGITAL' },
      { content_id: 'cid-rental', dvd_id: 'DVD-001-R', display_code: 'DVD-001-R' },
    ],
  }

  assert.deepEqual(
    visibleVariantItems(primary).map(item => item.content_id),
    ['cid-digital', 'cid-rental'],
  )
})

test('visibleVariantItems hides only the current row when display codes are shared', () => {
  const primary = {
    content_id: 'cid-primary',
    dvd_id: 'DVD-001',
    display_code: 'DVD-001',
    service_code: 'mono',
    variant_group_items: [
      { content_id: 'cid-primary', dvd_id: 'DVD-001', display_code: 'DVD-001', service_code: 'mono' },
      { content_id: 'cid-digital', dvd_id: null, display_code: 'DVD-001' },
      { content_id: 'cid-rental', dvd_id: '4DVD001', display_code: '4DVD001' },
    ],
  }

  assert.deepEqual(
    visibleVariantItems(primary).map(item => item.content_id),
    ['cid-digital', 'cid-rental'],
  )
})

test('visibleVariantItems keeps same-content digital rows distinct from dvd rows', () => {
  const primary = {
    content_id: 'miaa00784',
    dvd_id: 'MIAA-784',
    display_code: 'MIAA-784',
    service_code: 'mono',
    variant_group_items: [
      { content_id: 'miaa00784', dvd_id: 'MIAA-784', display_code: 'MIAA-784', service_code: 'mono' },
      { content_id: 'miaa00784', dvd_id: null, display_code: 'MIAA-784', service_code: 'digital' },
      { content_id: 'miaa00784bod', dvd_id: 'MIAA-784BOD', display_code: 'MIAA-784BOD', service_code: 'mono' },
    ],
  }

  assert.deepEqual(
    visibleVariantItems(primary).map(item => item.service_code || item.dvd_id),
    ['digital', 'mono'],
  )
})

test('visibleVariantItems returns an empty list when the backend did not include a group', () => {
  assert.deepEqual(visibleVariantItems({ content_id: 'solo' }), [])
})
