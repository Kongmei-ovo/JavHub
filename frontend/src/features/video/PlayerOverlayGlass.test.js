import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

const overlaySources = [
  ['VideoPlayerOverlay', readFileSync(new URL('./VideoPlayerOverlay.vue', import.meta.url), 'utf8')],
  ['HlsPlayerOverlay', readFileSync(new URL('./HlsPlayerOverlay.vue', import.meta.url), 'utf8')],
]

function cssBlock(source, selector) {
  const escaped = selector.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  const match = source.match(new RegExp(`${escaped}\\s*\\{([^}]*)\\}`))
  assert.ok(match, `${selector} should exist`)
  return match[1]
}

function backgroundIncludes(block, token) {
  const match = block.match(/background:\s*([^;]+);/)
  return Boolean(match && match[1].includes(token))
}

function customPropertyIncludes(block, property, token) {
  const escaped = property.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  const match = block.match(new RegExp(`${escaped}:\\s*([^;]+);`))
  return Boolean(match && match[1].includes(token))
}

for (const [name, source] of overlaySources) {
  test(`${name} uses shared Apple glass player chrome`, () => {
    const overlayBlock = cssBlock(source, '.vp-overlay')
    const closeBlock = cssBlock(source, '.vp-close')
    const closeHoverBlock = cssBlock(source, '.vp-close:hover')
    const closeFocusBlock = cssBlock(source, '.vp-close:focus-visible')
    const closeActiveBlock = cssBlock(source, '.vp-close:active')
    const playerBlock = cssBlock(source, '.vp-player-wrap')
    const infoBlock = cssBlock(source, '.vp-info')
    const titleBlock = cssBlock(source, '.vp-title')
    const speedBlock = cssBlock(source, '.vp-speed-btn')
    const speedHoverBlock = cssBlock(source, '.vp-speed-btn:hover')
    const speedFocusBlock = cssBlock(source, '.vp-speed-btn:focus-visible')
    const speedActiveBlock = cssBlock(source, '.vp-speed-btn:active')
    const activeBlock = cssBlock(source, '.vp-speed-btn.active')

    assert.ok(customPropertyIncludes(overlayBlock, '--vp-control-bg', '--material-glass-control'))
    assert.match(overlayBlock, /--vp-control-bg:[^;]*var\(--surface-specular-edge\)[^;]*var\(--surface-noise\)[^;]*var\(--material-glass-control\)/)
    assert.ok(customPropertyIncludes(overlayBlock, '--vp-control-bg-hover', '--material-glass-control-hover'))
    assert.match(overlayBlock, /--vp-control-bg-hover:[^;]*var\(--surface-specular-edge-strong\)[^;]*var\(--surface-noise\)[^;]*var\(--material-glass-control-hover\)/)
    assert.match(overlayBlock, /--vp-control-border:\s*var\(--glass-control-border\)/)
    assert.match(overlayBlock, /--vp-control-shadow:\s*var\(--glass-control-shadow\)/)
    assert.match(overlayBlock, /--vp-sheet-bg:\s*var\(--material-glass-sheet\)/)
    assert.match(overlayBlock, /--vp-player-blackout:\s*var\(--media-blackout\)/)
    assert.match(overlayBlock, /--vp-player-bg:\s*var\(--vp-player-blackout\)/)
    assert.match(overlayBlock, /background:\s*var\(--surface-scrim,\s*var\(--scrim\)\)/)
    assert.match(overlayBlock, /backdrop-filter:\s*blur\(var\(--glass-blur-sheet\)\)\s*saturate\(var\(--glass-saturate-surface\)\)/)
    assert.doesNotMatch(overlayBlock, /rgba\(0,\s*0,\s*0,\s*0\.7\)|blur\(32px\)|saturate\(180%\)/)
    assert.doesNotMatch(overlayBlock, /--vp-control-bg:\s*var\(--material-glass-control\);/)
    assert.doesNotMatch(overlayBlock, /--vp-control-bg-hover:\s*var\(--material-glass-control-hover\);/)
    assert.doesNotMatch(source, /--vp-player-bg:\s*#000|#000000/)

    for (const block of [closeBlock, infoBlock, speedBlock]) {
      assert.match(block, /background:\s*var\(--vp-control-bg\)/)
      assert.match(block, /border:\s*var\(--stroke-pro\) solid var\(--vp-control-border\)|border:\s*1px solid var\(--vp-control-border\)/)
      assert.match(block, /box-shadow:\s*var\(--vp-control-shadow\)/)
      assert.match(block, /backdrop-filter:\s*blur\(var\(--glass-blur-control\)\)\s*saturate\(var\(--glass-saturate-control\)\)/)
      assert.doesNotMatch(block, /rgba\(255,\s*255,\s*255,\s*0\.(?:07|08|1|12|15|2)\)|transition:\s*var\(--transition-pro\)/)
    }

    for (const block of [closeHoverBlock, speedHoverBlock]) {
      assert.match(block, /background:\s*var\(--vp-control-bg-hover\)/)
      assert.match(block, /border-color:\s*var\(--vp-control-border-hover\)/)
      assert.match(block, /box-shadow:\s*var\(--vp-control-shadow-hover\)/)
    }

    for (const block of [closeFocusBlock, speedFocusBlock]) {
      assert.match(block, /outline:\s*none/)
      assert.match(block, /box-shadow:\s*var\(--vp-control-shadow-hover\),\s*var\(--focus-ring-wide\)/)
    }

    assert.match(closeActiveBlock, /transform:\s*rotate\(90deg\)\s*scale\(0\.96\)/)
    assert.match(speedActiveBlock, /transform:\s*translateY\(0\)\s*scale\(0\.97\)/)

    assert.match(playerBlock, /background:\s*var\(--vp-player-bg\)/)
    assert.match(playerBlock, /border:\s*var\(--stroke-pro\) solid var\(--vp-sheet-border\)/)
    assert.match(playerBlock, /box-shadow:\s*var\(--shadow-sheet\)/)
    assert.doesNotMatch(playerBlock, /0 40px 120px rgba\(0,\s*0,\s*0,\s*0\.8\)|rgba\(255,\s*255,\s*255,\s*0\.1\)/)

    assert.match(titleBlock, /color:\s*var\(--text-secondary\)/)
    assert.match(titleBlock, /letter-spacing:\s*0/)
    assert.doesNotMatch(titleBlock, /text-transform:\s*uppercase/)

    assert.ok(backgroundIncludes(activeBlock, '--glass-active-material'))
    assert.match(activeBlock, /var\(--surface-specular-edge-strong\)/)
    assert.match(activeBlock, /var\(--surface-noise\)/)
    assert.match(activeBlock, /border-color:\s*var\(--glass-active-border\)/)
    assert.match(activeBlock, /box-shadow:\s*var\(--glass-active-shadow\)/)
    assert.doesNotMatch(source, /^\.vp-speed-btn\.active\s*\{\s*background:\s*var\(--glass-active-material\);/m)
  })
}
