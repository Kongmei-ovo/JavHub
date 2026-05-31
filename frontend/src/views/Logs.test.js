import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

const source = readFileSync(new URL('./Logs.vue', import.meta.url), 'utf8')

function cssBlock(selector) {
  const blocks = [...source.matchAll(/([^{}]+)\{([^{}]*)\}/g)]
  const match = blocks.find(([, selectors]) => selectors
    .split(',')
    .map(part => part.trim())
    .includes(selector))
  assert.ok(match, `${selector} block should exist in Logs.vue`)
  return match[2]
}

test('logs toolbar uses shared liquid glass controls', () => {
  const input = cssBlock('.toolbar input')
  const inputFocus = cssBlock('.toolbar input:focus')
  const button = cssBlock('.toolbar-btn')
  const buttonHover = cssBlock('.toolbar-btn:hover:not(:disabled)')
  const primary = cssBlock('.toolbar-btn.primary')
  const danger = cssBlock('.toolbar-btn.danger')
  const dangerHover = cssBlock('.toolbar-btn.danger:hover:not(:disabled)')

  assert.match(input, /border:\s*1px solid var\(--glass-control-border\)/)
  assert.match(input, /background:\s*var\(--surface-control\)/)
  assert.match(input, /box-shadow:\s*var\(--glass-control-shadow\)/)
  assert.match(input, /backdrop-filter:\s*blur\(var\(--glass-blur-control\)\)\s*saturate\(var\(--glass-saturate-control\)\)/)
  assert.match(inputFocus, /background:\s*var\(--surface-input-focus\)/)
  assert.match(inputFocus, /box-shadow:\s*var\(--glass-active-shadow\)/)

  assert.match(button, /border:\s*1px solid var\(--glass-control-border\)/)
  assert.match(button, /background:\s*var\(--surface-control\)/)
  assert.match(button, /box-shadow:\s*var\(--glass-control-shadow\)/)
  assert.match(button, /backdrop-filter:\s*blur\(var\(--glass-blur-control\)\)/)
  assert.match(buttonHover, /background:\s*var\(--surface-control-hover\)/)
  assert.match(buttonHover, /box-shadow:\s*var\(--glass-control-shadow-hover\)/)
  assert.match(primary, /background:\s*var\(--glass-active-material\)/)
  assert.match(primary, /box-shadow:\s*var\(--glass-active-shadow\)/)
  assert.match(danger, /background:\s*var\(--surface-control\)/)
  assert.match(danger, /box-shadow:\s*var\(--glass-control-shadow\)/)
  assert.match(dangerHover, /background:\s*var\(--surface-control-hover\)/)
})

test('logs summary and list surfaces avoid legacy flat cards', () => {
  const summaryItem = cssBlock('.activity-summary-strip > div')
  const container = cssBlock('.logs-container')
  const logItem = cssBlock('.log-item')
  const empty = cssBlock('.loading')
  const paginationButton = cssBlock('.pagination button')
  const paginationHover = cssBlock('.pagination button:hover:not(:disabled)')

  assert.match(summaryItem, /border:\s*1px solid var\(--glass-control-border\)/)
  assert.match(summaryItem, /background:\s*var\(--surface-card\)/)
  assert.match(summaryItem, /box-shadow:\s*var\(--glass-surface-shadow\)/)
  assert.match(summaryItem, /backdrop-filter:\s*blur\(var\(--glass-blur-surface\)\)/)

  assert.match(container, /background:\s*var\(--surface-card\)/)
  assert.match(container, /border:\s*1px solid var\(--glass-control-border\)/)
  assert.match(container, /box-shadow:\s*var\(--glass-surface-shadow\)/)
  assert.match(container, /backdrop-filter:\s*blur\(var\(--glass-blur-surface\)\)/)
  assert.doesNotMatch(container, /var\(--bg-card\)|var\(--border\)|var\(--shadow-card\)/)

  assert.match(logItem, /border-bottom:\s*1px solid var\(--glass-control-border\)/)
  assert.match(empty, /background:\s*var\(--material-glass-subtle\)/)

  assert.match(paginationButton, /background:\s*var\(--surface-control\)/)
  assert.match(paginationButton, /border:\s*1px solid var\(--glass-control-border\)/)
  assert.match(paginationButton, /box-shadow:\s*var\(--glass-control-shadow\)/)
  assert.match(paginationHover, /background:\s*var\(--surface-control-hover\)/)
  assert.match(paginationHover, /box-shadow:\s*var\(--glass-control-shadow-hover\)/)
})
