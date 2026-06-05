import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

const source = readFileSync(new URL('./Logs.vue', import.meta.url), 'utf8')

function cssBlock(selector) {
  const searchable = source.replace(/\/\*[\s\S]*?\*\//g, '')
  const blocks = [...searchable.matchAll(/([^{}]+)\{([^{}]*)\}/g)]
    .filter(([, selectors]) => selectors
    .split(',')
    .map(part => part.trim())
    .includes(selector))
    .map(([, , block]) => block)
  assert.ok(blocks.length, `${selector} block should exist in Logs.vue`)
  return blocks.join('\n')
}

function backgroundIncludes(block, token) {
  return new RegExp(`background:[\\s\\S]*var\\(${token}\\)`).test(block)
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
  assert.ok(backgroundIncludes(input, '--material-glass-control'))
  assert.match(input, /box-shadow:\s*var\(--glass-control-shadow\)/)
  assert.match(input, /backdrop-filter:\s*blur\(var\(--glass-blur-control\)\)\s*saturate\(var\(--glass-saturate-control\)\)/)
  assert.ok(backgroundIncludes(inputFocus, '--glass-active-material'))
  assert.match(inputFocus, /border-color:\s*var\(--glass-active-border\)/)
  assert.match(inputFocus, /box-shadow:\s*var\(--glass-active-shadow\)/)

  assert.match(button, /border:\s*1px solid var\(--glass-control-border\)/)
  assert.ok(backgroundIncludes(button, '--material-glass-control'))
  assert.match(button, /box-shadow:\s*var\(--glass-control-shadow\)/)
  assert.match(button, /backdrop-filter:\s*blur\(var\(--glass-blur-control\)\)/)
  assert.ok(backgroundIncludes(buttonHover, '--material-glass-control-hover'))
  assert.match(buttonHover, /box-shadow:\s*var\(--glass-control-shadow-hover\)/)
  assert.ok(backgroundIncludes(primary, '--glass-active-material'))
  assert.match(primary, /box-shadow:\s*var\(--glass-active-shadow\)/)
  assert.match(danger, /background:\s*var\(--surface-specular-edge\),\s*var\(--surface-noise\),\s*var\(--badge-error-bg\)/)
  assert.match(danger, /border-color:\s*var\(--badge-error-border\)/)
  assert.match(danger, /color:\s*var\(--badge-error-text\)/)
  assert.match(dangerHover, /background:\s*var\(--surface-specular-edge-strong\),\s*var\(--surface-noise\),\s*var\(--badge-error-bg\)/)
  assert.match(dangerHover, /border-color:\s*var\(--badge-error-border\)/)

  for (const block of [input, inputFocus, button, buttonHover, danger, dangerHover]) {
    assert.doesNotMatch(block, /var\(--surface-control\)|var\(--surface-control-hover\)|var\(--surface-input-focus\)|#FF375F|rgba\(255,\s*55,\s*95/i)
  }
})

test('logs summary and list surfaces avoid legacy flat cards', () => {
  const summaryItem = cssBlock('.activity-summary-strip > div')
  const container = cssBlock('.logs-container')
  const logItem = cssBlock('.log-item')
  const empty = cssBlock('.loading')
  const paginationButton = cssBlock('.pagination button')
  const paginationHover = cssBlock('.pagination button:hover:not(:disabled)')
  const warningLevel = cssBlock('.level-warning')
  const errorLevel = cssBlock('.level-error')

  assert.match(summaryItem, /border:\s*1px solid var\(--glass-control-border\)/)
  assert.ok(backgroundIncludes(summaryItem, '--material-glass-control'))
  assert.match(summaryItem, /box-shadow:\s*var\(--glass-surface-shadow\)/)
  assert.match(summaryItem, /backdrop-filter:\s*blur\(var\(--glass-blur-surface\)\)/)

  assert.ok(backgroundIncludes(container, '--material-glass-sheet'))
  assert.match(container, /border:\s*1px solid var\(--glass-control-border\)/)
  assert.match(container, /box-shadow:\s*var\(--glass-surface-shadow\)/)
  assert.match(container, /backdrop-filter:\s*blur\(var\(--glass-blur-surface\)\)/)
  assert.doesNotMatch(`${summaryItem}\n${container}`, /var\(--surface-card\)|var\(--bg-card\)|var\(--border\)|var\(--shadow-card\)/)

  assert.match(logItem, /border-bottom:\s*1px solid var\(--glass-control-border\)/)
  assert.match(empty, /background:\s*var\(--surface-specular-edge\),\s*var\(--surface-noise\),\s*var\(--material-glass-subtle\)/)

  assert.ok(backgroundIncludes(paginationButton, '--material-glass-control'))
  assert.match(paginationButton, /border:\s*1px solid var\(--glass-control-border\)/)
  assert.match(paginationButton, /box-shadow:\s*var\(--glass-control-shadow\)/)
  assert.ok(backgroundIncludes(paginationHover, '--material-glass-control-hover'))
  assert.match(paginationHover, /box-shadow:\s*var\(--glass-control-shadow-hover\)/)

  assert.match(warningLevel, /color:\s*var\(--badge-warning-text\)/)
  assert.match(errorLevel, /color:\s*var\(--badge-error-text\)/)
  assert.doesNotMatch(`${paginationButton}\n${paginationHover}\n${warningLevel}\n${errorLevel}`, /var\(--surface-control\)|var\(--surface-control-hover\)|#ff9800|#f44336/i)
})

test('logs buttons mirror hover glass treatment for keyboard focus', () => {
  const toolbarFocus = cssBlock('.toolbar-btn:focus-visible:not(:disabled)')
  const dangerFocus = cssBlock('.toolbar-btn.danger:focus-visible:not(:disabled)')
  const paginationFocus = cssBlock('.pagination button:focus-visible:not(:disabled)')

  for (const block of [toolbarFocus, paginationFocus]) {
    assert.match(block, /outline:\s*none/)
    assert.ok(backgroundIncludes(block, '--material-glass-control-hover'))
    assert.match(block, /border-color:\s*var\(--glass-control-border-hover\)/)
    assert.match(block, /box-shadow:\s*var\(--glass-control-shadow-hover\),\s*var\(--focus-ring\)/)
    assert.match(block, /transform:\s*translateY\(-1px\)/)
  }

  assert.match(dangerFocus, /outline:\s*none/)
  assert.match(dangerFocus, /background:\s*var\(--surface-specular-edge-strong\),\s*var\(--surface-noise\),\s*var\(--badge-error-bg\)/)
  assert.match(dangerFocus, /border-color:\s*var\(--badge-error-border\)/)
  assert.match(dangerFocus, /box-shadow:\s*var\(--glass-control-shadow-hover\),\s*0 0 0 3px color-mix\(in srgb,\s*var\(--badge-error-text\) 18%,\s*transparent\)/)
  assert.doesNotMatch(dangerFocus, /rgba\(var\(--error-rgb\)/)
  assert.match(dangerFocus, /transform:\s*translateY\(-1px\)/)
})

test('logs glass backgrounds are layered with specular and noise surfaces', () => {
  const singleLayerGlass = /^background:\s*var\(--(?:material-glass-subtle|material-glass-control|material-glass-control-hover|material-glass-sheet|glass-active-material)\);$/gm
  assert.doesNotMatch(source, singleLayerGlass)

  const layeredBlocks = [
    cssBlock('.toolbar input'),
    cssBlock('.toolbar input:focus'),
    cssBlock('.toolbar-btn'),
    cssBlock('.toolbar-btn:hover:not(:disabled)'),
    cssBlock('.toolbar-btn.primary'),
    cssBlock('.activity-summary-strip > div'),
    cssBlock('.logs-container'),
    cssBlock('.loading'),
    cssBlock('.pagination button'),
    cssBlock('.pagination button:hover:not(:disabled)'),
  ]

  for (const block of layeredBlocks) {
    assert.match(block, /var\(--surface-specular-edge/)
    assert.match(block, /var\(--surface-noise\)/)
  }
})
