import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

const source = readFileSync(new URL('./Duplicates.vue', import.meta.url), 'utf8')

function cssBlocks(content, selector) {
  const blocks = [...content.matchAll(/([^{}]+)\{([^{}]*)\}/g)]
    .filter(([, selectors]) => selectors
      .replace(/\/\*[\s\S]*?\*\//g, '')
      .split(',')
      .map(part => part.trim())
      .includes(selector))
    .map(([, , block]) => block)
  assert.ok(blocks.length, `${selector} block should exist`)
  return blocks
}

function cssBlock(selector) {
  return cssBlocks(source, selector).join('\n')
}

function backgroundIncludes(block, token) {
  return new RegExp(`background:\\s*(?:[^;]*,\\s*)*var\\(${token}\\)(?:\\s*,[^;]*)?;`).test(block)
}

function singleLayerGlassBackgrounds(css) {
  const singleLayerGlass = /^background:\s*var\(--(?:material-glass-control|material-glass-control-hover|material-glass-elevated|material-glass-sheet|glass-active-material)\);$/gm
  return [...css.matchAll(singleLayerGlass)].map(match => match[0])
}

test('duplicates page uses shared Apple glass surfaces and actions', () => {
  const rescanButton = cssBlock('.rescan-btn')
  const duplicateItem = cssBlock('.duplicate-item')
  const duplicateEntry = cssBlock('.duplicate-entry')
  const actionButton = cssBlock('.action-btn')
  const deleteButton = cssBlock('.action-btn.delete')
  const ignoreButton = cssBlock('.action-btn.ignore')
  const stateBlock = cssBlock('.loading')
  const errorBlock = cssBlock('.error')

  for (const block of [rescanButton, duplicateItem, duplicateEntry, actionButton, ignoreButton, stateBlock]) {
    assert.match(block, /border:\s*1px solid var\(--glass-control-border\)/)
    assert.ok(backgroundIncludes(block, '--material-glass-control'))
    assert.match(block, /box-shadow:\s*var\(--glass-control-shadow\)/)
    assert.match(block, /backdrop-filter:\s*blur\(var\(--glass-blur-control\)\)\s*saturate\(var\(--glass-saturate-control\)\)/)
    assert.doesNotMatch(block, /border:\s*(?:0|none)|background:\s*(?:none|transparent)/)
  }

  assert.match(deleteButton, /border-color:\s*var\(--badge-error-border\)/)
  assert.match(deleteButton, /background:\s*var\(--badge-error-bg\)/)
  assert.match(deleteButton, /color:\s*var\(--badge-error-text\)/)
  assert.doesNotMatch(deleteButton, /#fff|#ffffff|#ff4d4f/i)

  assert.match(errorBlock, /color:\s*var\(--badge-error-text\)/)
  assert.doesNotMatch(errorBlock, /#ff4d4f/i)
})

test('duplicates keyboard focus mirrors hover glass treatment', () => {
  const rescanFocus = cssBlock('.rescan-btn:focus-visible')
  const actionFocus = cssBlock('.action-btn:focus-visible')
  const deleteFocus = cssBlock('.action-btn.delete:focus-visible')
  const entryFocus = cssBlock('.duplicate-entry:focus-within')

  for (const block of [rescanFocus, actionFocus]) {
    assert.match(block, /outline:\s*none/)
    assert.ok(backgroundIncludes(block, '--material-glass-control-hover'))
    assert.match(block, /border-color:\s*var\(--glass-control-border-hover\)/)
    assert.match(block, /box-shadow:\s*var\(--glass-control-shadow-hover\),\s*0 0 0 3px rgba\(var\(--accent-rgb\),\s*0\.12\)/)
    assert.match(block, /transform:\s*translateY\(-1px\)/)
  }

  assert.match(deleteFocus, /outline:\s*none/)
  assert.match(deleteFocus, /background:\s*var\(--badge-error-bg\)/)
  assert.match(deleteFocus, /border-color:\s*var\(--badge-error-border\)/)
  assert.match(deleteFocus, /box-shadow:\s*var\(--glass-control-shadow-hover\),\s*0 0 0 3px rgba\(var\(--error-rgb\),\s*0\.16\)/)

  assert.ok(backgroundIncludes(entryFocus, '--material-glass-control-hover'))
  assert.match(entryFocus, /border-color:\s*var\(--glass-control-border-hover\)/)
  assert.match(entryFocus, /box-shadow:\s*var\(--glass-control-shadow-hover\),\s*0 0 0 3px rgba\(var\(--accent-rgb\),\s*0\.1\)/)
  assert.match(entryFocus, /transform:\s*translateY\(-1px\)/)
})

test('duplicates glass backgrounds are layered with specular and noise surfaces', () => {
  assert.deepEqual(singleLayerGlassBackgrounds(source), [])

  for (const selector of [
    '.rescan-btn',
    '.rescan-btn:hover',
    '.duplicate-item',
    '.duplicate-entry',
    '.action-btn',
    '.action-btn:hover',
    '.action-btn.ignore',
    '.loading',
  ]) {
    const block = cssBlock(selector)
    assert.match(block, /var\(--surface-specular-edge/)
    assert.match(block, /var\(--surface-noise\)/)
  }
})
