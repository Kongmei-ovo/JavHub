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

test('modal sheet keeps a visible translucent fallback without relying on backdrop filtering', () => {
  const source = readFileSync(new URL('./VideoModal.vue', import.meta.url), 'utf8')

  assert.match(source, /--modal-sheet-bg/)
  assert.match(source, /--modal-panel-bg/)
  assert.match(source, /\.modal-container\s*\{[\s\S]*background:\s*var\(--modal-sheet-bg\)/)
  assert.match(source, /\.modal-container\s*\{[\s\S]*backdrop-filter:\s*none/)
  assert.match(source, /\.modal-container\s*\{[\s\S]*-webkit-backdrop-filter:\s*none/)
  assert.doesNotMatch(source, /\.modal-container\s*\{[\s\S]*background:\s*rgba\(255,\s*255,\s*255,\s*0\.01\)/)
})

test('modal material stays readable and consistent over busy result grids', () => {
  const source = readFileSync(new URL('./VideoModal.vue', import.meta.url), 'utf8')
  const overlayBlock = source.match(/\.modal-overlay\s*\{[^}]*\}/)?.[0] || ''

  assert.match(source, /--modal-sheet-bg:\s*rgba\(18,\s*18,\s*20,\s*0\.64\)/)
  assert.match(source, /--modal-sheet-fallback:\s*rgba\(18,\s*18,\s*20,\s*0\.64\)/)
  assert.match(source, /:root\[data-theme="dark"\]\s+\.modal-overlay\s*\{[\s\S]*--modal-sheet-bg:\s*rgba\(14,\s*14,\s*16,\s*0\.68\)/)
  assert.match(source, /--modal-panel-bg:\s*rgba\(0,\s*0,\s*0,\s*0\.24\)/)
  assert.match(overlayBlock, /backdrop-filter:\s*none/)
  assert.match(overlayBlock, /-webkit-backdrop-filter:\s*none/)
  assert.doesNotMatch(source, /--modal-backdrop-blur/)
  assert.doesNotMatch(overlayBlock, /backdrop-filter:\s*blur/)
  assert.match(source, /\.modal-container\s*\{[\s\S]*backdrop-filter:\s*none/)
  assert.match(source, /\.modal-container\s*\{[\s\S]*-webkit-backdrop-filter:\s*none/)
})

test('modal actions use liquid glass control tokens instead of hardcoded pills', () => {
  const source = readFileSync(new URL('./VideoModal.vue', import.meta.url), 'utf8')
  const actionBlock = source.match(/\.preview-btn,\s*\n\.stream-btn,\s*\n\.favorite-btn\s*\{[\s\S]*?\n\}/)?.[0] || ''
  const primaryBlock = source.match(/\.preview-btn,\s*\n\.stream-btn\s*\{[\s\S]*?\n\}/)?.[0] || ''
  const secondaryBlock = source.match(/\.favorite-btn,\s*\n\.stream-download-btn\s*\{[\s\S]*?\n\}/)?.[0] || ''

  assert.match(source, /--modal-action-primary-bg:\s*var\(--glass-active-material\)/)
  assert.match(source, /--modal-action-secondary-bg:\s*var\(--material-glass-control\)/)
  assert.match(actionBlock, /backdrop-filter:\s*blur\(var\(--glass-blur-control\)\)\s*saturate\(var\(--glass-saturate-control\)\)/)
  assert.match(actionBlock, /box-shadow:\s*var\(--modal-action-shadow\)/)
  assert.match(primaryBlock, /background:\s*var\(--modal-action-primary-bg\)/)
  assert.match(secondaryBlock, /background:\s*var\(--modal-action-secondary-bg\)/)
  assert.doesNotMatch(source, /\.preview-btn\s*\{[^}]*background:\s*rgba\(255,\s*255,\s*255,\s*0\.9\)/)
  assert.doesNotMatch(source, /\.stream-btn\s*\{[^}]*background:\s*rgba\(255,\s*255,\s*255,\s*0\.9\)/)
})

test('modal detail labels use inherited modal text tokens without uppercase tracking', () => {
  const source = readFileSync(new URL('./VideoModal.vue', import.meta.url), 'utf8')
  const sectionTitleBlock = source.match(/\.section-title\s*\{[^}]*\}/)?.[0] || ''
  const metaLabelBlock = source.match(/\.meta-label\s*\{[^}]*\}/)?.[0] || ''

  assert.match(source, /--modal-text-muted:\s*rgba\(255,\s*255,\s*255,\s*0\.58\)/)
  assert.match(sectionTitleBlock, /color:\s*var\(--modal-text-muted\)/)
  assert.match(sectionTitleBlock, /letter-spacing:\s*0/)
  assert.doesNotMatch(sectionTitleBlock, /text-transform:\s*uppercase/)
  assert.match(metaLabelBlock, /color:\s*var\(--modal-text-muted\)/)
  assert.match(metaLabelBlock, /letter-spacing:\s*0/)
  assert.doesNotMatch(metaLabelBlock, /text-transform:\s*uppercase/)
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
