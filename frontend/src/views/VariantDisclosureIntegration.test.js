import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

const discoveryDetail = readFileSync(new URL('./DiscoveryDetail.vue', import.meta.url), 'utf8')
const subscription = readFileSync(new URL('./Subscription.vue', import.meta.url), 'utf8')
const favorites = readFileSync(new URL('./Favorites.vue', import.meta.url), 'utf8')

test('DiscoveryDetail requests grouped variants and renders shared disclosure for every card mode', () => {
  assert.match(discoveryDetail, /variant_mode:\s*'grouped'/)
  assert.match(discoveryDetail, /variant_scope:\s*'indexed'/)
  assert.match(discoveryDetail, /include_variant_explanations:\s*1/)
  assert.match(discoveryDetail, /VariantGroupDisclosure/)
  assert.match(discoveryDetail, /movieCardVariantProps\(item\)/)
  assert.match(discoveryDetail, /visibleVariantItems\(item\)/)
  assert.match(discoveryDetail, /@openVariant="openModal"/)
  assert.equal((discoveryDetail.match(/<VariantGroupDisclosure/g) || []).length, 2)
})

test('Subscription sheet requests grouped variants and renders shared disclosure', () => {
  assert.match(subscription, /variant_mode:\s*'grouped'/)
  assert.match(subscription, /variant_scope:\s*'indexed'/)
  assert.match(subscription, /include_variant_explanations:\s*1/)
  assert.match(subscription, /VariantGroupDisclosure/)
  assert.match(subscription, /movieCardVariantProps\(movie\)/)
  assert.match(subscription, /visibleVariantItems\(movie\)/)
  assert.match(subscription, /@openVariant="openVideoModal"/)
})

test('Favorites renders variant disclosure only from existing metadata', () => {
  assert.match(favorites, /VariantGroupDisclosure/)
  assert.match(favorites, /movieCardVariantProps\(item\.metadata \|\| \{\}\)/)
  assert.match(favorites, /visibleVariantItems\(item\.metadata \|\| \{\}\)/)
  assert.match(favorites, /@openVariant="openVideoModalFromMetadata"/)
  assert.doesNotMatch(favorites, /variant_mode:\s*'grouped'/)
  assert.doesNotMatch(favorites, /include_variant_explanations:\s*1/)
})
