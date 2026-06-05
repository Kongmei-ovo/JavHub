import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

const source = readFileSync(new URL('./ActressCard.vue', import.meta.url), 'utf8')

function cssRule(selector) {
  const escaped = selector.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  const match = source.match(new RegExp(`${escaped}\\s*\\{([\\s\\S]*?)\\n\\}`))
  assert.ok(match, `Expected CSS rule for ${selector}`)
  return match[1]
}

function assertLayeredSemanticBackground(block, token, label) {
  assert.match(
    block,
    new RegExp(`background:\\s*var\\(--surface-specular-edge\\),\\s*var\\(--surface-noise\\),\\s*var\\(${token}\\)`),
    `${label} should layer semantic fill with shared glass highlights`
  )
}

test('ActressCard uses shared Apple glass materials instead of legacy dark fog', () => {
  const card = cssRule('.actress-card')
  const hover = cssRule('.actress-card:hover')
  const focus = cssRule('.actress-card:focus-visible')
  const imageFocus = cssRule('.actress-card:focus-visible .cover-img')
  const media = cssRule('.card-cover')

  assert.match(card, /background:\s*var\(--surface-specular-edge\),\s*var\(--surface-noise\),\s*var\(--material-glass-control\)/)
  assert.match(card, /border:\s*1px solid var\(--glass-control-border\)/)
  assert.match(card, /box-shadow:\s*var\(--glass-control-shadow\)/)
  assert.match(card, /backdrop-filter:\s*blur\(var\(--glass-blur-control\)\)\s*saturate\(var\(--glass-saturate-control\)\)/)
  assert.match(card, /transition:\s*transform var\(--motion-standard\),\s*background var\(--motion-standard\),\s*border-color var\(--motion-standard\),\s*box-shadow var\(--motion-standard\)/)
  assert.doesNotMatch(card, /var\(--surface-card\)|var\(--glass-surface-shadow\)|var\(--glass-blur-surface\)|transition:\s*all|blur\(80px\)|rgba\(255,\s*255,\s*255,\s*0\.04\)/)

  assert.match(hover, /background:\s*var\(--surface-specular-edge-strong\),\s*var\(--surface-noise\),\s*var\(--material-glass-control-hover\)/)
  assert.match(hover, /border-color:\s*var\(--glass-control-border-hover\)/)
  assert.match(hover, /box-shadow:\s*var\(--glass-control-shadow-hover\)/)
  assert.doesNotMatch(hover, /var\(--surface-card-hover\)|var\(--shadow-floating\)|rgba\(0,\s*0,\s*0,\s*0\.4\)/)

  assert.match(focus, /border-color:\s*var\(--glass-control-border-hover\)/)
  assert.match(focus, /background:\s*var\(--surface-specular-edge-strong\),\s*var\(--surface-noise\),\s*var\(--material-glass-control-hover\)/)
  assert.match(focus, /box-shadow:\s*var\(--glass-control-shadow-hover\),\s*var\(--focus-ring-wide\),\s*var\(--glass-inner-shadow\)/)
  assert.doesNotMatch(focus, /var\(--shadow-floating\)/)
  assert.match(imageFocus, /transform:\s*scale\(1\.06\)/)

  assert.match(media, /background:\s*var\(--surface-specular-edge\),\s*var\(--surface-noise\),\s*var\(--material-glass-subtle\)/)
  assert.match(media, /box-shadow:\s*var\(--glass-inner-shadow\)/)
  assert.doesNotMatch(media, /background:\s*var\(--material-glass-subtle\);/)
  assert.doesNotMatch(media, /rgba\(255,\s*255,\s*255,\s*0\.03\)/)
})

test('ActressCard badges and meta colors use theme status tokens', () => {
  const coverBadge = cssRule('.cover-badge')
  const coverHeart = cssRule('.cover-heart')
  const candidateBadge = cssRule('.candidate-badge')
  const subscribedMeta = cssRule('.meta-subscribed')
  const candidateMeta = cssRule('.meta-candidate')

  for (const block of [coverBadge, coverHeart]) {
    assert.match(block, /background:\s*var\(--surface-specular-edge\),\s*var\(--surface-noise\),\s*var\(--material-glass-control\)/)
    assert.match(block, /border:\s*1px solid var\(--glass-control-border\)/)
    assert.match(block, /box-shadow:\s*var\(--glass-control-shadow\)/)
    assert.match(block, /backdrop-filter:\s*blur\(var\(--glass-blur-control\)\)\s*saturate\(var\(--glass-saturate-control\)\)/)
    assert.doesNotMatch(block, /rgba\(0,\s*0,\s*0|rgba\(255,\s*255,\s*255/)
  }

  assertLayeredSemanticBackground(candidateBadge, '--badge-warning-bg', 'candidate badge')
  assert.match(candidateBadge, /border:\s*1px solid var\(--badge-warning-border\)/)
  assert.match(candidateBadge, /color:\s*var\(--badge-warning-text\)/)
  assert.match(candidateBadge, /box-shadow:\s*var\(--glass-control-shadow\)/)
  assert.doesNotMatch(candidateBadge, /#ff9f0a|#111|rgba\(0,\s*0,\s*0/)

  assert.match(subscribedMeta, /color:\s*var\(--badge-error-text\)/)
  assert.match(candidateMeta, /color:\s*var\(--badge-warning-text\)/)
  assert.doesNotMatch(source, /fill="#FF375F"/)
})
