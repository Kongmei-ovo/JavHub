import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

const source = readFileSync(new URL('./Inventory.vue', import.meta.url), 'utf8')

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

  for (const block of [searchBox, searchClear, inlineLink, pageButton, jumpInput, jumpButton, jobItem, closeButton]) {
    assert.match(block, /background:\s*var\(--material-glass-control\)/)
    assert.match(block, /border:\s*1px solid var\(--glass-control-border\)/)
    assert.match(block, /box-shadow:\s*var\(--glass-control-shadow\)/)
  }

  assert.match(searchBox, /backdrop-filter:\s*blur\(var\(--glass-blur-control\)\)\s*saturate\(var\(--glass-saturate-control\)\)/)
  assert.match(searchFocus, /border-color:\s*var\(--glass-control-border-hover\)/)
  assert.match(searchFocus, /background:\s*var\(--material-glass-control-hover\)/)
  assert.match(searchFocus, /box-shadow:\s*var\(--glass-active-shadow\)/)

  for (const block of [pageButtonHover, jumpButtonHover]) {
    assert.match(block, /background:\s*var\(--material-glass-control-hover\)/)
    assert.match(block, /border-color:\s*var\(--glass-control-border-hover\)/)
    assert.match(block, /box-shadow:\s*var\(--glass-control-shadow-hover\)/)
  }

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

  assert.match(actorCard, /background:\s*var\(--material-glass-control\)/)
  assert.match(actorCard, /border:\s*1px solid var\(--glass-control-border\)/)
  assert.match(actorCard, /box-shadow:\s*var\(--glass-control-shadow\)/)
  assert.match(actorCard, /backdrop-filter:\s*blur\(var\(--glass-blur-control\)\)\s*saturate\(var\(--glass-saturate-control\)\)/)
  assert.match(actorCardHover, /background:\s*var\(--material-glass-control-hover\)/)
  assert.match(actorCardHover, /border-color:\s*var\(--glass-control-border-hover\)/)
  assert.match(actorCardHover, /box-shadow:\s*var\(--glass-control-shadow-hover\)/)

  assert.match(actorCover, /background:\s*var\(--material-glass-subtle\)/)
  assert.match(actorCover, /border-bottom:\s*1px solid var\(--glass-control-border\)/)

  for (const block of [skeletonCover, skeletonLine]) {
    assert.match(block, /background:\s*var\(--material-glass-subtle\)/)
    assert.match(block, /border:\s*1px solid var\(--glass-control-border\)/)
    assert.doesNotMatch(block, /var\(--bg-card-hover\)|var\(--surface-card-hover\)|rgba\(255,\s*255,\s*255/)
  }

  for (const block of [actorCard, actorCardHover, actorCover]) {
    assert.doesNotMatch(block, /var\(--bg-card\)|var\(--bg-secondary\)|var\(--shadow-card\)/)
  }
})
