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
  assert.match(block, /background:\s*var\(--card\)/)
  assert.doesNotMatch(block, /var\(--surface-specular-edge|var\(--surface-noise\)/)
  assert.doesNotMatch(block, /var\(--surface-specular-edge|var\(--surface-noise\)/)
}

function assertLayeredBackground(block, token, label) {
  assert.ok(backgroundIncludes(block, token), `${label} should include ${token}`)
  assert.match(block, /var\(--surface-specular-edge/, `${label} should include specular edge`)
  assert.match(block, /var\(--surface-noise\)/, `${label} should include surface noise`)
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

  for (const block of [parseConsole, summaryItem, magnetsCard, magnetsHeader, magnetsList, magnetRow, magnetRowEven, magnetRowHover, magnetIndex, statusPill, issuePanel, issueRow]) {
    assert.doesNotMatch(block, /var\(--surface-card\)|var\(--bg-card\)|var\(--bg-secondary\)|var\(--border\)|var\(--border-light\)|var\(--transition\)/)
  }

  assert.match(parseConsole, /background:\s*var\(--card\)/)
  assert.match(parseConsole, /border:\s*1px solid var\(--glass-edge\)/)
  assert.match(parseConsole, /box-shadow:\s*var\(--shadow-card\)/)

  assertLayeredSubtle(summaryItem)
  assert.match(summaryItem, /border:\s*1px solid var\(--hairline\)/)
  assert.match(summaryItem, /box-shadow:\s*none/)

  assert.match(magnetsCard, /background:\s*var\(--card\)/)
  assert.match(magnetsCard, /border:\s*1px solid var\(--glass-edge\)/)
  assert.match(magnetsCard, /box-shadow:\s*var\(--shadow-card\)/)
  assert.match(magnetsHeader, /border-bottom:\s*1px solid var\(--glass-edge\)/)
  assert.match(magnetsList, /gap:\s*8px/)

  assert.ok(backgroundIncludes(magnetRow, '--material-glass-control'))
  assert.match(magnetRow, /border:\s*1px solid var\(--glass-control-border\)/)
  assert.match(magnetRow, /box-shadow:\s*var\(--glass-control-shadow\)/)
  assert.match(magnetRow, /transition:\s*transform var\(--motion-fast\),\s*opacity var\(--motion-fast\)/)
  assert.doesNotMatch(magnetRow, /transition:[^;]*(?:background|border-color|box-shadow|color|filter|backdrop-filter)/)
  assert.ok(backgroundIncludes(magnetRowEven, '--material-glass-control'))
  assert.ok(backgroundIncludes(magnetRowHover, '--material-glass-control-hover'))
  assert.match(magnetRowHover, /border-color:\s*var\(--glass-control-border-hover\)/)
  assert.match(magnetRowHover, /box-shadow:\s*var\(--glass-control-shadow-hover\)/)

  assertLayeredSubtle(magnetIndex)
  assert.match(magnetIndex, /border:\s*1px solid var\(--hairline\)/)
  assert.match(statusPill, /border:\s*1px solid var\(--hairline\)/)
  assertLayeredSubtle(statusPill)
  assert.match(issuePanel, /background:\s*var\(--card\)/)
  assert.match(issuePanel, /border:\s*1px solid var\(--badge-warning-border\)/)
  assert.match(issuePanel, /box-shadow:\s*var\(--shadow-card\)/)
  assertLayeredSubtle(issueRow)
  assert.match(issueRow, /border:\s*1px solid var\(--hairline\)/)
  assert.match(source, /<AppleEmptyState/)
  assert.match(source, /class="parse-empty-state"/)
  assert.match(source, /action-label="重新解析"/)
  assert.match(source, /secondary-action-label="清空输入"/)
})

test('magnet rows mirror hover glass treatment while child actions are focused', () => {
  const magnetRowFocus = cssBlock(source, '.magnet-row:focus-within')

  assert.ok(backgroundIncludes(magnetRowFocus, '--material-glass-control-hover'))
  assert.match(magnetRowFocus, /border-color:\s*var\(--glass-control-border-hover\)/)
  assert.match(magnetRowFocus, /box-shadow:\s*var\(--glass-control-shadow-hover\),\s*var\(--focus-ring\)/)
  assert.match(magnetRowFocus, /transform:\s*translateY\(-1px\)/)
})

test('magnet parser semantic status surfaces use layered glass badge materials', () => {
  const summarySuccess = cssBlock(source, '.summary-item.success')
  const summaryWarning = cssBlock(source, '.summary-item.warning')
  const summaryDanger = cssBlock(source, '.summary-item.danger')
  const statusSuccess = cssBlock(source, '.status-pill.success')
  const statusDanger = cssBlock(source, '.status-pill.danger')
  const rowAdded = cssBlock(source, '.magnet-row.added')

  assertLayeredBackground(summarySuccess, '--badge-success-bg', 'summary success')
  assert.match(summarySuccess, /border-color:\s*var\(--badge-success-border\)/)

  assertLayeredBackground(summaryWarning, '--badge-warning-bg', 'summary warning')
  assert.match(summaryWarning, /border-color:\s*var\(--badge-warning-border\)/)

  assertLayeredBackground(summaryDanger, '--badge-error-bg', 'summary danger')
  assert.match(summaryDanger, /border-color:\s*var\(--badge-error-border\)/)

  assertLayeredBackground(statusSuccess, '--badge-success-bg', 'status success')
  assert.match(statusSuccess, /color:\s*var\(--badge-success-text\)/)
  assert.match(statusSuccess, /border-color:\s*var\(--badge-success-border\)/)

  assertLayeredBackground(statusDanger, '--badge-error-bg', 'status danger')
  assert.match(statusDanger, /color:\s*var\(--badge-error-text\)/)
  assert.match(statusDanger, /border-color:\s*var\(--badge-error-border\)/)

  assertLayeredBackground(rowAdded, '--badge-success-bg', 'added magnet row')
})

test('magnet parser glass backgrounds are layered with specular and noise surfaces', () => {
  const singleLayerGlass = /^background:\s*var\(--(?:material-glass-control|material-glass-control-hover|material-glass-sheet|material-glass-subtle)\);$/gm
  assert.doesNotMatch(source, singleLayerGlass)
  assert.match(source, /<AppleEmptyState[\s\S]*class="parse-empty-state"[\s\S]*next-step=/)
  assert.match(source, /@action="parseMagnets"/)
  assert.match(source, /@secondary-action="clearAll"/)

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
  ]

  for (const block of layeredBlocks) {
    // v2：实底块不得有玻璃分层；仍是玻璃的块必须分层完整
    if (/background:\s*var\(--card\b/.test(block)) {
      assert.doesNotMatch(block, /var\(--surface-specular-edge|var\(--surface-noise\)/)
    } else if (/var\(--material-glass|var\(--glass-active-material\)/.test(block)) {
      assert.match(block, /var\(--surface-specular-edge/)
      assert.match(block, /var\(--surface-noise\)/)
    }
  }
})
