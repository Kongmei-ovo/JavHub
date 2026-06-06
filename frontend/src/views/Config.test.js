import test from 'node:test'
import assert from 'node:assert/strict'
import { existsSync, readFileSync } from 'node:fs'

const vueSource = readFileSync(new URL('./Config.vue', import.meta.url), 'utf8')
const advancedPanelSource = readFileSync(new URL('../features/config/AdvancedSettingsPanel.vue', import.meta.url), 'utf8')
const baseStyle = readFileSync(new URL('../features/config/config.css', import.meta.url), 'utf8')
const advancedStyleUrl = new URL('../features/config/advancedSettingsPanel.css', import.meta.url)
const advancedStyle = existsSync(advancedStyleUrl) ? readFileSync(advancedStyleUrl, 'utf8') : ''
const externalStyle = `${baseStyle}\n${advancedStyle}`
const source = `${vueSource}\n${advancedPanelSource}\n${externalStyle}`
const cssBlocksBySelector = new Map()

for (const [, selectors, block] of source.matchAll(/([^{}]+)\{([^{}]*)\}/g)) {
  for (const selector of selectors.split(',').map(part => part.trim())) {
    cssBlocksBySelector.set(
      selector,
      `${cssBlocksBySelector.get(selector) || ''}${selectors.trim()} {${block}}\n`
    )
  }
}

function cssBlock(selector) {
  return cssBlocksBySelector.get(selector) || ''
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

function selectorDefinitionCount(css, selector) {
  const escaped = selector.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  return [...css.matchAll(new RegExp(`(?:^|\\n)\\s*${escaped}\\s*\\{`, 'g'))].length
}

function vueSectionBlock(className) {
  const start = vueSource.indexOf(`<section class="${className}">`)
  assert.notEqual(start, -1, `expected ${className} section to exist`)
  const end = vueSource.indexOf('\n              </section>', start)
  assert.notEqual(end, -1, `expected ${className} section to close`)
  return vueSource.slice(start, end)
}

test('settings secret reveal controls use shared Apple glass button chrome', () => {
  const base = cssBlock('.input-eye-btn')
  assert.match(base, backgroundIncludes('material-glass-control'))
  assert.match(base, /border:\s*1px solid var\(--glass-control-border\)/)
  assert.match(base, /box-shadow:\s*var\(--glass-control-shadow\)/)
  assert.match(base, /backdrop-filter:\s*blur\(var\(--glass-blur-control\)\)\s*saturate\(var\(--glass-saturate-control\)\)/)
  assert.match(base, /transition:\s*transform var\(--motion-standard\),\s*opacity var\(--motion-fast\)/)
  assert.doesNotMatch(base, /transition:[^;]*(?:background|border-color|box-shadow|color|filter|backdrop-filter)/)
  assert.doesNotMatch(base, /background:\s*none|border:\s*none|transition:\s*all/)

  const hover = cssBlock('.input-eye-btn:hover')
  assert.match(hover, backgroundIncludes('material-glass-control-hover'))
  assert.match(hover, /border-color:\s*var\(--glass-control-border-hover\)/)
  assert.match(hover, /box-shadow:\s*var\(--glass-control-shadow-hover\)/)

  const focus = cssBlock('.input-eye-btn:focus-visible')
  assert.match(focus, /outline:\s*none/)
  assert.match(focus, /box-shadow:\s*var\(--glass-control-shadow\),\s*var\(--focus-ring-wide-strong\)/)
})

test('settings controls mirror hover glass treatment for keyboard focus', () => {
  const hoverSelectors = [
    '.tab-item:hover',
    '.source-check-item:hover',
    '.segmented-mini button:hover',
  ]

  for (const selector of hoverSelectors) {
    const block = cssBlock(selector)
    assert.match(block, backgroundIncludes('material-glass-control-hover'), `${selector} should use hover glass material`)
    assert.match(block, /border-color:\s*var\(--glass-control-border-hover\)/, `${selector} should use hover border`)
    assert.match(block, /box-shadow:\s*var\(--glass-control-shadow-hover\)/, `${selector} should use hover shadow`)
    assert.match(block, /transform:\s*translateY\(-1px\)/, `${selector} should lift lightly`)
  }

  const focusSelectors = [
    '.tab-item:focus-visible',
    '.source-check-item:focus-within',
    '.segmented-mini button:focus-visible',
  ]

  for (const selector of focusSelectors) {
    const block = cssBlock(selector)
    assert.match(block, /outline:\s*none/, `${selector} should avoid double native focus chrome`)
    assert.match(block, backgroundIncludes('material-glass-control-hover'), `${selector} should use hover glass material`)
    assert.match(block, /border-color:\s*var\(--glass-control-border-hover\)/, `${selector} should use hover border`)
    assert.match(block, /box-shadow:\s*var\(--glass-control-shadow-hover\),\s*var\(--focus-ring\)/, `${selector} should add a soft focus halo`)
    assert.match(block, /transform:\s*translateY\(-1px\)/, `${selector} should keep the hover lift while focused`)
  }

  for (const selector of ['.tab-item.active:focus-visible', '.segmented-mini button.active:focus-visible']) {
    const block = cssBlock(selector)
    assert.match(block, /outline:\s*none/, `${selector} should avoid double native focus chrome`)
    assert.match(block, backgroundIncludes('glass-active-material'), `${selector} should preserve active glass material`)
    assert.match(block, /border-color:\s*var\(--glass-active-border\)/, `${selector} should keep active border`)
    assert.match(block, /box-shadow:\s*var\(--glass-active-shadow\),\s*var\(--focus-ring\)/, `${selector} should combine active depth with focus halo`)
    assert.match(block, /transform:\s*translateY\(-1px\)/, `${selector} should stay lifted while focused`)
  }
})

test('settings workspace panels use shared Apple glass materials instead of legacy cards', () => {
  const cardContent = cssBlock('.card-content')
  const formSlot = cssBlock('.form-slot')
  const runtimePanel = cssBlock('.javinfo-runtime-panel')
  const sourceCheck = cssBlock('.source-check-item')
  const appearanceStack = cssBlock('.appearance-settings-stack')
  const sharedGroup = cssBlock('.settings-group')
  const sharedList = cssBlock('.settings-list')
  const importFileControl = cssBlock('.import-file-control')
  const importProgress = cssBlock('.import-progress')
  const importLogTail = cssBlock('.import-log-tail')
  const importJobRow = cssBlock('.import-job-row')
  const settingsTabs = cssBlock('.settings-tabs')

  for (const block of [cardContent, formSlot, runtimePanel, sourceCheck, appearanceStack, sharedGroup, sharedList, importFileControl, importProgress, importLogTail, importJobRow]) {
    assert.ok(block, 'expected settings workspace block to exist')
    assert.doesNotMatch(block, /var\(--bg-card\)|var\(--border\)|var\(--border-light\)|var\(--shadow-card\)|var\(--surface-card\)/)
  }

  assert.match(cardContent, backgroundIncludes('material-glass-sheet'))
  assert.match(cardContent, /border:\s*1px solid var\(--glass-edge\)/)
  assert.match(cardContent, /box-shadow:\s*var\(--glass-surface-shadow\)/)

  for (const block of [formSlot, runtimePanel, sharedList, importProgress, importJobRow]) {
    assert.match(block, /background:[\s\S]*var\(--material-glass-(?:subtle|control)\)/)
    assert.match(block, /border:\s*1px solid var\(--glass-control-border\)/)
  }

  assert.match(sharedGroup, backgroundIncludes('material-glass-sheet'))
  assert.match(sharedGroup, /border:\s*1px solid var\(--glass-edge\)/)
  assert.match(sourceCheck, backgroundIncludes('material-glass-control'))
  assert.match(sourceCheck, /box-shadow:\s*var\(--glass-control-shadow\)/)
  assert.match(importFileControl, /border:\s*1px dashed var\(--glass-control-border\)/)
  assert.match(importLogTail, backgroundIncludes('material-glass-control'))
  assert.match(settingsTabs, /scrollbar-color:\s*var\(--glass-edge\) transparent/)
  assert.doesNotMatch(settingsTabs, /var\(--border-light\)/)
})

test('settings visual preview and loading states avoid hardcoded white glass fragments', () => {
  const auraPreview = cssBlock('.aura-preview')
  const previewBubble = cssBlock('.preview-bubble')

  assert.match(vueSource, /import AppleSkeleton from '\.\.\/components\/AppleSkeleton\.vue'/)
  assert.match(vueSource, /<AppleSkeleton\s+v-if="configLoading"[\s\S]*label="配置加载中"/)
  assert.doesNotMatch(vueSource, /<div class="spinner-large"><\/div>/)

  assert.match(auraPreview, backgroundIncludes('material-glass-subtle'))
  assert.match(auraPreview, /box-shadow:\s*var\(--glass-inner-shadow\)/)
  assert.doesNotMatch(auraPreview, /radial-gradient|rgba\(255,\s*255,\s*255|rgba\(255,255,255/)

  assert.match(previewBubble, /box-shadow:\s*var\(--glass-inner-shadow\)/)
  assert.doesNotMatch(previewBubble, /rgba\(255,\s*255,\s*255|rgba\(255,255,255/)
})

test('settings page keeps heavyweight styles in external scoped stylesheets', () => {
  assert.match(vueSource, /<style scoped src="\.\.\/features\/config\/config\.css"><\/style>/)
  assert.ok(baseStyle.length > 16000, 'settings shell stylesheet should carry shared workspace CSS')
  assert.ok(advancedStyle.length > 5000, 'advanced lazy chunk should carry its own workspace CSS')
  assert.ok(vueSource.split('\n').length < 1300, 'Config.vue should stay small enough to review and parse quickly')
})

test('settings advanced workspace stays in a lazy child chunk', () => {
  assert.match(vueSource, /const AdvancedSettingsPanel = defineAsyncComponent\(\(\) => import\('\.\.\/features\/config\/AdvancedSettingsPanel\.vue'\)\)/)
  assert.match(vueSource, /<AdvancedSettingsPanel\s+v-else-if="activeGroup === 'advanced'"/)
  assert.doesNotMatch(vueSource, /JavInfo 数据库导入/)
  assert.doesNotMatch(vueSource, /<h2>公共智能模型<\/h2>/)
  assert.doesNotMatch(vueSource, /<h2>网络代理<\/h2>/)
})

test('settings advanced lazy chunk owns its scoped stylesheet boundary', () => {
  assert.match(advancedPanelSource, /<style scoped src="\.\/advancedSettingsPanel\.css"><\/style>/)
  assert.match(vueSource, /<style scoped src="\.\.\/features\/config\/config\.css"><\/style>/)
  assert.match(advancedStyle, /\.javinfo-import-panel\s*\{/)
  assert.match(advancedStyle, /\.card-content\s*\{/)
  assert.doesNotMatch(baseStyle, /\.javinfo-import-panel\s*\{|\.import-log-tail\s*\{|\.ai-provider-control\s*\{/)
})

test('settings glass backgrounds are layered with specular and noise surfaces', () => {
  assert.deepEqual(singleLayerGlassBackgrounds(externalStyle), [])
})

test('settings page exposes macOS-style grouped lists and row controls', () => {
  assert.match(vueSource, /class="settings-header-meta"/)
  assert.match(vueSource, /class="settings-sidebar-list"/)
  assert.match(vueSource, /class="settings-pane"/)
  assert.match(vueSource, /class="settings-group"/)
  assert.match(vueSource, /class="settings-list"/)
  assert.match(vueSource, /class="settings-row"/)
  assert.match(vueSource, /class="settings-control"/)
  assert.match(vueSource, /aria-current="activeGroup === group\.id \? 'page' : undefined"/)

  const shell = cssBlock('.settings-shell')
  const sidebar = cssBlock('.settings-sidebar-list')
  const pane = cssBlock('.settings-pane')
  const group = cssBlock('.settings-group')
  const row = cssBlock('.settings-row')
  const control = cssBlock('.settings-control')

  assert.match(shell, /display:\s*grid/)
  assert.match(shell, /grid-template-columns:\s*minmax\(190px,\s*240px\)\s+minmax\(0,\s*1fr\)/)
  assert.match(sidebar, backgroundIncludes('material-glass-sheet'))
  assert.match(pane, /max-width:\s*920px/)
  assert.match(group, /border-radius:\s*var\(--radius-lg\)/)
  assert.match(row, /grid-template-columns:\s*minmax\(180px,\s*0\.42fr\)\s+minmax\(0,\s*1fr\)/)
  assert.match(control, /justify-self:\s*end/)
})

test('settings save footer exposes a System Settings-style status area', () => {
  assert.match(vueSource, /class="settings-footer"/)
  assert.match(vueSource, /:aria-busy="saving"/)
  assert.match(vueSource, /aria-live="polite"/)
  assert.match(vueSource, /class="settings-save-status"/)
  assert.match(vueSource, /role="status"/)
  assert.match(vueSource, /id="config-save-status"/)
  assert.match(vueSource, /{{ saveFooterTitle }}/)
  assert.match(vueSource, /{{ saveFooterNote }}/)
  assert.match(vueSource, /class="settings-save-actions"/)
  assert.match(vueSource, /:aria-describedby="'config-save-status'"/)
  assert.match(vueSource, /saveFooterTitle\(\)/)
  assert.match(vueSource, /saveFooterNote\(\)/)

  const footer = cssBlock('.settings-footer')
  const content = cssBlock('.footer-content')
  const status = cssBlock('.settings-save-status')
  const actions = cssBlock('.settings-save-actions')
  const mobile = baseStyle.slice(baseStyle.indexOf('@media (max-width: 768px)'))

  assert.match(footer, backgroundIncludes('material-glass-sheet'))
  assert.match(footer, /border-top:\s*1px solid var\(--glass-edge\)/)
  assert.match(content, /display:\s*grid/)
  assert.match(content, /grid-template-columns:\s*minmax\(0,\s*1fr\)\s+auto/)
  assert.match(status, /min-width:\s*0/)
  assert.match(status, /color:\s*var\(--text-secondary\)/)
  assert.match(actions, /justify-content:\s*flex-end/)
  assert.match(mobile, /\.footer-content\s*\{[\s\S]*grid-template-columns:\s*1fr/)
  assert.match(mobile, /\.settings-save-actions\s*\{[\s\S]*width:\s*100%/)
  assert.match(mobile, /bottom:\s*calc\(var\(--settings-mobile-footer-offset\)\s*\+\s*8px\)/)
  assert.match(mobile, /--settings-mobile-footer-offset:\s*var\(--mobile-bottom-nav-reserve,\s*calc\(70px\s*\+\s*max\(10px,\s*env\(safe-area-inset-bottom,\s*0px\)\)\s*\+\s*12px\)\)/)
})

test('settings save footer stays viewport anchored during page transitions', () => {
  const transitionRule = cssBlock('.settings.page-enter-active')

  assert.match(vueSource, /<Teleport to="body">[\s\S]*class="settings-footer"/)
  assert.match(transitionRule, /\.settings\.page-enter-from/)
  assert.match(transitionRule, /\.settings\.page-enter-active/)
  assert.match(transitionRule, /\.settings\.page-enter-to/)
  assert.match(transitionRule, /\.settings\.page-leave-from/)
  assert.match(transitionRule, /\.settings\.page-leave-active/)
  assert.match(transitionRule, /\.settings\.page-leave-to/)
  assert.match(transitionRule, /transform:\s*none\s*!important/)
})

test('advanced import flow marks dangerous and busy states explicitly', () => {
  assert.match(advancedPanelSource, /class="[^"]*\badvanced-settings-stack\b/)
  assert.match(advancedPanelSource, /class="advanced-settings-group import-danger-zone"/)
  assert.match(advancedPanelSource, /class="import-step-list"/)
  assert.match(advancedPanelSource, /class="import-step"/)
  assert.match(advancedPanelSource, /class="danger-summary"/)
  assert.match(advancedPanelSource, /class="btn btn-danger"/)
  assert.match(advancedPanelSource, /aria-busy="javinfoImportUploading \|\| isJavInfoImportActive\(javinfoImportJob\)"/)
  assert.match(advancedPanelSource, /aria-live="polite"/)

  const stack = cssBlock('.advanced-settings-stack')
  const group = cssBlock('.advanced-settings-group')
  const dangerZone = cssBlock('.import-danger-zone')
  const stepList = cssBlock('.import-step-list')
  const step = cssBlock('.import-step')
  const dangerSummary = cssBlock('.danger-summary')
  const dangerButton = cssBlock('.btn-danger')
  const busyPanel = cssBlock('.javinfo-import-panel[aria-busy="true"]')

  assert.match(stack, /display:\s*grid/)
  assert.match(group, backgroundIncludes('material-glass-sheet'))
  assert.match(dangerZone, /border-color:\s*var\(--badge-error-border\)/)
  assert.match(stepList, /counter-reset:\s*import-step/)
  assert.match(step, /grid-template-columns:\s*32px\s+minmax\(0,\s*1fr\)/)
  assert.match(dangerSummary, backgroundIncludes('badge-error-bg'))
  assert.match(dangerButton, /color:\s*var\(--badge-error-text\)/)
  assert.match(dangerButton, /border-color:\s*var\(--badge-error-border\)/)
  assert.match(busyPanel, /cursor:\s*progress/)
})

test('advanced settings chunk keeps every panel in grouped settings rows', () => {
  assert.doesNotMatch(advancedPanelSource, /<div class="settings-card">/)
  assert.match(advancedPanelSource, /<section class="advanced-settings-group ai-settings-group">/)
  assert.match(advancedPanelSource, /<section class="advanced-settings-group proxy-settings-group">/)

  const row = cssBlock('.advanced-settings-group .settings-row')
  const control = cssBlock('.advanced-settings-group .settings-control')
  const list = cssBlock('.advanced-settings-group .settings-list')

  assert.match(list, backgroundIncludes('material-glass-subtle'))
  assert.match(row, /grid-template-columns:\s*minmax\(180px,\s*0\.42fr\)\s+minmax\(0,\s*1fr\)/)
  assert.match(control, /justify-self:\s*end/)
})

test('settings base tabs have no legacy card form layouts after grouping pass', () => {
  assert.doesNotMatch(vueSource, /<div class="settings-card">/)
  assert.doesNotMatch(vueSource, /<div class="form-slot">/)
  assert.match(vueSource, /class="settings-group telegram-settings-group"/)
  assert.match(vueSource, /class="settings-group notification-settings-group"/)
  assert.match(vueSource, /class="settings-group automation-settings-group"/)
  assert.match(vueSource, /class="settings-group torznab-settings-group"/)
  assert.match(vueSource, /class="settings-group crawler-settings-group"/)
  assert.match(vueSource, /class="settings-group inventory-schedule-group"/)

  const actionRow = cssBlock('.settings-row--actions')
  const toggleRow = cssBlock('.settings-row--toggle')

  assert.match(actionRow, /align-items:\s*start/)
  assert.match(toggleRow, /min-height:\s*54px/)
})

test('advanced import exposes a macOS-style readiness summary before danger action', () => {
  assert.match(advancedPanelSource, /class="import-readiness-summary"/)
  assert.match(advancedPanelSource, /javinfoImportReadinessItems/)
  assert.match(advancedPanelSource, /class="\['readiness-row', item\.state\]"/)
  assert.match(advancedPanelSource, /id="javinfo-import-start-note"/)
  assert.match(advancedPanelSource, /:aria-describedby="'javinfo-import-danger-action-status javinfo-import-start-note'"/)

  const summary = cssBlock('.import-readiness-summary')
  const row = cssBlock('.readiness-row')
  const ready = cssBlock('.readiness-row.ready')
  const pending = cssBlock('.readiness-row.pending')
  const note = cssBlock('.danger-action-note')

  assert.match(summary, backgroundIncludes('material-glass-subtle'))
  assert.match(summary, /border:\s*1px solid var\(--glass-control-border\)/)
  assert.match(row, /grid-template-columns:\s*16px\s+minmax\(0,\s*1fr\)/)
  assert.match(ready, /color:\s*var\(--badge-success-text\)/)
  assert.match(pending, /color:\s*var\(--text-muted\)/)
  assert.match(note, /color:\s*var\(--text-muted\)/)
})

test('advanced import progress exposes accessible loading semantics', () => {
  assert.match(advancedPanelSource, /class="progress-bar"/)
  assert.match(advancedPanelSource, /role="progressbar"/)
  assert.match(advancedPanelSource, /aria-label="JavInfo 数据库导入进度"/)
  assert.match(advancedPanelSource, /aria-valuemin="0"/)
  assert.match(advancedPanelSource, /aria-valuemax="100"/)
  assert.match(advancedPanelSource, /:aria-valuenow="javinfoImportProgress"/)
  assert.match(advancedPanelSource, /class="progress-bar-fill"/)

  const progress = cssBlock('.import-progress .progress-bar')
  const fill = cssBlock('.import-progress .progress-bar-fill')

  assert.match(progress, /overflow:\s*hidden/)
  assert.match(progress, /background:[\s\S]*var\(--material-glass-control\)/)
  assert.match(fill, /transform-origin:\s*left center/)
  assert.match(fill, /transition:\s*transform var\(--motion-standard\)/)
})

test('advanced import preflight actions expose busy status semantics', () => {
  assert.match(advancedPanelSource, /class="import-actions import-actions--preflight"/)
  assert.match(advancedPanelSource, /:aria-busy="javinfoImportPreflighting \|\| javinfoMigrating"/)
  assert.match(advancedPanelSource, /aria-live="polite"/)
  assert.match(advancedPanelSource, /id="javinfo-preflight-action-status"/)
  assert.match(advancedPanelSource, /role="status"/)
  assert.match(advancedPanelSource, /{{ javinfoPreflightActionStatus }}/)
  assert.match(advancedPanelSource, /javinfoPreflightActionStatus\(\)/)

  const actions = cssBlock('.import-actions--preflight')
  const status = cssBlock('.import-action-status')
  const busy = cssBlock('.import-actions--preflight[aria-busy="true"]')

  assert.match(actions, /align-items:\s*center/)
  assert.match(status, /color:\s*var\(--text-muted\)/)
  assert.match(status, /font-size:\s*12px/)
  assert.match(busy, /cursor:\s*progress/)
})

test('advanced export flow exposes readiness and busy status before download action', () => {
  assert.match(advancedPanelSource, /class="advanced-settings-group export-settings-group"/)
  assert.match(advancedPanelSource, /:aria-busy="exportingConfig"/)
  assert.match(advancedPanelSource, /aria-live="polite"/)
  assert.match(advancedPanelSource, /class="export-readiness-summary"/)
  assert.match(advancedPanelSource, /exportReadinessItems/)
  assert.match(advancedPanelSource, /class="\['export-readiness-row', item\.state\]"/)
  assert.match(advancedPanelSource, /id="config-export-note"/)
  assert.match(advancedPanelSource, /:aria-describedby="'config-export-note'"/)

  const group = cssBlock('.export-settings-group[aria-busy="true"]')
  const summary = cssBlock('.export-readiness-summary')
  const row = cssBlock('.export-readiness-row')
  const ready = cssBlock('.export-readiness-row.ready')
  const pending = cssBlock('.export-readiness-row.pending')
  const note = cssBlock('.export-action-note')

  assert.match(group, /cursor:\s*progress/)
  assert.match(summary, backgroundIncludes('material-glass-subtle'))
  assert.match(summary, /border:\s*1px solid var\(--glass-control-border\)/)
  assert.match(row, /grid-template-columns:\s*16px\s+minmax\(0,\s*1fr\)/)
  assert.match(ready, /color:\s*var\(--badge-success-text\)/)
  assert.match(pending, /color:\s*var\(--text-muted\)/)
  assert.match(note, /color:\s*var\(--text-muted\)/)
})

test('appearance settings use the shared macOS grouped row layout', () => {
  const appearanceSections = {
    global: vueSectionBlock('settings-group appearance-global-group'),
    search: vueSectionBlock('settings-group appearance-search-group'),
    discovery: vueSectionBlock('settings-group appearance-discovery-group'),
    visual: vueSectionBlock('settings-group appearance-visual-group'),
  }

  assert.match(vueSource, /class="appearance-settings-stack"/)
  assert.match(vueSource, /class="settings-group appearance-global-group"/)
  assert.match(vueSource, /class="settings-group appearance-search-group"/)
  assert.match(vueSource, /class="settings-group appearance-discovery-group"/)
  assert.match(vueSource, /class="settings-group appearance-visual-group"/)
  assert.match(appearanceSections.global, /<h2>全局偏好<\/h2>/)
  assert.match(appearanceSections.search, /<h2>影片检索<\/h2>/)
  assert.match(appearanceSections.discovery, /<h2>随机探索<\/h2>/)
  assert.match(appearanceSections.visual, /<h2>题材 \/ 系列气泡<\/h2>/)
  assert.doesNotMatch(vueSource, /class="preference-stack"|class="preference-section"|class="scope-card"/)
  assert.doesNotMatch(vueSource, /class="appearance-setting-row"/)

  const stack = cssBlock('.appearance-settings-stack')
  const visualGroup = cssBlock('.appearance-visual-group .settings-list')
  const visualRow = cssBlock('.appearance-visual-row')

  assert.match(stack, /display:\s*grid/)
  assert.match(stack, /gap:\s*18px/)
  assert.match(visualGroup, /overflow:\s*visible/)
  assert.match(visualRow, /align-items:\s*start/)
})

test('advanced export readiness styles are defined once in the lazy stylesheet', () => {
  const baseAdvancedStyle = advancedStyle.split('@media')[0]

  for (const selector of [
    '.export-settings-group[aria-busy="true"]',
    '.export-readiness-summary',
    '.export-readiness-row',
    '.export-readiness-row span',
    '.export-readiness-row p',
    '.export-readiness-row.ready',
    '.export-readiness-row.pending',
    '.export-action-control',
    '.export-action-note',
  ]) {
    assert.equal(selectorDefinitionCount(baseAdvancedStyle, selector), 1, `${selector} should have one base definition`)
  }

  assert.match(advancedStyle, /@media \(max-width:\s*768px\)[\s\S]*\.export-action-control\s*\{[\s\S]*justify-items:\s*stretch/)
  assert.match(advancedStyle, /@media \(max-width:\s*768px\)[\s\S]*\.export-action-note\s*\{[\s\S]*text-align:\s*left/)
})

test('advanced import file and confirmation controls use row-native settings structure', () => {
  assert.match(advancedPanelSource, /class="settings-row settings-row--stacked import-file-row"/)
  assert.match(advancedPanelSource, /class="import-file-control"/)
  assert.doesNotMatch(advancedPanelSource, /class="form-group import-file-drop"/)
  assert.match(advancedPanelSource, /class="settings-row settings-row--toggle import-confirm-row"/)
  assert.match(advancedPanelSource, /class="settings-row settings-row--toggle import-confirm-row import-confirm-row--direct"/)
  assert.doesNotMatch(advancedPanelSource, /class="form-group checkbox import-confirm"/)

  const fileRow = cssBlock('.import-file-row')
  const fileControl = cssBlock('.import-file-control')
  const confirmRow = cssBlock('.import-confirm-row')

  assert.match(fileRow, /align-items:\s*start/)
  assert.match(fileControl, /border:\s*1px dashed var\(--glass-control-border\)/)
  assert.match(fileControl, backgroundIncludes('material-glass-subtle'))
  assert.match(confirmRow, /grid-template-columns:\s*minmax\(0,\s*1fr\)\s+auto/)
  assert.match(confirmRow, /cursor:\s*pointer/)
})

test('advanced import file picker exposes explicit file status and busy semantics', () => {
  assert.match(advancedPanelSource, /:aria-busy="javinfoImportFileInputDisabled"/)
  assert.match(advancedPanelSource, /:aria-disabled="javinfoImportFileInputDisabled"/)
  assert.match(advancedPanelSource, /:class="\{ 'is-selected': javinfoImportFile \}"/)
  assert.match(advancedPanelSource, /id="javinfo-import-file-status"/)
  assert.match(advancedPanelSource, /role="status"/)
  assert.match(advancedPanelSource, /{{ javinfoImportFileStatus }}/)
  assert.match(advancedPanelSource, /id="javinfo-import-file-note"/)
  assert.match(advancedPanelSource, /{{ javinfoImportFileNote }}/)
  assert.match(advancedPanelSource, /:disabled="javinfoImportFileInputDisabled"/)
  assert.match(advancedPanelSource, /aria-describedby="javinfo-import-file-status javinfo-import-file-note"/)
  assert.match(advancedPanelSource, /javinfoImportFileInputDisabled\(\)/)
  assert.match(advancedPanelSource, /javinfoImportFileStatus\(\)/)
  assert.match(advancedPanelSource, /javinfoImportFileNote\(\)/)

  const fileControl = cssBlock('.import-file-control')
  const fileState = cssBlock('.import-file-state')
  const selectedDot = cssBlock('.import-file-control.is-selected .import-file-state-dot')
  const disabledControl = cssBlock('.import-file-control[aria-disabled="true"]')
  const status = cssBlock('.import-file-status')
  const note = cssBlock('.import-file-note')

  assert.match(fileControl, /position:\s*relative/)
  assert.match(fileState, /grid-template-columns:\s*10px\s+minmax\(0,\s*1fr\)/)
  assert.match(fileState, backgroundIncludes('material-glass-control'))
  assert.match(selectedDot, /background:\s*var\(--badge-success-text\)/)
  assert.match(disabledControl, /cursor:\s*progress/)
  assert.match(status, /overflow-wrap:\s*anywhere/)
  assert.match(note, /color:\s*var\(--text-muted\)/)
})

test('advanced import recent jobs render as a grouped status list with an empty state', () => {
  assert.match(advancedPanelSource, /class="settings-list import-job-settings-list"/)
  assert.match(advancedPanelSource, /class="settings-row settings-row--stacked import-job-summary-row"/)
  assert.match(advancedPanelSource, /id="javinfo-import-job-summary"/)
  assert.match(advancedPanelSource, /role="status"/)
  assert.match(advancedPanelSource, /{{ javinfoImportJobSummary }}/)
  assert.match(advancedPanelSource, /class="import-job-items"/)
  assert.match(advancedPanelSource, /class="import-job-empty"/)
  assert.match(advancedPanelSource, /v-if="javinfoImportJobs.length"/)
  assert.match(advancedPanelSource, /v-else/)
  assert.match(advancedPanelSource, /{{ javinfoImportJobEmptyNote }}/)
  assert.match(advancedPanelSource, /class="import-job-meta"/)
  assert.match(advancedPanelSource, /{{ javinfoImportJobDetail\(job\) }}/)
  assert.match(advancedPanelSource, /javinfoImportJobSummary\(\)/)
  assert.match(advancedPanelSource, /javinfoImportJobEmptyNote\(\)/)
  assert.match(advancedPanelSource, /javinfoImportJobDetail\(job\)/)

  const settingsList = cssBlock('.import-job-settings-list')
  const summaryRow = cssBlock('.import-job-summary-row')
  const items = cssBlock('.import-job-items')
  const empty = cssBlock('.import-job-empty')
  const row = cssBlock('.import-job-row')
  const meta = cssBlock('.import-job-meta')

  assert.match(settingsList, /margin-top:\s*4px/)
  assert.match(summaryRow, /align-items:\s*start/)
  assert.match(items, /display:\s*grid/)
  assert.match(empty, backgroundIncludes('material-glass-control'))
  assert.match(empty, /color:\s*var\(--text-muted\)/)
  assert.match(row, /grid-template-columns:\s*minmax\(0,\s*1fr\)\s+auto/)
  assert.match(row, backgroundIncludes('material-glass-control'))
  assert.match(meta, /color:\s*var\(--text-muted\)/)
})

test('advanced import danger actions expose a dedicated busy status row', () => {
  assert.match(advancedPanelSource, /class="import-actions import-actions--danger"/)
  assert.match(advancedPanelSource, /:aria-busy="javinfoImportDangerActionsBusy"/)
  assert.match(advancedPanelSource, /aria-live="polite"/)
  assert.match(advancedPanelSource, /id="javinfo-import-danger-action-status"/)
  assert.match(advancedPanelSource, /role="status"/)
  assert.match(advancedPanelSource, /{{ javinfoImportDangerActionStatus }}/)
  assert.match(advancedPanelSource, /:aria-describedby="'javinfo-import-danger-action-status javinfo-import-start-note'"/)
  assert.match(advancedPanelSource, /javinfoImportDangerActionsBusy\(\)/)
  assert.match(advancedPanelSource, /javinfoImportDangerActionStatus\(\)/)

  const actions = cssBlock('.import-actions--danger')
  const status = cssBlock('.import-danger-action-status')
  const busy = cssBlock('.import-actions--danger[aria-busy="true"]')

  assert.match(actions, /display:\s*grid/)
  assert.match(actions, /grid-template-columns:\s*auto\s+minmax\(0,\s*1fr\)/)
  assert.match(actions, /align-items:\s*center/)
  assert.match(status, /color:\s*var\(--text-secondary\)/)
  assert.match(status, /overflow-wrap:\s*anywhere/)
  assert.match(busy, /cursor:\s*progress/)
})

test('advanced AI connection check exposes System Settings-style busy status', () => {
  assert.match(advancedPanelSource, /class="settings-control settings-control--wide ai-test-row"/)
  assert.match(advancedPanelSource, /:aria-busy="aiConnectionBusy"/)
  assert.match(advancedPanelSource, /aria-live="polite"/)
  assert.match(advancedPanelSource, /id="ai-connection-status"/)
  assert.match(advancedPanelSource, /role="status"/)
  assert.match(advancedPanelSource, /{{ aiConnectionStatus }}/)
  assert.match(advancedPanelSource, /:aria-describedby="'ai-connection-status'"/)
  assert.match(advancedPanelSource, /aiConnectionBusy\(\)/)
  assert.match(advancedPanelSource, /aiConnectionStatus\(\)/)

  const row = cssBlock('.ai-test-row')
  const buttons = cssBlock('.ai-test-actions')
  const status = cssBlock('.ai-connection-status')
  const busy = cssBlock('.ai-test-row[aria-busy="true"]')

  assert.match(row, /display:\s*grid/)
  assert.match(row, /grid-template-columns:\s*auto\s+minmax\(0,\s*1fr\)/)
  assert.match(buttons, /display:\s*flex/)
  assert.match(status, /color:\s*var\(--text-secondary\)/)
  assert.match(status, /overflow-wrap:\s*anywhere/)
  assert.match(busy, /cursor:\s*progress/)
})

test('telegram test action exposes System Settings-style busy status', () => {
  assert.match(vueSource, /class="settings-control settings-control--wide telegram-test-row"/)
  assert.match(vueSource, /:aria-busy="telegramTestBusy"/)
  assert.match(vueSource, /aria-live="polite"/)
  assert.match(vueSource, /id="telegram-test-status"/)
  assert.match(vueSource, /role="status"/)
  assert.match(vueSource, /{{ telegramTestStatus }}/)
  assert.match(vueSource, /:aria-describedby="'telegram-test-status'"/)
  assert.match(vueSource, /telegramTestBusy\(\)/)
  assert.match(vueSource, /telegramTestStatus\(\)/)

  const row = cssBlock('.telegram-test-row')
  const actions = cssBlock('.telegram-test-actions')
  const status = cssBlock('.telegram-test-status')
  const busy = cssBlock('.telegram-test-row[aria-busy="true"]')
  const mobile = baseStyle.slice(baseStyle.indexOf('@media (max-width: 768px)'))

  assert.match(row, /display:\s*grid/)
  assert.match(row, /grid-template-columns:\s*auto\s+minmax\(0,\s*1fr\)/)
  assert.match(actions, /display:\s*flex/)
  assert.match(status, /color:\s*var\(--text-secondary\)/)
  assert.match(status, /overflow-wrap:\s*anywhere/)
  assert.match(busy, /cursor:\s*progress/)
  assert.match(mobile, /\.telegram-test-row\s*\{[\s\S]*grid-template-columns:\s*1fr/)
})
