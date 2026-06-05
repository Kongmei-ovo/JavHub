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

function backgroundIncludes(token) {
  return new RegExp(`background:[\\s\\S]*var\\(--${token}\\)`)
}

function singleLayerGlassBackgrounds(css) {
  return css
    .split('\n')
    .map((line, index) => ({ line: index + 1, text: line.trim() }))
    .filter(({ text }) => /^background:\s*var\(--(?:material-glass-control|material-glass-control-hover|material-glass-sheet|material-glass-subtle|glass-active-material)\);$/.test(text))
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
  assert.match(collectionManager, backgroundIncludes('material-glass-sheet'))
  assert.match(collectionManager, /box-shadow:\s*var\(--glass-surface-shadow\)/)
  assert.match(collectionManager, /backdrop-filter:\s*blur\(var\(--glass-blur-surface\)\)\s*saturate\(var\(--glass-saturate-surface\)\)/)

  assert.match(miniButton, /border:\s*1px solid var\(--glass-control-border\)/)
  assert.match(miniButton, backgroundIncludes('material-glass-control'))
  assert.match(miniButton, /box-shadow:\s*var\(--glass-control-shadow\)/)
  assert.match(miniButton, /backdrop-filter:\s*blur\(var\(--glass-blur-control\)\)/)
  assert.match(miniButtonHover, backgroundIncludes('material-glass-control-hover'))
  assert.match(miniButtonHover, /box-shadow:\s*var\(--glass-control-shadow-hover\)/)
  assert.match(activeMiniButton, backgroundIncludes('glass-active-material'))
  assert.match(activeMiniButton, /box-shadow:\s*var\(--glass-active-shadow\)/)
  assert.match(dangerMiniButton, /color:\s*var\(--badge-error-text\)/)
  assert.match(dangerMiniButton, /border-color:\s*var\(--badge-error-border\)/)
  assert.match(dangerMiniButton, backgroundIncludes('badge-error-bg'))
  assert.doesNotMatch(dangerMiniButton, /#ff375f/i)

  assert.match(segmentedControl, backgroundIncludes('material-glass-control'))
  assert.match(segmentedControl, /border:\s*1px solid var\(--glass-control-border\)/)
  assert.match(segmentedControl, /box-shadow:\s*var\(--glass-control-shadow\)/)
  assert.match(segmentedControl, /backdrop-filter:\s*blur\(var\(--glass-blur-control\)\)/)
  assert.match(segmentItem, /border:\s*1px solid var\(--glass-control-border\)/)
  assert.match(segmentItem, backgroundIncludes('material-glass-control'))
  assert.match(segmentItem, /box-shadow:\s*var\(--glass-control-shadow\)/)
  assert.doesNotMatch(segmentItem, /border:\s*1px solid transparent|background:\s*transparent/)
  assert.match(segmentItemHover, backgroundIncludes('material-glass-control-hover'))
  assert.match(segmentItemHover, /border-color:\s*var\(--glass-control-border-hover\)/)
  assert.match(segmentItemHover, /box-shadow:\s*var\(--glass-control-shadow-hover\)/)
  assert.match(activeSegment, backgroundIncludes('glass-active-material'))
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

  assert.match(entityBubble, backgroundIncludes('material-glass-control'))
  assert.match(entityBubble, /border:\s*1px solid var\(--glass-control-border\)/)
  assert.match(entityBubble, /box-shadow:\s*var\(--glass-control-shadow\)/)
  assert.match(entityBubble, /backdrop-filter:\s*blur\(var\(--glass-blur-control\)\)/)
  assert.match(entityBubbleHover, backgroundIncludes('material-glass-control-hover'))
  assert.match(entityBubbleHover, /box-shadow:\s*var\(--glass-control-shadow-hover\)/)
  assert.match(entityBubbleSelected, backgroundIncludes('glass-active-material'))
  assert.doesNotMatch(entityBubble, /var\(--bg-card\)|border:\s*1px solid var\(--border\)/)

  assert.match(selectCheck, /border:\s*1px solid var\(--glass-control-border\)/)
  assert.match(selectCheck, backgroundIncludes('material-glass-control'))
  assert.match(selectCheck, /box-shadow:\s*var\(--glass-control-shadow\)/)
  assert.doesNotMatch(selectCheck, /rgba\(255,255,255/)
  assert.match(selectedCard, /outline:\s*2px solid var\(--glass-active-border\)/)
  assert.doesNotMatch(selectedCard, /rgba\(var\(--accent-rgb\)/)
  assert.match(selectedDot, /border-color:\s*var\(--glass-active-border\)/)
  assert.match(selectedDot, backgroundIncludes('glass-active-material'))
  assert.match(selectedDot, /box-shadow:\s*var\(--glass-active-shadow\)/)
  assert.doesNotMatch(selectedDot, /#fff|rgba\(255,255,255/)

  assert.match(entityTypeTag, backgroundIncludes('material-glass-subtle'))
  assert.match(entityTypeTag, /border:\s*1px solid var\(--glass-control-border\)/)
  assert.match(entityFavButton, /border:\s*1px solid var\(--badge-error-border\)/)
  assert.match(entityFavButton, backgroundIncludes('badge-error-bg'))
  assert.match(entityFavButton, /color:\s*var\(--badge-error-text\)/)
  assert.match(entityFavButton, /box-shadow:\s*var\(--glass-control-shadow\)/)
  assert.doesNotMatch(entityFavButton, /background:\s*none|border:\s*none|#ff375f/i)
  assert.match(entityFavButtonHover, backgroundIncludes('material-glass-control-hover'))
  assert.match(entityFavButtonHover, /border-color:\s*var\(--badge-error-border\)/)
  assert.match(emptyIcon, backgroundIncludes('material-glass-control'))
  assert.match(emptyIcon, /box-shadow:\s*var\(--glass-control-shadow\)/)
  assert.match(exploreButton, backgroundIncludes('glass-active-material'))
  assert.match(exploreButton, /box-shadow:\s*var\(--glass-active-shadow\)/)
  assert.match(skeletonCard, backgroundIncludes('material-glass-sheet'))
  assert.match(skeletonCard, /border:\s*1px solid var\(--glass-control-border\)/)
  assert.match(skeletonCard, /box-shadow:\s*var\(--glass-surface-shadow\)/)
  assert.match(skeletonCover, backgroundIncludes('material-glass-subtle'))
  assert.match(skeletonLine, backgroundIncludes('material-glass-subtle'))
})

test('favorites keyboard focus mirrors hover glass treatment', () => {
  const miniButtonFocus = cssBlock('.btn-mini:focus-visible:not(:disabled)')
  const dangerMiniButtonFocus = cssBlock('.btn-mini.danger:focus-visible:not(:disabled)')
  const segmentFocus = cssBlock('.segment-item:focus-visible')
  const entityBubbleFocus = cssBlock('.entity-bubble:focus-visible')
  const entityFavButtonFocus = cssBlock('.entity-fav-btn:focus-visible')
  const exploreFocus = cssBlock('.btn-explore:focus-visible')

  for (const block of [miniButtonFocus, segmentFocus]) {
    assert.match(block, /outline:\s*none/)
    assert.match(block, backgroundIncludes('material-glass-control-hover'))
    assert.match(block, /border-color:\s*var\(--glass-control-border-hover\)/)
    assert.match(block, /box-shadow:\s*var\(--glass-control-shadow-hover\),\s*0 0 0 3px rgba\(var\(--accent-rgb\),\s*0\.12\)/)
    assert.match(block, /transform:\s*translateY\(-1px\)/)
  }

  assert.match(dangerMiniButtonFocus, /outline:\s*none/)
  assert.match(dangerMiniButtonFocus, backgroundIncludes('badge-error-bg'))
  assert.match(dangerMiniButtonFocus, /border-color:\s*var\(--badge-error-border\)/)
  assert.match(dangerMiniButtonFocus, /box-shadow:\s*var\(--glass-control-shadow-hover\),\s*0 0 0 3px rgba\(var\(--error-rgb\),\s*0\.16\)/)

  assert.match(entityBubbleFocus, /outline:\s*none/)
  assert.match(entityBubbleFocus, backgroundIncludes('material-glass-control-hover'))
  assert.match(entityBubbleFocus, /border-color:\s*var\(--glass-control-border-hover\)/)
  assert.match(entityBubbleFocus, /box-shadow:\s*var\(--glass-control-shadow-hover\),\s*0 0 0 3px rgba\(var\(--accent-rgb\),\s*0\.12\)/)
  assert.match(entityBubbleFocus, /transform:\s*translateY\(-2px\)/)

  assert.match(entityFavButtonFocus, /outline:\s*none/)
  assert.match(entityFavButtonFocus, /opacity:\s*1/)
  assert.match(entityFavButtonFocus, backgroundIncludes('material-glass-control-hover'))
  assert.match(entityFavButtonFocus, /border-color:\s*var\(--badge-error-border\)/)
  assert.match(entityFavButtonFocus, /box-shadow:\s*var\(--glass-control-shadow-hover\),\s*0 0 0 3px rgba\(var\(--error-rgb\),\s*0\.16\)/)
  assert.match(entityFavButtonFocus, /transform:\s*translateY\(-1px\) scale\(1\.05\)/)

  assert.match(exploreFocus, /outline:\s*none/)
  assert.match(exploreFocus, backgroundIncludes('glass-active-material'))
  assert.match(exploreFocus, /border-color:\s*var\(--glass-active-border\)/)
  assert.match(exploreFocus, /box-shadow:\s*var\(--glass-control-shadow-hover\),\s*0 0 0 3px rgba\(var\(--accent-rgb\),\s*0\.14\)/)
  assert.match(exploreFocus, /transform:\s*translateY\(-2px\)/)
})

test('favorites glass backgrounds are layered with specular and noise surfaces', () => {
  assert.deepEqual(singleLayerGlassBackgrounds(externalStyle), [])
})
