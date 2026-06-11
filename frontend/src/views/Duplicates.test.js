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

test('duplicates page keeps glass actions over solid duplicate content', () => {
  const rescanButton = cssBlock('.rescan-btn')
  const duplicateItem = cssBlock('.duplicate-item')
  const duplicateEntry = cssBlock('.duplicate-entry')
  const actionButton = cssBlock('.action-btn')
  const deleteButton = cssBlock('.action-btn.delete')
  const deleteButtonHover = cssBlock('.action-btn.delete:hover')
  const ignoreButton = cssBlock('.action-btn.ignore')
  const stateBlock = cssBlock('.loading')
  const errorBlock = cssBlock('.error')

  for (const block of [rescanButton, actionButton, ignoreButton]) {
    assert.match(block, /border:\s*1px solid var\(--glass-control-border\)/)
    assert.ok(backgroundIncludes(block, '--material-glass-control'))
    assert.match(block, /box-shadow:\s*var\(--glass-control-shadow\)/)
    assert.match(block, /backdrop-filter:\s*blur\(var\(--glass-blur-control\)\)\s*saturate\(var\(--glass-saturate-control\)\)/)
    assert.doesNotMatch(block, /border:\s*(?:0|none)|background:\s*(?:none|transparent)/)
  }

  assert.match(duplicateItem, /border:\s*1px solid var\(--hairline\)/)
  assert.match(duplicateItem, /background:\s*var\(--card\)/)
  assert.match(duplicateItem, /box-shadow:\s*var\(--shadow-card\)/)
  assert.doesNotMatch(duplicateItem, /material-glass|surface-specular-edge|surface-noise|backdrop-filter/)

  assert.match(duplicateEntry, /border:\s*1px solid var\(--hairline\)/)
  assert.match(duplicateEntry, /background:\s*var\(--card-2\)/)
  assert.match(duplicateEntry, /box-shadow:\s*none/)
  assert.doesNotMatch(duplicateEntry, /material-glass|surface-specular-edge|surface-noise|backdrop-filter/)

  assert.match(stateBlock, /border:\s*1px solid var\(--hairline\)/)
  assert.match(stateBlock, /background:\s*var\(--card\)/)
  assert.match(stateBlock, /box-shadow:\s*var\(--shadow-card\)/)
  assert.doesNotMatch(stateBlock, /material-glass|surface-specular-edge|surface-noise|backdrop-filter/)

  assert.match(deleteButton, /border-color:\s*var\(--badge-error-border\)/)
  assert.ok(backgroundIncludes(deleteButton, '--badge-error-bg'))
  assert.match(deleteButton, /var\(--surface-specular-edge\)/)
  assert.match(deleteButton, /var\(--surface-noise\)/)
  assert.match(deleteButton, /color:\s*var\(--badge-error-text\)/)
  assert.ok(backgroundIncludes(deleteButtonHover, '--badge-error-bg'))
  assert.match(deleteButtonHover, /var\(--surface-specular-edge-strong\)/)
  assert.match(deleteButtonHover, /var\(--surface-noise\)/)
  assert.match(deleteButtonHover, /border-color:\s*var\(--badge-error-border\)/)
  assert.doesNotMatch(deleteButton, /#fff|#ffffff|#ff4d4f/i)

  assert.match(errorBlock, /color:\s*var\(--badge-error-text\)/)
  assert.doesNotMatch(errorBlock, /#ff4d4f/i)
})

test('duplicates keyboard focus keeps content rows solid and actions glassy', () => {
  const rescanFocus = cssBlock('.rescan-btn:focus-visible')
  const actionFocus = cssBlock('.action-btn:focus-visible')
  const deleteFocus = cssBlock('.action-btn.delete:focus-visible')
  const entryFocus = cssBlock('.duplicate-entry:focus-within')

  for (const block of [rescanFocus, actionFocus]) {
    assert.match(block, /outline:\s*none/)
    assert.ok(backgroundIncludes(block, '--material-glass-control-hover'))
    assert.match(block, /border-color:\s*var\(--glass-control-border-hover\)/)
    assert.match(block, /box-shadow:\s*var\(--glass-control-shadow-hover\),\s*var\(--focus-ring\)/)
    assert.match(block, /transform:\s*translateY\(-1px\)/)
  }

  assert.match(deleteFocus, /outline:\s*none/)
  assert.ok(backgroundIncludes(deleteFocus, '--badge-error-bg'))
  assert.match(deleteFocus, /var\(--surface-specular-edge-strong\)/)
  assert.match(deleteFocus, /var\(--surface-noise\)/)
  assert.match(deleteFocus, /border-color:\s*var\(--badge-error-border\)/)
  assert.match(deleteFocus, /box-shadow:\s*var\(--glass-control-shadow-hover\),\s*0 0 0 3px color-mix\(in srgb,\s*var\(--badge-error-text\) 18%,\s*transparent\)/)
  assert.doesNotMatch(deleteFocus, /rgba\(var\(--error-rgb\)/)

  assert.match(entryFocus, /background:\s*var\(--card-hover\)/)
  assert.match(entryFocus, /border-color:\s*var\(--hairline-strong\)/)
  assert.match(entryFocus, /box-shadow:\s*var\(--focus-ring\)/)
  assert.doesNotMatch(entryFocus, /material-glass|surface-specular-edge|surface-noise|backdrop-filter/)
  assert.match(entryFocus, /transform:\s*translateY\(-1px\)/)
})

test('duplicates glass backgrounds are layered with specular and noise surfaces', () => {
  assert.deepEqual(singleLayerGlassBackgrounds(source), [])

  for (const selector of [
    '.rescan-btn',
    '.rescan-btn:hover',
    '.action-btn',
    '.action-btn:hover',
    '.action-btn.delete',
    '.action-btn.delete:hover',
    '.action-btn.delete:focus-visible',
    '.action-btn.ignore',
  ]) {
    const block = cssBlock(selector)
    assert.match(block, /var\(--surface-specular-edge/)
    assert.match(block, /var\(--surface-noise\)/)
  }

  for (const selector of ['.duplicate-item', '.duplicate-entry', '.loading']) {
    const block = cssBlock(selector)
    assert.doesNotMatch(block, /var\(--surface-specular-edge|var\(--surface-noise\)|var\(--material-glass|backdrop-filter/)
  }
})
