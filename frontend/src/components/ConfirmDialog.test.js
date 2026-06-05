import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

const source = readFileSync(new URL('./ConfirmDialog.vue', import.meta.url), 'utf8')

function sourceBlock(selector) {
  const escaped = selector.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  const match = source.match(new RegExp(`${escaped}\\s*\\{([^}]*)\\}`))
  assert.ok(match, `${selector} should exist`)
  return match[1]
}

test('global confirm dialog uses shared Apple glass sheet and controls', () => {
  const overlayBlock = sourceBlock('.confirm-overlay')
  const dialogBlock = sourceBlock('.confirm-dialog')
  const buttonBlock = sourceBlock('.confirm-btn')
  const buttonFocusBlock = sourceBlock('.confirm-btn:focus-visible')
  const buttonActiveBlock = sourceBlock('.confirm-btn:active')
  const primaryBlock = sourceBlock('.confirm-primary')
  const dangerPrimaryBlock = sourceBlock('.confirm-primary.danger')
  const iconDangerBlock = sourceBlock('.confirm-icon.danger')

  assert.match(source, /--confirm-overlay-bg:\s*var\(--surface-scrim,\s*var\(--scrim\)\)/)
  assert.match(source, /--confirm-sheet-bg:\s*var\(--material-glass-sheet\)/)
  assert.match(source, /--confirm-control-bg:\s*var\(--material-glass-control\)/)
  assert.match(source, /--confirm-primary-bg:\s*var\(--glass-active-material\)/)
  assert.match(source, /--confirm-danger-bg:\s*var\(--badge-error-bg\)/)

  assert.match(overlayBlock, /background:\s*var\(--confirm-overlay-bg\)/)
  assert.match(overlayBlock, /backdrop-filter:\s*blur\(var\(--glass-blur-sheet\)\)\s*saturate\(var\(--glass-saturate-surface\)\)/)
  assert.doesNotMatch(overlayBlock, /rgba\(0,\s*0,\s*0,\s*0\.58\)|saturate\(110%\)/)

  assert.match(dialogBlock, /background:\s*var\(--surface-specular-edge-strong\),\s*var\(--surface-noise\),\s*var\(--confirm-sheet-bg\)/)
  assert.match(dialogBlock, /border:\s*1px solid var\(--confirm-sheet-border\)/)
  assert.match(dialogBlock, /box-shadow:\s*var\(--shadow-sheet\)/)

  assert.match(buttonBlock, /transition:\s*transform var\(--motion-standard\),\s*background var\(--motion-standard\),\s*border-color var\(--motion-standard\),\s*box-shadow var\(--motion-standard\),\s*opacity var\(--motion-fast\)/)
  assert.doesNotMatch(buttonBlock, /transition:\s*var\(--transition-pro\)/)
  assert.match(buttonFocusBlock, /outline:\s*none/)
  assert.match(buttonFocusBlock, /box-shadow:\s*var\(--confirm-control-shadow-hover\),\s*0 0 0 4px rgba\(var\(--accent-rgb\),\s*0\.12\)/)
  assert.match(buttonActiveBlock, /transform:\s*translateY\(0\)\s*scale\(0\.97\)/)

  assert.match(sourceBlock('.confirm-icon'), /background:\s*var\(--surface-specular-edge\),\s*var\(--surface-noise\),\s*var\(--confirm-control-bg\)/)
  assert.match(sourceBlock('.confirm-cancel'), /background:\s*var\(--surface-specular-edge\),\s*var\(--surface-noise\),\s*var\(--confirm-control-bg\)/)
  assert.match(sourceBlock('.confirm-cancel:hover'), /background:\s*var\(--surface-specular-edge\),\s*var\(--surface-noise\),\s*var\(--confirm-control-bg-hover\)/)

  assert.match(primaryBlock, /background:\s*var\(--surface-specular-edge-strong\),\s*var\(--surface-noise\),\s*var\(--confirm-primary-bg\)/)
  assert.match(primaryBlock, /border-color:\s*var\(--confirm-primary-border\)/)
  assert.match(primaryBlock, /box-shadow:\s*var\(--glass-active-shadow\)/)
  assert.doesNotMatch(primaryBlock, /background:\s*var\(--accent\)|border-color:\s*transparent/)

  assert.match(dangerPrimaryBlock, /background:\s*var\(--surface-specular-edge\),\s*var\(--surface-noise\),\s*var\(--confirm-danger-bg\)/)
  assert.match(dangerPrimaryBlock, /border-color:\s*var\(--confirm-danger-border\)/)
  assert.match(dangerPrimaryBlock, /color:\s*var\(--confirm-danger-text\)/)
  assert.doesNotMatch(dangerPrimaryBlock, /#ff6b6b|#160b0b/)

  assert.match(iconDangerBlock, /color:\s*var\(--confirm-danger-text\)/)
  assert.match(iconDangerBlock, /border-color:\s*var\(--confirm-danger-border\)/)
  assert.match(iconDangerBlock, /background:\s*var\(--surface-specular-edge\),\s*var\(--surface-noise\),\s*var\(--confirm-danger-bg\)/)
})
