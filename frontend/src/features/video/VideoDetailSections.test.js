import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

const gallerySource = readFileSync(new URL('./VideoGallerySection.vue', import.meta.url), 'utf8')
const magnetSource = readFileSync(new URL('./VideoMagnetSection.vue', import.meta.url), 'utf8')

function backgroundIncludes(block, token) {
  const match = block.match(/background:\s*([^;]+);/)
  return Boolean(match && match[1].includes(token))
}

function cssBlocks(source, selector) {
  const escaped = selector.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  return [...source.matchAll(new RegExp(`${escaped}\\s*\\{([^}]*)\\}`, 'g'))].map(match => match[1])
}

function cssBlockWith(source, selector, token) {
  const block = cssBlocks(source, selector).find(candidate => candidate.includes(token)) || ''
  assert.ok(block, `${selector} should include ${token}`)
  return block
}

function assertLayeredBackground(block, token, label) {
  assert.ok(backgroundIncludes(block, token), `${label} should include ${token}`)
  assert.match(block, /var\(--surface-specular-edge/, `${label} should include a specular edge layer`)
  assert.match(block, /var\(--surface-noise\)/, `${label} should include the shared noise layer`)
}

test('video gallery section uses shared liquid glass media surfaces', () => {
  const titleBlock = gallerySource.match(/\.section-title\s*\{[^}]*\}/)?.[0] || ''
  const itemBlock = gallerySource.match(/\.gallery-item\s*\{[^}]*\}/)?.[0] || ''
  const hoverBlock = gallerySource.match(/\.gallery-item:hover\s*\{[^}]*\}/)?.[0] || ''
  const focusBlock = gallerySource.match(/\.gallery-item:focus-visible\s*\{[^}]*\}/)?.[0] || ''
  const imageBlock = gallerySource.match(/\.gallery-item img\s*\{[^}]*\}/)?.[0] || ''
  const imageHoverBlock = gallerySource.match(/\.gallery-item:hover img\s*\{[^}]*\}/)?.[0] || ''
  const imageFocusBlock = gallerySource.match(/\.gallery-item:focus-visible img\s*\{[^}]*\}/)?.[0] || ''
  const skeletonBlock = gallerySource.match(/\.skeleton\s*\{[^}]*\}/)?.[0] || ''
  const skeletonAfterBlock = gallerySource.match(/\.skeleton::after\s*\{[^}]*\}/)?.[0] || ''

  assert.match(gallerySource, /<button[\s\S]*class="gallery-item"[\s\S]*type="button"[\s\S]*@click="\$emit\('open', idx\)"/)
  assert.doesNotMatch(gallerySource, /<div v-for="\(\s*thumb,\s*idx\s*\) in thumbs"[\s\S]*class="gallery-item"[\s\S]*@click/)
  assert.match(titleBlock, /color:\s*var\(--modal-text-muted,\s*var\(--text-muted\)\)/)
  assert.match(titleBlock, /letter-spacing:\s*0/)
  assert.doesNotMatch(titleBlock, /text-transform:\s*uppercase/)
  assert.ok(backgroundIncludes(itemBlock, '--material-glass-control'))
  assert.match(itemBlock, /var\(--surface-specular-edge\)/)
  assert.match(itemBlock, /var\(--surface-noise\)/)
  assert.match(itemBlock, /border:\s*1px solid var\(--glass-control-border\)/)
  assert.match(itemBlock, /box-shadow:\s*var\(--glass-control-shadow\)/)
  assert.match(itemBlock, /backdrop-filter:\s*blur\(var\(--glass-blur-control\)\)\s*saturate\(var\(--glass-saturate-control\)\)/)
  assert.ok(backgroundIncludes(hoverBlock, '--material-glass-control-hover'))
  assert.match(hoverBlock, /var\(--surface-specular-edge-strong\)/)
  assert.match(hoverBlock, /var\(--surface-noise\)/)
  assert.match(hoverBlock, /box-shadow:\s*var\(--glass-control-shadow-hover\)/)
  assert.ok(backgroundIncludes(focusBlock, '--material-glass-control-hover'))
  assert.match(focusBlock, /outline:\s*none/)
  assert.match(focusBlock, /box-shadow:\s*var\(--glass-control-shadow-hover\),\s*0 0 0 3px rgba\(var\(--accent-rgb\),\s*0\.12\)/)
  assert.match(itemBlock, /appearance:\s*none/)
  assert.match(itemBlock, /padding:\s*0/)
  assert.match(imageBlock, /transition:\s*transform var\(--motion-standard\),\s*filter var\(--motion-standard\),\s*opacity var\(--motion-fast\)/)
  assert.match(imageHoverBlock, /transform:\s*scale\(1\.015\)/)
  assert.match(imageFocusBlock, /transform:\s*scale\(1\.015\)/)
  assert.match(skeletonBlock, /background:\s*var\(--skeleton-base\)/)
  assert.match(skeletonBlock, /cursor:\s*default/)
  assert.match(skeletonBlock, /pointer-events:\s*none/)
  assert.match(skeletonAfterBlock, /var\(--skeleton-highlight\)/)
  assert.doesNotMatch(gallerySource, /rgba\(255,\s*255,\s*255,\s*0\.05\)|transition:\s*var\(--transition-pro\)|transition:\s*all\b/)
})

test('video magnet section uses shared glass controls and mobile-safe rows', () => {
  const titleBlock = magnetSource.match(/\.section-title\s*\{[^}]*\}/)?.[0] || ''
  const itemBlock = magnetSource.match(/\.magnet-item\s*\{[^}]*\}/)?.[0] || ''
  const itemFocusBlock = magnetSource.match(/\.magnet-item:focus-within\s*\{[^}]*\}/)?.[0] || ''
  const actionBlock = magnetSource.match(/\.btn-copy,\s*\n\.btn-download\s*\{[\s\S]*?\n\}/)?.[0] || ''
  const copyFocusBlock = magnetSource.match(/\.btn-copy:focus-visible\s*\{[^}]*\}/)?.[0] || ''
  const downloadBlock = cssBlockWith(magnetSource, '.btn-download', '--glass-active-material')
  const downloadFocusBlock = magnetSource.match(/\.btn-download:focus-visible\s*\{[^}]*\}/)?.[0] || ''
  const skeletonBlock = magnetSource.match(/\.skeleton\s*\{[^}]*\}/)?.[0] || ''
  const mediaBlock = magnetSource.match(/@media \(max-width:\s*768px\)\s*\{[\s\S]*\n\}/)?.[0] || ''

  assert.match(titleBlock, /color:\s*var\(--modal-text-muted,\s*var\(--text-muted\)\)/)
  assert.match(titleBlock, /letter-spacing:\s*0/)
  assert.doesNotMatch(titleBlock, /text-transform:\s*uppercase/)
  assert.ok(backgroundIncludes(itemBlock, '--material-glass-control'))
  assert.match(itemBlock, /var\(--surface-specular-edge\)/)
  assert.match(itemBlock, /var\(--surface-noise\)/)
  assert.match(itemBlock, /border:\s*1px solid var\(--glass-control-border\)/)
  assert.match(itemBlock, /box-shadow:\s*var\(--glass-control-shadow\)/)
  assert.match(itemBlock, /backdrop-filter:\s*blur\(var\(--glass-blur-control\)\)\s*saturate\(var\(--glass-saturate-control\)\)/)
  assert.ok(backgroundIncludes(itemFocusBlock, '--material-glass-control-hover'))
  assert.match(itemFocusBlock, /border-color:\s*var\(--glass-control-border-hover\)/)
  assert.match(itemFocusBlock, /box-shadow:\s*var\(--glass-control-shadow-hover\),\s*0 0 0 3px rgba\(var\(--accent-rgb\),\s*0\.12\)/)
  assert.match(itemFocusBlock, /transform:\s*translateY\(-1px\)/)
  assert.ok(backgroundIncludes(actionBlock, '--material-glass-control'))
  assert.match(actionBlock, /var\(--surface-specular-edge\)/)
  assert.match(actionBlock, /var\(--surface-noise\)/)
  assert.match(actionBlock, /border:\s*1px solid var\(--glass-control-border\)/)
  assert.match(actionBlock, /box-shadow:\s*var\(--glass-control-shadow\)/)
  assert.ok(backgroundIncludes(copyFocusBlock, '--material-glass-control-hover'))
  assert.match(copyFocusBlock, /outline:\s*none/)
  assert.match(copyFocusBlock, /box-shadow:\s*var\(--glass-control-shadow-hover\),\s*0 0 0 3px rgba\(var\(--accent-rgb\),\s*0\.12\)/)
  assert.ok(backgroundIncludes(downloadBlock, '--glass-active-material'))
  assert.match(downloadBlock, /var\(--surface-specular-edge-strong\)/)
  assert.match(downloadBlock, /var\(--surface-noise\)/)
  assert.match(downloadBlock, /border-color:\s*var\(--glass-active-border\)/)
  assert.ok(backgroundIncludes(downloadFocusBlock, '--glass-active-material'))
  assert.match(downloadFocusBlock, /outline:\s*none/)
  assert.match(downloadFocusBlock, /border-color:\s*var\(--glass-active-border\)/)
  assert.match(downloadFocusBlock, /box-shadow:\s*var\(--glass-active-shadow\),\s*0 0 0 3px rgba\(var\(--accent-rgb\),\s*0\.14\)/)
  assert.match(skeletonBlock, /cursor:\s*default/)
  assert.match(skeletonBlock, /pointer-events:\s*none/)
  assert.match(mediaBlock, /\.magnet-item\s*\{[\s\S]*flex-direction:\s*column/)
  assert.match(mediaBlock, /\.magnet-actions\s*\{[\s\S]*grid-template-columns:\s*repeat\(2,\s*minmax\(0,\s*1fr\)\)/)
  assert.doesNotMatch(magnetSource, /var\(--active-border\)/)
  assert.doesNotMatch(magnetSource, /\.btn-download\s*\{[^}]*background:\s*rgba\(255,\s*255,\s*255,\s*0\.9\)/)
})

test('video magnet badges use semantic layered glass tokens', () => {
  const baseBadge = cssBlocks(magnetSource, '.magnet-badge')[0] || ''
  const hdBadge = cssBlocks(magnetSource, '.magnet-badge.hd')[0] || ''
  const subtitleBadge = cssBlocks(magnetSource, '.magnet-badge.sub')[0] || ''

  assertLayeredBackground(baseBadge, '--badge-info-bg', 'video magnet badge')
  assert.match(baseBadge, /color:\s*var\(--badge-info-text\)/)
  assert.match(baseBadge, /border:\s*1px solid var\(--badge-info-border\)/)

  assertLayeredBackground(hdBadge, '--badge-success-bg', 'video magnet HD badge')
  assert.match(hdBadge, /color:\s*var\(--badge-success-text\)/)
  assert.match(hdBadge, /border-color:\s*var\(--badge-success-border\)/)

  assertLayeredBackground(subtitleBadge, '--badge-warning-bg', 'video magnet subtitle badge')
  assert.match(subtitleBadge, /color:\s*var\(--badge-warning-text\)/)
  assert.match(subtitleBadge, /border-color:\s*var\(--badge-warning-border\)/)
})

test('video detail sections layer glass with specular and noise surfaces', () => {
  const singleLayerGlass = /^background:\s*var\(--(?:material-glass-control|material-glass-control-hover|glass-active-material)\);$/gm

  assert.deepEqual([...gallerySource.matchAll(singleLayerGlass)].map(match => match[0]), [], 'gallery controls should not use single-layer glass backgrounds')
  assert.deepEqual([...magnetSource.matchAll(singleLayerGlass)].map(match => match[0]), [], 'magnet controls should not use single-layer glass backgrounds')

  for (const [source, selector, token] of [
    [gallerySource, '.gallery-item', '--material-glass-control'],
    [gallerySource, '.gallery-item:hover', '--material-glass-control-hover'],
    [gallerySource, '.gallery-item:focus-visible', '--material-glass-control-hover'],
    [magnetSource, '.magnet-item', '--material-glass-control'],
    [magnetSource, '.magnet-item:hover', '--material-glass-control-hover'],
    [magnetSource, '.magnet-item:focus-within', '--material-glass-control-hover'],
    [magnetSource, '.btn-copy,\n.btn-download', '--material-glass-control'],
    [magnetSource, '.btn-copy:hover,\n.btn-download:hover', '--material-glass-control-hover'],
    [magnetSource, '.btn-copy:focus-visible', '--material-glass-control-hover'],
    [magnetSource, '.btn-download', '--glass-active-material'],
    [magnetSource, '.btn-download:hover', '--glass-active-material'],
    [magnetSource, '.btn-download:focus-visible', '--glass-active-material'],
    [magnetSource, '.no-magnets', '--material-glass-control'],
  ]) {
    const block = cssBlockWith(source, selector, token)

    assert.ok(backgroundIncludes(block, token), `${selector} should include ${token}`)
    assert.match(block, /var\(--surface-specular-edge/, `${selector} should include a specular edge layer`)
    assert.match(block, /var\(--surface-noise\)/, `${selector} should include the shared noise layer`)
  }
})
