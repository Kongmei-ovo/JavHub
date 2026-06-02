import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

const source = readFileSync(new URL('./TranslationJobs.vue', import.meta.url), 'utf8')

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

test('translation donut and compact rows use semantic Apple glass tokens', () => {
  const donut = cssBlock(source, '.coverage-donut')
  const donutHole = cssBlock(source, '.coverage-donut div')
  const darkTokens = source.match(/:global\(:root\[data-theme='dark'\]\)\s*\{([^}]*)\}/)?.[1] || ''
  const overviewTrackFill = cssBlock(source, '.overview-track div')
  const segmentedButton = cssBlock(source, '.segmented-control button')
  const segmentedHover = cssBlock(source, '.segmented-control button:hover')
  const compactJob = cssBlock(source, '.compact-job-row')
  const historyRow = cssBlock(source, '.history-row')

  assert.match(donut, /--translation-donut-track-base:\s*color-mix\(in srgb,\s*var\(--text-primary\) 13%,\s*transparent\)/)
  assert.match(donut, /--translation-donut-hole-bg-base:\s*var\(--material-glass-sheet\)/)
  assert.match(donut, /--translation-donut-hole-border-base:\s*var\(--glass-control-border\)/)
  assert.match(donut, /--translation-donut-edge-base:\s*var\(--glass-edge\)/)
  assert.match(donut, /--translation-donut-glow-base:\s*color-mix\(in srgb,\s*var\(--accent\) 12%,\s*transparent\)/)
  assert.match(donut, /--translation-donut-ring-highlight:\s*color-mix\(in srgb,\s*var\(--text-primary\) 24%,\s*transparent\)/)
  assert.match(donut, /--donut-glow:\s*var\(--translation-donut-glow,\s*var\(--translation-donut-glow-base\)\)/)
  assert.match(donut, /radial-gradient\(circle at 50% 50%,\s*transparent 60%,\s*var\(--translation-donut-ring-highlight\) 61%,\s*transparent 62%\)/)
  assert.match(donutHole, /background:\s*var\(--donut-hole-bg\)/)
  assert.match(donutHole, /border:\s*1px solid var\(--donut-hole-border\)/)
  assert.doesNotMatch(donut, /rgba\(255,\s*255,\s*255/i)
  assert.match(darkTokens, /--translation-donut-glow-depth:\s*color-mix\(in srgb,\s*var\(--bg-primary\) 82%,\s*transparent\)/)
  assert.match(darkTokens, /--translation-donut-glow:\s*var\(--translation-donut-glow-depth\)/)
  assert.doesNotMatch(darkTokens, /rgba\(0,\s*0,\s*0|rgba\(0,0,0|#000|#000000/i)
  assert.doesNotMatch(darkTokens, /rgba\(255,\s*255,\s*255|#fff|#ffffff/i)
  assert.match(overviewTrackFill, /background:\s*var\(--glass-active-material\)/)
  assert.match(overviewTrackFill, /box-shadow:\s*var\(--glass-active-shadow\)/)
  assert.doesNotMatch(overviewTrackFill, /background:\s*var\(--accent\)/)

  for (const block of [segmentedButton, compactJob, historyRow]) {
    assert.match(block, /border:\s*1px solid var\(--glass-control-border\)/)
    assert.match(block, /background:\s*var\(--material-glass-control\)/)
    assert.match(block, /box-shadow:\s*var\(--glass-control-shadow\)/)
    assert.doesNotMatch(block, /border:\s*(?:0|none|1px solid transparent)/)
    assert.doesNotMatch(block, /background:\s*(?:transparent|none)/)
  }

  assert.match(segmentedHover, /background:\s*var\(--material-glass-control-hover\)/)
  assert.match(segmentedHover, /border-color:\s*var\(--glass-control-border-hover\)/)
  assert.match(segmentedHover, /box-shadow:\s*var\(--glass-control-shadow-hover\)/)
})

test('translation review and source workspaces avoid legacy flat separators', () => {
  const providerList = cssBlock(source, '.provider-list')
  const providerRow = cssBlock(source, '.provider-row')
  const reviewTable = cssBlock(source, '.review-table')
  const reviewHead = cssBlock(source, '.review-head')
  const reviewRow = cssBlock(source, '.review-row')
  const reviewHistoryPanel = cssBlock(source, '.review-history-panel')
  const resultSummary = cssBlock(source, '.result-summary')
  const emptyPanel = cssBlock(source, '.empty-panel')
  const sourceDivider = cssBlock(source, '.source-section + .source-section')

  assert.doesNotMatch(source, /border(?:-(?:top|bottom|left|right))?:\s*1px (?:solid|dashed) var\(--border\)/)

  assert.match(providerList, /display:\s*grid/)
  assert.match(providerList, /gap:\s*8px/)
  assert.match(providerRow, /border:\s*1px solid var\(--glass-control-border\)/)
  assert.match(providerRow, /background:\s*var\(--material-glass-control\)/)
  assert.match(providerRow, /box-shadow:\s*var\(--glass-control-shadow\)/)

  assert.match(reviewTable, /display:\s*grid/)
  assert.match(reviewTable, /gap:\s*8px/)
  assert.match(reviewHead, /border:\s*1px solid var\(--glass-control-border\)/)
  assert.match(reviewHead, /background:\s*var\(--material-glass-subtle\)/)
  assert.match(reviewRow, /border:\s*1px solid var\(--glass-control-border\)/)
  assert.match(reviewRow, /background:\s*var\(--material-glass-control\)/)
  assert.match(reviewRow, /box-shadow:\s*var\(--glass-control-shadow\)/)

  for (const block of [reviewHistoryPanel, resultSummary, sourceDivider]) {
    assert.match(block, /border-(?:top|left):\s*1px solid var\(--glass-edge\)/)
  }
  assert.match(emptyPanel, /border:\s*1px dashed var\(--glass-control-border\)/)
  assert.match(emptyPanel, /background:\s*var\(--material-glass-subtle\)/)
})

test('translation form and status surfaces use shared glass and badge tokens', () => {
  const sharedControlSelectors = [
    '.coverage-hero',
    '.metadata-overview',
    '.signal-card',
    '.job-control-card',
    '.notice-row',
    '.input',
    '.boxed',
    '.review-stats div',
    '.message-line',
  ]

  for (const selector of sharedControlSelectors) {
    const block = cssBlock(source, selector)
    assert.match(block, /border:\s*1px solid var\(--glass-control-border\)/, `${selector} should use the shared glass border`)
    assert.match(block, /background:\s*var\(--material-glass-control\)/, `${selector} should use the shared glass material`)
    assert.match(block, /box-shadow:\s*var\(--glass-control-shadow\)/, `${selector} should use the shared glass shadow`)
    assert.doesNotMatch(block, /var\(--surface-control\)|var\(--surface-input-focus\)/, `${selector} should not depend on legacy surface aliases`)
  }

  const inputFocus = cssBlock(source, '.input:focus')
  assert.match(inputFocus, /background:\s*var\(--material-glass-control-hover\)/)
  assert.doesNotMatch(inputFocus, /var\(--surface-input-focus\)/)

  const dangerMetric = cssBlock(source, '.job-control-metrics .danger strong')
  const jobError = cssBlock(source, '.job-error')
  const failedStatus = cssBlock(source, '.status-failed')
  const reviewDanger = cssBlock(source, '.review-actions .danger')
  const messageError = cssBlock(source, '.message-line.error')

  for (const block of [dangerMetric, jobError, failedStatus, reviewDanger, messageError]) {
    assert.match(block, /var\(--badge-error-text\)/)
    assert.doesNotMatch(block, /#ff6b78|rgba\(255,\s*80,\s*90/i)
  }

  for (const block of [jobError, failedStatus]) {
    assert.match(block, /background:\s*var\(--badge-error-bg\)/)
    assert.match(block, /border-color:\s*var\(--badge-error-border\)/)
  }

  assert.doesNotMatch(source, /var\(--surface-control\)|var\(--surface-input-focus\)|#ff6b78|rgba\(255,\s*80,\s*90|rgba\(245,\s*181,\s*80|rgba\(90,\s*200,\s*150/i)
})
