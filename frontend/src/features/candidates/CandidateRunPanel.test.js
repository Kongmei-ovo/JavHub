import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

const source = readFileSync(new URL('./CandidateRunPanel.vue', import.meta.url), 'utf8')

function cssBlock(selector) {
  const escaped = selector.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  return source.match(new RegExp(`${escaped}\\s*\\{[^}]*\\}`))?.[0] || ''
}

test('candidate run panel uses shared Apple glass surfaces instead of legacy cards', () => {
  const panel = cssBlock('.candidate-run-panel')
  assert.match(panel, /background:\s*var\(--material-glass-sheet\)/)
  assert.match(panel, /border:\s*1px solid var\(--glass-edge\)/)
  assert.match(panel, /box-shadow:\s*var\(--glass-surface-shadow\)/)
  assert.match(panel, /backdrop-filter:\s*blur\(var\(--glass-blur-surface\)\)\s*saturate\(var\(--glass-saturate-surface\)\)/)
  assert.doesNotMatch(panel, /var\(--bg-card\)|var\(--border\)/)

  const row = cssBlock('.candidate-run-row')
  assert.match(row, /background:\s*var\(--material-glass-control\)/)
  assert.match(row, /border:\s*1px solid var\(--glass-control-border\)/)
  assert.match(row, /box-shadow:\s*var\(--glass-control-shadow\)/)

  const stat = cssBlock('.candidate-run-stats span')
  assert.match(stat, /background:\s*var\(--material-glass-subtle\)/)
  assert.match(stat, /border:\s*1px solid var\(--glass-control-border\)/)
  assert.match(stat, /box-shadow:\s*var\(--glass-inner-shadow\)/)
})
