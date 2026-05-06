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

test('metadataLoaded resolves when MetaTube loading finishes with empty metadata', () => {
  assert.equal(metadataLoadedFor({
    content_id: 'MIAA-784',
    _loading: { metatube: false },
  }), true)
})

test('metadataLoaded remains true when legacy callers provide metadata fields', () => {
  assert.equal(metadataLoadedFor({
    content_id: 'MIAA-784',
    summary: 'Metadata summary',
  }), true)
})
