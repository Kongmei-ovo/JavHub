import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

const source = readFileSync(new URL('./Favorites.vue', import.meta.url), 'utf8')

function cssBlock(selector) {
  const pattern = new RegExp(`${selector.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\s*\\{([\\s\\S]*?)\\n\\}`)
  const match = source.match(pattern)
  assert.ok(match, `${selector} should exist in Favorites.vue`)
  return match[1]
}

test('favorites curation chrome uses shared Apple glass materials', () => {
  const collectionManager = cssBlock('.collection-manager')
  const miniButton = cssBlock('.btn-mini')
  const miniButtonHover = cssBlock('.btn-mini:hover:not(:disabled)')
  const activeMiniButton = cssBlock('.btn-mini.active')
  const segmentedControl = cssBlock('.segmented-control')
  const activeSegment = cssBlock('.segment-item.active')

  assert.match(collectionManager, /border:\s*1px solid var\(--glass-control-border\)/)
  assert.match(collectionManager, /background:\s*var\(--surface-card\)/)
  assert.match(collectionManager, /box-shadow:\s*var\(--glass-surface-shadow\)/)
  assert.match(collectionManager, /backdrop-filter:\s*blur\(var\(--glass-blur-surface\)\)\s*saturate\(var\(--glass-saturate-surface\)\)/)

  assert.match(miniButton, /border:\s*1px solid var\(--glass-control-border\)/)
  assert.match(miniButton, /background:\s*var\(--surface-control\)/)
  assert.match(miniButton, /box-shadow:\s*var\(--glass-control-shadow\)/)
  assert.match(miniButton, /backdrop-filter:\s*blur\(var\(--glass-blur-control\)\)/)
  assert.match(miniButtonHover, /background:\s*var\(--surface-control-hover\)/)
  assert.match(miniButtonHover, /box-shadow:\s*var\(--glass-control-shadow-hover\)/)
  assert.match(activeMiniButton, /background:\s*var\(--glass-active-material\)/)
  assert.match(activeMiniButton, /box-shadow:\s*var\(--glass-active-shadow\)/)

  assert.match(segmentedControl, /background:\s*var\(--material-glass-control\)/)
  assert.match(segmentedControl, /border:\s*1px solid var\(--glass-control-border\)/)
  assert.match(segmentedControl, /box-shadow:\s*var\(--glass-control-shadow\)/)
  assert.match(segmentedControl, /backdrop-filter:\s*blur\(var\(--glass-blur-control\)\)/)
  assert.match(activeSegment, /background:\s*var\(--glass-active-material\)/)
  assert.match(activeSegment, /box-shadow:\s*var\(--glass-active-shadow\)/)
  assert.doesNotMatch(segmentedControl, /blur\(20px\)|rgba\(255,\s*255,\s*255,\s*0\.05\)/)
  assert.doesNotMatch(activeSegment, /rgba\(0,\s*0,\s*0,\s*0\.3\)|var\(--white-10\)/)
})

test('favorites entity and empty states avoid legacy flat card styling', () => {
  const sectionLabel = cssBlock('.section-label')
  const entityBubble = cssBlock('.entity-bubble')
  const entityBubbleHover = cssBlock('.entity-bubble:hover')
  const entityBubbleSelected = cssBlock('.entity-bubble.selected')
  const entityTypeTag = cssBlock('.entity-type-tag')
  const emptyIcon = cssBlock('.empty-icon')
  const exploreButton = cssBlock('.btn-explore')
  const skeletonCard = cssBlock('.skeleton-card')

  assert.match(sectionLabel, /letter-spacing:\s*0/)
  assert.doesNotMatch(sectionLabel, /text-transform:\s*uppercase/)

  assert.match(entityBubble, /background:\s*var\(--surface-control\)/)
  assert.match(entityBubble, /border:\s*1px solid var\(--glass-control-border\)/)
  assert.match(entityBubble, /box-shadow:\s*var\(--glass-control-shadow\)/)
  assert.match(entityBubble, /backdrop-filter:\s*blur\(var\(--glass-blur-control\)\)/)
  assert.match(entityBubbleHover, /background:\s*var\(--surface-control-hover\)/)
  assert.match(entityBubbleHover, /box-shadow:\s*var\(--glass-control-shadow-hover\)/)
  assert.match(entityBubbleSelected, /background:\s*var\(--glass-active-material\)/)
  assert.doesNotMatch(entityBubble, /var\(--bg-card\)|border:\s*1px solid var\(--border\)/)

  assert.match(entityTypeTag, /background:\s*var\(--material-glass-subtle\)/)
  assert.match(entityTypeTag, /border:\s*1px solid var\(--glass-control-border\)/)
  assert.match(emptyIcon, /background:\s*var\(--material-glass-control\)/)
  assert.match(emptyIcon, /box-shadow:\s*var\(--glass-control-shadow\)/)
  assert.match(exploreButton, /background:\s*var\(--glass-active-material\)/)
  assert.match(exploreButton, /box-shadow:\s*var\(--glass-active-shadow\)/)
  assert.match(skeletonCard, /background:\s*var\(--surface-card\)/)
  assert.match(skeletonCard, /border:\s*1px solid var\(--glass-control-border\)/)
  assert.match(skeletonCard, /box-shadow:\s*var\(--glass-surface-shadow\)/)
})
