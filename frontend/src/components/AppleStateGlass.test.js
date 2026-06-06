import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

const emptySource = readFileSync(new URL('./AppleEmptyState.vue', import.meta.url), 'utf8')
const errorSource = readFileSync(new URL('./AppleErrorState.vue', import.meta.url), 'utf8')

function sourceBlock(source, selector) {
  const escaped = selector.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  const match = source.match(new RegExp(`${escaped}\\s*\\{([^}]*)\\}`))
  assert.ok(match, `${selector} should exist`)
  return match[1]
}

function assertGlassAction(block, name) {
  assert.match(block, /background:\s*var\(--surface-specular-edge-strong\),\s*var\(--surface-noise\),\s*var\(--apple-state-action-bg\)/, `${name} should use layered active glass material`)
  assert.match(block, /border:\s*1px solid var\(--apple-state-action-border\)/, `${name} should use active glass border`)
  assert.match(block, /box-shadow:\s*var\(--apple-state-action-shadow\)/, `${name} should use active glass shadow`)
  assert.match(block, /backdrop-filter:\s*blur\(var\(--glass-blur-control\)\)\s*saturate\(var\(--glass-saturate-control\)\)/, `${name} should use control blur`)
  assert.match(block, /transition:\s*transform var\(--motion-standard\),\s*opacity var\(--motion-fast\)/, `${name} should use composited motion tokens`)
  assert.doesNotMatch(block, /background:\s*var\(--accent\)|border:\s*1px solid transparent|color:\s*var\(--text-on-accent\)|transition:[^;]*(?:background|border-color|box-shadow|color|filter|backdrop-filter)/, `${name} should not keep the legacy solid accent button or paint-heavy transitions`)
}

function assertGlassActionHover(block, name) {
  assert.match(block, /background:\s*var\(--surface-specular-edge\),\s*var\(--surface-noise\),\s*var\(--apple-state-action-bg-hover\)/, `${name} hover should use layered shared hover material`)
  assert.match(block, /border-color:\s*var\(--apple-state-action-border-hover\)/, `${name} hover should use shared hover border`)
  assert.match(block, /box-shadow:\s*var\(--apple-state-action-shadow-hover\)/, `${name} hover should use shared hover shadow`)
  assert.doesNotMatch(block, /background:\s*var\(--accent-light\)/, `${name} hover should not use accent-light`)
}

test('Apple empty and error states use shared glass actions', () => {
  const emptyRootBlock = sourceBlock(emptySource, '.apple-empty-state')
  const emptyOrbBlock = sourceBlock(emptySource, '.empty-orb')
  const emptyActionBlock = sourceBlock(emptySource, '.empty-action')
  const emptyActionHoverBlock = sourceBlock(emptySource, '.empty-action:hover')
  const errorRootBlock = sourceBlock(errorSource, '.apple-error-state')
  const errorButtonBlock = sourceBlock(errorSource, '.error-action')
  const errorButtonHoverBlock = sourceBlock(errorSource, '.error-action:hover')

  for (const [source, name] of [[emptySource, 'empty state'], [errorSource, 'error state']]) {
    assert.match(source, /--apple-state-action-bg:\s*var\(--glass-active-material\)/, `${name} should define active action material`)
    assert.match(source, /--apple-state-action-border:\s*var\(--glass-active-border\)/, `${name} should define active action border`)
    assert.match(source, /--apple-state-action-shadow:\s*var\(--glass-active-shadow\)/, `${name} should define active action shadow`)
  }

  assert.match(emptyRootBlock, /--apple-state-orb-bg:\s*var\(--material-glass-control\)/)
  assert.match(emptyOrbBlock, /background:\s*var\(--surface-specular-edge\),\s*var\(--surface-noise\),\s*var\(--apple-state-orb-bg\)/)
  assert.match(emptyOrbBlock, /border:\s*1px solid var\(--apple-state-orb-border\)/)
  assert.match(emptyOrbBlock, /box-shadow:\s*var\(--apple-state-orb-shadow\)/)
  assert.doesNotMatch(emptyOrbBlock, /radial-gradient\(circle at 30% 20%|var\(--surface-control\)|var\(--border-light\)/)

  assert.match(errorRootBlock, /--apple-state-action-bg-hover:\s*var\(--material-glass-control-hover\)/)

  assertGlassAction(emptyActionBlock, 'empty action')
  assertGlassActionHover(emptyActionHoverBlock, 'empty action')
  assertGlassAction(errorButtonBlock, 'error retry button')
  assertGlassActionHover(errorButtonHoverBlock, 'error retry button')
})

test('AppleEmptyState exposes a complete action area for next steps', () => {
  assert.match(emptySource, /:class="\['apple-empty-state apple-surface', `apple-empty-state--\$\{density\}`\]"/)
  assert.match(emptySource, /<div v-if="hasActions" class="apple-state-actions"/)
  assert.match(emptySource, /<button v-if="actionLabel" class="empty-action empty-action--primary"/)
  assert.match(emptySource, /<button v-if="secondaryActionLabel" class="empty-action empty-action--secondary"/)
  assert.match(emptySource, /<slot name="actions"/)
  assert.match(emptySource, /defineEmits\(\['action', 'secondary-action'\]\)/)
})

test('AppleErrorState uses alert semantics and offers primary plus secondary recovery actions', () => {
  assert.match(errorSource, /role="alert"/)
  assert.match(errorSource, /aria-live="assertive"/)
  assert.match(errorSource, /<div class="error-mark" aria-hidden="true"/)
  assert.match(errorSource, /<div v-if="hasActions" class="apple-state-actions"/)
  assert.match(errorSource, /<button v-if="retryLabel" class="error-action error-action--primary"/)
  assert.match(errorSource, /<button v-if="secondaryActionLabel" class="error-action error-action--secondary"/)
  assert.match(errorSource, /<slot name="actions"/)
  assert.match(errorSource, /defineEmits\(\['retry', 'secondary-action'\]\)/)
})
