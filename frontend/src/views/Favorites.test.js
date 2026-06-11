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

  assert.match(collectionManager, /border:\s*1px solid var\(--hairline\)/)
  assert.match(collectionManager, /background:\s*var\(--card\)/)
  assert.match(collectionManager, /box-shadow:\s*var\(--shadow-card\)/)
  assert.doesNotMatch(collectionManager, /backdrop-filter/)

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
  assert.match(dangerMiniButton, /var\(--surface-specular-edge\)/)
  assert.match(dangerMiniButton, /var\(--surface-noise\)/)
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

  assert.match(entityTypeTag, /background:\s*var\(--card\)/)
  assert.match(entityTypeTag, /border:\s*1px solid var\(--hairline\)/)
  assert.match(entityFavButton, /border:\s*1px solid var\(--badge-error-border\)/)
  assert.match(entityFavButton, backgroundIncludes('badge-error-bg'))
  assert.match(entityFavButton, /var\(--surface-specular-edge\)/)
  assert.match(entityFavButton, /var\(--surface-noise\)/)
  assert.match(entityFavButton, /color:\s*var\(--badge-error-text\)/)
  assert.match(entityFavButton, /box-shadow:\s*var\(--glass-control-shadow\)/)
  assert.doesNotMatch(entityFavButton, /background:\s*none|border:\s*none|#ff375f/i)
  assert.match(entityFavButtonHover, backgroundIncludes('badge-error-bg'))
  assert.match(entityFavButtonHover, /var\(--surface-specular-edge-strong\)/)
  assert.match(entityFavButtonHover, /var\(--surface-noise\)/)
  assert.match(entityFavButtonHover, /border-color:\s*var\(--badge-error-border\)/)
  assert.match(emptyIcon, backgroundIncludes('material-glass-control'))
  assert.match(emptyIcon, /box-shadow:\s*var\(--glass-control-shadow\)/)
  assert.match(exploreButton, backgroundIncludes('glass-active-material'))
  assert.match(exploreButton, /box-shadow:\s*var\(--glass-active-shadow\)/)
  assert.match(skeletonCard, /background:\s*var\(--card\)/)
  assert.match(skeletonCard, /border:\s*1px solid var\(--hairline\)/)
  assert.match(skeletonCard, /box-shadow:\s*var\(--shadow-card\)/)
  assert.match(skeletonCover, /background:\s*var\(--card\)/)
  assert.match(skeletonLine, /background:\s*var\(--card\)/)
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
    assert.match(block, /box-shadow:\s*var\(--glass-control-shadow-hover\),\s*var\(--focus-ring\)/)
    assert.match(block, /transform:\s*translateY\(-1px\)/)
  }

  assert.match(dangerMiniButtonFocus, /outline:\s*none/)
  assert.match(dangerMiniButtonFocus, backgroundIncludes('badge-error-bg'))
  assert.match(dangerMiniButtonFocus, /border-color:\s*var\(--badge-error-border\)/)
  assert.match(dangerMiniButtonFocus, /var\(--surface-specular-edge-strong\)/)
  assert.match(dangerMiniButtonFocus, /var\(--surface-noise\)/)
  assert.match(dangerMiniButtonFocus, /box-shadow:\s*var\(--glass-control-shadow-hover\),\s*0 0 0 3px color-mix\(in srgb,\s*var\(--badge-error-text\) 18%,\s*transparent\)/)
  assert.doesNotMatch(dangerMiniButtonFocus, /rgba\(var\(--error-rgb\)/)

  assert.match(entityBubbleFocus, /outline:\s*none/)
  assert.match(entityBubbleFocus, backgroundIncludes('material-glass-control-hover'))
  assert.match(entityBubbleFocus, /border-color:\s*var\(--glass-control-border-hover\)/)
  assert.match(entityBubbleFocus, /box-shadow:\s*var\(--glass-control-shadow-hover\),\s*var\(--focus-ring\)/)
  assert.match(entityBubbleFocus, /transform:\s*translateY\(-2px\)/)

  assert.match(entityFavButtonFocus, /outline:\s*none/)
  assert.match(entityFavButtonFocus, /opacity:\s*1/)
  assert.match(entityFavButtonFocus, backgroundIncludes('badge-error-bg'))
  assert.match(entityFavButtonFocus, /var\(--surface-specular-edge-strong\)/)
  assert.match(entityFavButtonFocus, /var\(--surface-noise\)/)
  assert.match(entityFavButtonFocus, /border-color:\s*var\(--badge-error-border\)/)
  assert.match(entityFavButtonFocus, /box-shadow:\s*var\(--glass-control-shadow-hover\),\s*0 0 0 3px color-mix\(in srgb,\s*var\(--badge-error-text\) 18%,\s*transparent\)/)
  assert.doesNotMatch(entityFavButtonFocus, /rgba\(var\(--error-rgb\)/)
  assert.match(entityFavButtonFocus, /transform:\s*translateY\(-1px\) scale\(1\.02\)/)

  assert.match(exploreFocus, /outline:\s*none/)
  assert.match(exploreFocus, backgroundIncludes('glass-active-material'))
  assert.match(exploreFocus, /border-color:\s*var\(--glass-active-border\)/)
  assert.match(exploreFocus, /box-shadow:\s*var\(--glass-control-shadow-hover\),\s*var\(--focus-ring-strong\)/)
  assert.match(exploreFocus, /transform:\s*translateY\(-2px\)/)
})

test('favorites glass backgrounds are layered with specular and noise surfaces', () => {
  assert.deepEqual(singleLayerGlassBackgrounds(externalStyle), [])
})

test('favorites liquid glass surfaces keep inner edge highlights and pressed feedback', () => {
  // v2 内容层去玻璃：实底面板用 --shadow-card，玻璃 inner edge 只留控件
  for (const [selector, shadowToken] of [
    ['.collection-form input', 'glass-control-shadow'],
    ['.btn-mini', 'glass-control-shadow'],
    ['.segmented-control', 'glass-control-shadow'],
    ['.segment-item', 'glass-control-shadow'],
    ['.entity-bubble', 'glass-control-shadow'],
    ['.select-check', 'glass-control-shadow'],
    ['.empty-icon', 'glass-control-shadow'],
  ]) {
    const block = cssBlock(selector)
    assert.match(block, new RegExp(`box-shadow:\\s*var\\(--${shadowToken}\\),\\s*var\\(--glass-inner-shadow\\)`), `${selector} should keep an inner glass edge`)
  }
  const collectionRow = cssBlock('.collection-row')
  assert.match(collectionRow, /border:\s*1px solid var\(--hairline\)/)
  assert.match(collectionRow, /background:\s*var\(--card-2\)/)
  assert.match(collectionRow, /box-shadow:\s*none/)
  assert.doesNotMatch(collectionRow, /material-glass|surface-specular-edge|surface-noise|backdrop-filter/)
  for (const selector of ['.collection-manager', '.skeleton-card']) {
    const block = cssBlock(selector)
    assert.match(block, /background:\s*var\(--card\)/, `${selector} should be solid --card`)
    assert.match(block, /box-shadow:\s*var\(--shadow-card\)/, `${selector} should use the solid card shadow`)
  }

  for (const selector of [
    '.btn-mini:active:not(:disabled)',
    '.segment-item:active',
    '.select-check:active',
    '.entity-bubble:active',
    '.entity-fav-btn:active',
    '.btn-explore:active',
  ]) {
    const block = cssBlock(selector)
    assert.match(block, /transform:\s*translateY\(0\)\s*scale\(0\.9[78]\)/, `${selector} should have compact pressed feedback`)
    assert.doesNotMatch(block, /transition:\s*all\b/, `${selector} should avoid transition-all`)
  }
})

test('favorites empty and loading states are composed glass surfaces', () => {
  const emptyState = cssBlock('.curate-empty')
  const skeletonCover = cssBlock('.skeleton-cover')
  const skeletonLine = cssBlock('.skeleton-line')
  const skeletonCoverShine = cssGroupedBlock('.skeleton-cover::after,')
  const skeletonLineShine = cssBlock('.skeleton-line::after')

  assert.match(emptyState, /max-width:\s*min\(520px,\s*100%\)/)
  assert.match(emptyState, /border:\s*1px solid var\(--hairline\)/)
  assert.match(emptyState, /background:\s*var\(--card\)/)
  assert.match(emptyState, /box-shadow:\s*var\(--shadow-card\)/)
  assert.doesNotMatch(emptyState, /backdrop-filter/)

  for (const block of [skeletonCover, skeletonLine]) {
    assert.match(block, /position:\s*relative/)
    assert.match(block, /overflow:\s*hidden/)
  }

  for (const block of [skeletonCoverShine, skeletonLineShine]) {
    assert.match(block, /content:\s*""/)
    assert.match(block, /background:\s*linear-gradient\(100deg,\s*transparent 0%,\s*var\(--skeleton-highlight\) 46%,\s*transparent 72%\)/)
    assert.match(block, /animation:\s*favorites-skeleton-shimmer 1\.8s ease-in-out infinite/)
    assert.doesNotMatch(block, /rgba\(255,\s*255,\s*255|rgba\(255,255,255/)
  }
})

test('favorites edit mode exposes a Photos-style selection bar for batch curation', () => {
  assert.match(vueSource, /class="selection-bar"[\s\S]*role="toolbar"[\s\S]*aria-label="收藏批量操作"/)
  assert.match(vueSource, /selectedFavoriteCount/)
  assert.match(vueSource, /visibleFavoriteCount/)
  assert.match(vueSource, /allVisibleSelected/)
  assert.match(vueSource, /selectAllVisibleFavorites/)
  assert.match(vueSource, /clearFavoriteSelection/)
  assert.match(vueSource, /取消收藏 \{\{ selectedFavoriteCount/)

  const selectionBar = cssBlock('.selection-bar')
  const selectionSummary = cssBlock('.selection-summary')
  const selectionSummaryStrong = cssBlock('.selection-summary strong')
  const selectionActions = cssBlock('.selection-actions')

  assert.match(selectionBar, /display:\s*flex/)
  assert.match(selectionBar, /align-items:\s*center/)
  assert.match(selectionBar, /justify-content:\s*space-between/)
  assert.match(selectionBar, /border:\s*1px solid var\(--hairline\)/)
  assert.match(selectionBar, /background:\s*var\(--card\)/)
  assert.match(selectionBar, /box-shadow:\s*var\(--shadow-card\)/)
  assert.doesNotMatch(selectionBar, /backdrop-filter/)

  assert.match(selectionSummary, /display:\s*grid/)
  assert.match(selectionSummaryStrong, /font-variant-numeric:\s*tabular-nums/)
  assert.match(selectionActions, /display:\s*flex/)
  assert.match(selectionActions, /flex-wrap:\s*wrap/)
})

test('favorites edit mode trims stale selections to the visible collection', () => {
  assert.match(vueSource, /trimSelectionToVisibleFavorites/)
  assert.match(vueSource, /watch\(\s*allVisibleFavoriteItems/)
  assert.match(vueSource, /const visibleKeys = new Set\(items\.map\(favoriteKey\)\)/)
  assert.match(vueSource, /selectedFavoriteKeys\.value = new Set\(\[\.\.\.selectedFavoriteKeys\.value\]\.filter\(key => visibleKeys\.has\(key\)\)\)/)
})

test('favorites edit mode can always be finished after switching to an empty view', () => {
  assert.match(vueSource, /:disabled="!editMode && visibleFavoriteCount === 0"/)
  assert.match(vueSource, /{{ editMode \? '完成' : '编辑' }}/)
})

test('favorites empty state offers media-library next actions without entering edit mode', () => {
  assert.match(vueSource, /<AppleEmptyState/)
  assert.match(vueSource, /:next-step="emptyNextStep"/)
  assert.match(vueSource, /:action-label="emptyActionLabel"/)
  assert.match(vueSource, /:secondary-action-label="emptySecondaryActionLabel"/)
  assert.match(vueSource, /@action="handleEmptyAction"/)
  assert.match(vueSource, /@secondary-action="handleEmptySecondaryAction"/)
  assert.match(vueSource, /浏览题材/)
  assert.match(vueSource, /订阅演员/)
  assert.match(vueSource, /activeTab\.value === 'all'[\s\S]*router\.push\('\/genres'\)/)
  assert.match(vueSource, /router\.push\('\/subscription'\)/)
  assert.match(vueSource, /:disabled="!editMode && visibleFavoriteCount === 0"[\s\S]*{{ editMode \? '完成' : '编辑' }}/)
})
