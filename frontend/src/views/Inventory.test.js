import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

const vueSource = readFileSync(new URL('./Inventory.vue', import.meta.url), 'utf8')
const externalStyle = readFileSync(new URL('../features/inventory/inventory.css', import.meta.url), 'utf8')
const source = `${vueSource}\n${externalStyle}`

function cssBlocks(content, selector) {
  const contentWithoutComments = content.replace(/\/\*[\s\S]*?\*\//g, '')
  const blocks = [...contentWithoutComments.matchAll(/([^{}]+)\{([^{}]*)\}/g)]
    .filter(([, selectors]) => selectors
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

function assertSemanticBadgeGlass(block, token, borderToken, textToken, name) {
  assertLayeredBackground(block, token, name)
  assert.match(block, new RegExp(`border:\\s*1px solid var\\(${borderToken}\\)`), `${name} should use semantic border`)
  assert.match(block, new RegExp(`color:\\s*var\\(${textToken}\\)`), `${name} should use semantic text`)
  assert.match(block, /box-shadow:\s*var\(--glass-control-shadow\)/, `${name} should use shared glass shadow`)
  assert.match(block, /backdrop-filter:\s*blur\(var\(--glass-blur-control\)\)\s*saturate\(var\(--glass-saturate-control\)\)/, `${name} should use shared control blur`)
}

test('inventory page keeps large scoped styles in a feature stylesheet', () => {
  assert.match(vueSource, /<style scoped src="\.\.\/features\/inventory\/inventory\.css"><\/style>/)
  assert.ok(vueSource.split('\n').length < 520, 'Inventory.vue should stay below 520 lines')
  assert.ok(externalStyle.split('\n').length > 450, 'external stylesheet should contain the moved inventory styles')
})

test('inventory controls use shared Apple glass materials', () => {
  assert.match(source, /class="progress-ring-bg"[\s\S]*stroke="var\(--glass-control-border\)"/)
  assert.match(source, /class="progress-ring-fill"[\s\S]*stroke="var\(--glass-active-border\)"/)
  assert.doesNotMatch(source, /stroke="var\(--border\)"/)
  assert.doesNotMatch(source, /stroke="var\(--accent\)"/)

  const searchBox = cssBlock(source, '.search-box')
  const searchFocus = cssBlock(source, '.search-box:focus-within')
  const searchClear = cssBlock(source, '.search-clear')
  const inlineLink = cssBlock(source, '.inline-link')
  const pageButton = cssBlock(source, '.page-btn')
  const pageButtonHover = cssBlock(source, '.page-btn:hover:not(:disabled)')
  const jumpInput = cssBlock(source, '.jump-input')
  const jumpButton = cssBlock(source, '.jump-btn')
  const jumpButtonHover = cssBlock(source, '.jump-btn:hover')
  const jobItem = cssBlock(source, '.job-item')
  const dialogOverlay = cssBlock(source, '.dialog-overlay')
  const jobsDialog = cssBlock(source, '.jobs-dialog')
  const dialogHeader = cssBlock(source, '.dialog-header')
  const closeButton = cssBlock(source, '.close-btn')

  const controlBlocks = [searchBox, searchClear, inlineLink, pageButton, jumpInput, jumpButton, jobItem, closeButton]
  for (const block of controlBlocks) {
    assertLayeredBackground(block, '--material-glass-control', 'inventory control')
    assert.match(block, /border:\s*1px solid var\(--glass-control-border\)/)
    assert.match(block, /box-shadow:\s*var\(--glass-control-shadow\)/)
  }
  assert.doesNotMatch(controlBlocks.join('\n'), /^.*background:\s*var\(--material-glass-control\);.*$/gm)

  assert.match(searchBox, /backdrop-filter:\s*blur\(var\(--glass-blur-control\)\)\s*saturate\(var\(--glass-saturate-control\)\)/)
  assert.match(searchFocus, /border-color:\s*var\(--glass-control-border-hover\)/)
  assertLayeredBackground(searchFocus, '--material-glass-control-hover', 'inventory focused search')
  assert.match(searchFocus, /box-shadow:\s*var\(--glass-active-shadow\)/)

  for (const block of [pageButtonHover, jumpButtonHover]) {
    assertLayeredBackground(block, '--material-glass-control-hover', 'inventory hovered control')
    assert.match(block, /border-color:\s*var\(--glass-control-border-hover\)/)
    assert.match(block, /box-shadow:\s*var\(--glass-control-shadow-hover\)/)
  }
  assert.doesNotMatch([searchFocus, pageButtonHover, jumpButtonHover].join('\n'), /^.*background:\s*var\(--material-glass-control-hover\);.*$/gm)

  assertLayeredBackground(jobsDialog, '--material-glass-sheet', 'inventory jobs dialog')
  assert.match(jobsDialog, /border:\s*1px solid var\(--glass-edge\)/)
  assert.match(jobsDialog, /box-shadow:\s*var\(--shadow-sheet\),\s*var\(--glass-surface-shadow\)/)
  assert.match(jobsDialog, /backdrop-filter:\s*blur\(var\(--glass-blur-sheet\)\)\s*saturate\(var\(--glass-saturate-surface\)\)/)
  assert.match(dialogOverlay, /background:\s*var\(--surface-scrim\)/)
  assert.match(dialogOverlay, /z-index:\s*var\(--z-modal\)/)
  assert.match(dialogOverlay, /backdrop-filter:\s*blur\(var\(--glass-blur-control\)\)\s*saturate\(var\(--glass-saturate-control\)\)/)
  assert.doesNotMatch(dialogOverlay, /rgba\(0,\s*0,\s*0|z-index:\s*\d+/)
  assert.match(dialogHeader, /border-bottom:\s*1px solid var\(--glass-edge\)/)
  assert.doesNotMatch(dialogHeader, /var\(--border\)/)

  for (const block of [searchClear, inlineLink, closeButton]) {
    assert.doesNotMatch(block, /background:\s*(?:transparent|none)/)
    assert.doesNotMatch(block, /border:\s*(?:0|none|1px solid transparent)/)
  }
})

test('inventory actor cards and skeletons use shared Apple glass surfaces', () => {
  const actorCard = cssBlock(source, '.actor-card')
  const actorCardHover = cssBlock(source, '.actor-card:hover')
  const actorCover = cssBlock(source, '.actor-cover')
  const skeletonCover = cssBlock(source, '.skeleton-cover')
  const skeletonLine = cssBlock(source, '.skeleton-line')

  assertLayeredBackground(actorCard, '--material-glass-control', 'inventory actor card')
  assert.match(actorCard, /border:\s*1px solid var\(--glass-control-border\)/)
  assert.match(actorCard, /box-shadow:\s*var\(--glass-control-shadow\)/)
  assert.match(actorCard, /backdrop-filter:\s*blur\(var\(--glass-blur-control\)\)\s*saturate\(var\(--glass-saturate-control\)\)/)
  assertLayeredBackground(actorCardHover, '--material-glass-control-hover', 'inventory hovered actor card')
  assert.match(actorCardHover, /border-color:\s*var\(--glass-control-border-hover\)/)
  assert.match(actorCardHover, /box-shadow:\s*var\(--glass-control-shadow-hover\)/)

  assertLayeredBackground(actorCover, '--material-glass-subtle', 'inventory actor cover')
  assert.match(actorCover, /border-bottom:\s*1px solid var\(--glass-control-border\)/)

  for (const block of [skeletonCover, skeletonLine]) {
    assertLayeredBackground(block, '--material-glass-subtle', 'inventory skeleton')
    assert.match(block, /border:\s*1px solid var\(--glass-control-border\)/)
    assert.doesNotMatch(block, /var\(--bg-card-hover\)|var\(--surface-card-hover\)|rgba\(255,\s*255,\s*255/)
  }
  assert.doesNotMatch([actorCard, actorCardHover, actorCover, skeletonCover, skeletonLine].join('\n'), /^.*background:\s*var\(--(?:material-glass-control|material-glass-control-hover|material-glass-subtle)\);.*$/gm)

  for (const block of [actorCard, actorCardHover, actorCover]) {
    assert.doesNotMatch(block, /var\(--bg-card\)|var\(--bg-secondary\)|var\(--shadow-card\)/)
  }
})

test('inventory semantic status surfaces use layered badge glass', () => {
  const snapshotInfo = cssBlock(source, '.snapshot-info')
  const snapshotWarn = cssBlock(source, '.snapshot-warn')
  const missingBadge = cssBlock(source, '.missing-badge')

  assertSemanticBadgeGlass(snapshotInfo, '--badge-success-bg', '--badge-success-border', '--badge-success-text', 'inventory snapshot success')
  assertSemanticBadgeGlass(snapshotWarn, '--badge-warning-bg', '--badge-warning-border', '--badge-warning-text', 'inventory snapshot warning')
  assertSemanticBadgeGlass(missingBadge, '--badge-error-bg', '--badge-error-border', '--badge-error-text', 'inventory missing count badge')
  assert.doesNotMatch(`${snapshotInfo}\n${snapshotWarn}\n${missingBadge}`, /#fff|#ffffff|rgba\(255,\s*255,\s*255/i)
})

test('inventory interactive controls expose Apple glass keyboard focus states', () => {
  assert.match(vueSource, /class="actor-card"[\s\S]*role="button"/)
  assert.match(vueSource, /class="actor-card"[\s\S]*tabindex="0"/)
  assert.match(vueSource, /class="actor-card"[\s\S]*@keydown\.enter\.prevent="openActor\(actor\)"/)
  assert.match(vueSource, /class="actor-card"[\s\S]*@keydown\.space\.prevent="openActor\(actor\)"/)

  const actorFocus = cssBlock(source, '.actor-card:focus-visible')
  const pageButtonFocus = cssBlock(source, '.page-btn:focus-visible:not(:disabled)')
  const jumpButtonFocus = cssBlock(source, '.jump-btn:focus-visible')
  const searchClearFocus = cssBlock(source, '.search-clear:focus-visible')
  const inlineLinkFocus = cssBlock(source, '.inline-link:focus-visible')
  const closeButtonFocus = cssBlock(source, '.close-btn:focus-visible')

  for (const [block, label] of [
    [actorFocus, 'inventory actor card focus'],
    [pageButtonFocus, 'inventory page button focus'],
    [jumpButtonFocus, 'inventory jump button focus'],
    [searchClearFocus, 'inventory search clear focus'],
    [inlineLinkFocus, 'inventory inline link focus'],
    [closeButtonFocus, 'inventory close button focus'],
  ]) {
    assert.match(block, /outline:\s*none/, `${label} should replace the default outline`)
    assert.match(block, /border-color:\s*var\(--glass-control-border-hover\)/, `${label} should use hover border`)
    assertLayeredBackground(block, '--material-glass-control-hover', label)
    assert.match(block, /box-shadow:\s*var\(--glass-control-shadow-hover\),\s*0 0 0 3px rgba\(var\(--accent-rgb\),\s*0\.12\)/, `${label} should expose a subtle focus ring`)
  }

  assert.match(actorFocus, /transform:\s*translateY\(-4px\)/)
  assert.match(pageButtonFocus, /transform:\s*translateY\(-1px\)/)
  assert.match(jumpButtonFocus, /transform:\s*translateY\(-1px\)/)
  assert.match(searchClearFocus, /transform:\s*translateY\(-1px\)/)
  assert.match(closeButtonFocus, /transform:\s*rotate\(90deg\)/)
})
