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

function layeredBackground(token) {
  return new RegExp(`background:\\s*var\\(--surface-specular-edge(?:-strong)?\\),\\s*var\\(--surface-noise\\),\\s*var\\(--${token}\\)`)
}

function singleLayerGlassBackgrounds(css) {
  return css
    .split('\n')
    .map(line => line.trim())
    .filter(line => /^background:\s*var\(--(?:material-glass-control|material-glass-control-hover|material-glass-sheet|glass-active-material)\);$/.test(line))
}

test('legacy library checker keeps shared glass surfaces while it redirects users to organizer flow', () => {
  const input = cssBlock('.check-form input')
  const inputFocus = cssBlock('.check-form input:focus')
  const button = cssBlock('.check-form button')
  const buttonHover = cssBlock('.check-form button:hover:not(:disabled)')
  const result = cssBlock('.result')
  const item = cssBlock('.item')

  for (const [block, name] of [[input, 'input'], [button, 'button'], [item, 'item']]) {
    assert.match(block, layeredBackground('material-glass-control'), `${name} should use layered glass control material`)
    assert.match(block, /border:\s*1px solid var\(--glass-control-border\)/, `${name} should use glass control border`)
    assert.match(block, /box-shadow:\s*var\(--glass-control-shadow\)/, `${name} should use glass control shadow`)
    assert.match(block, /backdrop-filter:\s*blur\(var\(--glass-blur-control\)\)\s*saturate\(var\(--glass-saturate-control\)\)/, `${name} should use control blur`)
  }

  assert.match(inputFocus, /border-color:\s*var\(--glass-active-border\)/)
  assert.match(inputFocus, layeredBackground('glass-active-material'))
  assert.match(inputFocus, /box-shadow:\s*var\(--glass-active-shadow\)/)

  assert.match(buttonHover, layeredBackground('material-glass-control-hover'))
  assert.match(buttonHover, /border-color:\s*var\(--glass-control-border-hover\)/)
  assert.match(buttonHover, /box-shadow:\s*var\(--glass-control-shadow-hover\)/)

  assert.match(result, /background:\s*var\(--card\)/)
  assert.match(result, /border:\s*1px solid var\(--glass-edge\)/)
  assert.match(result, /box-shadow:\s*var\(--shadow-card\)/)

  assert.doesNotMatch(source, /rgba\(255,\s*255,\s*255|rgba\(255,255,255|var\(--bg-card\)|var\(--bg-card-hover\)|var\(--border\)|var\(--border-light\)|background:\s*var\(--accent\)/)
})

test('legacy library checker glass backgrounds are layered with specular and noise surfaces', () => {
  assert.deepEqual(singleLayerGlassBackgrounds(source), [])
})
