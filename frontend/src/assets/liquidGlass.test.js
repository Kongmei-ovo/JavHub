import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { THEMES } from './themes.js'

const mainCss = readFileSync(new URL('./main.css', import.meta.url), 'utf8')
const search = readFileSync(new URL('../views/Search.vue', import.meta.url), 'utf8')

function cssBlock(selector) {
  const pattern = new RegExp(`${selector.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\s*\\{([\\s\\S]*?)\\n\\}`)
  const match = mainCss.match(pattern)
  assert.ok(match, `${selector} should exist in main.css`)
  return match[1]
}

test('theme materials include refractive liquid glass layers', () => {
  const requiredTokens = [
    '--glass-control-material',
    '--glass-control-material-hover',
    '--glass-card-material',
    '--glass-sheet-material',
    '--glass-control-shadow',
    '--glass-control-shadow-hover',
    '--glass-surface-shadow',
    '--glass-blur-control',
    '--glass-blur-surface',
    '--glass-saturate-control',
  ]

  for (const [key, theme] of Object.entries(THEMES)) {
    for (const token of requiredTokens) {
      assert.ok(theme.vars[token], `${key} should define ${token}`)
    }
    assert.match(theme.vars['--glass-control-material'], /linear-gradient/)
    assert.match(theme.vars['--glass-control-shadow'], /inset 0 1px 0/)
  }

  assert.notEqual(THEMES['apple-dark'].vars['--glass-control-bg'], 'rgba(255, 255, 255, 0.060)')
  assert.match(THEMES['apple-dark'].vars['--glass-control-bg'], /rgba\(18,\s*19,\s*21,\s*0\.36\)/)
  assert.match(THEMES['apple-light'].vars['--glass-control-shadow'], /0 10px 26px/)
})

test('global controls use shared liquid glass material instead of flat tint', () => {
  assert.match(cssBlock('.btn-ghost'), /background:\s*var\(--material-glass-control\)/)
  assert.match(cssBlock('.btn-ghost'), /box-shadow:\s*var\(--glass-control-shadow\)/)
  assert.match(cssBlock('.glass-select__button'), /background:\s*var\(--material-glass-control, var\(--glass-control-bg/)
  assert.match(cssBlock('.glass-select__menu'), /background:\s*var\(--material-glass-sheet\)/)
  assert.match(cssBlock('.apple-surface'), /background:\s*var\(--surface-card\)/)
  assert.match(cssBlock('.apple-surface'), /box-shadow:\s*var\(--glass-surface-shadow\)/)
  assert.match(search, /\.sort-pill\s*\{[\s\S]*background:\s*var\(--surface-control\)[\s\S]*box-shadow:\s*var\(--glass-control-shadow\)[\s\S]*backdrop-filter:\s*blur\(var\(--glass-blur-control\)\)/)
  assert.match(search, /\.filter-item\s*\{[\s\S]*background:\s*var\(--surface-control\)[\s\S]*box-shadow:\s*var\(--glass-control-shadow\)[\s\S]*backdrop-filter:\s*blur\(var\(--glass-blur-control\)\)/)
})
