import test from 'node:test'
import assert from 'node:assert/strict'
import { existsSync, readFileSync } from 'node:fs'

const vueSource = readFileSync(new URL('./Config.vue', import.meta.url), 'utf8')
const advancedPanelSource = readFileSync(new URL('../features/config/AdvancedSettingsPanel.vue', import.meta.url), 'utf8')
const advancedAsyncSource = readFileSync(new URL('../features/config/advancedSettingsAsync.js', import.meta.url), 'utf8')
const advancedImportPresentationSource = readFileSync(new URL('../features/config/advancedSettingsImportPresentation.js', import.meta.url), 'utf8')
const baseStyle = readFileSync(new URL('../features/config/config.css', import.meta.url), 'utf8')
const advancedStyleUrl = new URL('../features/config/advancedSettingsPanel.css', import.meta.url)
const appearanceStyleUrl = new URL('../features/config/configAppearance.css', import.meta.url)
const advancedResponsiveStyleUrl = new URL('../features/config/advancedSettingsPanelResponsive.css', import.meta.url)
const advancedAiStyleUrl = new URL('../features/config/advancedSettingsAi.css', import.meta.url)
const advancedActionRowsStyleUrl = new URL('../features/config/advancedActionRows.css', import.meta.url)
const advancedSwitchesStyleUrl = new URL('../features/config/advancedSwitches.css', import.meta.url)
const advancedStyle = readFileSync(advancedStyleUrl, 'utf8')
const appearanceStyle = readFileSync(appearanceStyleUrl, 'utf8')
const advancedResponsiveStyle = readFileSync(advancedResponsiveStyleUrl, 'utf8')
const advancedAiStyle = readFileSync(advancedAiStyleUrl, 'utf8')
const advancedBaseStyle = advancedStyle
const advancedCombinedStyle = `${advancedStyle}\n${advancedAiStyle}\n${advancedResponsiveStyle}`
const externalStyle = `${baseStyle}\n${appearanceStyle}\n${advancedCombinedStyle}`
const source = `${vueSource}\n${advancedPanelSource}\n${advancedAsyncSource}\n${externalStyle}`
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
  return [...css.matchAll(/([^{}]+)\{/g)]
    .filter(([, selectors]) => selectors.split(',').map(part => part.trim()).includes(selector))
    .length
}

function vueSectionBlock(className) {
  const start = vueSource.indexOf(`<section class="${className}">`)
  assert.notEqual(start, -1, `expected ${className} section to exist`)
  const end = vueSource.indexOf('\n              </section>', start)
  assert.notEqual(end, -1, `expected ${className} section to close`)
  return vueSource.slice(start, end)
}

function advancedSectionBlock(className) {
  const start = advancedPanelSource.indexOf(`<section class="${className}">`)
  assert.notEqual(start, -1, `expected ${className} section to exist`)
  const end = advancedPanelSource.indexOf('\n    </section>', start)
  assert.notEqual(end, -1, `expected ${className} section to close`)
  return advancedPanelSource.slice(start, end)
}

function advancedNativeImportFileInput() {
  const match = advancedPanelSource.match(/<input ref="javinfoImportFileInput"[^>]*>/)
  assert.ok(match, 'expected JavInfo import native file input to exist')
  return match[0]
}

function toggleSwitchInputs(sourceText) {
  return [...sourceText.matchAll(/<label class="settings-row settings-row--toggle[^"]*"[^>]*>[\s\S]*?<input type="checkbox"[^>]*>/g)]
    .map(match => match[0].match(/<input type="checkbox"[^>]*>/)?.[0])
    .filter(Boolean)
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

  for (const block of [runtimePanel, sourceCheck, appearanceStack, sharedGroup, sharedList, importFileControl, importProgress, importLogTail, importJobRow]) {
    assert.ok(block, 'expected settings workspace block to exist')
    assert.doesNotMatch(block, /var\(--bg-card\)|var\(--border\)|var\(--border-light\)|var\(--surface-card\)/)
  }

  // v2 内容层去玻璃：设置面板 = 实底
  for (const block of [runtimePanel, sharedList, importProgress]) {
    assert.match(block, /background:\s*var\(--card\)/)
    assert.match(block, /border:\s*1px solid var\(--hairline\)/)
  }
  assert.match(importJobRow, /border:\s*1px solid var\(--hairline\)/)
  assert.match(importJobRow, /background:\s*var\(--card-2\)/)
  assert.match(importJobRow, /box-shadow:\s*none/)
  assert.doesNotMatch(importJobRow, /material-glass|surface-specular-edge|surface-noise|backdrop-filter/)

  assert.match(sharedGroup, /background:\s*var\(--card\)/)
  assert.match(sharedGroup, /border:\s*1px solid var\(--glass-edge\)/)
  assert.match(sourceCheck, backgroundIncludes('material-glass-control'))
  assert.match(sourceCheck, /box-shadow:\s*var\(--glass-control-shadow\)/)
  assert.match(importFileControl, /border:\s*1px dashed var\(--glass-control-border\)/)
  assert.match(importLogTail, backgroundIncludes('material-glass-control'))
  assert.match(settingsTabs, /scrollbar-color:\s*var\(--glass-edge\) transparent/)
  assert.doesNotMatch(settingsTabs, /var\(--border-light\)/)
})

test('advanced import flow owns a grouped process container instead of legacy form shells', () => {
  assert.match(advancedPanelSource, /class="javinfo-import-panel"/)
  assert.doesNotMatch(advancedPanelSource, /class="form-slot javinfo-import-panel"/)
  assert.doesNotMatch(advancedPanelSource, /class="settings-card"|class="card-content"|class="form-group"|class="checkbox import-confirm"/)
  assert.doesNotMatch(advancedStyle, /\.settings-card(?=[\s,{.:#])|\.card-content\b|\.form-slot\b|\.form-group\b|\.checkbox\.import-confirm\b|accent-color/)

  const importPanel = cssBlock('.javinfo-import-panel')

  assert.match(importPanel, /display:\s*grid/)
  assert.match(importPanel, /gap:\s*14px/)
  assert.match(importPanel, /border:\s*1px solid var\(--hairline\)/)
  assert.match(importPanel, /background:\s*var\(--card\)/)
  assert.match(importPanel, /box-shadow:\s*none/)
})

test('automation source picker reads like a System Settings multi-select list', () => {
  assert.match(vueSource, /class="settings-control settings-control--wide source-check-list-control"/)
  assert.match(vueSource, /class="source-check-list"/)
  assert.match(vueSource, /:class="\['source-check-item', \{ 'is-selected': config\.automation\.candidate_sources\.includes\(source\.value\) \}\]"/)
  assert.match(vueSource, /class="source-check-dot" aria-hidden="true"/)
  assert.match(vueSource, /class="source-check-label"/)

  const listControl = cssBlock('.source-check-list-control')
  const list = cssBlock('.source-check-list')
  const item = cssBlock('.source-check-item')
  const selected = cssBlock('.source-check-item.is-selected')
  const input = cssBlock('.source-check-item input')
  const dot = cssBlock('.source-check-dot')
  const selectedDot = cssBlock('.source-check-item.is-selected .source-check-dot')
  const label = cssBlock('.source-check-label')

  assert.match(listControl, /width:\s*100%/)
  assert.match(list, /display:\s*grid/)
  assert.match(list, /gap:\s*6px/)
  assert.match(item, /display:\s*grid/)
  assert.match(item, /grid-template-columns:\s*14px\s+minmax\(0,\s*1fr\)/)
  assert.match(item, backgroundIncludes('material-glass-control'))
  assert.match(item, /border:\s*1px solid var\(--glass-control-border\)/)
  assert.match(selected, backgroundIncludes('glass-active-material'))
  assert.match(selected, /border-color:\s*var\(--glass-active-border\)/)
  assert.match(input, /position:\s*absolute/)
  assert.match(input, /opacity:\s*0/)
  assert.match(dot, /border-radius:\s*50%/)
  assert.match(dot, /background:\s*var\(--text-muted\)/)
  assert.match(selectedDot, /background:\s*var\(--badge-success-text\)/)
  assert.match(label, /overflow-wrap:\s*anywhere/)
})

test('settings numeric inputs use compact System Settings stepper controls', () => {
  const numberControlMatches = [...vueSource.matchAll(/class="settings-number-control"/g)]
  assert.equal(numberControlMatches.length, 4)
  const numberControlWrapperMatches = [...vueSource.matchAll(/class="settings-control settings-control--compact settings-control--number"[\s\S]*?<input/g)]
  assert.equal(numberControlWrapperMatches.length, 4)

  for (const markup of [
    /class="settings-number-control"[\s\S]*v-model\.number="config\.automation\.auto_process_interval_minutes"[\s\S]*<span class="settings-number-unit">分钟<\/span>/,
    /class="settings-number-control"[\s\S]*v-model\.number="config\.automation\.max_auto_downloads_per_run"[\s\S]*<span class="settings-number-unit">次<\/span>/,
    /class="settings-number-control"[\s\S]*v-model\.number="config\.automation\.max_auto_downloads_per_24h"[\s\S]*<span class="settings-number-unit">24 小时<\/span>/,
    /class="settings-number-control"[\s\S]*v-model\.number="config\.scheduler\.subscription_check_hour"[\s\S]*<span class="settings-number-unit">时<\/span>/,
  ]) {
    assert.match(vueSource, markup)
  }
  assert.match(vueSource, /class="settings-number-control"[\s\S]*v-model\.number="config\.scheduler\.subscription_check_hour" type="number" min="0" max="23" step="1" inputmode="numeric"[\s\S]*<span class="settings-number-range">0-23<\/span>/)

  const control = cssBlock('.settings-number-control')
  const input = cssBlock('.settings-number-control .input')
  const spinButton = cssBlock('.settings-number-control .input::-webkit-outer-spin-button')
  const unit = cssBlock('.settings-number-unit')
  const range = cssBlock('.settings-number-range')
  const focus = cssBlock('.settings-number-control:focus-within')
  const mobile = baseStyle.slice(baseStyle.indexOf('@media (max-width: 768px)'))

  assert.match(control, /display:\s*grid/)
  assert.match(control, /grid-template-columns:\s*minmax\(64px,\s*1fr\)\s+auto\s+auto/)
  assert.match(control, /align-items:\s*center/)
  assert.match(control, /border:\s*1px solid var\(--glass-control-border\)/)
  assert.match(control, backgroundIncludes('material-glass-control'))
  assert.match(control, /box-shadow:\s*var\(--glass-control-shadow\)/)
  assert.match(input, /border:\s*0/)
  assert.match(input, /background:\s*transparent/)
  assert.match(input, /font-variant-numeric:\s*tabular-nums/)
  assert.match(spinButton, /-webkit-appearance:\s*none/)
  assert.match(unit, /color:\s*var\(--text-secondary\)/)
  assert.match(unit, /font-weight:\s*700/)
  assert.match(range, /color:\s*var\(--text-muted\)/)
  assert.match(range, /border-left:\s*1px solid var\(--glass-control-border\)/)
  assert.match(focus, /outline:\s*none/)
  assert.match(focus, /border-color:\s*var\(--glass-control-border-hover\)/)
  assert.match(focus, /box-shadow:\s*var\(--glass-control-shadow-hover\),\s*var\(--focus-ring\)/)
  assert.match(mobile, /\.settings-number-control\s*\{[\s\S]*grid-template-columns:\s*minmax\(68px,\s*1fr\)\s+auto/)
})

test('settings number control width class stays off switch rows', () => {
  const switchRows = [...vueSource.matchAll(/<label class="settings-row settings-row--toggle"[\s\S]*?<\/label>/g)].map(match => match[0])
  assert.equal(switchRows.length, 6)
  for (const row of switchRows) {
    assert.doesNotMatch(row, /settings-control--number/)
  }
})

test('settings visual preview and loading states avoid hardcoded white glass fragments', () => {
  const auraPreview = cssBlock('.aura-preview')
  const previewBubble = cssBlock('.preview-bubble')

  assert.match(vueSource, /import AppleSkeleton from '\.\.\/components\/AppleSkeleton\.vue'/)
  assert.match(vueSource, /<AppleSkeleton\s+v-if="configLoading"[\s\S]*label="配置加载中"/)
  assert.doesNotMatch(vueSource, /<div class="spinner-large"><\/div>/)
  assert.doesNotMatch(baseStyle, /\.settings-loading-skeleton\b/)
  assert.doesNotMatch(baseStyle, /settings-skeleton-shimmer/)
  assert.doesNotMatch(baseStyle, /\.spinner-large\b/)
  assert.match(baseStyle, /\.save-spinner\s*\{[\s\S]*width:\s*16px/)

  assert.match(auraPreview, /background:\s*var\(--card\)/)
  assert.match(auraPreview, /box-shadow:\s*none/)
  assert.doesNotMatch(auraPreview, /radial-gradient|rgba\(255,\s*255,\s*255|rgba\(255,255,255/)

  assert.match(previewBubble, /box-shadow:\s*var\(--glass-inner-shadow\)/)
  assert.doesNotMatch(previewBubble, /rgba\(255,\s*255,\s*255|rgba\(255,255,255/)
})

test('settings page keeps heavyweight styles in external scoped stylesheets', () => {
  assert.match(vueSource, /<style scoped src="\.\.\/features\/config\/config\.css"><\/style>/)
  assert.match(vueSource, /<style scoped src="\.\.\/features\/config\/configAppearance\.css"><\/style>/)
  assert.ok(`${baseStyle}\n${appearanceStyle}`.length > 16000, 'settings shell stylesheets should carry shared workspace CSS')
  assert.ok(advancedCombinedStyle.length > 5000, 'advanced lazy chunk should carry its own workspace CSS')
  assert.ok(vueSource.split('\n').length < 1300, 'Config.vue should stay small enough to review and parse quickly')
})

test('settings advanced workspace stays in a lazy child chunk', () => {
  assert.match(vueSource, /import \{ AdvancedSettingsPanel \} from '\.\.\/features\/config\/advancedSettingsAsync\.js'/)
  assert.match(advancedAsyncSource, /export const AdvancedSettingsPanel = defineAsyncComponent\(\{[\s\S]*loader:\s*\(\)\s*=>\s*import\('\.\/AdvancedSettingsPanel\.vue'\)/)
  assert.match(vueSource, /<AdvancedSettingsPanel\s+v-if="activeGroup === 'advanced'"/)
  assert.doesNotMatch(vueSource, /<AdvancedSettingsPanel\s+v-else-if="activeGroup === 'advanced'"/)
  assert.doesNotMatch(vueSource, /JavInfo 数据库导入/)
  assert.doesNotMatch(vueSource, /<h2>公共智能模型<\/h2>/)
  assert.doesNotMatch(vueSource, /<h2>网络代理<\/h2>/)
})

test('advanced route renders from an independent branch instead of the appearance else-chain', () => {
  const appearanceIndex = vueSource.indexOf('<div v-if="activeGroup === \'appearance\'"')
  const advancedIndex = vueSource.indexOf('<AdvancedSettingsPanel')

  assert.notEqual(appearanceIndex, -1, 'appearance branch should exist')
  assert.notEqual(advancedIndex, -1, 'advanced branch should exist')
  assert.ok(advancedIndex > appearanceIndex, 'advanced branch should follow appearance in the settings pane')
  assert.match(vueSource.slice(advancedIndex, advancedIndex + 160), /v-if="activeGroup === 'advanced'"/)
  assert.doesNotMatch(vueSource.slice(appearanceIndex, advancedIndex + 160), /v-else-if="activeGroup === 'advanced'"/)
})

test('advanced lazy chunk shows a System Settings skeleton while loading', () => {
  assert.match(advancedAsyncSource, /const AdvancedSettingsSkeleton = \{[\s\S]*name:\s*'AdvancedSettingsSkeleton'/)
  assert.match(advancedAsyncSource, /<AppleSkeleton class="advanced-settings-skeleton apple-surface" variant="list" :items="4" label="高级设置加载中" \/>/)
  assert.match(advancedAsyncSource, /export const AdvancedSettingsPanel = defineAsyncComponent\(\{[\s\S]*loader:\s*\(\)\s*=>\s*import\('\.\/AdvancedSettingsPanel\.vue'\)/)
  assert.match(advancedAsyncSource, /loadingComponent:\s*AdvancedSettingsSkeleton/)
  assert.match(advancedAsyncSource, /delay:\s*120/)
  assert.match(advancedAsyncSource, /suspensible:\s*false/)
  assert.match(vueSource, /components:\s*\{ AdvancedSettingsPanel, AppleErrorState, AppleSkeleton, GlassSelect, Open115SettingsPanel \}/)

  const skeleton = cssBlock('.advanced-settings-skeleton')
  assert.match(skeleton, /min-height:\s*320px/)
  assert.match(skeleton, /padding:\s*18px/)
  assert.match(skeleton, /border:\s*1px solid var\(--glass-edge\)/)
  assert.match(skeleton, /background:\s*var\(--card\)/)
  assert.match(skeleton, /box-shadow:\s*var\(--shadow-card\)/)
  assert.match(skeleton, /overflow:\s*hidden/)
})

test('advanced lazy chunk shows an inline System Settings error state if loading fails', () => {
  assert.match(advancedAsyncSource, /const AdvancedSettingsError = \{[\s\S]*name:\s*'AdvancedSettingsError'/)
  assert.match(advancedAsyncSource, /components:\s*\{ AppleErrorState \}/)
  assert.match(advancedAsyncSource, /<AppleErrorState class="advanced-settings-error apple-surface"[\s\S]*title="高级设置加载失败"/)
  assert.match(advancedAsyncSource, /description="无法载入高级设置模块，刷新页面会重新请求这个模块。"/)
  assert.match(advancedAsyncSource, /retry-label="刷新页面"/)
  assert.match(advancedAsyncSource, /@retry="reloadPage"/)
  assert.match(advancedAsyncSource, /reloadPage\(\)\s*\{[\s\S]*window\.location\.reload\(\)/)
  assert.match(advancedAsyncSource, /errorComponent:\s*AdvancedSettingsError/)
  assert.match(advancedAsyncSource, /timeout:\s*15000/)

  const error = cssBlock('.advanced-settings-error')
  assert.match(error, /min-height:\s*320px/)
  assert.match(error, /border:\s*1px solid var\(--badge-warning-border\)/)
  assert.match(error, /background:\s*var\(--card\)/)
  assert.match(error, /box-shadow:\s*var\(--shadow-card\)/)
  assert.match(error, /overflow:\s*hidden/)
})

test('settings advanced lazy chunk owns its scoped stylesheet boundary', () => {
  assert.match(advancedPanelSource, /<style scoped src="\.\/advancedSettingsPanel\.css"><\/style>/)
  assert.match(advancedPanelSource, /<style scoped src="\.\/advancedSettingsAi\.css"><\/style>/)
  assert.match(advancedPanelSource, /<style scoped src="\.\/advancedSettingsPanelResponsive\.css"><\/style>/)
  assert.doesNotMatch(advancedPanelSource, /<style scoped src="\.\/advancedActionRows\.css"><\/style>/)
  assert.doesNotMatch(advancedPanelSource, /<style scoped src="\.\/advancedSwitches\.css"><\/style>/)
  assert.equal(existsSync(advancedActionRowsStyleUrl), false, 'advanced action row styles should stay inside advancedSettingsPanel.css')
  assert.equal(existsSync(advancedSwitchesStyleUrl), false, 'advanced switch styles should stay inside advancedSettingsPanel.css')
  assert.match(vueSource, /<style scoped src="\.\.\/features\/config\/config\.css"><\/style>/)
  assert.match(advancedStyle, /\.javinfo-import-panel\s*\{/)
  assert.match(advancedStyle, /\.import-actions--danger\s*\{/)
  assert.match(advancedStyle, /\.export-action-control\s*\{/)
  assert.match(advancedAiStyle, /\.ai-test-row\s*\{/)
  assert.match(advancedStyle, /\.import-confirm-switch\s*\{/)
  assert.doesNotMatch(baseStyle, /\.javinfo-import-panel\s*\{|\.import-log-tail\s*\{|\.ai-provider-control\s*\{/)
  assert.match(appearanceStyle, /\.appearance-settings-stack\s*\{/)
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

  // 分类已从左侧栏改为顶部横向标签，内容区全宽
  assert.match(shell, /display:\s*flex/)
  assert.match(shell, /flex-direction:\s*column/)
  assert.match(sidebar, /background:\s*var\(--card\)/)
  assert.match(sidebar, /flex-wrap:\s*wrap/)
  assert.match(pane, /max-width:\s*none/)
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

  // settings-footer 是 fixed 定位外壳（透明），玻璃面下沉到 .footer-content 成悬浮圆角坞
  assert.match(footer, /position:\s*fixed/)
  assert.match(footer, /pointer-events:\s*none/)
  assert.match(content, /background:[\s\S]*var\(--material-glass-sheet\)/)
  assert.match(content, /border:\s*1px solid var\(--glass-edge\)/)
  assert.match(content, /border-radius:\s*var\(--radius-sheet\)/)
  assert.match(content, /pointer-events:\s*auto/)
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
  assert.match(group, /background:\s*var\(--card\)/)
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

  assert.match(list, /background:\s*var\(--card\)/)
  assert.match(row, /grid-template-columns:\s*minmax\(180px,\s*0\.42fr\)\s+minmax\(0,\s*1fr\)/)
  assert.match(control, /justify-self:\s*end/)
})

test('settings base tabs have no legacy card form layouts after grouping pass', () => {
  assert.doesNotMatch(vueSource, /<div class="settings-card">/)
  assert.doesNotMatch(vueSource, /class="settings-card-header"/)
  assert.doesNotMatch(baseStyle, /\.settings-card-header\b/)
  assert.doesNotMatch(baseStyle, /\.settings-card\b|\.card-content\b|\.form-slot\b/)
  assert.match(vueSource, /class="settings-group-header"/)
  assert.doesNotMatch(vueSource, /<div class="form-slot">/)
  assert.match(vueSource, /class="settings-group telegram-settings-group"/)
  assert.match(vueSource, /class="settings-group notification-settings-group"/)
  assert.match(vueSource, /class="settings-group automation-settings-group"/)
  assert.match(vueSource, /class="settings-group subscription-schedule-group"/)
  // 磁力索引源/爬虫/库存对比定时任务已分别迁移到下载中心或删除
  assert.doesNotMatch(vueSource, /class="settings-group torznab-settings-group"/)
  assert.doesNotMatch(vueSource, /class="settings-group crawler-settings-group"/)
  assert.doesNotMatch(vueSource, /class="settings-group inventory-schedule-group"/)

  const actionRow = cssBlock('.settings-row--actions')
  const toggleRow = cssBlock('.settings-row--toggle')
  const groupHeader = cssBlock('.settings-group-header')
  const groupHeaderTitle = cssBlock('.settings-group-header h2')
  const appearanceHeader = cssBlock('.appearance-section .settings-group-header')
  const appearanceHeaderTrailing = `${cssBlock('.appearance-section .settings-group-header .appearance-chip')}\n${cssBlock('.appearance-section .settings-group-header .btn')}`

  assert.match(actionRow, /align-items:\s*start/)
  assert.match(toggleRow, /min-height:\s*54px/)
  assert.match(groupHeader, /display:\s*flex/)
  assert.match(groupHeader, /margin-bottom:\s*24px/)
  assert.match(groupHeaderTitle, /font-size:\s*var\(--type-panel-title\)/)
  assert.match(appearanceHeader, /justify-content:\s*flex-start/)
  assert.match(appearanceHeaderTrailing, /margin-left:\s*auto/)
})

test('settings boolean rows use System Settings-style switch controls', () => {
  assert.match(vueSource, /<label class="settings-row settings-row--toggle" for="notifEnabled">/)
  assert.match(vueSource, /<label class="settings-row settings-row--toggle" for="rulesRequireMagnet">/)
  assert.doesNotMatch(vueSource, /for="torznabEnabled"/)
  const proxySection = advancedSectionBlock('advanced-settings-group proxy-settings-group')
  assert.match(proxySection, /<label class="settings-row settings-row--toggle" for="proxyEnabled">[\s\S]*<span class="setting-title">启用代理<\/span>[\s\S]*id="proxyEnabled"/)
  const aiSection = advancedSectionBlock('advanced-settings-group ai-settings-group')
  assert.doesNotMatch(aiSection, /for="proxyEnabled"/)
  const baseSwitchInputs = toggleSwitchInputs(vueSource)
  const advancedSwitchInputs = toggleSwitchInputs(advancedPanelSource)
  assert.equal(baseSwitchInputs.length, 6)
  assert.equal(advancedSwitchInputs.length, 3)
  for (const inputMarkup of [...baseSwitchInputs, ...advancedSwitchInputs]) {
    assert.match(inputMarkup, /role="switch"/)
  }
  assert.doesNotMatch(vueSource, /class="source-check-item"[\s\S]*<input type="checkbox"[^>]*role="switch"/)

  for (const [selector, style] of [
    ['base', baseStyle],
    ['advanced', advancedCombinedStyle],
  ]) {
    const toggle = cssBlocksBySelector.get('.settings-row--toggle .settings-control > input[type="checkbox"]') || ''
    const checked = cssBlocksBySelector.get('.settings-row--toggle .settings-control > input[type="checkbox"]:checked') || ''
    const thumb = cssBlocksBySelector.get('.settings-row--toggle .settings-control > input[type="checkbox"]::before') || ''
    const checkedThumb = cssBlocksBySelector.get('.settings-row--toggle .settings-control > input[type="checkbox"]:checked::before') || ''
    const focus = cssBlocksBySelector.get('.settings-row--toggle .settings-control > input[type="checkbox"]:focus-visible') || ''

    assert.match(style, /\.settings-row--toggle \.settings-control > input\[type="checkbox"\]\s*\{/, `${selector} stylesheet should own switch track styles`)
    assert.match(toggle, /appearance:\s*none/, `${selector} switch should remove native checkbox chrome`)
    assert.match(toggle, /width:\s*46px/, `${selector} switch should have fixed track width`)
    assert.match(toggle, /height:\s*28px/, `${selector} switch should have fixed track height`)
    assert.match(toggle, /border-radius:\s*999px/, `${selector} switch should use capsule track`)
    assert.match(toggle, backgroundIncludes('material-glass-control'), `${selector} switch should use glass control material`)
    assert.match(toggle, /border:\s*1px solid var\(--glass-control-border\)/, `${selector} switch should keep grouped-list border`)
    assert.match(checked, backgroundIncludes('badge-success-bg'), `${selector} checked switch should use success material`)
    assert.match(checked, /border-color:\s*var\(--badge-success-border\)/, `${selector} checked switch should use success border`)
    assert.match(thumb, /width:\s*22px/, `${selector} switch thumb should have fixed width`)
    assert.match(thumb, /height:\s*22px/, `${selector} switch thumb should have fixed height`)
    assert.match(thumb, /background:\s*var\(--text-secondary\)/, `${selector} switch thumb should use muted off color`)
    assert.match(thumb, /transform:\s*translateX\(0\)/, `${selector} switch thumb should start on the left`)
    assert.match(thumb, /transition:\s*transform var\(--motion-standard\),\s*opacity var\(--motion-fast\)/, `${selector} switch thumb should animate state changes`)
    assert.match(checkedThumb, /background:\s*var\(--badge-success-text\)/, `${selector} checked thumb should use success color`)
    assert.match(checkedThumb, /transform:\s*translateX\(18px\)/, `${selector} checked thumb should move to the right`)
    assert.match(focus, /box-shadow:\s*var\(--glass-control-shadow\),\s*var\(--focus-ring\)/, `${selector} switch should expose focus state`)
  }
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

  assert.match(summary, /background:\s*var\(--card\)/)
  assert.match(summary, /border:\s*1px solid var\(--hairline\)/)
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

test('advanced numeric inputs use compact lazy-chunk stepper controls', () => {
  const controlMatches = [...advancedPanelSource.matchAll(/class="advanced-number-control"/g)]
  assert.equal(controlMatches.length, 2)
  const wrapperMatches = [...advancedPanelSource.matchAll(/class="settings-control settings-control--compact advanced-control--number"[\s\S]*?<input/g)]
  assert.equal(wrapperMatches.length, 2)

  assert.match(advancedPanelSource, /class="advanced-number-control"[\s\S]*v-model\.number="config\.javinfo\.import_db\.port" type="number" min="1" max="65535" step="1" inputmode="numeric"[\s\S]*<span class="advanced-number-unit">端口<\/span>[\s\S]*<span class="advanced-number-range">1-65535<\/span>/)
  assert.match(advancedPanelSource, /class="advanced-number-control"[\s\S]*v-model\.number="currentAiConfig\.timeout" type="number" min="1" step="1" inputmode="numeric"[\s\S]*<span class="advanced-number-unit">秒<\/span>[\s\S]*<span class="advanced-number-range">>=1<\/span>/)
  assert.doesNotMatch(advancedPanelSource, /<input class="input" v-model\.number="config\.javinfo\.import_db\.port" type="number" min="1" max="65535" \/>/)
  assert.doesNotMatch(advancedPanelSource, /<input class="input" v-model\.number="currentAiConfig\.timeout" type="number" min="1" \/>/)

  const control = cssBlock('.advanced-number-control')
  const input = cssBlock('.advanced-number-control .input')
  const spinButton = cssBlock('.advanced-number-control .input::-webkit-outer-spin-button')
  const unit = cssBlock('.advanced-number-unit')
  const range = cssBlock('.advanced-number-range')
  const focus = cssBlock('.advanced-number-control:focus-within')
  const mobile = advancedResponsiveStyle

  assert.match(control, /display:\s*grid/)
  assert.match(control, /grid-template-columns:\s*minmax\(64px,\s*1fr\)\s+auto\s+auto/)
  assert.match(control, /border:\s*1px solid var\(--glass-control-border\)/)
  assert.match(control, backgroundIncludes('material-glass-control'))
  assert.match(control, /box-shadow:\s*var\(--glass-control-shadow\)/)
  assert.match(input, /border:\s*0/)
  assert.match(input, /background:\s*transparent/)
  assert.match(input, /font-variant-numeric:\s*tabular-nums/)
  assert.match(spinButton, /-webkit-appearance:\s*none/)
  assert.match(unit, /color:\s*var\(--text-secondary\)/)
  assert.match(range, /border-left:\s*1px solid var\(--glass-control-border\)/)
  assert.match(focus, /box-shadow:\s*var\(--glass-control-shadow-hover\),\s*var\(--focus-ring\)/)
  assert.match(mobile, /\.advanced-number-control\s*\{[\s\S]*grid-template-columns:\s*minmax\(68px,\s*1fr\)\s+auto/)
  assert.match(mobile, /\.advanced-number-range\s*\{[\s\S]*display:\s*none/)
  assert.doesNotMatch(baseStyle, /\.advanced-number-control|\.advanced-control--number/)
})

test('advanced import preflight actions expose busy status semantics', () => {
  assert.match(advancedPanelSource, /class="import-actions import-actions--preflight"/)
  assert.match(advancedPanelSource, /:aria-busy="javinfoImportPreflighting \|\| javinfoMigrating"/)
  assert.match(advancedPanelSource, /aria-live="polite"/)
  assert.match(advancedPanelSource, /class="import-preflight-action-buttons"/)
  assert.match(advancedPanelSource, /id="javinfo-preflight-action-status"/)
  assert.match(advancedPanelSource, /role="status"/)
  assert.match(advancedPanelSource, /{{ javinfoPreflightActionStatus }}/)
  assert.match(advancedPanelSource, /:aria-describedby="'javinfo-preflight-action-status'"/)
  assert.match(advancedPanelSource, /javinfoPreflightActionStatus\(\)/)

  const actions = cssBlock('.import-actions--preflight')
  const buttons = cssBlock('.import-preflight-action-buttons')
  const status = cssBlock('.import-action-status')
  const busy = cssBlock('.import-actions--preflight[aria-busy="true"]')
  const mobile = advancedResponsiveStyle

  assert.match(actions, /display:\s*grid/)
  assert.match(actions, /grid-template-columns:\s*auto\s+minmax\(0,\s*1fr\)/)
  assert.match(actions, /align-items:\s*center/)
  assert.match(buttons, /display:\s*flex/)
  assert.match(status, /color:\s*var\(--text-secondary\)/)
  assert.match(status, /overflow-wrap:\s*anywhere/)
  assert.match(busy, /cursor:\s*progress/)
  assert.match(mobile, /\.import-actions--preflight,[\s\S]*\.ai-test-row\s*\{[\s\S]*grid-template-columns:\s*1fr/)
  assert.match(mobile, /\.import-preflight-action-buttons,[\s\S]*\.ai-test-actions\s*\{[\s\S]*grid-template-columns:\s*1fr/)
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
  assert.match(summary, /background:\s*var\(--card\)/)
  assert.match(summary, /border:\s*1px solid var\(--hairline\)/)
  assert.match(row, /grid-template-columns:\s*16px\s+minmax\(0,\s*1fr\)/)
  assert.match(ready, /color:\s*var\(--badge-success-text\)/)
  assert.match(pending, /color:\s*var\(--text-muted\)/)
  assert.match(note, /color:\s*var\(--text-secondary\)/)
})

test('advanced export action exposes row-native busy status semantics', () => {
  assert.match(advancedPanelSource, /class="settings-control settings-control--wide export-action-control"/)
  assert.match(advancedPanelSource, /:aria-busy="exportingConfig"/)
  assert.match(advancedPanelSource, /aria-live="polite"/)
  assert.match(advancedPanelSource, /class="export-action-buttons"/)
  assert.match(advancedPanelSource, /id="config-export-note"/)
  assert.match(advancedPanelSource, /role="status"/)
  assert.match(advancedPanelSource, /:class="\{ error: exportConfigStatusType === 'error' \}"/)
  assert.match(advancedPanelSource, /{{ exportActionNote }}/)
  assert.match(advancedPanelSource, /:aria-describedby="'config-export-note'"/)
  assert.match(advancedPanelSource, /exportConfigStatus:\s*''/)
  assert.match(advancedPanelSource, /exportConfigStatusType:\s*'info'/)
  assert.match(advancedPanelSource, /if \(this\.exportConfigStatus\) return this\.exportConfigStatus/)
  assert.match(advancedPanelSource, /this\.exportConfigStatus = ''/)
  assert.match(advancedPanelSource, /this\.exportConfigStatusType = 'info'/)
  assert.match(advancedPanelSource, /this\.exportConfigStatus = `已导出 \$\{link\.download\}`/)
  assert.match(advancedPanelSource, /this\.exportConfigStatusType = 'success'/)
  assert.match(advancedPanelSource, /this\.exportConfigStatus = e\.response\?\.data\?\.detail \|\| '导出失败'/)
  assert.match(advancedPanelSource, /this\.exportConfigStatusType = 'error'/)

  const control = cssBlock('.export-action-control')
  const buttons = cssBlock('.export-action-buttons')
  const note = cssBlock('.export-action-note')
  const error = cssBlock('.export-action-note.error')
  const busy = cssBlock('.export-action-control[aria-busy="true"]')
  const mobile = advancedResponsiveStyle

  assert.match(control, /display:\s*grid/)
  assert.match(control, /grid-template-columns:\s*auto\s+minmax\(0,\s*1fr\)/)
  assert.match(control, /align-items:\s*center/)
  assert.match(buttons, /display:\s*flex/)
  assert.match(note, /color:\s*var\(--text-secondary\)/)
  assert.match(note, /overflow-wrap:\s*anywhere/)
  assert.match(error, /color:\s*var\(--badge-error-text\)/)
  assert.match(busy, /cursor:\s*progress/)
  assert.match(mobile, /\.export-action-control\s*\{[\s\S]*grid-template-columns:\s*1fr/)
})

test('appearance settings use the shared macOS grouped row layout', () => {
  const appearanceSections = {
    global: vueSectionBlock('settings-group appearance-global-group'),
    search: vueSectionBlock('settings-group appearance-search-group'),
  }

  assert.match(vueSource, /class="appearance-settings-stack"/)
  assert.match(vueSource, /class="settings-group appearance-global-group"/)
  assert.match(vueSource, /class="settings-group appearance-search-group"/)
  assert.match(appearanceSections.global, /<h2>全局偏好<\/h2>/)
  assert.match(appearanceSections.search, /<h2>影片检索<\/h2>/)
  assert.doesNotMatch(vueSource, /class="preference-stack"|class="preference-section"|class="scope-card"/)
  assert.doesNotMatch(vueSource, /class="appearance-setting-row"/)
  // 发现模块已移除:随机探索 / 题材气泡两个外观分组不再存在
  assert.doesNotMatch(vueSource, /appearance-discovery-group|appearance-visual-group/)

  const stack = cssBlock('.appearance-settings-stack')
  assert.match(stack, /display:\s*grid/)
  assert.match(stack, /gap:\s*18px/)
})

test('advanced export readiness styles are defined once in the lazy stylesheet', () => {
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
    assert.equal(selectorDefinitionCount(advancedBaseStyle, selector), 1, `${selector} should have one base definition`)
  }

  assert.match(advancedResponsiveStyle, /@media \(max-width:\s*768px\)[\s\S]*\.export-action-control\s*\{[\s\S]*grid-template-columns:\s*1fr/)
  assert.match(advancedResponsiveStyle, /@media \(max-width:\s*768px\)[\s\S]*\.export-action-buttons \.btn\s*\{[\s\S]*width:\s*100%/)
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
  assert.match(fileControl, /background:\s*var\(--card\)/)
  assert.match(confirmRow, /grid-template-columns:\s*minmax\(0,\s*1fr\)\s+auto/)
  assert.match(confirmRow, /cursor:\s*pointer/)
})

test('advanced import confirmation controls render as System Settings-style switches', () => {
  assert.match(advancedPanelSource, /:class="\['import-confirm-switch', \{ 'is-on': javinfoImportConfirm \}\]"[\s\S]*<input type="checkbox" v-model="javinfoImportConfirm"[\s\S]*:class="\['import-confirm-switch-track', \{ 'is-on': javinfoImportConfirm \}\]" aria-hidden="true"[\s\S]*:class="\['import-confirm-switch-thumb', \{ 'is-on': javinfoImportConfirm \}\]" aria-hidden="true"/)
  assert.match(advancedPanelSource, /:class="\['import-confirm-switch', \{ 'is-on': javinfoImportDirectConfirm \}\]"[\s\S]*<input type="checkbox" v-model="javinfoImportDirectConfirm"[\s\S]*:class="\['import-confirm-switch-track', \{ 'is-on': javinfoImportDirectConfirm \}\]" aria-hidden="true"[\s\S]*:class="\['import-confirm-switch-thumb', \{ 'is-on': javinfoImportDirectConfirm \}\]" aria-hidden="true"/)
  assert.doesNotMatch(advancedPanelSource, /<span class="settings-control settings-control--compact">\s*<input type="checkbox" v-model="javinfoImport(?:Direct)?Confirm" \/>/)

  const switchWrap = cssBlock('.import-confirm-switch')
  const switchInput = cssBlock('.import-confirm-switch input')
  const switchTrack = cssBlock('.import-confirm-switch-track')
  const switchThumb = cssBlock('.import-confirm-switch-thumb')
  const checkedTrack = cssBlock('.import-confirm-switch-track.is-on')
  const checkedThumb = cssBlock('.import-confirm-switch-thumb.is-on')
  const focusedTrack = cssBlock('.import-confirm-switch input:focus-visible + .import-confirm-switch-track')

  assert.match(switchWrap, /position:\s*relative/)
  assert.match(switchWrap, /display:\s*inline-flex/)
  assert.match(switchInput, /position:\s*absolute/)
  assert.match(switchInput, /opacity:\s*0/)
  assert.match(switchTrack, /width:\s*46px/)
  assert.match(switchTrack, /height:\s*28px/)
  assert.match(switchTrack, backgroundIncludes('material-glass-control'))
  assert.match(switchTrack, /border:\s*1px solid var\(--glass-control-border\)/)
  assert.doesNotMatch(switchTrack, /transition:\s*(?:background|border-color|box-shadow)/)
  assert.match(switchThumb, /width:\s*22px/)
  assert.match(switchThumb, /height:\s*22px/)
  assert.match(switchThumb, /--import-confirm-thumb-scale:\s*1/)
  assert.match(switchThumb, /background:\s*var\(--text-secondary\)/)
  assert.match(switchThumb, /transform:\s*translateX\(0\)\s+scale\(var\(--import-confirm-thumb-scale\)\)/)
  assert.match(switchThumb, /transition:\s*transform var\(--motion-standard\),\s*opacity var\(--motion-fast\)/)
  assert.match(checkedTrack, /border-color:\s*var\(--badge-success-border\)/)
  assert.match(checkedTrack, backgroundIncludes('badge-success-bg'))
  assert.match(checkedThumb, /background:\s*var\(--badge-success-text\)/)
  assert.match(checkedThumb, /transform:\s*translateX\(18px\)\s+scale\(var\(--import-confirm-thumb-scale\)\)/)
  assert.match(focusedTrack, /box-shadow:\s*var\(--glass-control-shadow\),\s*var\(--focus-ring\)/)
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
  const nativeInputMarkup = advancedNativeImportFileInput()
  assert.match(nativeInputMarkup, /class="import-file-native-input"/)
  assert.match(nativeInputMarkup, /aria-hidden="true"/)
  assert.match(nativeInputMarkup, /tabindex="-1"/)
  assert.match(advancedPanelSource, /class="btn btn-secondary import-file-trigger"/)
  assert.match(advancedPanelSource, /@click="openJavInfoImportFilePicker"/)
  assert.match(advancedPanelSource, /{{ javinfoImportFile \? '更换文件' : '选择文件' }}/)
  assert.doesNotMatch(advancedPanelSource, /class="input file-input"/)
  assert.match(advancedPanelSource, /openJavInfoImportFilePicker\(\)/)

  const fileControl = cssBlock('.import-file-control')
  const fileState = cssBlock('.import-file-state')
  const nativeInput = cssBlock('.import-file-native-input')
  const trigger = cssBlock('.import-file-trigger')
  const selectedDot = cssBlock('.import-file-control.is-selected .import-file-state-dot')
  const disabledControl = cssBlock('.import-file-control[aria-disabled="true"]')
  const status = cssBlock('.import-file-status')
  const note = cssBlock('.import-file-note')

  assert.match(fileControl, /position:\s*relative/)
  assert.match(fileState, /grid-template-columns:\s*10px\s+minmax\(0,\s*1fr\)/)
  assert.match(fileState, backgroundIncludes('material-glass-control'))
  assert.match(nativeInput, /position:\s*absolute/)
  assert.match(nativeInput, /width:\s*1px/)
  assert.match(nativeInput, /opacity:\s*0/)
  assert.match(trigger, /justify-self:\s*start/)
  assert.match(trigger, /min-width:\s*104px/)
  assert.match(selectedDot, /background:\s*var\(--badge-success-text\)/)
  assert.match(disabledControl, /cursor:\s*progress/)
  assert.match(status, /overflow-wrap:\s*anywhere/)
  assert.match(note, /color:\s*var\(--text-muted\)/)
})

test('advanced import recent jobs render as a grouped status list with an empty state', () => {
  assert.match(advancedPanelSource, /class="settings-list import-job-settings-list"/)
  assert.match(advancedPanelSource, /class="settings-row settings-row--stacked import-job-summary-row"/)
  assert.match(advancedPanelSource, /class="settings-control settings-control--wide import-job-control"/)
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
  assert.match(advancedPanelSource, /\.\.\.javinfoImportJobComputed/)
  assert.match(advancedImportPresentationSource, /javinfoImportJobSummary\(\)/)
  assert.match(advancedImportPresentationSource, /javinfoImportJobEmptyNote\(\)/)
  assert.match(advancedPanelSource, /javinfoImportJobDetail\(job\)/)

  const settingsList = cssBlock('.import-job-settings-list')
  const summaryRow = cssBlock('.import-job-summary-row')
  const control = cssBlock('.import-job-control')
  const items = cssBlock('.import-job-items')
  const empty = cssBlock('.import-job-empty')
  const row = cssBlock('.import-job-row')
  const meta = cssBlock('.import-job-meta')

  assert.match(settingsList, /margin-top:\s*4px/)
  assert.match(summaryRow, /align-items:\s*start/)
  assert.match(control, /display:\s*grid/)
  assert.match(control, /gap:\s*10px/)
  assert.match(items, /display:\s*grid/)
  assert.match(empty, /background:\s*var\(--card-2\)/)
  assert.match(empty, /border:\s*1px solid var\(--hairline\)/)
  assert.match(empty, /box-shadow:\s*none/)
  assert.match(empty, /color:\s*var\(--text-muted\)/)
  assert.match(row, /grid-template-columns:\s*minmax\(0,\s*1fr\)\s+auto/)
  assert.match(row, /background:\s*var\(--card-2\)/)
  assert.match(row, /border:\s*1px solid var\(--hairline\)/)
  assert.match(row, /box-shadow:\s*none/)
  assert.match(meta, /color:\s*var\(--text-muted\)/)
})

test('advanced import recent jobs expose loading and recoverable error states', () => {
  assert.match(advancedPanelSource, /class="settings-control settings-control--wide import-job-control"/)
  assert.match(advancedPanelSource, /:aria-busy="javinfoImportJobsLoading"/)
  assert.match(advancedPanelSource, /aria-live="polite"/)
  assert.match(advancedPanelSource, /class="import-job-state"/)
  assert.match(advancedPanelSource, /:class="\{ error: javinfoImportJobsError \}"/)
  assert.match(advancedPanelSource, /{{ javinfoImportJobsStateNote }}/)
  assert.match(advancedPanelSource, /v-if="javinfoImportJobsError"/)
  assert.match(advancedPanelSource, /class="btn btn-ghost import-job-retry"/)
  assert.match(advancedPanelSource, /@click="listJavInfoImportJobs"/)
  assert.match(advancedPanelSource, /javinfoImportJobsLoading:\s*false/)
  assert.match(advancedPanelSource, /javinfoImportJobsError:\s*''/)
  assert.match(advancedPanelSource, /\.\.\.javinfoImportJobComputed/)
  assert.match(advancedImportPresentationSource, /javinfoImportJobsStateNote\(\)/)
  assert.match(advancedImportPresentationSource, /if \(this\.javinfoImportJobsLoading\) return '正在读取最近导入任务。'/)
  assert.match(advancedImportPresentationSource, /if \(this\.javinfoImportJobsError\) return this\.javinfoImportJobsError/)
  assert.match(advancedPanelSource, /this\.javinfoImportJobsLoading = true/)
  assert.match(advancedPanelSource, /this\.javinfoImportJobsError = ''/)
  assert.match(advancedPanelSource, /this\.javinfoImportJobsError = e\.response\?\.data\?\.detail \|\| '最近任务读取失败'/)
  assert.doesNotMatch(advancedPanelSource, /catch \(e\) \{\s*this\.javinfoImportJobs = \[\]\s*\}/)

  const control = cssBlock('.import-job-control')
  const busy = cssBlock('.import-job-control[aria-busy="true"]')
  const state = cssBlock('.import-job-state')
  const error = cssBlock('.import-job-state.error')
  const retry = cssBlock('.import-job-retry')
  const mobile = advancedResponsiveStyle

  assert.match(control, /display:\s*grid/)
  assert.match(control, /gap:\s*10px/)
  assert.match(busy, /cursor:\s*progress/)
  assert.match(state, /grid-template-columns:\s*10px\s+minmax\(0,\s*1fr\)\s+auto/)
  assert.match(state, /background:\s*var\(--card-2\)/)
  assert.match(state, /border:\s*1px solid var\(--hairline\)/)
  assert.match(state, /box-shadow:\s*none/)
  assert.doesNotMatch(state, /material-glass|surface-specular-edge|surface-noise|backdrop-filter/)
  assert.match(state, /color:\s*var\(--text-secondary\)/)
  assert.match(error, /border-color:\s*var\(--badge-error-border\)/)
  assert.match(error, /color:\s*var\(--badge-error-text\)/)
  assert.match(retry, /justify-self:\s*end/)
  assert.match(mobile, /\.import-job-state\s*\{[\s\S]*grid-template-columns:\s*10px\s+minmax\(0,\s*1fr\)/)
  assert.match(mobile, /\.import-job-retry\s*\{[\s\S]*justify-self:\s*stretch/)
})

test('advanced import danger actions expose a dedicated busy status row', () => {
  assert.match(advancedPanelSource, /class="import-actions import-actions--danger"/)
  assert.match(advancedPanelSource, /:aria-busy="javinfoImportDangerActionsBusy"/)
  assert.match(advancedPanelSource, /aria-live="polite"/)
  assert.match(advancedPanelSource, /id="javinfo-import-danger-action-status"/)
  assert.match(advancedPanelSource, /role="status"/)
  assert.match(advancedPanelSource, /{{ javinfoImportDangerActionStatus }}/)
  assert.match(advancedPanelSource, /class="btn btn-danger"[\s\S]*aria-label="开始 JavInfo 全量替换导入"/)
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
  assert.match(advancedPanelSource, /\.\.\.aiConnectionComputed/)
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

test('telegram test mobile layout overrides base row styles in cascade order', () => {
  const baseRowIndex = baseStyle.indexOf('.telegram-test-row {\n  display: grid')
  const mobileRowIndex = baseStyle.lastIndexOf('.telegram-test-row {\n    grid-template-columns: 1fr;')
  const mobileButtonIndex = baseStyle.lastIndexOf('.telegram-test-actions .btn {\n    width: 100%;')

  assert.notEqual(baseRowIndex, -1, 'expected base telegram test row styles')
  assert.notEqual(mobileRowIndex, -1, 'expected mobile telegram test row override')
  assert.notEqual(mobileButtonIndex, -1, 'expected mobile telegram test button override')
  assert.ok(mobileRowIndex > baseRowIndex, 'mobile row override should appear after base row styles')
  assert.ok(mobileButtonIndex > baseRowIndex, 'mobile button override should appear after base row styles')
})

