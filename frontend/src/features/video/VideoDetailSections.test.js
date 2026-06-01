import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

const gallerySource = readFileSync(new URL('./VideoGallerySection.vue', import.meta.url), 'utf8')
const magnetSource = readFileSync(new URL('./VideoMagnetSection.vue', import.meta.url), 'utf8')

test('video gallery section uses shared liquid glass media surfaces', () => {
  const titleBlock = gallerySource.match(/\.section-title\s*\{[^}]*\}/)?.[0] || ''
  const itemBlock = gallerySource.match(/\.gallery-item\s*\{[^}]*\}/)?.[0] || ''
  const hoverBlock = gallerySource.match(/\.gallery-item:hover\s*\{[^}]*\}/)?.[0] || ''
  const imageBlock = gallerySource.match(/\.gallery-item img\s*\{[^}]*\}/)?.[0] || ''
  const imageHoverBlock = gallerySource.match(/\.gallery-item:hover img\s*\{[^}]*\}/)?.[0] || ''
  const skeletonBlock = gallerySource.match(/\.skeleton\s*\{[^}]*\}/)?.[0] || ''
  const skeletonAfterBlock = gallerySource.match(/\.skeleton::after\s*\{[^}]*\}/)?.[0] || ''

  assert.match(titleBlock, /color:\s*var\(--modal-text-muted,\s*var\(--text-muted\)\)/)
  assert.match(titleBlock, /letter-spacing:\s*0/)
  assert.doesNotMatch(titleBlock, /text-transform:\s*uppercase/)
  assert.match(itemBlock, /background:\s*var\(--material-glass-control\)/)
  assert.match(itemBlock, /border:\s*1px solid var\(--glass-control-border\)/)
  assert.match(itemBlock, /box-shadow:\s*var\(--glass-control-shadow\)/)
  assert.match(itemBlock, /backdrop-filter:\s*blur\(var\(--glass-blur-control\)\)\s*saturate\(var\(--glass-saturate-control\)\)/)
  assert.match(hoverBlock, /background:\s*var\(--material-glass-control-hover\)/)
  assert.match(hoverBlock, /box-shadow:\s*var\(--glass-control-shadow-hover\)/)
  assert.match(imageBlock, /transition:\s*transform var\(--motion-standard\),\s*filter var\(--motion-standard\),\s*opacity var\(--motion-fast\)/)
  assert.match(imageHoverBlock, /transform:\s*scale\(1\.015\)/)
  assert.match(skeletonBlock, /background:\s*var\(--skeleton-base\)/)
  assert.match(skeletonAfterBlock, /var\(--skeleton-highlight\)/)
  assert.doesNotMatch(gallerySource, /rgba\(255,\s*255,\s*255,\s*0\.05\)|transition:\s*var\(--transition-pro\)|transition:\s*all\b/)
})

test('video magnet section uses shared glass controls and mobile-safe rows', () => {
  const titleBlock = magnetSource.match(/\.section-title\s*\{[^}]*\}/)?.[0] || ''
  const itemBlock = magnetSource.match(/\.magnet-item\s*\{[^}]*\}/)?.[0] || ''
  const actionBlock = magnetSource.match(/\.btn-copy,\s*\n\.btn-download\s*\{[\s\S]*?\n\}/)?.[0] || ''
  const mediaBlock = magnetSource.match(/@media \(max-width:\s*768px\)\s*\{[\s\S]*\n\}/)?.[0] || ''

  assert.match(titleBlock, /color:\s*var\(--modal-text-muted,\s*var\(--text-muted\)\)/)
  assert.match(titleBlock, /letter-spacing:\s*0/)
  assert.doesNotMatch(titleBlock, /text-transform:\s*uppercase/)
  assert.match(itemBlock, /background:\s*var\(--material-glass-control\)/)
  assert.match(itemBlock, /border:\s*1px solid var\(--glass-control-border\)/)
  assert.match(itemBlock, /box-shadow:\s*var\(--glass-control-shadow\)/)
  assert.match(itemBlock, /backdrop-filter:\s*blur\(var\(--glass-blur-control\)\)\s*saturate\(var\(--glass-saturate-control\)\)/)
  assert.match(actionBlock, /background:\s*var\(--material-glass-control\)/)
  assert.match(actionBlock, /border:\s*1px solid var\(--glass-control-border\)/)
  assert.match(actionBlock, /box-shadow:\s*var\(--glass-control-shadow\)/)
  assert.match(mediaBlock, /\.magnet-item\s*\{[\s\S]*flex-direction:\s*column/)
  assert.match(mediaBlock, /\.magnet-actions\s*\{[\s\S]*grid-template-columns:\s*repeat\(2,\s*minmax\(0,\s*1fr\)\)/)
  assert.doesNotMatch(magnetSource, /\.btn-download\s*\{[^}]*background:\s*rgba\(255,\s*255,\s*255,\s*0\.9\)/)
})
