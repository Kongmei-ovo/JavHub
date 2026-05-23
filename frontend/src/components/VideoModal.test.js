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

test('modal overlay teleports globally and can render inline on the detail page', () => {
  const source = readFileSync(new URL('./VideoModal.vue', import.meta.url), 'utf8')

  assert.match(source, /<teleport to="body" :disabled="inline">\s*<div v-if="visible" class="modal-overlay"/)
  assert.match(source, /inline:\s*\{ type: Boolean, default: false \}/)
  assert.match(source, /\.modal-overlay\.inline\s*\{[\s\S]*position:\s*static/)
  assert.match(source, /\.modal-overlay\s*\{[\s\S]*z-index:\s*var\(--z-lightbox\)/)
})

test('modal sheet keeps a visible frosted fallback when backdrop filtering is unavailable', () => {
  const source = readFileSync(new URL('./VideoModal.vue', import.meta.url), 'utf8')

  assert.match(source, /--modal-sheet-bg/)
  assert.match(source, /--modal-panel-bg/)
  assert.match(source, /\.modal-container\s*\{[\s\S]*background:\s*var\(--modal-sheet-bg\)/)
  assert.doesNotMatch(source, /\.modal-container\s*\{[\s\S]*background:\s*rgba\(255,\s*255,\s*255,\s*0\.01\)/)
})

test('modal material normalizes busy result grids behind the sheet', () => {
  const source = readFileSync(new URL('./VideoModal.vue', import.meta.url), 'utf8')
  const overlayBlock = source.match(/\.modal-overlay\s*\{[^}]*\}/)?.[0] || ''

  assert.match(source, /--modal-sheet-bg:\s*var\(--material-glass-sheet\)/)
  assert.match(source, /--modal-sheet-fallback:\s*rgba\(24,\s*24,\s*27,\s*0\.72\)/)
  assert.match(source, /:root\[data-theme="dark"\]\s+\.modal-overlay\s*\{[\s\S]*--modal-sheet-fallback:\s*rgba\(18,\s*18,\s*20,\s*0\.82\)/)
  assert.match(overlayBlock, /backdrop-filter:\s*none/)
  assert.match(overlayBlock, /-webkit-backdrop-filter:\s*none/)
  assert.doesNotMatch(source, /--modal-backdrop-blur/)
  assert.doesNotMatch(overlayBlock, /backdrop-filter:\s*blur/)
  assert.match(source, /\.modal-container\s*\{[\s\S]*backdrop-filter:\s*blur\(var\(--glass-blur-sheet\)\)\s*saturate\(var\(--glass-saturate-surface\)\)/)
})

test('modal keeps media player and hls libraries out of the base modal chunk', () => {
  const source = readFileSync(new URL('./VideoModal.vue', import.meta.url), 'utf8')

  assert.match(source, /defineAsyncComponent/)
  assert.match(source, /const VideoPlayerOverlay = defineAsyncComponent\(\(\) => import\('\.\.\/features\/video\/VideoPlayerOverlay\.vue'\)\)/)
  assert.match(source, /const HlsPlayerOverlay = defineAsyncComponent\(\(\) => import\('\.\.\/features\/video\/HlsPlayerOverlay\.vue'\)\)/)
  assert.match(source, /await import\('hls\.js\/dist\/hls\.light\.mjs'\)/)
  assert.doesNotMatch(source, /import Hls from 'hls\.js'/)
  assert.doesNotMatch(source, /import VideoPlayerOverlay from '\.\.\/features\/video\/VideoPlayerOverlay\.vue'/)
  assert.doesNotMatch(source, /import HlsPlayerOverlay from '\.\.\/features\/video\/HlsPlayerOverlay\.vue'/)
})

test('modal uses the lightweight message proxy after removing the Element Plus plugin', () => {
  const source = readFileSync(new URL('./VideoModal.vue', import.meta.url), 'utf8')

  assert.match(source, /import \{ ElMessage \} from '\.\.\/utils\/message\.js'/)
  assert.doesNotMatch(source, /\$message/)
})

test('modal declares emitted events for async component listeners', () => {
  const source = readFileSync(new URL('./VideoModal.vue', import.meta.url), 'utf8')

  assert.match(source, /emits:\s*\[\s*'close',\s*'download',\s*'navigate'\s*\]/)
})

test('modal favorites are keyed by concrete service version', () => {
  const source = readFileSync(new URL('./VideoModal.vue', import.meta.url), 'utf8')

  assert.match(source, /function videoFavoriteId\(video = \{\}\)/)
  assert.match(source, /return id && serviceCode \? `\$\{id\}::\$\{serviceCode\}` : id/)
  assert.match(source, /favoriteState\.isFavorited\('video', id\)/)
  assert.match(source, /favoriteState\.toggle\('video', id, \{[\s\S]*service_code: this\.video\.service_code \|\| ''/)
})

test('mobile modal taxonomy chips stay in a resilient grid on iOS widths', () => {
  const source = readFileSync(new URL('./VideoModal.vue', import.meta.url), 'utf8')

  assert.match(source, /class="tag-list"/)
  assert.match(source, /class="tag-label"/)
  assert.match(source, /\.tag-list\s*\{[\s\S]*display:\s*flex/)
  assert.match(source, /@media \(max-width: 768px\)\s*\{[\s\S]*\.tag-list\s*\{[\s\S]*display:\s*grid/)
  assert.match(source, /grid-template-columns:\s*repeat\(auto-fill,\s*minmax\(clamp\(108px,\s*31vw,\s*148px\),\s*1fr\)\)/)
  assert.match(source, /\.tag-label\s*\{[\s\S]*-webkit-line-clamp:\s*2/)
  assert.match(source, /\.actress-tag\.clickable\s*\{[\s\S]*text-decoration:\s*none/)
})

test('mobile modal sheet uses stable poster sizing and momentum scrolling', () => {
  const source = readFileSync(new URL('./VideoModal.vue', import.meta.url), 'utf8')

  assert.match(source, /-webkit-overflow-scrolling:\s*touch/)
  assert.match(source, /\.modal-gallery\s*\{[\s\S]*height:\s*min\(42dvh,\s*320px\)/)
  assert.match(source, /\.gallery-img\s*\{[\s\S]*height:\s*100%[\s\S]*object-fit:\s*contain/)
  assert.match(source, /\.modal-actions\s*\{[\s\S]*grid-template-columns:\s*repeat\(auto-fit,\s*minmax\(96px,\s*1fr\)\)/)
})
