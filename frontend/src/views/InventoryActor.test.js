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

function backgroundIncludes(block, token) {
  const match = block.match(/background:\s*([^;]+);/)
  return Boolean(match && match[1].includes(token))
}

function assertLayeredBackground(block, token, name) {
  assert.ok(backgroundIncludes(block, token), `${name} should include ${token}`)
  assert.match(block, /var\(--surface-specular-edge/, `${name} should include a specular edge layer`)
  assert.match(block, /var\(--surface-noise\)/, `${name} should include the shared noise layer`)
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
    assert.ok(backgroundIncludes(block, '--material-glass-control'))
    assert.match(block, /var\(--surface-specular-edge\)/)
    assert.match(block, /var\(--surface-noise\)/)
    assert.match(block, /box-shadow:\s*var\(--glass-control-shadow\)/)
    assert.match(block, /backdrop-filter:\s*blur\(var\(--glass-blur-control\)\)\s*saturate\(var\(--glass-saturate-control\)\)/)
    assert.doesNotMatch(block, /background:\s*(?:none|transparent)/)
    assert.doesNotMatch(block, /border:\s*(?:0|none|1px solid transparent)/)
  }

  assert.match(tabBar, /border:\s*1px solid var\(--glass-control-border\)/)
  assert.ok(backgroundIncludes(tabBar, '--material-glass-sheet'))
  assert.match(tabBar, /var\(--surface-specular-edge-strong\)/)
  assert.match(tabBar, /var\(--surface-noise\)/)
  assert.match(tabBar, /box-shadow:\s*var\(--glass-inner-shadow\)/)

  for (const block of [tabHover, videoCardHover, candidateButtonHover]) {
    assert.ok(backgroundIncludes(block, '--material-glass-control-hover'))
    assert.match(block, /var\(--surface-specular-edge-strong\)/)
    assert.match(block, /var\(--surface-noise\)/)
    assert.match(block, /border-color:\s*var\(--glass-control-border-hover\)/)
    assert.match(block, /box-shadow:\s*var\(--glass-control-shadow-hover\)/)
  }

  assert.ok(backgroundIncludes(tabActive, '--glass-active-material'))
  assert.match(tabActive, /var\(--surface-specular-edge-strong\)/)
  assert.match(tabActive, /var\(--surface-noise\)/)
  assert.match(tabActive, /border-color:\s*var\(--glass-active-border\)/)
  assert.match(tabActive, /box-shadow:\s*var\(--glass-active-shadow\)/)

  assert.match(mappingBanner, /border:\s*1px solid var\(--badge-success-border\)/)
  assertLayeredBackground(mappingBanner, '--badge-success-bg', 'inventory actor mapped banner')
  assert.match(mappingBanner, /color:\s*var\(--badge-success-text\)/)
  assert.match(mappingBannerUnmapped, /border-color:\s*var\(--badge-warning-border\)/)
  assertLayeredBackground(mappingBannerUnmapped, '--badge-warning-bg', 'inventory actor unmapped banner')
  assert.match(mappingBannerUnmapped, /color:\s*var\(--badge-warning-text\)/)

  assert.match(emptyState, /border:\s*1px solid var\(--glass-control-border\)/)
  assertLayeredBackground(emptyState, '--material-glass-subtle', 'inventory actor empty state')
  assert.match(yearTitle, /border-bottom:\s*1px solid var\(--glass-edge\)/)
  assert.doesNotMatch(yearTitle, /var\(--border\)/)
  assertLayeredBackground(videoCover, '--material-glass-subtle', 'inventory actor video cover')
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

test('inventory actor controls mirror hover glass treatment for keyboard focus', () => {
  assert.match(source, /class="video-card"[\s\S]*role="button"/)
  assert.match(source, /class="video-card"[\s\S]*tabindex="0"/)
  assert.match(source, /class="video-card"[\s\S]*@keydown\.enter\.prevent="openEmbyItem\(video\)"/)
  assert.match(source, /class="video-card"[\s\S]*@keydown\.space\.prevent="openEmbyItem\(video\)"/)

  const backFocus = cssBlock(source, '.back-btn:focus-visible')
  const mappingFocus = cssBlock(source, '.mapping-link:focus-visible')
  const tabFocus = cssBlock(source, '.tab-btn:focus-visible')
  const videoFocus = cssBlock(source, '.video-card:focus-visible')
  const candidateFocus = cssBlock(source, '.candidate-btn:focus-visible')

  for (const [block, label] of [
    [backFocus, 'inventory actor back focus'],
    [mappingFocus, 'inventory actor mapping focus'],
    [tabFocus, 'inventory actor tab focus'],
    [videoFocus, 'inventory actor video card focus'],
    [candidateFocus, 'inventory actor candidate focus'],
  ]) {
    assert.match(block, /outline:\s*none/, `${label} should replace the default outline`)
    assert.match(block, /border-color:\s*var\(--glass-control-border-hover\)/, `${label} should use hover border`)
    assertLayeredBackground(block, '--material-glass-control-hover', label)
    assert.match(block, /box-shadow:\s*var\(--glass-control-shadow-hover\),\s*var\(--focus-ring\)/, `${label} should expose a subtle focus ring`)
  }

  assert.match(backFocus, /transform:\s*translateY\(-1px\)/)
  assert.match(tabFocus, /transform:\s*translateY\(-1px\)/)
  assert.match(videoFocus, /transform:\s*translateY\(-2px\)/)
  assert.match(candidateFocus, /transform:\s*translateY\(-1px\)/)
  assert.match(mappingFocus, /text-decoration-color:\s*var\(--link-underline-hover\)/)
})

test('inventory actor glass backgrounds are layered with specular and noise surfaces', () => {
  const offenders = source
    .split('\n')
    .map(line => line.trim())
    .filter(line => /(?:^|;\s*)background:\s*var\(--(?:material-glass-control|material-glass-control-hover|material-glass-sheet|material-glass-subtle|glass-active-material)\);/.test(line))

  assert.deepEqual(offenders, [], 'inventory actor primary glass surfaces should not use single-layer glass backgrounds')

  for (const [selector, token] of [
    ['.back-btn', '--material-glass-control'],
    ['.back-btn:hover', '--material-glass-control-hover'],
    ['.mapping-link', '--material-glass-control'],
    ['.mapping-link:hover', '--material-glass-control-hover'],
    ['.tab-bar', '--material-glass-sheet'],
    ['.tab-btn', '--material-glass-control'],
    ['.tab-btn:hover', '--material-glass-control-hover'],
    ['.tab-btn.active', '--glass-active-material'],
    ['.video-card', '--material-glass-control'],
    ['.video-card:hover', '--material-glass-control-hover'],
    ['.video-cover', '--material-glass-subtle'],
    ['.candidate-btn', '--material-glass-control'],
    ['.candidate-btn:hover', '--material-glass-control-hover'],
    ['.loading', '--material-glass-subtle'],
  ]) {
    const block = cssBlock(source, selector)
    assertLayeredBackground(block, token, selector)
  }
})
