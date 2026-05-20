import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { THEMES } from './themes.js'

const mainCss = readFileSync(new URL('./main.css', import.meta.url), 'utf8')

function rootToken(name) {
  const match = mainCss.match(new RegExp(`${name}:\\s*([^;]+);`))
  assert.ok(match, `${name} should be defined in main.css`)
  return match[1].trim()
}

function pxValue(value) {
  const match = value.match(/^([0-9.]+)px$/)
  assert.ok(match, `${value} should be a fixed px value`)
  return Number(match[1])
}

test('desktop page title scale stays below display scale', () => {
  const displaySize = pxValue(rootToken('--type-display'))
  const pageTitleSize = pxValue(rootToken('--page-title-size'))

  assert.ok(pageTitleSize >= 34 && pageTitleSize <= 44)
  assert.ok(pageTitleSize < displaySize)
})

test('desktop layout tokens are sized for a dense app shell', () => {
  assert.ok(pxValue(rootToken('--sidebar-width')) <= 228)
  assert.ok(pxValue(rootToken('--touch-target')) <= 42)
  assert.ok(pxValue(rootToken('--radius-card')) <= 24)
})

test('runtime themes keep the same desktop scale tokens', () => {
  const sharedTokens = [
    '--page-title-size',
    '--page-title-line',
    '--sidebar-width',
    '--touch-target',
    '--radius-card',
  ]

  for (const [key, theme] of Object.entries(THEMES)) {
    for (const token of sharedTokens) {
      assert.equal(theme.vars[token], rootToken(token), `${key} ${token} should match main.css`)
    }
  }
})
