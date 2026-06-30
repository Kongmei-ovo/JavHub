import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

const vueSource = readFileSync(new URL('./TranslationJobs.vue', import.meta.url), 'utf8')
const sourcesPanel = readFileSync(new URL('../features/translations/TranslationSourcesPanel.vue', import.meta.url), 'utf8')
const reviewPanel = readFileSync(new URL('../features/translations/TranslationReviewPanel.vue', import.meta.url), 'utf8')
let externalStyle = ''
try {
  externalStyle = [
    readFileSync(new URL('../features/translations/translationJobs.css', import.meta.url), 'utf8'),
    readFileSync(new URL('../features/translations/translationPanelControls.css', import.meta.url), 'utf8'),
    readFileSync(new URL('../features/translations/translationSourcesPanel.css', import.meta.url), 'utf8'),
    readFileSync(new URL('../features/translations/translationReviewPanel.css', import.meta.url), 'utf8'),
  ].join('\n')
} catch {
  externalStyle = ''
}
const source = `${vueSource}\n${sourcesPanel}\n${reviewPanel}\n${externalStyle}`

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
  return new RegExp(`background:\\s*(?:[^;]*,\\s*)*var\\(${token}\\)(?:\\s*,[^;]*)?;`).test(block)
}

function singleLayerGlassBackgrounds(css) {
  const singleLayerGlass = /^background:\s*var\(--(?:material-glass-subtle|material-glass-control|material-glass-control-hover|material-glass-elevated|material-glass-sheet|glass-active-material)\);$/gm
  return [...css.matchAll(singleLayerGlass)].map(match => match[0])
}

test('translation donut and compact rows use semantic solid content tokens', () => {
  const donut = cssBlock(source, '.coverage-donut')
  const donutHole = cssBlock(source, '.coverage-donut div')
  const darkTokens = source.match(/:global\(:root\[data-theme='dark'\]\)\s*\{([^}]*)\}/)?.[1] || ''
  const overviewTrackFill = cssBlock(source, '.overview-track div')
  const overviewTrack = cssBlock(source, '.overview-track')
  const segmentedButton = cssBlock(source, '.segmented-control button')
  const segmentedHover = cssBlock(source, '.segmented-control button:hover')
  const compactJob = cssBlock(source, '.compact-job-row')
  const historyRow = cssBlock(source, '.history-row')

  assert.match(donut, /--translation-donut-track-base:\s*color-mix\(in srgb,\s*var\(--text-primary\) 13%,\s*transparent\)/)
  assert.match(donut, /--translation-donut-hole-bg-base:\s*var\(--card-2\)/)
  assert.match(donut, /--translation-donut-hole-border-base:\s*var\(--hairline\)/)
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
  assert.ok(backgroundIncludes(overviewTrackFill, '--glass-active-material'))
  assert.match(overviewTrackFill, /box-shadow:\s*var\(--glass-active-shadow\)/)
  assert.doesNotMatch(overviewTrackFill, /background:\s*var\(--accent\)/)
  assert.match(overviewTrack, /background:\s*var\(--card\)/)
  assert.match(overviewTrack, /box-shadow:\s*none/)
  assert.doesNotMatch(overviewTrack, /rgba\(var\(--accent-rgb\)/)

  // 胶囊 tab(对齐收藏/补全):透明描边 + subtle 底,玻璃/阴影在轨道 .segmented-control 上。
  assert.match(segmentedButton, /border:\s*1px solid transparent/)
  assert.ok(backgroundIncludes(segmentedButton, '--material-glass-subtle'))

  for (const block of [compactJob, historyRow]) {
    assert.match(block, /border:\s*1px solid var\(--hairline\)/)
    assert.match(block, /background:\s*var\(--card-2\)/)
    assert.match(block, /box-shadow:\s*none/)
    assert.doesNotMatch(block, /material-glass|surface-specular-edge|surface-noise|backdrop-filter/)
  }

  assert.ok(backgroundIncludes(segmentedHover, '--material-glass-control-hover'))
  assert.match(segmentedHover, /border-color:\s*var\(--glass-control-border-hover\)/)
  assert.match(segmentedHover, /box-shadow:\s*var\(--glass-control-shadow-hover\)/)
})

test('translation controls mirror Apple glass hover treatment for keyboard focus', () => {
  const segmentedHover = cssBlock(source, '.segmented-control button:hover')
  const segmentedFocus = cssBlock(source, '.segmented-control button:focus-visible')
  const segmentedActiveFocus = cssBlock(source, '.segmented-control button.active:focus-visible')
  const providerEnabled = cssBlock(source, '.provider-row.enabled')
  const providerFocus = cssBlock(source, '.provider-row:focus-within')
  const providerEnabledFocus = cssBlock(source, '.provider-row.enabled:focus-within')
  const historyFocus = cssBlock(source, '.history-row:focus-visible')

  for (const [block, name] of [
    [segmentedHover, 'segmented hover'],
    [segmentedFocus, 'segmented focus'],
  ]) {
    assert.ok(backgroundIncludes(block, '--material-glass-control-hover'), `${name} should use hover glass material`)
    assert.match(block, /border-color:\s*var\(--glass-control-border-hover\)/, `${name} should use shared hover border`)
    assert.match(block, /box-shadow:\s*var\(--glass-control-shadow-hover\)(?:,\s*var\(--focus-ring\))?/, `${name} should use shared hover shadow`)
    assert.match(block, /transform:\s*translateY\(-1px\)/, `${name} should lift lightly`)
  }

  for (const [block, name] of [
    [providerFocus, 'provider focus'],
    [historyFocus, 'history focus'],
  ]) {
    assert.match(block, /background:\s*var\(--card-hover\)/, `${name} should use the solid hover surface`)
    assert.match(block, /border-color:\s*var\(--hairline-strong\)/, `${name} should use the strong hairline`)
    assert.match(block, /box-shadow:\s*var\(--shadow-card\),\s*var\(--focus-ring\)/, `${name} should use solid content depth`)
    assert.doesNotMatch(block, /material-glass|surface-specular-edge|surface-noise|backdrop-filter/)
  }

  for (const [block, name] of [
    [segmentedFocus, 'segmented focus'],
    [providerFocus, 'provider focus'],
    [historyFocus, 'history focus'],
  ]) {
    assert.match(block, /outline:\s*none/, `${name} should avoid double native focus chrome`)
    assert.match(block, /var\(--focus-ring\)/, `${name} should include a soft accent focus halo`)
  }

  for (const [block, name] of [
    [providerEnabled, 'selected provider'],
    [segmentedActiveFocus, 'active segment focus'],
    [providerEnabledFocus, 'selected provider focus'],
  ]) {
    assert.ok(backgroundIncludes(block, '--glass-active-material'), `${name} should preserve active glass material`)
    assert.match(block, /border-color:\s*var\(--glass-active-border\)/, `${name} should use active glass border`)
    assert.match(block, /box-shadow:\s*var\(--glass-active-shadow\)/, `${name} should use active glass shadow`)
  }

  assert.match(segmentedActiveFocus, /outline:\s*none/, 'active segment focus should avoid double native focus chrome')
  assert.match(segmentedActiveFocus, /var\(--focus-ring\)/, 'active segment focus should include a focus halo')
  assert.match(providerEnabledFocus, /outline:\s*none/, 'selected provider focus should avoid double native focus chrome')
  assert.match(providerEnabledFocus, /var\(--focus-ring\)/, 'selected provider focus should include a focus halo')
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
  assert.match(providerRow, /border:\s*1px solid var\(--hairline\)/)
  assert.match(providerRow, /background:\s*var\(--card-2\)/)
  assert.match(providerRow, /box-shadow:\s*none/)
  assert.doesNotMatch(providerRow, /material-glass|surface-specular-edge|surface-noise|backdrop-filter/)

  assert.match(reviewTable, /display:\s*grid/)
  assert.match(reviewTable, /gap:\s*8px/)
  assert.match(reviewHead, /border:\s*1px solid var\(--hairline\)/)
  assert.match(reviewHead, /background:\s*var\(--card\)/)
  assert.match(reviewRow, /border:\s*1px solid var\(--hairline\)/)
  assert.match(reviewRow, /background:\s*var\(--card-2\)/)
  assert.match(reviewRow, /box-shadow:\s*none/)
  assert.doesNotMatch(reviewRow, /material-glass|surface-specular-edge|surface-noise|backdrop-filter/)

  for (const block of [reviewHistoryPanel, resultSummary, sourceDivider]) {
    assert.match(block, /border-(?:top|left):\s*1px solid var\(--glass-edge\)/)
  }
  assert.match(emptyPanel, /border:\s*1px dashed var\(--glass-control-border\)/)
  assert.match(emptyPanel, /background:\s*var\(--card\)/)
})

test('translation form controls stay glass while content cards use solid surfaces', () => {
  const solidCardSelectors = [
    '.coverage-hero',
    '.metadata-overview',
    '.signal-card',
    '.job-control-card',
  ]
  const solidInsetSelectors = [
    '.notice-row',
    '.boxed',
    '.review-stats div',
    '.message-line',
  ]

  for (const selector of solidCardSelectors) {
    const block = cssBlock(source, selector)
    assert.match(block, /border:\s*1px solid var\(--hairline\)/, `${selector} should use a content hairline`)
    assert.match(block, /background:\s*var\(--card\)/, `${selector} should use the solid card surface`)
    assert.match(block, /box-shadow:\s*var\(--shadow-card\)/, `${selector} should use card depth`)
    assert.doesNotMatch(block, /material-glass|surface-specular-edge|surface-noise|backdrop-filter/)
  }

  for (const selector of solidInsetSelectors) {
    const block = cssBlock(source, selector)
    assert.match(block, /border:\s*1px solid var\(--hairline\)/, `${selector} should use a content hairline`)
    assert.match(block, /background:\s*var\(--card-2\)/, `${selector} should use the inset content surface`)
    assert.match(block, /box-shadow:\s*none/, `${selector} should avoid glass depth`)
    assert.doesNotMatch(block, /material-glass|surface-specular-edge|surface-noise|backdrop-filter/)
  }

  const input = cssBlock(source, '.input')
  assert.match(input, /border:\s*1px solid var\(--glass-control-border\)/)
  assert.ok(backgroundIncludes(input, '--material-glass-control'))
  assert.match(input, /box-shadow:\s*var\(--glass-control-shadow\)/)

  const inputFocus = cssBlock(source, '.input:focus')
  assert.ok(backgroundIncludes(inputFocus, '--material-glass-control-hover'))
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
    assert.ok(backgroundIncludes(block, '--badge-error-bg'))
    assert.match(block, /var\(--surface-specular-edge/)
    assert.match(block, /var\(--surface-noise\)/)
    assert.match(block, /border-color:\s*var\(--badge-error-border\)/)
  }

  assert.doesNotMatch(source, /var\(--surface-control\)|var\(--surface-input-focus\)|#ff6b78|rgba\(255,\s*80,\s*90|rgba\(245,\s*181,\s*80|rgba\(90,\s*200,\s*150/i)
})

test('translation review reset danger action uses semantic layered glass states', () => {
  const reviewDanger = cssBlock(source, '.review-actions .danger')
  const reviewDangerHover = cssBlock(source, '.review-actions .danger:hover')
  const reviewDangerFocus = cssBlock(source, '.review-actions .danger:focus-visible')

  assert.match(reviewDanger, /border-color:\s*var\(--badge-error-border\)/)
  assert.ok(backgroundIncludes(reviewDanger, '--badge-error-bg'))
  assert.match(reviewDanger, /var\(--surface-specular-edge\)/)
  assert.match(reviewDanger, /var\(--surface-noise\)/)
  assert.match(reviewDanger, /color:\s*var\(--badge-error-text\)/)
  assert.match(reviewDanger, /box-shadow:\s*var\(--glass-control-shadow\)/)

  for (const [block, name] of [
    [reviewDangerHover, 'review danger hover'],
    [reviewDangerFocus, 'review danger focus'],
  ]) {
    assert.match(block, /border-color:\s*var\(--badge-error-border\)/, `${name} should keep semantic error border`)
    assert.ok(backgroundIncludes(block, '--badge-error-bg'), `${name} should keep semantic error fill`)
    assert.match(block, /var\(--surface-specular-edge-strong\)/, `${name} should strengthen the specular edge`)
    assert.match(block, /var\(--surface-noise\)/, `${name} should preserve texture noise`)
    assert.match(block, /box-shadow:\s*var\(--glass-control-shadow-hover\)/, `${name} should use shared hover depth`)
    assert.match(block, /transform:\s*translateY\(-1px\)/, `${name} should lift lightly`)
  }

  assert.match(reviewDangerFocus, /outline:\s*none/)
  assert.match(reviewDangerFocus, /0 0 0 3px color-mix\(in srgb,\s*var\(--badge-error-text\) 18%,\s*transparent\)/)
  assert.doesNotMatch(`${reviewDanger}\n${reviewDangerHover}\n${reviewDangerFocus}`, /#ff6b78|rgba\(255,\s*80,\s*90|rgba\(var\(--error-rgb\)|rgba\(var\(--accent-rgb\)/i)
})

test('translation long lists skip unnecessary row rendering work', () => {
  assert.match(
    source,
    /v-for="item in reviewItems"[\s\S]*v-memo="\[item\.item_type,\s*item\.item_id,\s*item\.edit_text,\s*item\.status,\s*item\.provider,\s*item\.updated_at,\s*item\.last_error\]"/,
  )
  assert.match(
    source,
    /v-for="job in jobs"[\s\S]*v-memo="\[job\.id,\s*job\.status,\s*job\.progress_percent,\s*job\.translated,\s*job\.failed,\s*selectedJob\?\.id\]"/,
  )

  for (const selector of ['.review-row', '.history-row']) {
    const block = cssBlock(source, selector)
    assert.match(block, /content-visibility:\s*auto/)
    assert.match(block, /contain-intrinsic-size:\s*1px\s+(?:74|58)px/)
  }
})

test('translation glass controls stay layered while content surfaces stay solid', () => {
  assert.deepEqual(singleLayerGlassBackgrounds(externalStyle), [])

  for (const selector of [
    '.segmented-control',
    '.segmented-control button',
    '.input',
  ]) {
    const block = cssBlock(source, selector)
    assert.match(block, /var\(--surface-specular-edge/)
    assert.match(block, /var\(--surface-noise\)/)
  }

  for (const selector of [
    '.coverage-hero',
    '.compact-job-row',
    '.notice-row',
    '.provider-row',
    '.review-row',
    '.message-line',
  ]) {
    const block = cssBlock(source, selector)
    assert.doesNotMatch(block, /var\(--surface-specular-edge|var\(--surface-noise\)|var\(--material-glass|backdrop-filter/)
  }
})

test('translation page keeps heavyweight styles in an external scoped stylesheet', () => {
  assert.match(vueSource, /<style scoped src="\.\.\/features\/translations\/translationJobs\.css"><\/style>/)
  assert.match(vueSource, /const TranslationSourcesPanel = defineAsyncComponent\(\(\) => import\('\.\.\/features\/translations\/TranslationSourcesPanel\.vue'\)\)/)
  assert.match(vueSource, /const TranslationReviewPanel = defineAsyncComponent\(\(\) => import\('\.\.\/features\/translations\/TranslationReviewPanel\.vue'\)\)/)
  assert.match(sourcesPanel, /<style scoped src="\.\/translationPanelControls\.css"><\/style>/)
  assert.match(sourcesPanel, /<style scoped src="\.\/translationSourcesPanel\.css"><\/style>/)
  assert.match(reviewPanel, /<style scoped src="\.\/translationPanelControls\.css"><\/style>/)
  assert.match(reviewPanel, /<style scoped src="\.\/translationReviewPanel\.css"><\/style>/)
  assert.ok(externalStyle.length > 20000, 'external translation stylesheet should carry the moved workspace CSS')
  assert.ok(vueSource.split('\n').length < 1100, 'TranslationJobs.vue should stay small enough to review and parse quickly')
})
