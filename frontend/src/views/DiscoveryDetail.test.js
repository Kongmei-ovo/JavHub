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
    assert.match(block, /background:\s*var\(--material-glass-control\)/, `${name} should use shared glass material`)
    assert.match(block, /border:\s*1px solid var\(--glass-control-border\)/, `${name} should use shared glass border`)
    assert.match(block, /box-shadow:\s*var\(--glass-control-shadow\)/, `${name} should use shared glass shadow`)
    assert.match(block, /backdrop-filter:\s*blur\(var\(--glass-blur-control\)\)\s*saturate\(var\(--glass-saturate-control\)\)/, `${name} should use control blur`)
    assert.match(block, /transition:\s*transform var\(--motion-standard\),\s*background var\(--motion-standard\),\s*border-color var\(--motion-standard\),\s*box-shadow var\(--motion-standard\),\s*color var\(--motion-fast\),\s*opacity var\(--motion-fast\)/, `${name} should use explicit motion tokens`)
    assert.doesNotMatch(block, /border:\s*1px solid transparent|transition:\s*all\b|transition:\s*var\(--transition-pro\)/, `${name} should not keep legacy flat control behavior`)
  }

  for (const [block, name] of [
    [sortPillHoverBlock, 'sort pill hover'],
    [chronicleButtonHoverBlock, 'chronicle button hover'],
    [pageButtonHoverBlock, 'page button hover'],
  ]) {
    assert.match(block, /background:\s*var\(--material-glass-control-hover\)/, `${name} should use shared hover material`)
    assert.match(block, /border-color:\s*var\(--glass-control-border-hover\)/, `${name} should use shared hover border`)
    assert.match(block, /box-shadow:\s*var\(--glass-control-shadow-hover\)/, `${name} should use shared hover shadow`)
    assert.match(block, /transform:\s*translateY\(-1px\)/, `${name} should lift lightly`)
  }

  for (const [block, name] of [
    [sortPillActiveBlock, 'sort pill active'],
    [chronicleButtonActiveBlock, 'chronicle button active'],
  ]) {
    assert.match(block, /background:\s*var\(--glass-active-material\)/, `${name} should use active glass material`)
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
    assert.match(block, /background:\s*var\(--material-glass-control\)/, `${name} should use shared glass material`)
    assert.match(block, /border:\s*1px solid var\(--glass-control-border\)/, `${name} should use shared glass border`)
    assert.match(block, /box-shadow:\s*var\(--glass-control-shadow\)/, `${name} should use shared glass shadow`)
    assert.match(block, /backdrop-filter:\s*blur\(var\(--glass-blur-control\)\)\s*saturate\(var\(--glass-saturate-control\)\)/, `${name} should use control blur`)
    assert.match(block, /transition:\s*transform var\(--motion-standard\),\s*background var\(--motion-standard\),\s*border-color var\(--motion-standard\),\s*box-shadow var\(--motion-standard\),\s*color var\(--motion-fast\),\s*opacity var\(--motion-fast\)/, `${name} should use explicit motion tokens`)
    assert.doesNotMatch(block, /background:\s*none|transition:\s*all\b|transition:\s*var\(--transition-pro\)/, `${name} should not keep flat legacy toolbar behavior`)
  }

  for (const [block, name] of [
    [backButtonHoverBlock, 'back button hover'],
    [favoriteButtonHoverBlock, 'favorite button hover'],
    [subscriptionButtonHoverBlock, 'subscription button hover'],
  ]) {
    assert.match(block, /background:\s*var\(--material-glass-control-hover\)/, `${name} should use shared hover material`)
    assert.match(block, /border-color:\s*var\(--glass-control-border-hover\)/, `${name} should use shared hover border`)
    assert.match(block, /box-shadow:\s*var\(--glass-control-shadow-hover\)/, `${name} should use shared hover shadow`)
    assert.match(block, /transform:\s*translateY\(-1px\)/, `${name} should lift lightly`)
  }

  for (const [block, name] of [
    [favoriteButtonActiveBlock, 'favorite button active'],
    [subscriptionButtonActiveBlock, 'subscription button active'],
  ]) {
    assert.match(block, /background:\s*var\(--glass-active-material\)/, `${name} should use active glass material`)
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

test('discovery detail chronicle headings use shared glass border tokens', () => {
  const toolbarBlock = cssBlock('.toolbar')
  const barDividerBlock = cssBlock('.bar-divider')
  const paginationBottomBlock = cssBlock('.pagination-bar.bottom')
  const yearHeaderBlock = cssBlock('.year-header')

  assert.match(toolbarBlock, /border-bottom:\s*1px solid var\(--glass-edge\)/)
  assert.match(barDividerBlock, /background:\s*var\(--glass-control-border\)/)
  assert.match(paginationBottomBlock, /border-top:\s*1px solid var\(--glass-edge\)/)
  assert.match(yearHeaderBlock, /border-left:\s*3px solid var\(--glass-control-border\)/)
  for (const block of [toolbarBlock, barDividerBlock, paginationBottomBlock, yearHeaderBlock]) {
    assert.doesNotMatch(block, /var\(--border\)|var\(--border-light\)|rgba\(255,\s*255,\s*255|#[0-9a-f]{3,6}/i)
  }
})

test('discovery detail does not retain unused legacy shuffle button chrome', () => {
  assert.doesNotMatch(source, /\.shuffle-btn\b/, 'unused shuffle button styles should not remain in discovery detail')
})
