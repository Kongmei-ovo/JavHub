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
  assert.match(block, /background:\s*var\(--apple-state-action-bg\)/, `${name} should use active glass material`)
  assert.match(block, /border:\s*1px solid var\(--apple-state-action-border\)/, `${name} should use active glass border`)
  assert.match(block, /box-shadow:\s*var\(--apple-state-action-shadow\)/, `${name} should use active glass shadow`)
  assert.match(block, /backdrop-filter:\s*blur\(var\(--glass-blur-control\)\)\s*saturate\(var\(--glass-saturate-control\)\)/, `${name} should use control blur`)
  assert.match(block, /transition:\s*transform var\(--motion-standard\),\s*background var\(--motion-standard\),\s*border-color var\(--motion-standard\),\s*box-shadow var\(--motion-standard\),\s*opacity var\(--motion-fast\)/, `${name} should use explicit motion tokens`)
  assert.doesNotMatch(block, /background:\s*var\(--accent\)|border:\s*1px solid transparent|color:\s*var\(--text-on-accent\)|transition:\s*transform var\(--motion-fast\),\s*background var\(--motion-fast\)/, `${name} should not keep the legacy solid accent button`)
}

function assertGlassActionHover(block, name) {
  assert.match(block, /background:\s*var\(--apple-state-action-bg-hover\)/, `${name} hover should use shared hover material`)
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
  const errorButtonBlock = sourceBlock(errorSource, 'button')
  const errorButtonHoverBlock = sourceBlock(errorSource, 'button:hover')

  for (const [source, name] of [[emptySource, 'empty state'], [errorSource, 'error state']]) {
    assert.match(source, /--apple-state-action-bg:\s*var\(--glass-active-material\)/, `${name} should define active action material`)
    assert.match(source, /--apple-state-action-border:\s*var\(--glass-active-border\)/, `${name} should define active action border`)
    assert.match(source, /--apple-state-action-shadow:\s*var\(--glass-active-shadow\)/, `${name} should define active action shadow`)
  }

  assert.match(emptyRootBlock, /--apple-state-orb-bg:\s*var\(--material-glass-control\)/)
  assert.match(emptyOrbBlock, /background:\s*var\(--apple-state-orb-bg\)/)
  assert.match(emptyOrbBlock, /border:\s*1px solid var\(--apple-state-orb-border\)/)
  assert.match(emptyOrbBlock, /box-shadow:\s*var\(--apple-state-orb-shadow\)/)
  assert.doesNotMatch(emptyOrbBlock, /radial-gradient\(circle at 30% 20%|var\(--surface-control\)|var\(--border-light\)/)

  assert.match(errorRootBlock, /--apple-state-action-bg-hover:\s*var\(--material-glass-control-hover\)/)

  assertGlassAction(emptyActionBlock, 'empty action')
  assertGlassActionHover(emptyActionHoverBlock, 'empty action')
  assertGlassAction(errorButtonBlock, 'error retry button')
  assertGlassActionHover(errorButtonHoverBlock, 'error retry button')
})
