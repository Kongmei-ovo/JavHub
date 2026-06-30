import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

const source = readFileSync(new URL('./DiscoveryDetail.vue', import.meta.url), 'utf8')

function cssBlock(selector) {
  const escaped = selector.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  const match = source.match(new RegExp(`(?:^|\\n)\\s*${escaped}(?=[\\s,{:#.])`))
  assert.ok(match, `${selector} should exist`)
  const index = match.index + match[0].lastIndexOf(selector)

  const open = source.indexOf('{', index)
  assert.notEqual(open, -1, `${selector} should have a declaration block`)

  let depth = 0
  for (let i = open; i < source.length; i += 1) {
    if (source[i] === '{') depth += 1
    if (source[i] === '}') {
      depth -= 1
      if (depth === 0) return source.slice(open + 1, i)
    }
  }

  assert.fail(`${selector} should have a closed declaration block`)
}

function backgroundIncludes(block, token) {
  const match = block.match(/background:\s*([^;]+);/)
  return Boolean(match && match[1].includes(token))
}

function assertLayeredBackground(block, token, selector) {
  assert.ok(backgroundIncludes(block, token), `${selector} should include ${token}`)
  assert.match(block, /var\(--surface-specular-edge/, `${selector} should include a specular edge layer`)
  assert.match(block, /var\(--surface-noise\)/, `${selector} should include the shared noise layer`)
}

test('discovery detail filter and pagination controls use shared glass materials and explicit motion', () => {
  const sortPillBlock = cssBlock('.sort-pill')
  const sortPillHoverBlock = cssBlock('.sort-pill:hover')
  const sortPillActiveBlock = cssBlock('.sort-pill.active')
  const chronicleButtonBlock = cssBlock('.chronicle-btn')
  const chronicleButtonHoverBlock = cssBlock('.chronicle-btn:hover')
  const chronicleButtonActiveBlock = cssBlock('.chronicle-btn.active')
  const pageButtonBlock = cssBlock('.page-btn')
  const pageButtonHoverBlock = cssBlock('.page-btn:hover:not(:disabled)')

  for (const [block, name] of [
    [sortPillBlock, 'sort pill'],
    [chronicleButtonBlock, 'chronicle button'],
    [pageButtonBlock, 'page button'],
  ]) {
    assertLayeredBackground(block, '--material-glass-control', name)
    assert.match(block, /border:\s*1px solid var\(--glass-control-border\)/, `${name} should use shared glass border`)
    assert.match(block, /box-shadow:\s*var\(--glass-control-shadow\)/, `${name} should use shared glass shadow`)
    assert.match(block, /backdrop-filter:\s*blur\(var\(--glass-blur-control\)\)\s*saturate\(var\(--glass-saturate-control\)\)/, `${name} should use control blur`)
    assert.match(block, /transition:\s*transform var\(--motion-standard\),\s*opacity var\(--motion-fast\)/, `${name} should use lightweight motion tokens`)
    assert.doesNotMatch(block, /transition:[^;]*(?:background|border-color|box-shadow|filter|backdrop-filter)/, `${name} should keep material changes out of transitions`)
    assert.doesNotMatch(block, /border:\s*1px solid transparent|transition:\s*all\b|transition:\s*var\(--transition-pro\)/, `${name} should not keep legacy flat control behavior`)
  }

  for (const [block, name] of [
    [sortPillHoverBlock, 'sort pill hover'],
    [chronicleButtonHoverBlock, 'chronicle button hover'],
    [pageButtonHoverBlock, 'page button hover'],
  ]) {
    assertLayeredBackground(block, '--material-glass-control-hover', name)
    assert.match(block, /border-color:\s*var\(--glass-control-border-hover\)/, `${name} should use shared hover border`)
    assert.match(block, /box-shadow:\s*var\(--glass-control-shadow-hover\)/, `${name} should use shared hover shadow`)
    assert.match(block, /transform:\s*translateY\(-1px\)/, `${name} should lift lightly`)
  }

  for (const [block, name] of [
    [sortPillActiveBlock, 'sort pill active'],
    [chronicleButtonActiveBlock, 'chronicle button active'],
  ]) {
    assertLayeredBackground(block, '--glass-active-material', name)
    assert.match(block, /border-color:\s*var\(--glass-active-border\)/, `${name} should use active glass border`)
    assert.match(block, /box-shadow:\s*var\(--glass-active-shadow\)/, `${name} should use active glass shadow`)
    assert.doesNotMatch(block, /box-shadow:\s*inset 0 -2px 0 var\(--active-indicator\)/, `${name} should not use old underline-active chrome`)
  }
})

test('discovery detail toolbar actions use shared glass controls without legacy transition-all', () => {
  const backButtonBlock = cssBlock('.back-btn')
  const backButtonHoverBlock = cssBlock('.back-btn:hover')
  const favoriteButtonBlock = cssBlock('.entity-fav-btn')
  const favoriteButtonHoverBlock = cssBlock('.entity-fav-btn:hover')
  const favoriteButtonActiveBlock = cssBlock('.entity-fav-btn.is-active')
  const favoriteButtonActiveHoverBlock = cssBlock('.entity-fav-btn.is-active:hover')
  const subscriptionButtonBlock = cssBlock('.entity-sub-btn')
  const subscriptionButtonHoverBlock = cssBlock('.entity-sub-btn:hover')
  const subscriptionButtonActiveBlock = cssBlock('.entity-sub-btn.is-active')

  for (const [block, name] of [
    [backButtonBlock, 'back button'],
    [favoriteButtonBlock, 'favorite button'],
    [subscriptionButtonBlock, 'subscription button'],
  ]) {
    assertLayeredBackground(block, '--material-glass-control', name)
    assert.match(block, /border:\s*1px solid var\(--glass-control-border\)/, `${name} should use shared glass border`)
    assert.match(block, /box-shadow:\s*var\(--glass-control-shadow\)/, `${name} should use shared glass shadow`)
    assert.match(block, /backdrop-filter:\s*blur\(var\(--glass-blur-control\)\)\s*saturate\(var\(--glass-saturate-control\)\)/, `${name} should use control blur`)
    assert.match(block, /transition:\s*transform var\(--motion-standard\),\s*opacity var\(--motion-fast\)/, `${name} should use lightweight motion tokens`)
    assert.doesNotMatch(block, /transition:[^;]*(?:background|border-color|box-shadow|filter|backdrop-filter)/, `${name} should keep material changes out of transitions`)
    assert.doesNotMatch(block, /background:\s*none|transition:\s*all\b|transition:\s*var\(--transition-pro\)/, `${name} should not keep flat legacy toolbar behavior`)
  }

  for (const [block, name] of [
    [backButtonHoverBlock, 'back button hover'],
    [favoriteButtonHoverBlock, 'favorite button hover'],
    [subscriptionButtonHoverBlock, 'subscription button hover'],
  ]) {
    assertLayeredBackground(block, '--material-glass-control-hover', name)
    assert.match(block, /border-color:\s*var\(--glass-control-border-hover\)/, `${name} should use shared hover border`)
    assert.match(block, /box-shadow:\s*var\(--glass-control-shadow-hover\)/, `${name} should use shared hover shadow`)
    assert.match(block, /transform:\s*translateY\(-1px\)/, `${name} should lift lightly`)
  }

  for (const [block, name] of [
    [favoriteButtonActiveBlock, 'favorite button active'],
    [subscriptionButtonActiveBlock, 'subscription button active'],
  ]) {
    assertLayeredBackground(block, '--glass-active-material', name)
    assert.match(block, /border-color:\s*var\(--glass-active-border\)/, `${name} should use active glass border`)
    assert.match(block, /box-shadow:\s*var\(--glass-active-shadow\)/, `${name} should use active glass shadow`)
    assert.doesNotMatch(block, /box-shadow:\s*inset 0 -2px 0 var\(--active-indicator\)/, `${name} should not use old underline-active chrome`)
  }

  assert.match(favoriteButtonActiveBlock, /color:\s*var\(--badge-error-text\)/, 'favorite active should use semantic favorite/error text')
  assert.match(favoriteButtonActiveHoverBlock, /color:\s*var\(--badge-error-text\)/, 'favorite active hover should keep semantic favorite/error text')
  assert.doesNotMatch(favoriteButtonActiveBlock, /#FF375F|#ff375f|rgba\(255,\s*55,\s*95/i)
  assert.doesNotMatch(favoriteButtonActiveHoverBlock, /#FF375F|#ff375f|rgba\(255,\s*55,\s*95/i)
  assert.doesNotMatch(source, /#FF375F|#ff375f|rgba\(255,\s*55,\s*95/i)
})

test('discovery detail keyboard focus mirrors hover glass treatment', () => {
  const focusSelectors = [
    '.back-btn:focus-visible',
    '.entity-fav-btn:focus-visible',
    '.entity-sub-btn:focus-visible',
    '.sort-pill:focus-visible',
    '.chronicle-btn:focus-visible',
    '.page-btn:focus-visible:not(:disabled)',
  ]

  for (const selector of focusSelectors) {
    const block = cssBlock(selector)
    assertLayeredBackground(block, '--material-glass-control-hover', selector)
    assert.match(block, /outline:\s*none/, `${selector} should avoid double native focus chrome`)
    assert.match(block, /border-color:\s*var\(--glass-control-border-hover\)/, `${selector} should use shared hover border`)
    assert.match(block, /box-shadow:\s*var\(--glass-control-shadow-hover\),\s*var\(--focus-ring\)/, `${selector} should add a soft accent focus halo`)
    assert.match(block, /transform:\s*translateY\(-1px\)/, `${selector} should keep the hover lift while focused`)
  }

  const activeFocusSelectors = [
    '.entity-fav-btn.is-active:focus-visible',
    '.entity-sub-btn.is-active:focus-visible',
    '.sort-pill.active:focus-visible',
    '.chronicle-btn.active:focus-visible',
  ]

  for (const selector of activeFocusSelectors) {
    const block = cssBlock(selector)
    assertLayeredBackground(block, '--glass-active-material', selector)
    assert.match(block, /outline:\s*none/, `${selector} should avoid double native focus chrome`)
    assert.match(block, /border-color:\s*var\(--glass-active-border\)/, `${selector} should preserve active glass border`)
    assert.match(block, /box-shadow:\s*var\(--glass-active-shadow\),\s*var\(--focus-ring\)/, `${selector} should combine active depth with focus halo`)
    assert.match(block, /transform:\s*translateY\(-1px\)/, `${selector} should keep active controls lifted while focused`)
  }

  assert.match(cssBlock('.entity-fav-btn.is-active:focus-visible'), /color:\s*var\(--badge-error-text\)/, 'favorite focus should preserve semantic favorite color')
})

test('discovery detail glass controls use layered backgrounds across base hover and active states', () => {
  const singleLayerGlass = /^.*background:\s*var\(--(?:material-glass-control|material-glass-control-hover|glass-active-material)\);.*$/gm
  const offenders = [...source.matchAll(singleLayerGlass)].map(match => match[0].trim())

  assert.deepEqual(offenders, [], 'discovery detail primary controls should not use single-layer glass backgrounds')

  for (const [selector, token] of [
    ['.back-btn', '--material-glass-control'],
    ['.back-btn:hover', '--material-glass-control-hover'],
    ['.entity-fav-btn', '--material-glass-control'],
    ['.entity-fav-btn:hover', '--material-glass-control-hover'],
    ['.entity-fav-btn.is-active', '--glass-active-material'],
    ['.entity-fav-btn.is-active:hover', '--glass-active-material'],
    ['.entity-sub-btn', '--material-glass-control'],
    ['.entity-sub-btn:hover', '--material-glass-control-hover'],
    ['.entity-sub-btn.is-active', '--glass-active-material'],
    ['.entity-sub-btn.is-active:hover', '--glass-active-material'],
    ['.sort-pill', '--material-glass-control'],
    ['.sort-pill:hover', '--material-glass-control-hover'],
    ['.sort-pill.active', '--glass-active-material'],
    ['.sort-pill.active:hover', '--glass-active-material'],
    ['.chronicle-btn', '--material-glass-control'],
    ['.chronicle-btn:hover', '--material-glass-control-hover'],
    ['.chronicle-btn.active', '--glass-active-material'],
    ['.chronicle-btn.active:hover', '--glass-active-material'],
    ['.page-btn', '--material-glass-control'],
    ['.page-btn:hover:not(:disabled)', '--material-glass-control-hover'],
  ]) {
    assertLayeredBackground(cssBlock(selector), token, selector)
  }
})

test('discovery detail chronicle headings use shared glass border tokens', () => {
  const toolbarBlock = cssBlock('.toolbar')
  const paginationBottomBlock = cssBlock('.pagination-bar.bottom')
  const yearHeaderBlock = cssBlock('.year-header')

  assert.match(toolbarBlock, /border-bottom:\s*1px solid var\(--glass-edge\)/)
  assert.match(paginationBottomBlock, /border-top:\s*1px solid var\(--glass-edge\)/)
  assert.match(yearHeaderBlock, /border-left:\s*3px solid var\(--glass-control-border\)/)
  for (const block of [toolbarBlock, paginationBottomBlock, yearHeaderBlock]) {
    assert.doesNotMatch(block, /var\(--border\)|var\(--border-light\)|rgba\(255,\s*255,\s*255|#[0-9a-f]{3,6}/i)
  }
})

test('discovery detail does not retain unused legacy shuffle button chrome', () => {
  assert.doesNotMatch(source, /\.shuffle-btn\b/, 'unused shuffle button styles should not remain in discovery detail')
})

test('discovery detail exposes inline error state with shared Apple state chrome', () => {
  assert.match(source, /import AppleErrorState from '\.\.\/components\/AppleErrorState\.vue'/)
  assert.match(source, /components:\s*\{[^}]*AppleErrorState/)
  assert.match(source, /searchError:\s*null/)
  assert.match(source, /this\.searchError\s*=\s*null/)
  assert.match(source, /this\.searchError\s*=\s*api\.formatApiError/)
  assert.match(source, /<AppleErrorState[\s\S]*title="发现页加载失败"[\s\S]*@retry="refresh"/)
  assert.match(source, /v-else-if="searchError"/)
})

test('discovery detail bars and state panels use compact glass trays', () => {
  const resultBarBlock = cssBlock('.result-bar')
  const paginationBarBlock = cssBlock('.pagination-bar')
  const statePanelBlock = cssBlock('.genre-detail-page :deep(.apple-empty-state),\n.genre-detail-page :deep(.apple-error-state)')
  const skeletonGridBlock = cssBlock('.skeleton-grid')

  // v2 内容层去玻璃：result/pagination 工具条与状态面板 = 实底
  for (const [block, name] of [[resultBarBlock, 'result bar'], [paginationBarBlock, 'pagination bar']]) {
    assert.match(block, /background:\s*var\(--card\)/, `${name} should be solid --card`)
    assert.match(block, /border:\s*1px solid var\(--glass-edge\)/, `${name} should use shared glass edge`)
    assert.doesNotMatch(block, /backdrop-filter/, `${name} should not blur`)
  }

  assert.match(resultBarBlock, /padding:\s*6px/)
  assert.match(paginationBarBlock, /width:\s*fit-content/)
  assert.match(paginationBarBlock, /max-width:\s*calc\(100% - var\(--page-gutter\) - var\(--page-gutter\)\)/)
  assert.match(statePanelBlock, /background:\s*var\(--card\)/)
  assert.match(statePanelBlock, /border:\s*1px solid var\(--glass-edge-strong\)/)
  assert.match(statePanelBlock, /box-shadow:\s*var\(--shadow-sheet\)/)
  assert.doesNotMatch(statePanelBlock, /backdrop-filter/)
  // 卡片栅格走全站统一 token（影片海报档），不再硬写像素值
  assert.match(skeletonGridBlock, /grid-template-columns:\s*repeat\(auto-fill,\s*minmax\(var\(--grid-min-poster\),\s*1fr\)\)/)
  assert.match(skeletonGridBlock, /align-items:\s*start/)
})

test('discovery detail page polishes variant disclosure focus without editing shared component', () => {
  const toggleFocusBlock = cssBlock('.genre-detail-page :deep(.variant-group-disclosure__toggle:focus-visible)')
  const rowFocusBlock = cssBlock('.genre-detail-page :deep(.variant-group-disclosure__row:focus-visible)')
  const labelBlock = cssBlock('.genre-detail-page :deep(.variant-group-disclosure__labels span)')

  assertLayeredBackground(toggleFocusBlock, '--material-glass-control-hover', 'variant toggle focus')
  assert.match(toggleFocusBlock, /border-color:\s*var\(--glass-control-border-hover\)/)
  assert.match(toggleFocusBlock, /box-shadow:\s*var\(--glass-control-shadow-hover\),\s*var\(--focus-ring-wide-strong\)/)
  assert.match(rowFocusBlock, /background:\s*var\(--card-hover\)/)
  assert.match(rowFocusBlock, /border-color:\s*var\(--hairline-strong\)/)
  assert.match(rowFocusBlock, /color:\s*var\(--text-primary\)/)
  assert.match(rowFocusBlock, /box-shadow:\s*var\(--shadow-card\),\s*var\(--focus-ring-wide-strong\)/)
  assert.doesNotMatch(rowFocusBlock, /material-glass|surface-specular-edge|surface-noise|backdrop-filter/)

  assertLayeredBackground(labelBlock, '--badge-info-bg', 'variant label')
  assert.match(labelBlock, /box-shadow:\s*var\(--glass-inner-shadow\)/)
})

test('discovery detail controls include pressed feedback across toolbar and filters', () => {
  for (const selector of [
    '.back-btn:active',
    '.entity-fav-btn:active',
    '.entity-sub-btn:active',
    '.sort-pill:active',
    '.chronicle-btn:active',
    '.page-btn:active:not(:disabled)',
  ]) {
    assert.match(cssBlock(selector), /transform:\s*translateY\(0\)\s*scale\(0\.(?:96|99)\)/, `${selector} should provide pressed feedback`)
  }
})
