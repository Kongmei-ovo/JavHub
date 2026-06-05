import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

const source = readFileSync(new URL('./MagnetParse.vue', import.meta.url), 'utf8')

function cssBlocks(content, selector) {
  const blocks = [...content.matchAll(/([^{}]+)\{([^{}]*)\}/g)]
    .filter(([, selectors]) => selectors
      .split(',')
      .map(part => part.trim())
      .includes(selector))
    .map(([, , block]) => block)
  assert.ok(blocks.length, `${selector} block should exist`)
  return blocks
}

function cssBlock(content, selector) {
  return cssBlocks(content, selector).join('\n')
}

function backgroundIncludes(block, token) {
  return new RegExp(`background:[\\s\\S]*var\\(${token}\\)`).test(block)
}

function assertLayeredSubtle(block) {
  assert.ok(backgroundIncludes(block, '--material-glass-subtle'))
  assert.match(block, /var\(--surface-specular-edge/)
  assert.match(block, /var\(--surface-noise\)/)
}

test('magnet parser workspace uses shared Apple glass surfaces', () => {
  const parseConsole = cssBlock(source, '.parse-console')
  const summaryItem = cssBlock(source, '.summary-item')
  const magnetsCard = cssBlock(source, '.magnets-card')
  const magnetsHeader = cssBlock(source, '.magnets-header')
  const magnetsList = cssBlock(source, '.magnets-list')
  const magnetRow = cssBlock(source, '.magnet-row')
  const magnetRowEven = cssBlock(source, '.magnet-row:nth-child(even)')
  const magnetRowHover = cssBlock(source, '.magnet-row:hover')
  const magnetIndex = cssBlock(source, '.magnet-index')
  const statusPill = cssBlock(source, '.status-pill')
  const issuePanel = cssBlock(source, '.issue-panel')
  const issueRow = cssBlock(source, '.issue-row')
  const emptyState = cssBlock(source, '.empty-state')

  for (const block of [parseConsole, summaryItem, magnetsCard, magnetsHeader, magnetsList, magnetRow, magnetRowEven, magnetRowHover, magnetIndex, statusPill, issuePanel, issueRow, emptyState]) {
    assert.doesNotMatch(block, /var\(--surface-card\)|var\(--bg-card\)|var\(--bg-secondary\)|var\(--border\)|var\(--border-light\)|var\(--shadow-card\)|var\(--transition\)/)
  }

  assert.ok(backgroundIncludes(parseConsole, '--material-glass-sheet'))
  assert.match(parseConsole, /border:\s*1px solid var\(--glass-edge\)/)
  assert.match(parseConsole, /box-shadow:\s*var\(--glass-surface-shadow\)/)

  assertLayeredSubtle(summaryItem)
  assert.match(summaryItem, /border:\s*1px solid var\(--glass-control-border\)/)
  assert.match(summaryItem, /box-shadow:\s*var\(--glass-inner-shadow\)/)

  assert.ok(backgroundIncludes(magnetsCard, '--material-glass-sheet'))
  assert.match(magnetsCard, /border:\s*1px solid var\(--glass-edge\)/)
  assert.match(magnetsCard, /box-shadow:\s*var\(--glass-surface-shadow\)/)
  assert.match(magnetsHeader, /border-bottom:\s*1px solid var\(--glass-edge\)/)
  assert.match(magnetsList, /gap:\s*8px/)

  assert.ok(backgroundIncludes(magnetRow, '--material-glass-control'))
  assert.match(magnetRow, /border:\s*1px solid var\(--glass-control-border\)/)
  assert.match(magnetRow, /box-shadow:\s*var\(--glass-control-shadow\)/)
  assert.match(magnetRow, /transition:\s*background var\(--motion-fast\)/)
  assert.ok(backgroundIncludes(magnetRowEven, '--material-glass-control'))
  assert.ok(backgroundIncludes(magnetRowHover, '--material-glass-control-hover'))
  assert.match(magnetRowHover, /border-color:\s*var\(--glass-control-border-hover\)/)
  assert.match(magnetRowHover, /box-shadow:\s*var\(--glass-control-shadow-hover\)/)

  assertLayeredSubtle(magnetIndex)
  assert.match(magnetIndex, /border:\s*1px solid var\(--glass-control-border\)/)
  assert.match(statusPill, /border:\s*1px solid var\(--glass-control-border\)/)
  assertLayeredSubtle(statusPill)
  assert.ok(backgroundIncludes(issuePanel, '--material-glass-sheet'))
  assert.match(issuePanel, /border:\s*1px solid var\(--badge-warning-border\)/)
  assert.match(issuePanel, /box-shadow:\s*var\(--glass-surface-shadow\)/)
  assertLayeredSubtle(issueRow)
  assert.match(issueRow, /border:\s*1px solid var\(--glass-control-border\)/)
  assertLayeredSubtle(emptyState)
  assert.match(emptyState, /border:\s*1px solid var\(--glass-control-border\)/)
})

test('magnet parser glass backgrounds are layered with specular and noise surfaces', () => {
  const singleLayerGlass = /^background:\s*var\(--(?:material-glass-control|material-glass-control-hover|material-glass-sheet|material-glass-subtle)\);$/gm
  assert.doesNotMatch(source, singleLayerGlass)

  const layeredBlocks = [
    cssBlock(source, '.parse-console'),
    cssBlock(source, '.summary-item'),
    cssBlock(source, '.magnets-card'),
    cssBlock(source, '.magnet-row'),
    cssBlock(source, '.magnet-row:nth-child(even)'),
    cssBlock(source, '.magnet-row:hover'),
    cssBlock(source, '.magnet-index'),
    cssBlock(source, '.status-pill'),
    cssBlock(source, '.issue-panel'),
    cssBlock(source, '.issue-row'),
    cssBlock(source, '.empty-state'),
  ]

  for (const block of layeredBlocks) {
    assert.match(block, /var\(--surface-specular-edge/)
    assert.match(block, /var\(--surface-noise\)/)
  }
})
