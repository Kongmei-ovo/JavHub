import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

const source = readFileSync(new URL('./Config.vue', import.meta.url), 'utf8')

function cssBlock(selector) {
  return [...source.matchAll(/([^{}]+)\{([^{}]*)\}/g)]
    .filter(([, selectors]) => selectors
      .split(',')
      .map(part => part.trim())
      .includes(selector))
    .map(([, selectors, block]) => `${selectors.trim()} {${block}}`)
    .join('\n')
}

test('settings secret reveal controls use shared Apple glass button chrome', () => {
  const base = cssBlock('.input-eye-btn')
  assert.match(base, /background:\s*var\(--material-glass-control\)/)
  assert.match(base, /border:\s*1px solid var\(--glass-control-border\)/)
  assert.match(base, /box-shadow:\s*var\(--glass-control-shadow\)/)
  assert.match(base, /backdrop-filter:\s*blur\(var\(--glass-blur-control\)\)\s*saturate\(var\(--glass-saturate-control\)\)/)
  assert.match(base, /transition:\s*background var\(--motion-fast\)/)
  assert.doesNotMatch(base, /background:\s*none|border:\s*none|transition:\s*all/)

  const hover = cssBlock('.input-eye-btn:hover')
  assert.match(hover, /background:\s*var\(--material-glass-control-hover\)/)
  assert.match(hover, /border-color:\s*var\(--glass-control-border-hover\)/)
  assert.match(hover, /box-shadow:\s*var\(--glass-control-shadow-hover\)/)

  const focus = cssBlock('.input-eye-btn:focus-visible')
  assert.match(focus, /outline:\s*none/)
  assert.match(focus, /box-shadow:\s*var\(--glass-control-shadow\),\s*0 0 0 4px rgba\(var\(--accent-rgb\), 0\.14\)/)
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

  assert.match(cardContent, /background:\s*var\(--material-glass-sheet\)/)
  assert.match(cardContent, /border:\s*1px solid var\(--glass-edge\)/)
  assert.match(cardContent, /box-shadow:\s*var\(--glass-surface-shadow\)/)

  for (const block of [formSlot, runtimePanel, preferenceStack, preferenceSection, scopeCard, importProgress, importJobRow]) {
    assert.match(block, /background:\s*var\(--material-glass-(?:subtle|control)\)/)
    assert.match(block, /border:\s*1px solid var\(--glass-control-border\)/)
  }

  assert.match(sourceCheck, /background:\s*var\(--material-glass-control\)/)
  assert.match(sourceCheck, /box-shadow:\s*var\(--glass-control-shadow\)/)
  assert.match(importDrop, /border:\s*1px dashed var\(--glass-control-border\)/)
  assert.match(importLogTail, /background:\s*var\(--material-glass-control\)/)
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

  assert.match(auraPreview, /background:\s*var\(--material-glass-subtle\)/)
  assert.match(auraPreview, /box-shadow:\s*var\(--glass-inner-shadow\)/)
  assert.doesNotMatch(auraPreview, /radial-gradient|rgba\(255,\s*255,\s*255|rgba\(255,255,255/)

  assert.match(previewBubble, /box-shadow:\s*var\(--glass-inner-shadow\)/)
  assert.doesNotMatch(previewBubble, /rgba\(255,\s*255,\s*255|rgba\(255,255,255/)
})
