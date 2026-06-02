import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

const source = readFileSync(new URL('./Library.vue', import.meta.url), 'utf8')

function cssBlock(selector) {
  const escaped = selector.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  const match = source.match(new RegExp(`${escaped}\\s*\\{([^}]*)\\}`))
  assert.ok(match, `${selector} should exist`)
  return match[1]
}

test('legacy library checker keeps shared glass surfaces while it redirects users to organizer flow', () => {
  const input = cssBlock('.check-form input')
  const inputFocus = cssBlock('.check-form input:focus')
  const button = cssBlock('.check-form button')
  const buttonHover = cssBlock('.check-form button:hover:not(:disabled)')
  const result = cssBlock('.result')
  const item = cssBlock('.item')

  for (const [block, name] of [[input, 'input'], [button, 'button'], [item, 'item']]) {
    assert.match(block, /background:\s*var\(--material-glass-control\)/, `${name} should use glass control material`)
    assert.match(block, /border:\s*1px solid var\(--glass-control-border\)/, `${name} should use glass control border`)
    assert.match(block, /box-shadow:\s*var\(--glass-control-shadow\)/, `${name} should use glass control shadow`)
    assert.match(block, /backdrop-filter:\s*blur\(var\(--glass-blur-control\)\)\s*saturate\(var\(--glass-saturate-control\)\)/, `${name} should use control blur`)
  }

  assert.match(inputFocus, /border-color:\s*var\(--glass-active-border\)/)
  assert.match(inputFocus, /background:\s*var\(--glass-active-material\)/)
  assert.match(inputFocus, /box-shadow:\s*var\(--glass-active-shadow\)/)

  assert.match(buttonHover, /background:\s*var\(--material-glass-control-hover\)/)
  assert.match(buttonHover, /border-color:\s*var\(--glass-control-border-hover\)/)
  assert.match(buttonHover, /box-shadow:\s*var\(--glass-control-shadow-hover\)/)

  assert.match(result, /background:\s*var\(--material-glass-sheet\)/)
  assert.match(result, /border:\s*1px solid var\(--glass-edge\)/)
  assert.match(result, /box-shadow:\s*var\(--glass-surface-shadow\)/)

  assert.doesNotMatch(source, /rgba\(255,\s*255,\s*255|rgba\(255,255,255|var\(--bg-card\)|var\(--bg-card-hover\)|var\(--border\)|var\(--border-light\)|var\(--shadow-card\)|background:\s*var\(--accent\)/)
})
