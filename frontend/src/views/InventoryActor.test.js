import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

const source = readFileSync(new URL('./InventoryActor.vue', import.meta.url), 'utf8')

function cssBlocks(content, selector) {
  const blocks = [...content.matchAll(/([^{}]+)\{([^{}]*)\}/g)]
    .filter(([, selectors]) => selectors
      .replace(/\/\*[\s\S]*?\*\//g, '')
      .split(',')
      .map(part => part.trim())
      .includes(selector))
    .map(([, , block]) => block)
  assert.ok(blocks.length, `${selector} block should exist`)
  return blocks
}

function cssBlock(content, selector) {
  return cssBlocks(content, selector).join('\n')
}

test('inventory actor workspace uses shared Apple glass controls', () => {
  const backButton = cssBlock(source, '.back-btn')
  const mappingBanner = cssBlock(source, '.mapping-banner')
  const mappingBannerUnmapped = cssBlock(source, '.mapping-banner.unmapped')
  const mappingLink = cssBlock(source, '.mapping-link')
  const tabBar = cssBlock(source, '.tab-bar')
  const tabButton = cssBlock(source, '.tab-btn')
  const tabHover = cssBlock(source, '.tab-btn:hover')
  const tabActive = cssBlock(source, '.tab-btn.active')
  const yearTitle = cssBlock(source, '.year-title')
  const videoCard = cssBlock(source, '.video-card')
  const videoCardHover = cssBlock(source, '.video-card:hover')
  const videoCover = cssBlock(source, '.video-cover')
  const candidateButton = cssBlock(source, '.candidate-btn')
  const candidateButtonHover = cssBlock(source, '.candidate-btn:hover')
  const emptyState = cssBlock(source, '.loading')

  for (const block of [backButton, mappingLink, tabButton, videoCard, candidateButton]) {
    assert.match(block, /border:\s*1px solid var\(--glass-control-border\)/)
    assert.match(block, /background:\s*var\(--material-glass-control\)/)
    assert.match(block, /box-shadow:\s*var\(--glass-control-shadow\)/)
    assert.match(block, /backdrop-filter:\s*blur\(var\(--glass-blur-control\)\)\s*saturate\(var\(--glass-saturate-control\)\)/)
    assert.doesNotMatch(block, /background:\s*(?:none|transparent)/)
    assert.doesNotMatch(block, /border:\s*(?:0|none|1px solid transparent)/)
  }

  assert.match(tabBar, /border:\s*1px solid var\(--glass-control-border\)/)
  assert.match(tabBar, /background:\s*var\(--material-glass-sheet\)/)
  assert.match(tabBar, /box-shadow:\s*var\(--glass-inner-shadow\)/)

  for (const block of [tabHover, videoCardHover, candidateButtonHover]) {
    assert.match(block, /background:\s*var\(--material-glass-control-hover\)/)
    assert.match(block, /border-color:\s*var\(--glass-control-border-hover\)/)
    assert.match(block, /box-shadow:\s*var\(--glass-control-shadow-hover\)/)
  }

  assert.match(tabActive, /background:\s*var\(--glass-active-material\)/)
  assert.match(tabActive, /border-color:\s*var\(--glass-active-border\)/)
  assert.match(tabActive, /box-shadow:\s*var\(--glass-active-shadow\)/)

  assert.match(mappingBanner, /border:\s*1px solid var\(--badge-success-border\)/)
  assert.match(mappingBanner, /background:\s*var\(--badge-success-bg\)/)
  assert.match(mappingBanner, /color:\s*var\(--badge-success-text\)/)
  assert.match(mappingBannerUnmapped, /border-color:\s*var\(--badge-warning-border\)/)
  assert.match(mappingBannerUnmapped, /background:\s*var\(--badge-warning-bg\)/)
  assert.match(mappingBannerUnmapped, /color:\s*var\(--badge-warning-text\)/)

  assert.match(emptyState, /border:\s*1px solid var\(--glass-control-border\)/)
  assert.match(emptyState, /background:\s*var\(--material-glass-subtle\)/)
  assert.match(yearTitle, /border-bottom:\s*1px solid var\(--glass-edge\)/)
  assert.doesNotMatch(yearTitle, /var\(--border\)/)
  assert.match(videoCover, /background:\s*var\(--material-glass-subtle\)/)
  assert.match(videoCover, /box-shadow:\s*var\(--glass-inner-shadow\)/)

  for (const block of [
    backButton,
    mappingBanner,
    mappingBannerUnmapped,
    mappingLink,
    tabBar,
    tabButton,
    tabActive,
    videoCard,
    videoCover,
    candidateButton,
    emptyState
  ]) {
    assert.doesNotMatch(block, /#fff|#ffffff|rgba\(255,\s*255,\s*255|rgba\(255,255,255/i)
  }
})
