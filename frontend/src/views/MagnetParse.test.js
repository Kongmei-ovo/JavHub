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

  assert.match(parseConsole, /background:\s*var\(--material-glass-sheet\)/)
  assert.match(parseConsole, /border:\s*1px solid var\(--glass-edge\)/)
  assert.match(parseConsole, /box-shadow:\s*var\(--glass-surface-shadow\)/)

  assert.match(summaryItem, /background:\s*var\(--material-glass-subtle\)/)
  assert.match(summaryItem, /border:\s*1px solid var\(--glass-control-border\)/)
  assert.match(summaryItem, /box-shadow:\s*var\(--glass-inner-shadow\)/)

  assert.match(magnetsCard, /background:\s*var\(--material-glass-sheet\)/)
  assert.match(magnetsCard, /border:\s*1px solid var\(--glass-edge\)/)
  assert.match(magnetsCard, /box-shadow:\s*var\(--glass-surface-shadow\)/)
  assert.match(magnetsHeader, /border-bottom:\s*1px solid var\(--glass-edge\)/)
  assert.match(magnetsList, /gap:\s*8px/)

  assert.match(magnetRow, /background:\s*var\(--material-glass-control\)/)
  assert.match(magnetRow, /border:\s*1px solid var\(--glass-control-border\)/)
  assert.match(magnetRow, /box-shadow:\s*var\(--glass-control-shadow\)/)
  assert.match(magnetRow, /transition:\s*background var\(--motion-fast\)/)
  assert.match(magnetRowEven, /background:\s*var\(--material-glass-control\)/)
  assert.match(magnetRowHover, /background:\s*var\(--material-glass-control-hover\)/)
  assert.match(magnetRowHover, /border-color:\s*var\(--glass-control-border-hover\)/)
  assert.match(magnetRowHover, /box-shadow:\s*var\(--glass-control-shadow-hover\)/)

  assert.match(magnetIndex, /background:\s*var\(--material-glass-subtle\)/)
  assert.match(magnetIndex, /border:\s*1px solid var\(--glass-control-border\)/)
  assert.match(statusPill, /border:\s*1px solid var\(--glass-control-border\)/)
  assert.match(statusPill, /background:\s*var\(--material-glass-subtle\)/)
  assert.match(issuePanel, /background:\s*var\(--material-glass-sheet\)/)
  assert.match(issuePanel, /border:\s*1px solid var\(--badge-warning-border\)/)
  assert.match(issuePanel, /box-shadow:\s*var\(--glass-surface-shadow\)/)
  assert.match(issueRow, /background:\s*var\(--material-glass-subtle\)/)
  assert.match(issueRow, /border:\s*1px solid var\(--glass-control-border\)/)
  assert.match(emptyState, /background:\s*var\(--material-glass-subtle\)/)
  assert.match(emptyState, /border:\s*1px solid var\(--glass-control-border\)/)
})
