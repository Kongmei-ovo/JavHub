import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

const source = readFileSync(new URL('./CandidateRunPanel.vue', import.meta.url), 'utf8')

function cssBlock(selector) {
  const escaped = selector.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  return source.match(new RegExp(`${escaped}\\s*\\{[^}]*\\}`))?.[0] || ''
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

test('candidate run panel uses solid content surfaces', () => {
  const panel = cssBlock('.candidate-run-panel')
  // v2 内容层去玻璃：面板 = 实底
  assert.ok(backgroundIncludes(panel, '--card'), 'candidate run panel should be solid --card')
  assert.match(panel, /border:\s*1px solid var\(--glass-edge\)/)
  assert.match(panel, /box-shadow:\s*var\(--shadow-card\)/)
  assert.doesNotMatch(panel, /backdrop-filter/)
  assert.doesNotMatch(panel, /var\(--bg-card\)|var\(--border\)/)

  const row = cssBlock('.candidate-run-row')
  assert.match(row, /background:\s*var\(--card-2\)/)
  assert.match(row, /border:\s*1px solid var\(--hairline\)/)
  assert.match(row, /box-shadow:\s*none/)
  assert.doesNotMatch(row, /material-glass|surface-specular-edge|surface-noise|backdrop-filter/)

  const stat = cssBlock('.candidate-run-stats span')
  assert.ok(backgroundIncludes(stat, '--card'), 'candidate run stat should be solid --card')
  assert.match(stat, /border:\s*1px solid var\(--hairline\)/)
  assert.match(stat, /box-shadow:\s*none/)
})

test('candidate run rows use solid hover while actions are focused', () => {
  const row = cssBlock('.candidate-run-row')
  const hover = cssBlock('.candidate-run-row:hover')
  const focusWithin = cssBlock('.candidate-run-row:focus-within')

  assert.match(row, /transition:\s*transform var\(--motion-standard\)/)
  assert.doesNotMatch(row, /transition:[^;]*(?:background|border-color|box-shadow|filter|backdrop-filter)/)

  for (const [block, name] of [
    [hover, 'candidate run row hover'],
    [focusWithin, 'candidate run row focus-within'],
  ]) {
    assert.match(block, /background:\s*var\(--card-hover\)/, `${name} should use solid hover material`)
    assert.match(block, /border-color:\s*var\(--hairline-strong\)/, `${name} should use strong content border`)
    assert.match(block, /box-shadow:\s*var\(--shadow-card\)/, `${name} should use content depth`)
    assert.doesNotMatch(block, /material-glass|surface-specular-edge|surface-noise|backdrop-filter/)
    assert.match(block, /transform:\s*translateY\(-1px\)/, `${name} should lift lightly`)
  }

  assert.match(focusWithin, /var\(--focus-ring\)/, 'focused action row should add a soft accent halo')
})

test('candidate run panel avoids single-layer primary glass backgrounds', () => {
  const singleLayerGlass = /^.*background:\s*var\(--(?:material-glass-subtle|material-glass-control|material-glass-sheet)\);.*$/gm
  const offenders = [...source.matchAll(singleLayerGlass)].map(match => match[0].trim())

  assert.deepEqual(offenders, [], 'candidate run primary surfaces should be layered with specular and noise materials')
})
