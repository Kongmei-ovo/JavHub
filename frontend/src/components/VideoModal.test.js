import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

function metadataLoadedFor(video) {
  const source = readFileSync(new URL('./VideoModal.vue', import.meta.url), 'utf8')
  const match = source.match(/metadataLoaded\(\) \{([\s\S]*?)\n    \},\n    directorsDisplay/)
  assert.ok(match, 'metadataLoaded computed property should be present')
  const metadataLoaded = new Function(`return function metadataLoaded() {${match[1]}\n}`)()
  return metadataLoaded.call({ video })
}

function galleryThumbsFor(video) {
  const source = readFileSync(new URL('./VideoModal.vue', import.meta.url), 'utf8')
  const match = source.match(/galleryThumbs\(\) \{([\s\S]*?)\n    \},\n  \},/)
  assert.ok(match, 'galleryThumbs computed property should be present')
  const galleryThumbs = new Function(`return function galleryThumbs() {${match[1]}\n}`)()
  return galleryThumbs.call({ video })
}

function summaryDisplayFor(video) {
  const source = readFileSync(new URL('./VideoModal.vue', import.meta.url), 'utf8')
  const match = source.match(/summaryDisplay\(\) \{([\s\S]*?)\n    \},\n    magnets/)
  assert.ok(match, 'summaryDisplay computed property should be present')
  const summaryDisplay = new Function(`return function summaryDisplay() {${match[1]}\n}`)()
  return summaryDisplay.call({ video })
}

test('metadataLoaded resolves when JavInfo detail loading finishes with empty metadata', () => {
  assert.equal(metadataLoadedFor({
    content_id: 'MIAA-784',
    _loading: { javinfo: false },
  }), true)
})

test('metadataLoaded remains true when legacy callers provide metadata fields', () => {
  assert.equal(metadataLoadedFor({
    content_id: 'MIAA-784',
    summary: 'Metadata summary',
  }), true)
})

test('metadataLoaded remains true when JavInfo directors are present', () => {
  assert.equal(metadataLoadedFor({
    content_id: 'MIAA-784',
    directors: [{ name_kanji: '松田コージ' }],
  }), true)
})

test('galleryThumbs uses supplement sample image urls when present', () => {
  assert.deepEqual(galleryThumbsFor({
    content_id: 'supp:1',
    sample_image_urls: ['https://example.test/1.jpg', 'https://example.test/2.jpg'],
  }), ['https://example.test/1.jpg', 'https://example.test/2.jpg'])
})

test('summaryDisplay prefers translated summary', () => {
  assert.equal(summaryDisplayFor({
    summary: 'Original summary',
    summary_translated: '翻译简介',
  }), '翻译简介')
  assert.equal(summaryDisplayFor({
    summary: 'Original summary',
  }), 'Original summary')
})

test('modal overlay is teleported above sheet overlays', () => {
  const source = readFileSync(new URL('./VideoModal.vue', import.meta.url), 'utf8')

  assert.match(source, /<teleport to="body">\s*<div v-if="visible" class="modal-overlay"/)
  assert.match(source, /\.modal-overlay\s*\{[\s\S]*z-index:\s*var\(--z-lightbox\)/)
})
