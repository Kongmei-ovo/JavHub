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
    assert.match(block, /background:\s*var\(--material-glass-control\)/, `${name} should use glass material`)
    assert.match(block, /box-shadow:\s*var\(--glass-control-shadow\)/, `${name} should use glass shadow`)
    assert.doesNotMatch(block, /background:\s*transparent|background:\s*var\(--bg-card\)|border:\s*0|border-bottom:\s*2px solid transparent/)
  }

  for (const [block, name] of [
    [tabActive, 'active tab'],
    [filterChipActive, 'active filter chip'],
  ]) {
    assert.match(block, /border-color:\s*var\(--glass-active-border\)/, `${name} should use active glass border`)
    assert.match(block, /background:\s*var\(--glass-active-material\)/, `${name} should use active glass material`)
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
    assert.match(block, /background:\s*var\(--material-glass-elevated\)/, `${name} should use elevated material`)
    assert.match(block, /box-shadow:\s*var\(--glass-surface-shadow\)/, `${name} should use surface shadow`)
    assert.doesNotMatch(block, /rgba\(255,\s*255,\s*255|background:\s*var\(--bg-card\)/)
  }

  assert.match(candidateHigh, /border-color:\s*var\(--badge-success-border\)/)
  assert.match(candidateRisky, /border-color:\s*var\(--badge-warning-border\)/)
  assert.match(avatar, /border:\s*1px solid var\(--glass-control-border\)/)
  assert.match(avatar, /background:\s*var\(--material-glass-control\)/)
  assert.match(avatar, /box-shadow:\s*var\(--glass-inner-shadow\)/)
  assert.match(statusPill, /border:\s*1px solid var\(--glass-control-border\)/)
  assert.match(statusPill, /background:\s*var\(--material-glass-control\)/)
  assert.match(reasonPill, /border:\s*1px solid var\(--glass-control-border\)/)
  assert.match(reasonPill, /background:\s*var\(--material-glass-control\)/)
  assert.match(reasonPill, /box-shadow:\s*var\(--glass-inner-shadow\)/)
  assert.match(riskPill, /border:\s*1px solid var\(--badge-warning-border\)/)
  assert.match(riskPill, /background:\s*var\(--badge-warning-bg\)/)
  assert.match(riskPill, /color:\s*var\(--badge-warning-text\)/)
  assert.doesNotMatch(riskPill, /#ffb340|rgba\(255,\s*159,\s*10/)
})
