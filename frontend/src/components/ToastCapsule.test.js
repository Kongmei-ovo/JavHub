import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

const source = readFileSync(new URL('./ToastCapsule.vue', import.meta.url), 'utf8')

function sourceBlock(selector) {
  const escaped = selector.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  const match = source.match(new RegExp(`${escaped}\\s*\\{([^}]*)\\}`))
  assert.ok(match, `${selector} should exist`)
  return match[1]
}

function assertLayeredToastBackground(block, materialToken) {
  assert.match(block, new RegExp(`background:\\s*var\\(--surface-specular-edge(?:-strong)?\\),\\s*var\\(--surface-noise\\),\\s*var\\(${materialToken}\\)`))
}

test('toast capsule uses shared Apple glass sheet and controls', () => {
  const capsuleBlock = sourceBlock('.toast-capsule')
  const actionBlock = sourceBlock('.toast-action')
  const actionHoverBlock = sourceBlock('.toast-action:hover')
  const actionFocusBlock = sourceBlock('.toast-action:focus-visible')
  const actionActiveBlock = sourceBlock('.toast-action:active')
  const closeBlock = sourceBlock('.toast-close')
  const closeHoverBlock = sourceBlock('.toast-close:hover')
  const closeFocusBlock = sourceBlock('.toast-close:focus-visible')
  const closeActiveBlock = sourceBlock('.toast-close:active')
  const enterBlock = sourceBlock('.toast-slide-enter-active')
  const leaveBlock = sourceBlock('.toast-slide-leave-active')

  assert.match(source, /--toast-sheet-bg:\s*var\(--material-glass-sheet\)/)
  assert.match(source, /--toast-control-bg:\s*var\(--material-glass-control\)/)
  assert.match(source, /--toast-action-bg:\s*var\(--glass-active-material\)/)

  assertLayeredToastBackground(capsuleBlock, '--toast-sheet-bg')
  assert.match(capsuleBlock, /border:\s*1px solid var\(--toast-sheet-border\)/)
  assert.match(capsuleBlock, /box-shadow:\s*var\(--shadow-sheet\)/)
  assert.match(capsuleBlock, /backdrop-filter:\s*blur\(var\(--glass-blur-sheet\)\)\s*saturate\(var\(--glass-saturate-surface\)\)/)

  assertLayeredToastBackground(actionBlock, '--toast-action-bg')
  assert.match(actionBlock, /border:\s*1px solid var\(--toast-action-border\)/)
  assert.match(actionBlock, /box-shadow:\s*var\(--toast-action-shadow\)/)
  assert.match(actionBlock, /backdrop-filter:\s*blur\(var\(--glass-blur-control\)\)\s*saturate\(var\(--glass-saturate-control\)\)/)
  assert.doesNotMatch(actionBlock, /background:\s*var\(--accent\)|border:\s*none|transition:\s*var\(--transition-pro\)/)

  assertLayeredToastBackground(actionHoverBlock, '--toast-action-bg-hover')
  assert.match(actionHoverBlock, /border-color:\s*var\(--toast-action-border-hover\)/)
  assert.match(actionHoverBlock, /box-shadow:\s*var\(--toast-control-shadow-hover\)/)
  assert.match(actionFocusBlock, /outline:\s*none/)
  assert.match(actionFocusBlock, /box-shadow:\s*var\(--toast-control-shadow-hover\),\s*var\(--focus-ring-wide\)/)
  assert.match(actionActiveBlock, /transform:\s*translateY\(0\)\s*scale\(0\.97\)/)

  assertLayeredToastBackground(closeBlock, '--toast-control-bg')
  assert.match(closeBlock, /border:\s*1px solid var\(--toast-control-border\)/)
  assert.match(closeBlock, /box-shadow:\s*var\(--toast-control-shadow\)/)
  assert.match(closeBlock, /backdrop-filter:\s*blur\(var\(--glass-blur-control\)\)\s*saturate\(var\(--glass-saturate-control\)\)/)
  assert.doesNotMatch(closeBlock, /background:\s*var\(--surface-control\)|transition:\s*var\(--transition-pro\)/)

  assertLayeredToastBackground(closeHoverBlock, '--toast-control-bg-hover')
  assert.match(closeHoverBlock, /border-color:\s*var\(--toast-control-border-hover\)/)
  assert.match(closeHoverBlock, /box-shadow:\s*var\(--toast-control-shadow-hover\)/)
  assert.doesNotMatch(closeHoverBlock, /background:\s*var\(--surface-control-hover\)/)
  assert.match(closeFocusBlock, /outline:\s*none/)
  assert.match(closeFocusBlock, /box-shadow:\s*var\(--toast-control-shadow-hover\),\s*var\(--focus-ring-wide\)/)
  assert.match(closeActiveBlock, /transform:\s*translateY\(0\)\s*scale\(0\.94\)/)

  for (const block of [enterBlock, leaveBlock]) {
    assert.doesNotMatch(block, /transition:\s*all\b|var\(--transition-pro\)/)
    assert.match(block, /transition:\s*opacity var\(--motion-standard\),\s*transform var\(--motion-standard\)/)
  }
})
