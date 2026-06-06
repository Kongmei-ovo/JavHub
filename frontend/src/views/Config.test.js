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

function cssBlock(selector) {
  return [...source.matchAll(/([^{}]+)\{([^{}]*)\}/g)]
    .filter(([, selectors]) => selectors
      .split(',')
      .map(part => part.trim())
      .includes(selector))
    .map(([, selectors, block]) => `${selectors.trim()} {${block}}`)
    .join('\n')
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

test('settings secret reveal controls use shared Apple glass button chrome', () => {
  const base = cssBlock('.input-eye-btn')
  assert.match(base, backgroundIncludes('material-glass-control'))
  assert.match(base, /border:\s*1px solid var\(--glass-control-border\)/)
  assert.match(base, /box-shadow:\s*var\(--glass-control-shadow\)/)
  assert.match(base, /backdrop-filter:\s*blur\(var\(--glass-blur-control\)\)\s*saturate\(var\(--glass-saturate-control\)\)/)
  assert.match(base, /transition:\s*background var\(--motion-fast\)/)
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
  const preferenceStack = cssBlock('.preference-stack')
  const preferenceSection = cssBlock('.preference-section')
  const scopeCard = cssBlock('.scope-card')
  const importDrop = cssBlock('.import-file-drop')
  const importProgress = cssBlock('.import-progress')
  const importLogTail = cssBlock('.import-log-tail')
  const importJobRow = cssBlock('.import-job-row')
  const settingsTabs = cssBlock('.settings-tabs')

  for (const block of [cardContent, formSlot, runtimePanel, sourceCheck, preferenceStack, preferenceSection, scopeCard, importDrop, importProgress, importLogTail, importJobRow]) {
    assert.ok(block, 'expected settings workspace block to exist')
    assert.doesNotMatch(block, /var\(--bg-card\)|var\(--border\)|var\(--border-light\)|var\(--shadow-card\)|var\(--surface-card\)/)
  }

  assert.match(cardContent, backgroundIncludes('material-glass-sheet'))
  assert.match(cardContent, /border:\s*1px solid var\(--glass-edge\)/)
  assert.match(cardContent, /box-shadow:\s*var\(--glass-surface-shadow\)/)

  for (const block of [formSlot, runtimePanel, preferenceStack, preferenceSection, scopeCard, importProgress, importJobRow]) {
    assert.match(block, /background:[\s\S]*var\(--material-glass-(?:subtle|control)\)/)
    assert.match(block, /border:\s*1px solid var\(--glass-control-border\)/)
  }

  assert.match(sourceCheck, backgroundIncludes('material-glass-control'))
  assert.match(sourceCheck, /box-shadow:\s*var\(--glass-control-shadow\)/)
  assert.match(importDrop, /border:\s*1px dashed var\(--glass-control-border\)/)
  assert.match(importLogTail, backgroundIncludes('material-glass-control'))
  assert.match(settingsTabs, /scrollbar-color:\s*var\(--glass-edge\) transparent/)
  assert.doesNotMatch(settingsTabs, /var\(--border-light\)/)
})

test('settings visual preview and loading states avoid hardcoded white glass fragments', () => {
  const spinner = cssBlock('.spinner-large')
  const auraPreview = cssBlock('.aura-preview')
  const previewBubble = cssBlock('.preview-bubble')

  assert.match(spinner, /border:\s*3px solid var\(--glass-control-border\)/)
  assert.match(spinner, /border-top-color:\s*var\(--glass-active-border\)/)
  assert.doesNotMatch(spinner, /rgba\(255,\s*255,\s*255/)

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
