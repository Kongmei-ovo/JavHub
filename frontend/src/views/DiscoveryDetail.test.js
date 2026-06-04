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
    assert.match(block, /transition:\s*transform var\(--motion-standard\),\s*background var\(--motion-standard\),\s*border-color var\(--motion-standard\),\s*box-shadow var\(--motion-standard\),\s*color var\(--motion-fast\),\s*opacity var\(--motion-fast\)/, `${name} should use explicit motion tokens`)
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
    assert.match(block, /transition:\s*transform var\(--motion-standard\),\s*background var\(--motion-standard\),\s*border-color var\(--motion-standard\),\s*box-shadow var\(--motion-standard\),\s*color var\(--motion-fast\),\s*opacity var\(--motion-fast\)/, `${name} should use explicit motion tokens`)
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
