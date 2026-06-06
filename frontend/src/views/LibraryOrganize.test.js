import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

const vueSource = readFileSync(new URL('./LibraryOrganize.vue', import.meta.url), 'utf8')
const externalStyle = readFileSync(new URL('../features/library/libraryOrganize.css', import.meta.url), 'utf8')
const source = `${vueSource}\n${externalStyle}`

function cssRule(selector) {
  const escaped = selector.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  const match = source.match(new RegExp(`${escaped} \\{([\\s\\S]*?)\\n\\}`))
  assert.ok(match, `Expected CSS rule for ${selector}`)
  return match[1]
}

function cssGroupedRule(selector) {
  const escaped = selector.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  const match = source.match(new RegExp(`${escaped}[\\s\\S]*?\\{([\\s\\S]*?)\\n\\}`))
  assert.ok(match, `Expected grouped CSS rule starting at ${selector}`)
  return match[1]
}

function darkRule(selector) {
  return cssGroupedRule(`:global(:root[data-theme="dark"] ${selector}`)
}

function backgroundIncludes(token) {
  return new RegExp(`background:[\\s\\S]*var\\(--${token}\\)`)
}

function singleLayerGlassBackgrounds(css) {
  return css
    .split('\n')
    .map((line, index) => ({ line: index + 1, text: line.trim() }))
    .filter(({ text }) => /^background:\s*var\(--(?:material-glass-subtle|material-glass-control|material-glass-control-hover|material-glass-elevated|material-glass-sheet|glass-active-material)\);$/.test(text))
}

test('library organize keeps large scoped styles in a feature stylesheet', () => {
  assert.match(vueSource, /<style scoped src="\.\.\/features\/library\/libraryOrganize\.css"><\/style>/)
  assert.ok(vueSource.split('\n').length < 1100, 'LibraryOrganize.vue should stay below 1100 lines')
  assert.ok(externalStyle.split('\n').length > 800, 'external stylesheet should contain the moved page styles')
})

test('library organize top chrome uses the shared Apple glass material', () => {
  assert.match(source, /class="organize-header apple-surface"/)
  assert.match(source, /class="status-strip organize-status apple-surface"/)
  assert.match(source, /class="organize-tabs apple-surface"/)

  const headerRule = cssRule('.organize-header')
  const headerBeforeRule = cssRule('.organize-header::before')
  const statusRule = cssRule('.organize-status')
  const tabActiveRule = cssRule('.tab-btn.active')
  const setupBannerRule = cssRule('.setup-banner')

  assert.match(headerRule, /min-height:\s*92px/)
  assert.match(headerRule, /border:\s*1px solid var\(--glass-edge-strong\)/)
  assert.match(headerRule, backgroundIncludes('material-glass-sheet'))
  assert.match(headerRule, /box-shadow:\s*var\(--glass-surface-shadow\)/)
  assert.match(headerRule, /backdrop-filter:\s*blur\(var\(--glass-blur-surface\)\)\s*saturate\(var\(--glass-saturate-surface\)\)/)
  assert.doesNotMatch(headerRule, /rgba\(255,\s*255,\s*255|rgba\(255,255,255|radial-gradient|linear-gradient\(145deg/)
  assert.match(headerRule, /overflow: hidden/)
  assert.match(headerBeforeRule, backgroundIncludes('material-glass-subtle'))
  assert.match(headerBeforeRule, /--organize-header-mask-start:\s*var\(--media-edge-mask-strong\)/)
  assert.match(headerBeforeRule, /--organize-header-mask-end:\s*var\(--media-edge-mask-clear\)/)
  assert.match(headerBeforeRule, /mask-image:\s*linear-gradient\(90deg,\s*var\(--organize-header-mask-start\),\s*var\(--organize-header-mask-end\) 74%\)/)
  assert.doesNotMatch(headerBeforeRule, /background-image|rgba\(255,\s*255,\s*255|rgba\(255,255,255|rgba\(0,\s*0,\s*0|rgba\(0,0,0|#000|#000000/i)
  assert.match(statusRule, backgroundIncludes('material-glass-sheet'))
  assert.match(statusRule, /backdrop-filter: blur\(var\(--glass-blur-surface\)\)/)
  assert.match(tabActiveRule, backgroundIncludes('glass-active-material'))
  assert.match(tabActiveRule, /box-shadow: var\(--glass-active-shadow\)/)

  assert.match(setupBannerRule, /border:\s*1px solid var\(--glass-edge-strong\)/)
  assert.match(setupBannerRule, backgroundIncludes('material-glass-sheet'))
  assert.match(setupBannerRule, /box-shadow:\s*var\(--glass-surface-shadow\)/)
  assert.match(setupBannerRule, /backdrop-filter:\s*blur\(var\(--glass-blur-surface\)\)\s*saturate\(var\(--glass-saturate-surface\)\)/)
  assert.doesNotMatch(setupBannerRule, /rgba\(255,\s*255,\s*255|rgba\(255,255,255|var\(--surface-card\)/)
})

test('library organize first viewport stays dense and operational', () => {
  const pageRule = cssRule('.library-organize-page')
  const headerRule = cssRule('.organize-header')
  const titleRule = cssRule('.organize-header h1')
  const statusRule = cssRule('.organize-status')
  const statusCellRule = cssRule('.status-cell')
  const statusValueRule = cssRule('.status-value')
  const tabsRule = cssRule('.organize-tabs')
  const tabRule = cssRule('.tab-btn')

  assert.match(pageRule, /padding-top:\s*12px/)
  assert.match(headerRule, /padding:\s*12px/)
  assert.match(headerRule, /align-items:\s*center/)
  assert.match(headerRule, /border-radius:\s*var\(--radius-lg\)/)
  assert.doesNotMatch(headerRule, /clamp\(22px|148px|5vw/)
  assert.match(titleRule, /font-size:\s*var\(--type-workbench-title\)/)
  assert.match(statusRule, /grid-template-columns:\s*repeat\(6,\s*minmax\(0,\s*1fr\)\)/)
  assert.match(statusRule, /gap:\s*6px/)
  assert.match(statusCellRule, /min-height:\s*54px/)
  assert.match(statusCellRule, /padding:\s*8px 10px/)
  assert.match(statusValueRule, /font-size:\s*18px/)
  assert.match(tabsRule, /margin-bottom:\s*10px/)
  assert.match(tabRule, /min-height:\s*34px/)
})

test('library organize tab controls use shared liquid glass tokens', () => {
  const tabRule = cssRule('.tab-btn')
  const tabHoverRule = cssRule('.tab-btn:hover')
  const tabActiveRule = cssRule('.tab-btn.active')

  assert.match(tabRule, /border:\s*1px solid var\(--glass-control-border\)/)
  assert.match(tabRule, backgroundIncludes('material-glass-control'))
  assert.match(tabRule, /box-shadow:\s*var\(--glass-control-shadow\)/)
  assert.match(tabRule, /backdrop-filter:\s*blur\(var\(--glass-blur-control\)\)\s*saturate\(var\(--glass-saturate-control\)\)/)
  assert.match(tabHoverRule, /border-color:\s*var\(--glass-control-border-hover\)/)
  assert.match(tabHoverRule, backgroundIncludes('material-glass-control-hover'))
  assert.match(tabHoverRule, /box-shadow:\s*var\(--glass-control-shadow-hover\)/)
  assert.match(tabActiveRule, /border-color:\s*var\(--glass-active-border\)/)
  assert.match(tabActiveRule, backgroundIncludes('glass-active-material'))
  assert.doesNotMatch(tabRule, /border:\s*1px solid transparent/)
  assert.doesNotMatch(tabRule, /background:\s*transparent/)
})

test('library organize keyboard focus mirrors hover glass control treatment', () => {
  const statusFocusRule = cssRule('.status-cell:focus-visible')
  const tabFocusRule = cssRule('.tab-btn:focus-visible')
  const workflowFocusRule = cssGroupedRule('.priority-row:focus-visible,')
  const chipFocusRule = cssGroupedRule('.candidate-pills button:focus-visible,')

  for (const [rule, label] of [
    [statusFocusRule, 'status metric focus'],
    [tabFocusRule, 'organize tab focus'],
    [workflowFocusRule, 'workflow action focus'],
    [chipFocusRule, 'candidate chip focus'],
  ]) {
    assert.match(rule, /outline:\s*none/, `${label} should replace the default outline`)
    assert.match(rule, /border-color:\s*var\(--glass-control-border-hover\)/, `${label} should use hover border`)
    assert.match(rule, backgroundIncludes('material-glass-control-hover'), `${label} should use hover glass material`)
    assert.match(rule, /box-shadow:\s*var\(--glass-control-shadow-hover\),\s*var\(--focus-ring\)/, `${label} should show a subtle Apple-style focus ring`)
  }

  assert.match(statusFocusRule, /transform:\s*translateY\(-1px\)/)
  assert.match(tabFocusRule, /color:\s*var\(--text-primary\)/)
  assert.match(workflowFocusRule, /transform:\s*translateY\(-1px\)/)
})

test('library organize workbench cards use liquid glass depth instead of flat white cards', () => {
  const panelRule = cssGroupedRule('.workbench-panel,')
  const rowRule = cssGroupedRule('.priority-row,')
  const inputRule = cssGroupedRule('.mini-check-form input,')

  assert.match(panelRule, /border: 1px solid var\(--glass-edge\)/)
  assert.match(panelRule, backgroundIncludes('material-glass-elevated'))
  assert.match(panelRule, /backdrop-filter: blur\(var\(--glass-blur-surface\)\)/)
  assert.match(rowRule, /box-shadow: var\(--glass-inner-shadow\)/)
  assert.match(rowRule, /transition:/)
  assert.match(inputRule, backgroundIncludes('material-glass-control'))
  assert.match(inputRule, /box-shadow: var\(--glass-control-shadow\)/)
  const focusRule = cssGroupedRule('.mini-check-form input:focus,')
  assert.match(focusRule, /border-color:\s*var\(--glass-active-border\)/)
  assert.doesNotMatch(focusRule, /border-color:\s*var\(--accent\)/)
})

test('library organize workbench panels expose a refractive inner edge layer', () => {
  const panelRule = cssGroupedRule('.workbench-panel,')
  const panelBeforeRule = cssRule('.workbench-panel::before')
  const panelChildrenRule = cssRule('.workbench-panel > *')

  assert.match(panelRule, /position:\s*relative/)
  assert.match(panelRule, /isolation:\s*isolate/)
  assert.match(panelRule, /overflow:\s*hidden/)
  assert.match(panelBeforeRule, /content:\s*""/)
  assert.match(panelBeforeRule, /position:\s*absolute/)
  assert.match(panelBeforeRule, /inset:\s*0/)
  assert.match(panelBeforeRule, /border-radius:\s*inherit/)
  assert.match(panelBeforeRule, backgroundIncludes('surface-specular-edge-strong'))
  assert.match(panelBeforeRule, backgroundIncludes('surface-noise'))
  assert.match(panelBeforeRule, /opacity:\s*0\.[45]2/)
  assert.match(panelBeforeRule, /pointer-events:\s*none/)
  assert.match(panelBeforeRule, /z-index:\s*0/)
  assert.match(panelChildrenRule, /position:\s*relative/)
  assert.match(panelChildrenRule, /z-index:\s*1/)
})

test('library organize dense controls keep stable numerals and pressed feedback', () => {
  const statusValueRule = cssRule('.status-value')
  const priorityMarkRule = cssRule('.priority-mark')
  const rowActiveRule = cssGroupedRule('.priority-row:active,')
  const chipActiveRule = cssGroupedRule('.candidate-pills button:active,')
  const nestedActionRule = cssGroupedRule('.mapping-item:has(button:active),')

  assert.match(statusValueRule, /font-variant-numeric:\s*tabular-nums/)
  assert.match(priorityMarkRule, /font-variant-numeric:\s*tabular-nums/)
  assert.match(rowActiveRule, /transform:\s*translateY\(0\)\s*scale\(0\.99\)/)
  assert.match(chipActiveRule, /transform:\s*scale\(0\.985\)/)
  assert.match(nestedActionRule, /transform:\s*translateY\(0\)\s*scale\(0\.995\)/)
  assert.match(nestedActionRule, /box-shadow:\s*var\(--glass-inner-shadow\)/)
})

test('library organize queue rows stay compact and table-scannable', () => {
  const priorityListRule = cssRule('.priority-list')
  const priorityRowRule = cssRule('.priority-row')
  const priorityMarkRule = cssRule('.priority-mark')
  const flowButtonRule = cssRule('.flow-steps button')
  const panelHeadRule = cssRule('.panel-head')

  assert.match(priorityListRule, /gap:\s*6px/)
  assert.match(priorityRowRule, /grid-template-columns:\s*38px minmax\(0,\s*1fr\)\s*72px/)
  assert.match(priorityRowRule, /min-height:\s*58px/)
  assert.match(priorityRowRule, /padding:\s*8px 10px/)
  assert.match(priorityMarkRule, /width:\s*34px/)
  assert.match(priorityMarkRule, /height:\s*34px/)
  assert.match(flowButtonRule, /min-height:\s*50px/)
  assert.match(flowButtonRule, /padding:\s*8px 10px/)
  assert.match(panelHeadRule, /margin-bottom:\s*10px/)
})

test('library organize status strip exposes structural urgency markers', () => {
  const statusCellRule = cssRule('.status-cell')
  const urgentRule = cssRule('.status-cell.urgent')
  const urgentBeforeRule = cssRule('.status-cell.urgent::before')

  assert.match(vueSource, /:class="\{ urgent: metric\.urgent \}"/)
  assert.match(statusCellRule, /position:\s*relative/)
  assert.match(statusCellRule, /overflow:\s*hidden/)
  assert.match(urgentRule, /border:\s*1px solid var\(--badge-warning-border\)/)
  assert.match(urgentRule, /background:[\s\S]*var\(--badge-warning-bg\)/)
  assert.match(urgentRule, /box-shadow:\s*inset 2px 0 0 var\(--badge-warning-border\),\s*var\(--glass-inner-shadow\)/)
  assert.match(urgentBeforeRule, /content:\s*""/)
  assert.match(urgentBeforeRule, /position:\s*absolute/)
  assert.match(urgentBeforeRule, /inset:\s*6px auto 6px 5px/)
  assert.match(urgentBeforeRule, /width:\s*2px/)
  assert.match(urgentBeforeRule, /background:\s*var\(--badge-warning-border\)/)
  assert.match(urgentBeforeRule, /pointer-events:\s*none/)
})

test('library organize top-level loading and error states use console state shells', () => {
  const shellRule = cssRule('.organize-state-shell')
  const ledgerRule = cssRule('.state-ledger')
  const ledgerSpanRule = cssRule('.state-ledger span')
  const consoleStateRule = cssRule('.console-state')

  assert.match(vueSource, /class="organize-state-shell"/)
  assert.match(vueSource, /class="state-ledger"/)
  assert.match(vueSource, /<AppleSkeleton[\s\S]*class="loading-panel console-state"[\s\S]*label="片库整理加载中"/)
  assert.match(vueSource, /<AppleErrorState[\s\S]*class="empty-panel console-state"[\s\S]*source-label="Library organize API"[\s\S]*details="overview · inventory · mapping"/)

  assert.match(shellRule, /display:\s*grid/)
  assert.match(shellRule, /gap:\s*6px/)
  assert.match(shellRule, /margin-bottom:\s*10px/)
  assert.match(ledgerRule, /display:\s*grid/)
  assert.match(ledgerRule, /grid-template-columns:\s*repeat\(3,\s*minmax\(0,\s*1fr\)\)/)
  assert.match(ledgerRule, /border:\s*1px solid var\(--glass-control-border\)/)
  assert.match(ledgerRule, backgroundIncludes('material-glass-control'))
  assert.match(ledgerRule, /font-family:\s*var\(--font-mono\)/)
  assert.match(ledgerRule, /font-variant-numeric:\s*tabular-nums/)
  assert.match(ledgerSpanRule, /overflow:\s*hidden/)
  assert.match(ledgerSpanRule, /text-overflow:\s*ellipsis/)
  assert.match(consoleStateRule, /max-width:\s*none/)
  assert.match(consoleStateRule, /margin:\s*0/)
  assert.match(consoleStateRule, /text-align:\s*left/)
})

test('library organize mobile controls preserve dense scan tracks', () => {
  assert.match(source, /@media \(max-width: 980px\)[\s\S]*\.state-ledger\s*\{[\s\S]*grid-template-columns:\s*repeat\(3,\s*minmax\(0,\s*1fr\)\)/)
  assert.match(source, /@media \(max-width: 640px\)[\s\S]*\.state-ledger\s*\{[\s\S]*grid-template-columns:\s*1fr/)
  assert.match(source, /@media \(max-width: 640px\)[\s\S]*\.status-cell\s*\{[\s\S]*min-height:\s*50px/)
  assert.match(source, /@media \(max-width: 640px\)[\s\S]*\.status-cell small\s*\{[\s\S]*display:\s*none/)
  assert.match(source, /@media \(max-width: 640px\)[\s\S]*\.priority-row\s*\{[\s\S]*grid-template-columns:\s*34px minmax\(0,\s*1fr\)\s*auto/)
  assert.match(source, /@media \(max-width: 640px\)[\s\S]*\.priority-mark\s*\{[\s\S]*width:\s*34px/)
})

test('library organize mobile tabs avoid an internal horizontal scroller', () => {
  assert.match(source, /@media \(max-width: 640px\)[\s\S]*\.organize-tabs\s*\{[\s\S]*display:\s*grid/)
  assert.match(source, /@media \(max-width: 640px\)[\s\S]*\.organize-tabs\s*\{[\s\S]*grid-template-columns:\s*repeat\(2,\s*minmax\(0,\s*1fr\)\)/)
  assert.match(source, /@media \(max-width: 640px\)[\s\S]*\.organize-tabs\s*\{[\s\S]*overflow-x:\s*visible/)
  assert.match(source, /@media \(max-width: 640px\)[\s\S]*\.tab-btn\s*\{[\s\S]*min-width:\s*0/)
  assert.match(source, /@media \(max-width: 640px\)[\s\S]*\.tab-btn\s*\{[\s\S]*justify-content:\s*center/)
  assert.match(source, /@media \(max-width: 640px\)[\s\S]*\.tab-btn\s*\{[\s\S]*padding:\s*0 8px/)
})

test('library organize tab counts read as compact console badges', () => {
  const tabRule = cssRule('.tab-btn')
  const tabCountRule = cssRule('.tab-count')
  const activeTabCountRule = cssRule('.tab-btn.active .tab-count')

  assert.match(vueSource, /<small v-if="tab\.count !== null" class="tab-count">\{\{\s*tab\.count\s*\}\}<\/small>/)
  assert.match(tabRule, /min-width:\s*0/)
  assert.match(tabCountRule, /display:\s*inline-flex/)
  assert.match(tabCountRule, /min-width:\s*24px/)
  assert.match(tabCountRule, /height:\s*20px/)
  assert.match(tabCountRule, /border:\s*1px solid var\(--glass-control-border\)/)
  assert.match(tabCountRule, backgroundIncludes('material-glass-subtle'))
  assert.match(tabCountRule, /font-variant-numeric:\s*tabular-nums/)
  assert.match(activeTabCountRule, /border-color:\s*var\(--glass-active-border\)/)
  assert.match(activeTabCountRule, backgroundIncludes('glass-active-material'))
  assert.match(source, /@media \(max-width: 640px\)[\s\S]*\.tab-count\s*\{[\s\S]*min-width:\s*22px/)
})

test('library organize exposes active filter ledgers for operational views', () => {
  assert.match(vueSource, /v-if="mappingFilterLedger\.length" class="filter-ledger organize-filter-ledger" aria-label="当前映射筛选"/)
  assert.match(vueSource, /v-if="candidateFilterLedger\.length" class="filter-ledger organize-filter-ledger" aria-label="当前候选筛选"/)
  assert.match(vueSource, /v-for="filter in mappingFilterLedger"/)
  assert.match(vueSource, /v-for="filter in candidateFilterLedger"/)
  assert.match(vueSource, /class="filter-token"/)
  assert.match(vueSource, /class="filter-reset"/)
  assert.match(source, /const mappingFilterLedger = computed\(\(\) => \{/)
  assert.match(source, /const candidateFilterLedger = computed\(\(\) => \{/)
  assert.match(source, /filters\.push\(\{ key: 'mapping_search'/)
  assert.match(source, /filters\.push\(\{ key: 'candidate_search'/)
  assert.match(source, /filters\.push\(\{ key: 'candidate_status'/)
  assert.match(source, /filters\.push\(\{ key: 'candidate_magnet'/)
  assert.match(source, /function clearCandidateFilters\(\) \{[\s\S]*candidateStatus\.value = ''/)

  const ledger = cssRule('.organize-filter-ledger')
  const token = cssRule('.filter-token')
  const reset = cssRule('.filter-reset')
  const resetFocus = cssRule('.filter-reset:focus-visible')

  assert.match(ledger, /display:\s*flex/)
  assert.match(ledger, /gap:\s*6px/)
  assert.match(ledger, /margin:\s*-4px 0 12px/)
  assert.match(ledger, /padding:\s*7px/)
  assert.match(ledger, /border:\s*1px solid var\(--glass-control-border\)/)
  assert.match(ledger, backgroundIncludes('material-glass-control'))
  assert.match(token, /font-family:\s*var\(--font-mono\)/)
  assert.match(token, /font-variant-numeric:\s*tabular-nums/)
  assert.match(token, backgroundIncludes('material-glass-subtle'))
  assert.match(reset, /border:\s*1px solid var\(--glass-control-border\)/)
  assert.match(reset, backgroundIncludes('material-glass-control'))
  assert.match(resetFocus, /box-shadow:\s*var\(--glass-control-shadow-hover\),\s*var\(--focus-ring\)/)
  assert.match(source, /@media \(max-width: 640px\)[\s\S]*\.organize-filter-ledger\s*\{[\s\S]*align-items:\s*stretch/)
})

test('library organize nested list rows mirror Apple glass hover while child actions are focused', () => {
  const nestedHoverRule = cssGroupedRule('.mapping-item:hover,')
  const nestedFocusRule = cssGroupedRule('.mapping-item:focus-within,')
  const darkNestedHoverRule = cssGroupedRule(':global(:root[data-theme="dark"] .mapping-item:hover),')
  const darkNestedFocusRule = cssGroupedRule(':global(:root[data-theme="dark"] .mapping-item:focus-within),')

  assert.match(source, /\.mapping-item:hover,\s*\.duplicate-group:hover,\s*\.job-row:hover,\s*\.duplicate-entry:hover,\s*\.check-item:hover,\s*\.inventory-candidate:hover,\s*\.missing-video:hover\s*\{/)
  assert.match(source, /\.mapping-item:focus-within,\s*\.duplicate-group:focus-within,\s*\.job-row:focus-within,\s*\.duplicate-entry:focus-within,\s*\.check-item:focus-within,\s*\.inventory-candidate:focus-within,\s*\.missing-video:focus-within\s*\{/)

  assert.match(nestedHoverRule, /border-color:\s*var\(--glass-control-border-hover\)/)
  assert.match(nestedHoverRule, backgroundIncludes('material-glass-control-hover'))
  assert.match(nestedHoverRule, /box-shadow:\s*var\(--glass-control-shadow-hover\)/)
  assert.match(nestedHoverRule, /transform:\s*translateY\(-1px\)/)

  assert.match(nestedFocusRule, /outline:\s*none/)
  assert.match(nestedFocusRule, /border-color:\s*var\(--glass-control-border-hover\)/)
  assert.match(nestedFocusRule, backgroundIncludes('material-glass-control-hover'))
  assert.match(nestedFocusRule, /box-shadow:\s*var\(--glass-control-shadow-hover\),\s*var\(--focus-ring\)/)
  assert.match(nestedFocusRule, /transform:\s*translateY\(-1px\)/)

  assert.match(darkNestedHoverRule, /border-color:\s*var\(--glass-control-border-hover\)/)
  assert.match(darkNestedHoverRule, backgroundIncludes('material-glass-control-hover'))
  assert.match(darkNestedHoverRule, /box-shadow:\s*var\(--glass-control-shadow-hover\)/)
  assert.match(darkNestedFocusRule, /border-color:\s*var\(--glass-control-border-hover\)/)
  assert.match(darkNestedFocusRule, backgroundIncludes('material-glass-control-hover'))
  assert.match(darkNestedFocusRule, /box-shadow:\s*var\(--glass-control-shadow-hover\),\s*var\(--focus-ring\)/)
  assert.match(darkNestedFocusRule, /transform:\s*translateY\(-1px\)/)
})

test('library organize nested controls keep glass treatment across light and dark themes', () => {
  const detailRule = cssRule('.actor-detail-head')
  const chipRule = cssGroupedRule('.candidate-pills button,')
  const chipActiveRule = cssRule('.chip.active')
  const autoMatchRule = cssRule('.auto-match-panel')

  assert.match(detailRule, /border: 1px solid var\(--glass-control-border\)/)
  assert.match(detailRule, backgroundIncludes('material-glass-control'))
  assert.match(chipRule, /box-shadow: var\(--glass-inner-shadow\)/)
  assert.match(chipActiveRule, backgroundIncludes('glass-active-material'))
  assert.match(autoMatchRule, backgroundIncludes('material-glass-control'))
  assert.match(source, /:global\(:root\[data-theme="dark"\] \.organize-header\)/)
  assert.match(source, /:global\(:root\[data-theme="dark"\] \.organize-status\)/)
  assert.doesNotMatch(externalStyle, /\.btn\.danger\s*\{/, 'danger buttons should use the global glass button treatment')
})

test('library organize inventory media placeholders use shared subtle glass material', () => {
  const posterRule = cssGroupedRule('.missing-video img,')
  const actorAvatarRule = cssRule('.actor-avatar')

  for (const rule of [posterRule, actorAvatarRule]) {
    assert.match(rule, backgroundIncludes('material-glass-subtle'))
    assert.match(rule, /border:\s*1px solid var\(--glass-control-border\)/)
    assert.match(rule, /box-shadow:\s*var\(--glass-inner-shadow\)/)
    assert.doesNotMatch(rule, /rgba\(255,\s*255,\s*255|linear-gradient\(145deg/)
  }
})

test('library organize dark theme overlays defer to shared material tokens', () => {
  const headerRule = darkRule('.organize-header)')
  const headerBeforeRule = darkRule('.organize-header::before)')
  const surfaceRule = darkRule('.organize-status),')
  const controlRule = darkRule('.status-cell),')
  const hoverRule = darkRule('.status-cell:hover),')
  const focusRule = darkRule('.mini-check-form input:focus),')

  assert.match(headerRule, /border-color:\s*var\(--glass-edge-strong\)/)
  assert.match(headerRule, backgroundIncludes('material-glass-elevated'))
  assert.doesNotMatch(headerRule, /rgba\(255,\s*255,\s*255|rgba\(255,255,255|linear-gradient|radial-gradient/)

  assert.match(headerBeforeRule, backgroundIncludes('material-glass-subtle'))
  assert.doesNotMatch(headerBeforeRule, /background-image|rgba\(255,\s*255,\s*255|rgba\(255,255,255/)

  assert.match(surfaceRule, /border-color:\s*var\(--glass-edge\)/)
  assert.match(surfaceRule, backgroundIncludes('material-glass-elevated'))
  assert.match(surfaceRule, /box-shadow:\s*var\(--glass-surface-shadow\)/)
  assert.doesNotMatch(surfaceRule, /rgba\(255,255,255/)
  assert.doesNotMatch(surfaceRule, /linear-gradient\(145deg/)

  assert.match(controlRule, /border-color:\s*var\(--glass-control-border\)/)
  assert.match(controlRule, backgroundIncludes('material-glass-control'))
  assert.doesNotMatch(controlRule, /rgba\(255,255,255/)
  assert.doesNotMatch(controlRule, /linear-gradient\(145deg/)

  assert.match(hoverRule, /border-color:\s*var\(--glass-control-border-hover\)/)
  assert.match(hoverRule, backgroundIncludes('material-glass-control-hover'))
  assert.match(hoverRule, /box-shadow:\s*var\(--glass-control-shadow-hover\)/)
  assert.doesNotMatch(hoverRule, /rgba\(255,255,255/)
  assert.doesNotMatch(hoverRule, /linear-gradient\(145deg/)

  assert.match(focusRule, /border-color:\s*var\(--glass-control-border-hover\)/)
  assert.match(focusRule, /box-shadow:\s*var\(--glass-control-shadow-hover\),\s*var\(--focus-ring-wide\)/)
  assert.doesNotMatch(focusRule, /rgba\(255,255,255/)
})

test('library organize first load uses compact overview instead of eight-way fanout', () => {
  const reloadAllBlock = source.match(/async function reloadAll\(\) \{[\s\S]*?\n\}/)?.[0] || ''

  assert.match(reloadAllBlock, /loadOverview\(\)/)
  assert.doesNotMatch(reloadAllBlock, /Promise\.all\(\[/)
  assert.match(source, /async function loadOverview\(\)/)
  assert.match(source, /api\.getLibraryOrganizeOverview/)
})

test('library organize uses overview totals instead of first page array length for queue metrics', () => {
  assert.match(source, /const missingTotal = ref\(0\)/)
  assert.match(source, /const duplicateTotal = ref\(0\)/)
  assert.match(source, /missingTotal\.value = Number\(data\?\.missing\?\.total \|\| missingVideos\.value\.length \|\| 0\)/)
  assert.match(source, /duplicateTotal\.value = Number\(data\?\.duplicates\?\.total \|\| duplicates\.value\.length \|\| 0\)/)
  assert.match(source, /\{ value: 'inventory', label: '库存对比', count: missingTotal\.value \}/)
  assert.match(source, /\{ value: 'duplicates', label: '重复清理', count: duplicateTotal\.value \}/)
  assert.match(source, /Number\(missingTotal\.value \|\| 0\)/)
  assert.match(source, /Number\(duplicateTotal\.value \|\| 0\)/)
})

test('library organize defers duplicate scan until duplicate tab is opened', () => {
  assert.match(source, /const duplicatesDeferred = ref\(false\)/)
  assert.match(source, /duplicatesDeferred\.value = Boolean\(data\?\.duplicates\?\.deferred\)/)
  assert.match(source, /function ensureDuplicateTabLoaded\(\)/)
  assert.match(source, /activeTab\.value === 'duplicates'[\s\S]*duplicatesDeferred\.value[\s\S]*loadDuplicates\(\)/)
  assert.match(source, /watch\(activeTab, ensureDuplicateTabLoaded\)/)
})

test('library organize requests a bounded missing-video page', () => {
  assert.match(source, /api\.listInventoryMissing\(\{ page: 1, page_size: 80 \}\)/)
})

test('library organize glass backgrounds are layered with specular and noise surfaces', () => {
  assert.deepEqual(singleLayerGlassBackgrounds(externalStyle), [])
})
