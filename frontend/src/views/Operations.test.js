import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

const vueSource = readFileSync(new URL('./Operations.vue', import.meta.url), 'utf8')
const externalStyle = readFileSync(new URL('../features/operations/operations.css', import.meta.url), 'utf8')
const source = `${vueSource}\n${externalStyle}`

function cssBlocks(content, selector) {
  const blocks = [...content.matchAll(/([^{}]+)\{([^{}]*)\}/g)]
    .filter(([, selectors]) => selectors
      .split(',')
      .map(part => part.trim())
      .includes(selector))
    .map(([, , block]) => block)
  assert.ok(blocks.length, `${selector} block should exist`)
  return blocks
}

function lastCssBlock(content, selector) {
  const blocks = cssBlocks(content, selector)
  return blocks.at(-1)
}

function backgroundIncludes(token) {
  return new RegExp(`background:[\\s\\S]*var\\(--${token}\\)`)
}

function singleLayerGlassBackgrounds(css) {
  return css
    .split('\n')
    .map((line, index) => ({ line: index + 1, text: line.trim() }))
    .filter(({ text }) => /^background:\s*var\(--(?:material-glass-subtle|material-glass-control|material-glass-control-hover|material-glass-sheet|glass-active-material)\);$/.test(text))
}

test('operations page keeps heavyweight styles in an external scoped stylesheet', () => {
  assert.match(vueSource, /<style scoped src="\.\.\/features\/operations\/operations\.css"><\/style>/)
  assert.ok(externalStyle.length > 18000, 'external operations stylesheet should carry the moved workspace CSS')
  assert.ok(vueSource.split('\n').length < 900, 'Operations.vue should stay small enough to review and parse quickly')
})

test('operations workbench controls use shared Apple glass tokens', () => {
  const segmentButton = lastCssBlock(source, '.operations-segments button')
  const segmentHover = lastCssBlock(source, '.operations-segments button:hover')
  const segmentActive = lastCssBlock(source, '.operations-segments button.active')
  const blockHeadButton = lastCssBlock(source, '.block-head button')
  const operationsPage = lastCssBlock(source, '.operations-page')
  const actionCard = cssBlocks(source, '.action-card').join('\n')
  const actionCardHover = cssBlocks(source, '.action-card:hover').join('\n')
  const queueFocus = cssBlocks(source, '.queue-focus').join('\n')
  const sharedHover = cssBlocks(source, '.queue-focus:hover').join('\n')
  const compactList = cssBlocks(source, '.compact-list').join('\n')
  const runList = cssBlocks(source, '.run-list').join('\n')
  const compactRow = cssBlocks(source, '.compact-row').join('\n')
  const runRow = cssBlocks(source, '.run-row').join('\n')
  const stateItem = cssBlocks(source, '.state-item').join('\n')
  const miniStat = cssBlocks(source, '.mini-stats > div').join('\n')
  const backendPill = lastCssBlock(source, '.backend-pill')
  const warningBlocks = cssBlocks(source, '.state-item.warning')

  assert.doesNotMatch(source, /var\(--surface-card\)|var\(--shadow-card\)|var\(--surface-card-hover\)|var\(--surface-control\)|var\(--surface-control-hover\)|var\(--surface-input-focus\)|var\(--border\)|var\(--border-light\)/)

  assert.match(operationsPage, /--operations-line:\s*var\(--glass-control-border\)/)
  assert.match(operationsPage, /--operations-soft-line:\s*var\(--glass-control-border\)/)

  assert.match(segmentButton, /border:\s*1px solid var\(--glass-control-border\)/)
  assert.match(segmentButton, backgroundIncludes('material-glass-control'))
  assert.match(segmentButton, /box-shadow:\s*var\(--glass-control-shadow\)/)
  assert.match(segmentButton, /backdrop-filter:\s*blur\(var\(--glass-blur-control\)\)\s*saturate\(var\(--glass-saturate-control\)\)/)
  assert.match(segmentHover, backgroundIncludes('material-glass-control-hover'))
  assert.match(segmentHover, /box-shadow:\s*var\(--glass-control-shadow-hover\)/)
  assert.match(segmentActive, backgroundIncludes('glass-active-material'))
  assert.match(segmentActive, /box-shadow:\s*var\(--glass-active-shadow\)/)

  assert.match(blockHeadButton, /border:\s*1px solid var\(--glass-control-border\)/)
  assert.match(blockHeadButton, backgroundIncludes('material-glass-control'))
  assert.match(blockHeadButton, /box-shadow:\s*var\(--glass-control-shadow\)/)

  for (const block of [actionCard, queueFocus, compactList, runList, compactRow, runRow]) {
    assert.match(block, /border:\s*1px solid var\(--operations-soft-line\)/)
    assert.match(block, backgroundIncludes('material-glass-control'))
  }

  for (const block of [compactRow, runRow]) {
    assert.match(block, /box-shadow:\s*var\(--glass-inner-shadow\)/)
  }

  for (const block of [stateItem, miniStat, backendPill]) {
    assert.match(block, /border:\s*1px solid var\(--operations-line\)/)
    assert.match(block, backgroundIncludes('material-glass-control'))
    assert.match(block, /box-shadow:\s*var\(--glass-inner-shadow\)/)
    assert.match(block, /backdrop-filter:\s*blur\(var\(--glass-blur-control\)\)\s*saturate\(var\(--glass-saturate-control\)\)/)
  }

  for (const block of [actionCardHover, sharedHover]) {
    assert.match(block, /border-color:\s*var\(--glass-control-border-hover\)/)
    assert.match(block, backgroundIncludes('material-glass-control-hover'))
  }

  for (const block of warningBlocks) {
    assert.match(block, /background:\s*var\(--operations-warning-material\)/)
    assert.doesNotMatch(block, /rgba\(255,\s*255,\s*255|rgba\(255,255,255/i)
  }

  for (const block of [segmentButton, blockHeadButton, actionCard, queueFocus, compactList, runList, compactRow, runRow, stateItem, miniStat, backendPill]) {
    assert.doesNotMatch(block, /border:\s*(?:0|none|1px solid transparent)/)
    assert.doesNotMatch(block, /background:\s*(?:transparent|none)/)
  }
})

test('operations keyboard focus mirrors hover glass control treatment', () => {
  const segmentFocus = lastCssBlock(source, '.operations-segments button:focus-visible')
  const heroFocus = lastCssBlock(source, '.hero-stat:focus-visible')
  const actionFocus = cssBlocks(source, '.action-card:focus-visible').join('\n')
  const queueFocus = cssBlocks(source, '.queue-focus:focus-visible').join('\n')
  const compactFocus = cssBlocks(source, '.compact-row:focus-visible').join('\n')
  const stateFocus = cssBlocks(source, '.state-item:is(button):focus-visible').join('\n')
  const blockHeadFocus = cssBlocks(source, '.block-head button:focus-visible').join('\n')
  const scopeFocus = cssBlocks(source, '.scope-chip:focus-visible').join('\n')

  for (const [block, label] of [
    [segmentFocus, 'operations segment focus'],
    [heroFocus, 'operations hero metric focus'],
    [actionFocus, 'operations action card focus'],
    [queueFocus, 'operations queue focus'],
    [compactFocus, 'operations compact row focus'],
    [stateFocus, 'operations state item focus'],
    [blockHeadFocus, 'operations block head focus'],
    [scopeFocus, 'operations scope chip focus'],
  ]) {
    assert.match(block, /outline:\s*none/, `${label} should replace the default outline`)
    assert.match(block, /border-color:\s*var\(--glass-control-border-hover\)/, `${label} should use hover border`)
    assert.match(block, backgroundIncludes('material-glass-control-hover'), `${label} should use hover glass material`)
    assert.match(block, /box-shadow:\s*var\(--glass-control-shadow-hover\),\s*var\(--focus-ring\)/, `${label} should expose a subtle focus ring`)
  }

  for (const block of [heroFocus, actionFocus, queueFocus, compactFocus, stateFocus, scopeFocus]) {
    assert.match(block, /transform:\s*translateY\(-1px\)/)
  }
  assert.match(segmentFocus, /color:\s*var\(--text-primary\)/)
  assert.match(blockHeadFocus, /color:\s*var\(--text-primary\)/)
})

test('operations glass backgrounds are layered with specular and noise surfaces', () => {
  assert.deepEqual(singleLayerGlassBackgrounds(externalStyle), [])
})
