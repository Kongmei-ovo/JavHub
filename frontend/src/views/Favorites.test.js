import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

const vueSource = readFileSync(new URL('./Favorites.vue', import.meta.url), 'utf8')
const externalStyle = readFileSync(new URL('../features/favorites/favorites.css', import.meta.url), 'utf8')
const source = `${vueSource}\n${externalStyle}`

function cssBlock(selector) {
  const pattern = new RegExp(`${selector.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\s*\\{([\\s\\S]*?)\\n\\}`)
  const match = source.match(pattern)
  assert.ok(match, `${selector} should exist in Favorites.vue`)
  return match[1]
}

function cssGroupedBlock(selector) {
  const pattern = new RegExp(`${selector.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}[\\s\\S]*?\\{([\\s\\S]*?)\\n\\}`)
  const match = source.match(pattern)
  assert.ok(match, `${selector} should exist in Favorites.vue`)
  return match[1]
}

test('favorites page keeps large scoped styles in a feature stylesheet', () => {
  assert.match(vueSource, /<style scoped src="\.\.\/features\/favorites\/favorites\.css"><\/style>/)
  assert.ok(vueSource.split('\n').length < 700, 'Favorites.vue should stay below 700 lines')
  assert.ok(externalStyle.split('\n').length > 550, 'external stylesheet should contain the moved favorites styles')
})

test('favorites curation chrome uses shared Apple glass materials', () => {
  const collectionManager = cssBlock('.collection-manager')
  const miniButton = cssBlock('.btn-mini')
  const miniButtonHover = cssBlock('.btn-mini:hover:not(:disabled)')
  const activeMiniButton = cssBlock('.btn-mini.active')
  const dangerMiniButton = cssBlock('.btn-mini.danger')
  const segmentedControl = cssBlock('.segmented-control')
  const segmentItem = cssBlock('.segment-item')
  const segmentItemHover = cssBlock('.segment-item:hover')
  const activeSegment = cssBlock('.segment-item.active')

  assert.doesNotMatch(source, /var\(--surface-card\)|var\(--surface-control\)|var\(--surface-control-hover\)|var\(--bg-secondary\)|var\(--transition\)/)

  assert.match(collectionManager, /border:\s*1px solid var\(--glass-control-border\)/)
  assert.match(collectionManager, /background:\s*var\(--material-glass-sheet\)/)
  assert.match(collectionManager, /box-shadow:\s*var\(--glass-surface-shadow\)/)
  assert.match(collectionManager, /backdrop-filter:\s*blur\(var\(--glass-blur-surface\)\)\s*saturate\(var\(--glass-saturate-surface\)\)/)

  assert.match(miniButton, /border:\s*1px solid var\(--glass-control-border\)/)
  assert.match(miniButton, /background:\s*var\(--material-glass-control\)/)
  assert.match(miniButton, /box-shadow:\s*var\(--glass-control-shadow\)/)
  assert.match(miniButton, /backdrop-filter:\s*blur\(var\(--glass-blur-control\)\)/)
  assert.match(miniButtonHover, /background:\s*var\(--material-glass-control-hover\)/)
  assert.match(miniButtonHover, /box-shadow:\s*var\(--glass-control-shadow-hover\)/)
  assert.match(activeMiniButton, /background:\s*var\(--glass-active-material\)/)
  assert.match(activeMiniButton, /box-shadow:\s*var\(--glass-active-shadow\)/)
  assert.match(dangerMiniButton, /color:\s*var\(--badge-error-text\)/)
  assert.match(dangerMiniButton, /border-color:\s*var\(--badge-error-border\)/)
  assert.match(dangerMiniButton, /background:\s*var\(--badge-error-bg\)/)
  assert.doesNotMatch(dangerMiniButton, /#ff375f/i)

  assert.match(segmentedControl, /background:\s*var\(--material-glass-control\)/)
  assert.match(segmentedControl, /border:\s*1px solid var\(--glass-control-border\)/)
  assert.match(segmentedControl, /box-shadow:\s*var\(--glass-control-shadow\)/)
  assert.match(segmentedControl, /backdrop-filter:\s*blur\(var\(--glass-blur-control\)\)/)
  assert.match(segmentItem, /border:\s*1px solid var\(--glass-control-border\)/)
  assert.match(segmentItem, /background:\s*var\(--material-glass-control\)/)
  assert.match(segmentItem, /box-shadow:\s*var\(--glass-control-shadow\)/)
  assert.doesNotMatch(segmentItem, /border:\s*1px solid transparent|background:\s*transparent/)
  assert.match(segmentItemHover, /background:\s*var\(--material-glass-control-hover\)/)
  assert.match(segmentItemHover, /border-color:\s*var\(--glass-control-border-hover\)/)
  assert.match(segmentItemHover, /box-shadow:\s*var\(--glass-control-shadow-hover\)/)
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
  const selectCheck = cssBlock('.select-check')
  const selectedCard = cssGroupedBlock('.favorites-grid.is-editing :deep(.apple-video-card),')
  const selectedDot = cssGroupedBlock('.favorite-selectable.selected .select-check span,')
  const entityTypeTag = cssBlock('.entity-type-tag')
  const entityFavButton = cssBlock('.entity-fav-btn')
  const entityFavButtonHover = cssBlock('.entity-fav-btn:hover')
  const emptyIcon = cssBlock('.empty-icon')
  const exploreButton = cssBlock('.btn-explore')
  const skeletonCard = cssBlock('.skeleton-card')
  const skeletonCover = cssBlock('.skeleton-cover')
  const skeletonLine = cssBlock('.skeleton-line')

  assert.match(sectionLabel, /letter-spacing:\s*0/)
  assert.doesNotMatch(sectionLabel, /text-transform:\s*uppercase/)

  assert.match(entityBubble, /background:\s*var\(--material-glass-control\)/)
  assert.match(entityBubble, /border:\s*1px solid var\(--glass-control-border\)/)
  assert.match(entityBubble, /box-shadow:\s*var\(--glass-control-shadow\)/)
  assert.match(entityBubble, /backdrop-filter:\s*blur\(var\(--glass-blur-control\)\)/)
  assert.match(entityBubbleHover, /background:\s*var\(--material-glass-control-hover\)/)
  assert.match(entityBubbleHover, /box-shadow:\s*var\(--glass-control-shadow-hover\)/)
  assert.match(entityBubbleSelected, /background:\s*var\(--glass-active-material\)/)
  assert.doesNotMatch(entityBubble, /var\(--bg-card\)|border:\s*1px solid var\(--border\)/)

  assert.match(selectCheck, /border:\s*1px solid var\(--glass-control-border\)/)
  assert.match(selectCheck, /background:\s*var\(--material-glass-control\)/)
  assert.match(selectCheck, /box-shadow:\s*var\(--glass-control-shadow\)/)
  assert.doesNotMatch(selectCheck, /rgba\(255,255,255/)
  assert.match(selectedCard, /outline:\s*2px solid var\(--glass-active-border\)/)
  assert.doesNotMatch(selectedCard, /rgba\(var\(--accent-rgb\)/)
  assert.match(selectedDot, /border-color:\s*var\(--glass-active-border\)/)
  assert.match(selectedDot, /background:\s*var\(--glass-active-material\)/)
  assert.match(selectedDot, /box-shadow:\s*var\(--glass-active-shadow\)/)
  assert.doesNotMatch(selectedDot, /#fff|rgba\(255,255,255/)

  assert.match(entityTypeTag, /background:\s*var\(--material-glass-subtle\)/)
  assert.match(entityTypeTag, /border:\s*1px solid var\(--glass-control-border\)/)
  assert.match(entityFavButton, /border:\s*1px solid var\(--badge-error-border\)/)
  assert.match(entityFavButton, /background:\s*var\(--badge-error-bg\)/)
  assert.match(entityFavButton, /color:\s*var\(--badge-error-text\)/)
  assert.match(entityFavButton, /box-shadow:\s*var\(--glass-control-shadow\)/)
  assert.doesNotMatch(entityFavButton, /background:\s*none|border:\s*none|#ff375f/i)
  assert.match(entityFavButtonHover, /background:\s*var\(--material-glass-control-hover\)/)
  assert.match(entityFavButtonHover, /border-color:\s*var\(--badge-error-border\)/)
  assert.match(emptyIcon, /background:\s*var\(--material-glass-control\)/)
  assert.match(emptyIcon, /box-shadow:\s*var\(--glass-control-shadow\)/)
  assert.match(exploreButton, /background:\s*var\(--glass-active-material\)/)
  assert.match(exploreButton, /box-shadow:\s*var\(--glass-active-shadow\)/)
  assert.match(skeletonCard, /background:\s*var\(--material-glass-sheet\)/)
  assert.match(skeletonCard, /border:\s*1px solid var\(--glass-control-border\)/)
  assert.match(skeletonCard, /box-shadow:\s*var\(--glass-surface-shadow\)/)
  assert.match(skeletonCover, /background:\s*var\(--material-glass-subtle\)/)
  assert.match(skeletonLine, /background:\s*var\(--material-glass-subtle\)/)
})
