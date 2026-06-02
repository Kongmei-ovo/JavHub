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
    assert.match(block, /background:\s*var\(--material-glass-control\)/)
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
