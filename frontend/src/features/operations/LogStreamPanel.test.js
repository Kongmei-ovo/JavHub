import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

const source = readFileSync(new URL('./LogStreamPanel.vue', import.meta.url), 'utf8')

function cssBlock(selector) {
  const searchable = source.replace(/\/\*[\s\S]*?\*\//g, '')
  const blocks = [...searchable.matchAll(/([^{}]+)\{([^{}]*)\}/g)]
    .filter(([, selectors]) => selectors
      .split(',')
      .map(part => part.trim())
      .includes(selector))
    .map(([, , block]) => block)
  assert.ok(blocks.length, `${selector} block should exist in LogStreamPanel.vue`)
  return blocks.join('\n')
}

test('logs renders as an accessible table with header, rows and states', () => {
  assert.match(source, /class="logs-table" role="table"/)
  assert.match(source, /class="logs-head" role="row"/)
  assert.match(source, /role="columnheader">时间/)
  assert.match(source, /role="columnheader">等级/)
  assert.match(source, /role="columnheader">消息/)
  assert.match(source, /class="logs-rows" role="rowgroup"/)
  assert.match(source, /:class="'logs-row is-' \+ toneFor\(log\.level\)"/)
  assert.match(source, /class="logs-row-time" role="cell"/)
  assert.match(source, /class="logs-row-level" role="cell"/)
  assert.match(source, /class="logs-row-msg" role="cell"/)
})

test('logs async states reuse the shared Apple state components', () => {
  assert.match(source, /<AppleSkeleton[\s\S]*v-if="loading && !logs\.length"[\s\S]*class="logs-state"[\s\S]*variant="list"[\s\S]*:items="6"/)
  assert.match(source, /<AppleErrorState[\s\S]*class="logs-state"[\s\S]*source-label="Logs API"[\s\S]*details="limit · level · query"/)
  assert.match(source, /<AppleEmptyState[\s\S]*class="logs-state"[\s\S]*density="compact"/)

  const logsState = cssBlock('.logs-state')
  assert.match(logsState, /max-width:\s*none/)
  assert.match(logsState, /margin:\s*0/)
  assert.match(logsState, /border-radius:\s*0/)
  assert.match(logsState, /box-shadow:\s*none/)
  assert.match(cssBlock('.logs-state:deep(.apple-state-copy)'), /text-align:\s*left/)
})

test('logs controls use the shared button system instead of bespoke glass buttons', () => {
  assert.match(source, /class="btn btn-primary btn-sm" type="button" @click="loadLogs">搜索/)
  assert.match(source, /class="btn btn-ghost btn-sm" type="button" @click="loadLogs">刷新/)
  assert.match(source, /class="btn btn-ghost btn-sm logs-danger" type="button" @click="clearLogs">清空/)
  // legacy bespoke control classes are gone
  assert.doesNotMatch(source, /class="toolbar-btn/)
  assert.doesNotMatch(source, /class="activity-header/)
  assert.doesNotMatch(source, /class="log-item/)

  const search = cssBlock('.logs-search')
  assert.match(search, /border:\s*1px solid var\(--hairline\)/)
  assert.match(search, /background:\s*var\(--surface-card\)/)
  assert.doesNotMatch(search, /backdrop-filter/)
  assert.match(cssBlock('.logs-search:focus'), /border-color:\s*var\(--accent\)/)
})

test('logs surfaces are flat cards, not heavy glass panels', () => {
  for (const selector of ['.logs-bar', '.logs-table']) {
    const block = cssBlock(selector)
    assert.match(block, /background:\s*var\(--card\)/)
    assert.match(block, /border:\s*1px solid var\(--hairline\)/)
    assert.doesNotMatch(block, /backdrop-filter|material-glass|surface-specular-edge|surface-noise/)
  }

  const head = cssBlock('.logs-head')
  assert.match(head, /position:\s*sticky/)
  assert.match(head, /border-bottom:\s*1px solid var\(--hairline\)/)
  assert.match(head, /background:\s*var\(--card\)/)
  assert.doesNotMatch(head, /material-glass|backdrop-filter/)
})

test('logs rows stay calm: no full-row level tint, color carried by a thin bar and the level word', () => {
  const row = cssBlock('.logs-row')
  assert.match(row, /border-bottom:\s*1px solid var\(--hairline\)/)
  assert.match(row, /font-family:\s*var\(--font-mono\)/)

  // the row itself must never be filled with a level/badge background
  assert.doesNotMatch(source, /\.logs-row\.is-(?:warn|bad)\s*\{[^}]*background/)
  assert.doesNotMatch(source, /\.logs-row[^{]*\{[^}]*badge-(?:warning|error)-bg/)

  const bar = cssBlock('.logs-row::before')
  assert.match(bar, /content:\s*""/)
  assert.match(bar, /width:\s*2px/)
  assert.match(cssBlock('.logs-row.is-warn::before'), /background:\s*var\(--warn\)/)
  assert.match(cssBlock('.logs-row.is-bad::before'), /background:\s*var\(--bad\)/)

  assert.match(cssBlock('.logs-row.is-warn .logs-row-level'), /color:\s*var\(--warn\)/)
  assert.match(cssBlock('.logs-row.is-bad .logs-row-level'), /color:\s*var\(--bad\)/)

  const hover = cssBlock('.logs-row:hover')
  assert.match(hover, /background:\s*var\(--surface-card\)/)
  assert.doesNotMatch(hover, /material-glass|surface-specular-edge|surface-noise|backdrop-filter/)
})

test('logs meta folds level counts and the result window into one line', () => {
  assert.match(source, /class="logs-counts" aria-label="日志等级汇总"/)
  assert.match(source, /countFor\('INFO'\)/)
  assert.match(source, /countFor\('WARNING'\)/)
  assert.match(source, /countFor\('ERROR'\)/)
  assert.match(source, /class="logs-window">\{\{ logWindowSummary \}\}/)
  assert.match(source, /logWindowSummary\(\)/)

  assert.match(cssBlock('.logs-count.is-warn strong'), /color:\s*var\(--warn\)/)
  assert.match(cssBlock('.logs-count.is-bad strong'), /color:\s*var\(--bad\)/)
  const win = cssBlock('.logs-window')
  assert.match(win, /font-family:\s*var\(--font-mono\)/)
  assert.match(win, /font-variant-numeric:\s*tabular-nums/)
})

test('logs active filters surface as compact tokens with a clear action', () => {
  assert.match(source, /v-if="activeLogFilters\.length" class="logs-filters" aria-label="当前日志筛选"/)
  assert.match(source, /v-for="filter in activeLogFilters"/)
  assert.match(source, /class="logs-filter-chip"/)
  assert.match(source, /class="logs-filter-clear"/)
  assert.match(source, /:disabled="!hasActiveLogFilters"/)
  assert.match(source, /const filters = \[\]/)
  assert.match(source, /filters\.push\(\{ key: 'level'/)
  assert.match(source, /filters\.push\(\{ key: 'query'/)

  const chip = cssBlock('.logs-filter-chip')
  assert.match(chip, /font-family:\s*var\(--font-mono\)/)
  assert.match(chip, /border:\s*1px solid var\(--hairline\)/)
  assert.match(cssBlock('.logs-filter-clear'), /color:\s*var\(--accent\)/)
})

test('logs append-loading preserves the visible window with a sticky footer', () => {
  assert.match(source, /v-if="loading && !logs\.length"/)
  assert.match(source, /:class="\{ 'is-loading-more': loading \}"/)
  const rows = cssBlock('.logs-rows.is-loading-more')
  const after = cssBlock('.logs-rows.is-loading-more::after')
  assert.match(rows, /position:\s*relative/)
  assert.match(after, /position:\s*sticky/)
  assert.match(after, /bottom:\s*0/)
  assert.match(after, /font-family:\s*var\(--font-mono\)/)
})

test('logs collapses to a compact single-column scan on mobile', () => {
  assert.match(source, /@media \(max-width: 768px\)[\s\S]*\.logs-head\s*\{[\s\S]*display:\s*none/)
  assert.match(source, /@media \(max-width: 768px\)[\s\S]*\.logs-bar-controls\s*\{[\s\S]*display:\s*grid/)
  assert.match(source, /@media \(max-width: 768px\)[\s\S]*\.logs-search\s*\{[\s\S]*grid-column:\s*1 \/ -1/)
  assert.match(source, /@media \(max-width: 768px\)[\s\S]*\.logs-row\s*\{[\s\S]*grid-template-columns:\s*1fr auto/)
})

test('logs script exposes the filter helpers the template relies on', () => {
  assert.match(source, /countFor\(level\)\s*\{/)
  assert.match(source, /toneFor\(level\)\s*\{/)
  assert.match(source, /if \(upper === 'ERROR'\) return 'bad'/)
  assert.match(source, /if \(upper === 'WARNING'\) return 'warn'/)
  assert.match(source, /hasActiveLogFilters\(\)\s*\{/)
  assert.match(source, /activeLogFilters\(\)\s*\{/)
})
