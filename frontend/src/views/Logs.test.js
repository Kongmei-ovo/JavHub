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

  assert.match(summaryItem, /border:\s*1px solid var\(--hairline\)/)
  assert.match(summaryItem, /background:\s*var\(--card\)/)
  assert.match(summaryItem, /box-shadow:\s*var\(--shadow-card\)/)
  assert.doesNotMatch(summaryItem, /backdrop-filter/)

  assert.match(container, /background:\s*var\(--card\)/)
  assert.match(container, /border:\s*1px solid var\(--hairline\)/)
  assert.match(container, /box-shadow:\s*var\(--shadow-card\)/)
  assert.doesNotMatch(container, /backdrop-filter/)
  assert.doesNotMatch(`${summaryItem}\n${container}`, /var\(--surface-card\)|var\(--bg-card\)|var\(--border\)/)

  assert.match(logItem, /border-bottom:\s*1px solid var\(--glass-control-border\)/)
  assert.match(empty, /background:\s*var\(--card\)/)

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

test('logs page reads as a dense console instead of an activity landing page', () => {
  assert.match(source, /class="logs-control-panel apple-surface"/)
  assert.match(source, /class="log-table-head"/)
  assert.match(source, /class="logs-container" role="table"/)
  assert.match(source, /class="log-list"/)
  assert.match(source, /:class="\{ 'is-loading-more': loading \}"/)
  assert.match(source, /role="rowgroup"/)
  assert.match(source, /class="'log-item level-' \+ log\.level\.toLowerCase\(\)"\s+role="row"/)

  const header = cssBlock('.activity-header')
  const title = cssBlock('.logs h1')
  const controlPanel = cssBlock('.logs-control-panel')
  const toolbar = cssBlock('.toolbar')
  const summary = cssBlock('.activity-summary-strip')
  const tableHead = cssBlock('.log-table-head')
  const logItem = cssBlock('.log-item')
  const logTime = cssBlock('.log-time')
  const logLevel = cssBlock('.log-level')

  assert.match(header, /min-height:\s*72px/)
  assert.match(header, /padding:\s*12px/)
  assert.match(title, /font-size:\s*var\(--type-workbench-title\)/)
  assert.match(controlPanel, /display:\s*grid/)
  assert.match(controlPanel, /grid-template-columns:\s*minmax\(280px,\s*1fr\)\s*minmax\(300px,\s*0\.72fr\)/)
  assert.match(toolbar, /margin:\s*0/)
  assert.match(summary, /margin:\s*0/)
  for (const block of [tableHead, logItem]) {
    assert.match(block, /grid-template-columns:\s*(?:4px )?168px 76px minmax\(0,\s*1fr\)/)
  }
  assert.match(tableHead, /position:\s*sticky/)
  assert.match(logItem, /min-height:\s*34px/)
  assert.match(logItem, /padding:\s*7px 12px/)
  assert.match(logTime, /font-variant-numeric:\s*tabular-nums/)
  assert.match(logLevel, /justify-content:\s*center/)
})

test('logs console rows expose calm status badges and scan states', () => {
  const tableHead = cssBlock('.log-table-head')
  const logItemHover = cssBlock('.log-item:hover')
  const logItemLevel = cssBlock('.log-item::before')
  const logLevel = cssBlock('.log-level')
  const warningLevel = cssBlock('.log-level.level-warning')
  const errorLevel = cssBlock('.log-level.level-error')
  const infoLevel = cssBlock('.log-level.level-info')

  assert.match(tableHead, /box-shadow:\s*var\(--glass-inner-shadow\)/)
  assert.match(logItemHover, /background:\s*var\(--surface-specular-edge\),\s*var\(--surface-noise\),\s*var\(--material-glass-control-hover\)/)
  assert.match(logItemHover, /box-shadow:\s*inset 2px 0 0 var\(--glass-active-border\)/)
  assert.match(logItemLevel, /content:\s*""/)
  assert.match(logItemLevel, /grid-row:\s*1/)
  assert.match(logItemLevel, /width:\s*2px/)
  assert.match(logItemLevel, /background:\s*var\(--glass-control-border\)/)
  assert.match(logLevel, /min-height:\s*22px/)
  assert.match(logLevel, /border:\s*1px solid var\(--hairline\)/)
  assert.match(logLevel, /border-radius:\s*var\(--radius-xs\)/)
  assert.match(infoLevel, /background:\s*var\(--card\)/)
  assert.match(warningLevel, /background:\s*var\(--surface-specular-edge\),\s*var\(--surface-noise\),\s*var\(--badge-warning-bg\)/)
  assert.match(errorLevel, /background:\s*var\(--surface-specular-edge\),\s*var\(--surface-noise\),\s*var\(--badge-error-bg\)/)
  assert.match(source, /@media \(max-width: 768px\)[\s\S]*\.log-table-head\s*\{\s*display:\s*none/)
})

test('logs append loading preserves the visible log window', () => {
  const loadMoreRule = cssBlock('.log-list.is-loading-more')
  const loadMoreAfterRule = cssBlock('.log-list.is-loading-more::after')

  assert.match(source, /v-if="loading && !logs\.length"/)
  assert.match(source, /:class="\{ 'is-loading-more': loading \}"/)
  assert.match(loadMoreRule, /position:\s*relative/)
  assert.match(loadMoreRule, /padding-bottom:\s*36px/)
  assert.match(loadMoreAfterRule, /content:\s*"loading next page"/)
  assert.match(loadMoreAfterRule, /position:\s*sticky/)
  assert.match(loadMoreAfterRule, /bottom:\s*0/)
  assert.match(loadMoreAfterRule, /font-family:\s*var\(--font-mono\)/)
  assert.match(loadMoreAfterRule, /background:[\s\S]*var\(--material-glass-control\)/)
})

test('logs control panel exposes a compact result window summary', () => {
  assert.match(source, /class="log-window-meta"/)
  assert.match(source, /logWindowSummary\(\)/)
  assert.match(source, /\{\{\s*logWindowSummary\s*\}\}/)

  const controlPanel = cssBlock('.logs-control-panel')
  const windowMeta = cssBlock('.log-window-meta')
  const mobileWindowMeta = source.match(/@media \(max-width: 768px\)[\s\S]*?\.log-window-meta\s*\{([\s\S]*?)\n\s*\}/)

  assert.match(controlPanel, /grid-template-columns:\s*minmax\(280px,\s*1fr\)\s*minmax\(300px,\s*0\.72fr\)\s*auto/)
  assert.match(windowMeta, /align-self:\s*stretch/)
  assert.match(windowMeta, /min-width:\s*132px/)
  assert.match(windowMeta, /padding:\s*8px 10px/)
  assert.match(windowMeta, /border:\s*1px solid var\(--glass-control-border\)/)
  assert.match(windowMeta, /background:\s*var\(--surface-specular-edge\),\s*var\(--surface-noise\),\s*var\(--material-glass-control\)/)
  assert.match(windowMeta, /font-family:\s*var\(--font-mono\)/)
  assert.match(windowMeta, /font-variant-numeric:\s*tabular-nums/)
  assert.match(windowMeta, /white-space:\s*nowrap/)
  assert.ok(mobileWindowMeta, 'log window metadata should have a compact mobile rule')
  assert.match(mobileWindowMeta[1], /min-width:\s*0/)
  assert.match(mobileWindowMeta[1], /text-align:\s*left/)
})

test('logs active filters are visible as compact console tokens', () => {
  assert.match(source, /v-if="activeLogFilters\.length" class="filter-ledger" aria-label="当前日志筛选"/)
  assert.match(source, /v-for="filter in activeLogFilters"/)
  assert.match(source, /class="filter-token"/)
  assert.match(source, /class="filter-reset"/)
  assert.match(source, /hasActiveLogFilters\(\)/)
  assert.match(source, /activeLogFilters\(\)/)
  assert.match(source, /const filters = \[\]/)
  assert.match(source, /filters\.push\(\{ key: 'level'/)
  assert.match(source, /filters\.push\(\{ key: 'query'/)
  assert.match(source, /:disabled="!hasActiveLogFilters"/)

  const ledger = cssBlock('.filter-ledger')
  const token = cssBlock('.filter-token')
  const reset = cssBlock('.filter-reset')
  const resetFocus = cssBlock('.filter-reset:focus-visible')

  assert.match(ledger, /grid-column:\s*1 \/ -1/)
  assert.match(ledger, /display:\s*flex/)
  assert.match(ledger, /gap:\s*6px/)
  assert.match(ledger, /border-top:\s*1px solid var\(--glass-control-border\)/)
  assert.match(token, /font-family:\s*var\(--font-mono\)/)
  assert.match(token, /font-variant-numeric:\s*tabular-nums/)
  assert.match(token, /background:\s*var\(--card\)/)
  assert.match(reset, /border:\s*1px solid var\(--glass-control-border\)/)
  assert.match(reset, /background:\s*var\(--surface-specular-edge\),\s*var\(--surface-noise\),\s*var\(--material-glass-control\)/)
  assert.match(resetFocus, /box-shadow:\s*var\(--glass-control-shadow-hover\),\s*var\(--focus-ring\)/)
  assert.match(source, /@media \(max-width: 768px\)[\s\S]*\.filter-ledger\s*\{[\s\S]*align-items:\s*stretch/)
}
)

test('logs state components are framed as dense console panels', () => {
  const logsState = cssBlock('.logs-state')
  const logsStateSkeletonRows = cssBlock('.logs-state:deep(.apple-skeleton-row)')
  const logsStateCopy = cssBlock('.logs-state:deep(.apple-state-copy)')

  assert.match(source, /<AppleSkeleton[\s\S]*class="logs-state"[\s\S]*variant="list"[\s\S]*:items="6"/)
  assert.match(source, /<AppleErrorState[\s\S]*class="logs-state"[\s\S]*source-label="Logs API"[\s\S]*details="limit · level · query"/)
  assert.match(source, /<AppleEmptyState[\s\S]*class="logs-state"[\s\S]*density="compact"/)
  assert.match(logsState, /max-width:\s*none/)
  assert.match(logsState, /margin:\s*0/)
  assert.match(logsState, /padding:\s*12px/)
  assert.match(logsState, /border-radius:\s*0/)
  assert.match(logsState, /box-shadow:\s*none/)
  assert.match(logsStateSkeletonRows, /min-height:\s*34px/)
  assert.match(logsStateSkeletonRows, /border-radius:\s*var\(--radius-sm\)/)
  assert.match(logsStateCopy, /text-align:\s*left/)
})

test('logs mobile controls remain compact for console scanning', () => {
  assert.match(source, /@media \(max-width: 768px\)[\s\S]*\.toolbar\s*\{[\s\S]*display:\s*grid/)
  assert.match(source, /@media \(max-width: 768px\)[\s\S]*\.toolbar\s*\{[\s\S]*grid-template-columns:\s*repeat\(2,\s*minmax\(0,\s*1fr\)\)/)
  assert.match(source, /@media \(max-width: 768px\)[\s\S]*\.toolbar input\s*\{[\s\S]*grid-column:\s*1 \/ -1/)
  assert.match(source, /@media \(max-width: 768px\)[\s\S]*\.activity-summary-strip\s*\{[\s\S]*grid-template-columns:\s*repeat\(3,\s*minmax\(0,\s*1fr\)\)/)
  assert.match(source, /@media \(max-width: 768px\)[\s\S]*\.activity-summary-strip > div\s*\{[\s\S]*padding:\s*7px 8px/)
})

test('logs mobile footer and summary metadata avoid horizontal overflow', () => {
  assert.match(source, /@media \(max-width: 768px\)[\s\S]*\.log-window-meta\s*\{[\s\S]*overflow:\s*hidden/)
  assert.match(source, /@media \(max-width: 768px\)[\s\S]*\.log-window-meta\s*\{[\s\S]*text-overflow:\s*ellipsis/)
  assert.match(source, /@media \(max-width: 768px\)[\s\S]*\.pagination\s*\{[\s\S]*margin-top:\s*10px/)
  assert.match(source, /@media \(max-width: 768px\)[\s\S]*\.pagination button\s*\{[\s\S]*width:\s*100%/)
  assert.match(source, /@media \(max-width: 768px\)[\s\S]*\.pagination button\s*\{[\s\S]*min-height:\s*40px/)
  assert.match(source, /@media \(max-width: 768px\)[\s\S]*\.logs-state\s*\{[\s\S]*padding:\s*10px/)
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
    // v2：实底块不得有玻璃分层；仍是玻璃的块必须分层完整
    if (/background:\s*var\(--card\b/.test(block)) {
      assert.doesNotMatch(block, /var\(--surface-specular-edge|var\(--surface-noise\)/)
    } else if (/var\(--material-glass|var\(--glass-active-material\)/.test(block)) {
      assert.match(block, /var\(--surface-specular-edge/)
      assert.match(block, /var\(--surface-noise\)/)
    }
  }
})
