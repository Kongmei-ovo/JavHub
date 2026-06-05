import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

const vueSource = readFileSync(new URL('./Normalize.vue', import.meta.url), 'utf8')
const externalStyle = readFileSync(new URL('../features/normalize/normalize.css', import.meta.url), 'utf8')
const source = `${vueSource}\n${externalStyle}`

function cssRule(selector) {
  const escaped = selector.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  const match = source.match(new RegExp(`${escaped}\\s*\\{([\\s\\S]*?)\\n\\}`))
  assert.ok(match, `Expected CSS rule for ${selector}`)
  return match[1]
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

test('normalize page keeps large scoped styles in a feature stylesheet', () => {
  assert.match(vueSource, /<style scoped src="\.\.\/features\/normalize\/normalize\.css"><\/style>/)
  assert.ok(vueSource.split('\n').length < 600, 'Normalize.vue should stay below 600 lines')
  assert.ok(externalStyle.split('\n').length > 350, 'external stylesheet should contain the moved normalize styles')
})

test('normalize actor mapping workbench uses shared Apple glass controls', () => {
  const autoMatchPanel = cssRule('.auto-match-panel')
  const tabBar = cssRule('.tab-bar')
  const tabButton = cssRule('.tab-btn')
  const tabActive = cssRule('.tab-btn.active')
  const filterChip = cssRule('.filter-chip')
  const filterChipActive = cssRule('.filter-chip.active')
  const searchInput = cssRule('.search-input')

  for (const [block, name] of [
    [autoMatchPanel, 'auto match panel'],
    [tabBar, 'tab bar'],
    [tabButton, 'tab button'],
    [filterChip, 'filter chip'],
    [searchInput, 'search input'],
  ]) {
    assert.match(block, /border:\s*1px solid var\(--glass-control-border\)/, `${name} should use glass border`)
    assert.ok(backgroundIncludes(block, '--material-glass-control'), `${name} should use glass material`)
    assert.match(block, /var\(--surface-specular-edge\)/, `${name} should include a specular glass edge`)
    assert.match(block, /var\(--surface-noise\)/, `${name} should include the shared noise layer`)
    assert.match(block, /box-shadow:\s*var\(--glass-control-shadow\)/, `${name} should use glass shadow`)
    assert.doesNotMatch(block, /background:\s*transparent|background:\s*var\(--bg-card\)|border:\s*0|border-bottom:\s*2px solid transparent/)
  }

  for (const [block, name] of [
    [tabActive, 'active tab'],
    [filterChipActive, 'active filter chip'],
  ]) {
    assert.match(block, /border-color:\s*var\(--glass-active-border\)/, `${name} should use active glass border`)
    assert.ok(backgroundIncludes(block, '--glass-active-material'), `${name} should use active glass material`)
    assert.match(block, /var\(--surface-specular-edge-strong\)/, `${name} should include a stronger active edge`)
    assert.match(block, /var\(--surface-noise\)/, `${name} should include the shared noise layer`)
    assert.match(block, /box-shadow:\s*var\(--glass-active-shadow\)/, `${name} should use active glass shadow`)
  }
})

test('normalize candidate and mapping rows avoid flat translucent cards', () => {
  const mappingCard = cssRule('.mapping-card')
  const candidateCard = cssRule('.candidate-card')
  const candidateHigh = cssRule('.candidate-card.high')
  const candidateRisky = cssRule('.candidate-card.risky')
  const mappingRow = cssRule('.mapping-row')
  const avatar = cssRule('.avatar')
  const statusPill = cssRule('.status-pill')
  const reasonPill = cssRule('.reason-pill')
  const riskPill = cssRule('.risk-row span')

  for (const [block, name] of [
    [mappingCard, 'mapping card'],
    [candidateCard, 'candidate card'],
    [mappingRow, 'mapping row'],
  ]) {
    assert.match(block, /border:\s*1px solid var\(--glass-edge\)/, `${name} should use glass edge`)
    assert.ok(backgroundIncludes(block, '--material-glass-elevated'), `${name} should use elevated material`)
    assert.match(block, /var\(--surface-specular-edge-strong\)/, `${name} should include a stronger elevated edge`)
    assert.match(block, /var\(--surface-noise\)/, `${name} should include the shared noise layer`)
    assert.match(block, /box-shadow:\s*var\(--glass-surface-shadow\)/, `${name} should use surface shadow`)
    assert.doesNotMatch(block, /rgba\(255,\s*255,\s*255|background:\s*var\(--bg-card\)/)
  }

  assert.match(candidateHigh, /border-color:\s*var\(--badge-success-border\)/)
  assert.match(candidateRisky, /border-color:\s*var\(--badge-warning-border\)/)
  assert.match(avatar, /border:\s*1px solid var\(--glass-control-border\)/)
  assert.ok(backgroundIncludes(avatar, '--material-glass-control'))
  assert.match(avatar, /var\(--surface-specular-edge\)/)
  assert.match(avatar, /var\(--surface-noise\)/)
  assert.match(avatar, /box-shadow:\s*var\(--glass-inner-shadow\)/)
  assert.match(statusPill, /border:\s*1px solid var\(--glass-control-border\)/)
  assert.ok(backgroundIncludes(statusPill, '--material-glass-control'))
  assert.match(reasonPill, /border:\s*1px solid var\(--glass-control-border\)/)
  assert.ok(backgroundIncludes(reasonPill, '--material-glass-control'))
  assert.match(reasonPill, /box-shadow:\s*var\(--glass-inner-shadow\)/)
  assert.match(riskPill, /border:\s*1px solid var\(--badge-warning-border\)/)
  assertLayeredBackground(riskPill, '--badge-warning-bg', 'normalize risky reason pill')
  assert.match(riskPill, /color:\s*var\(--badge-warning-text\)/)
  assert.match(riskPill, /box-shadow:\s*var\(--glass-inner-shadow\)/)
  assert.match(riskPill, /backdrop-filter:\s*blur\(var\(--glass-blur-control\)\)\s*saturate\(var\(--glass-saturate-control\)\)/)
  assert.doesNotMatch(riskPill, /#ffb340|rgba\(255,\s*159,\s*10/)
})

test('normalize keyboard focus mirrors Apple glass control depth', () => {
  const tabFocus = cssRule('.tab-btn:focus-visible')
  const filterFocus = cssRule('.filter-chip:focus-visible')
  const candidateFocus = cssRule('.candidate-card:focus-within')
  const mappingFocus = cssRule('.mapping-row:focus-within')

  for (const [block, name] of [
    [tabFocus, 'tab focus'],
    [filterFocus, 'filter chip focus'],
  ]) {
    assert.match(block, /outline:\s*none/, `${name} should suppress the default outline`)
    assert.ok(backgroundIncludes(block, '--material-glass-control-hover'), `${name} should use hover glass material`)
    assert.match(block, /border-color:\s*var\(--glass-control-border-hover\)/, `${name} should use hover glass border`)
    assert.match(block, /box-shadow:\s*var\(--glass-control-shadow-hover\),\s*0 0 0 3px rgba\(var\(--accent-rgb\),\s*0\.12\)/, `${name} should use glass shadow plus focus halo`)
    assert.match(block, /transform:\s*translateY\(-1px\)/, `${name} should preserve hover lift`)
  }

  for (const [block, name] of [
    [candidateFocus, 'candidate card focus'],
    [mappingFocus, 'mapping row focus'],
  ]) {
    assert.ok(backgroundIncludes(block, '--material-glass-elevated'), `${name} should keep elevated glass material`)
    assert.match(block, /border-color:\s*var\(--glass-control-border-hover\)/, `${name} should lift its edge when focused inside`)
    assert.match(block, /box-shadow:\s*var\(--glass-control-shadow-hover\),\s*var\(--glass-surface-shadow\),\s*0 0 0 3px rgba\(var\(--accent-rgb\),\s*0\.1\)/, `${name} should layer surface depth with focus halo`)
    assert.match(block, /transform:\s*translateY\(-1px\)/, `${name} should rise when an inner action is focused`)
  }
})

test('normalize glass backgrounds are layered with specular and noise surfaces', () => {
  const singleLayerGlass = /^background:\s*var\(--(?:material-glass-control|material-glass-control-hover|material-glass-elevated|material-glass-sheet|glass-active-material)\);$/gm
  const offenders = [...externalStyle.matchAll(singleLayerGlass)].map(match => match[0])

  assert.deepEqual(offenders, [], 'normalize primary glass surfaces should not use single-layer glass backgrounds')

  for (const [selector, token] of [
    ['.summary-card', '--material-glass-elevated'],
    ['.auto-match-panel', '--material-glass-control'],
    ['.tab-bar', '--material-glass-control'],
    ['.tab-btn', '--material-glass-control'],
    ['.tab-btn:hover', '--material-glass-control-hover'],
    ['.tab-btn.active', '--glass-active-material'],
    ['.filter-chip', '--material-glass-control'],
    ['.filter-chip:hover', '--material-glass-control-hover'],
    ['.filter-chip.active', '--glass-active-material'],
    ['.search-input', '--material-glass-control'],
    ['.search-input:focus', '--material-glass-control-hover'],
    ['.mapping-card', '--material-glass-elevated'],
    ['.candidate-card', '--material-glass-elevated'],
    ['.confidence-badge', '--material-glass-control'],
    ['.mapping-row', '--material-glass-elevated'],
    ['.status-pill', '--material-glass-control'],
    ['.reason-pill', '--material-glass-control'],
  ]) {
    const block = cssRule(selector)
    assert.ok(backgroundIncludes(block, token), `${selector} should include ${token}`)
    assertLayeredBackground(block, token, selector)
  }
})
