import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

const source = readFileSync(new URL('./Genres.vue', import.meta.url), 'utf8')

function cssBlock(selector) {
  const escaped = selector.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  return source.match(new RegExp(`${escaped}\\s*\\{[^}]*\\}`))?.[0] || ''
}

function backgroundIncludes(block, token) {
  return new RegExp(`background:[\\s\\S]*var\\(${token}\\)`).test(block)
}

test('genres page only loads data needed for the initial tab', () => {
  assert.match(source, /const initialLoads = \[\]/)
  assert.match(source, /if \(this\.activeTab === 'genre'\) initialLoads\.push\(this\.loadCategories\(\)\)/)
  assert.doesNotMatch(source, /const initialLoads = \[[\s\S]*this\.loadActresses\(\),[\s\S]*\]/)
})

test('genres page does not import the motion vendor bundle for lightweight bubbles', () => {
  assert.doesNotMatch(source, /from 'gsap'/)
  assert.doesNotMatch(source, /from "gsap"/)
  assert.doesNotMatch(source, /gsap\./)
})

test('genres page loads categories lazily when the genre tab is opened', () => {
  assert.match(source, /if \(tab === 'genre' && !this\.categories\.length && !this\.loading\) \{[\s\S]*this\.loadCategories\(\)/)
})

test('genres page loads actresses lazily when the actress tab is opened', () => {
  assert.match(source, /if \(tab === 'actress' && !this\.actressRawPage\.length && !this\.actressesLoading\) \{[\s\S]*this\.loadActresses\(this\.actressPage\)/)
  assert.match(source, /'cfg\.actressAvatarSize'\(\) \{[\s\S]*if \(this\.activeTab === 'actress'\) this\.loadActresses\(1\)/)
  assert.match(source, /'cfg\.actressPageSize'\(\) \{[\s\S]*if \(this\.activeTab === 'actress'\) this\.loadActresses\(1\)/)
})

test('genres tab state is restored from and written to the route query', () => {
  assert.match(source, /tabFromRoute\(query = this\.\$route\.query\)/)
  assert.match(source, /this\.activeTab = this\.tabFromRoute\(\) \|\| \(this\.tabs\.some\(tab => tab\.key === this\.cfg\.defaultTab\) \? this\.cfg\.defaultTab : 'genre'\)/)
  assert.match(source, /'\$route\.query\.tab'\(\) \{[\s\S]*this\.applyRouteTab\(\)/)
  assert.match(source, /switchTab\(tab\) \{[\s\S]*this\.\$router\.push\(\{ path: this\.\$route\.path, query: \{ \.\.\.this\.\$route\.query, tab \} \}\)/)
})

test('genres actress cards use shared Apple glass pressable media chrome', () => {
  const card = cssBlock('.actress-card')
  assert.ok(backgroundIncludes(card, '--material-glass-subtle'))
  assert.match(card, /border:\s*1px solid var\(--glass-control-border\)/)
  assert.match(card, /box-shadow:\s*var\(--glass-control-shadow\)/)
  assert.match(card, /backdrop-filter:\s*blur\(var\(--glass-blur-control\)\)\s*saturate\(var\(--glass-saturate-control\)\)/)
  assert.match(card, /transition:\s*background var\(--motion-fast\)/)
  assert.doesNotMatch(card, /background:\s*transparent|border:\s*0|transition:\s*all/)

  const hover = cssBlock('.actress-card:hover')
  assert.ok(backgroundIncludes(hover, '--material-glass-control-hover'))
  assert.match(hover, /border-color:\s*var\(--glass-control-border-hover\)/)
  assert.match(hover, /box-shadow:\s*var\(--glass-control-shadow-hover\)/)

  const focus = cssBlock('.actress-card:focus-visible')
  assert.ok(backgroundIncludes(focus, '--material-glass-control-hover'))
  assert.match(focus, /border-color:\s*var\(--glass-control-border-hover\)/)
  assert.match(focus, /box-shadow:\s*var\(--glass-control-shadow-hover\),\s*0 0 0 4px rgba\(var\(--accent-rgb\),\s*0\.12\)/)

  const avatar = cssBlock('.actress-avatar')
  assert.ok(backgroundIncludes(avatar, '--material-glass-control'))
  assert.match(avatar, /border:\s*1px solid var\(--glass-control-border\)/)
  assert.match(avatar, /box-shadow:\s*var\(--glass-inner-shadow\)/)

  const avatarFocus = cssBlock('.actress-card:focus-visible .actress-avatar')
  assert.match(avatarFocus, /border-color:\s*var\(--glass-control-border-hover\)/)
  assert.match(avatarFocus, /box-shadow:\s*var\(--glass-control-shadow-hover\)/)

  const avatarImage = cssBlock('.actress-avatar img')
  const avatarImageFocus = cssBlock('.actress-card:focus-visible .actress-avatar img')
  assert.match(avatarImage, /transition:\s*transform var\(--motion-emphasized\)/)
  assert.match(avatarImageFocus, /transform:\s*translateY\(-2px\)/)
})

test('genres primary controls mirror hover glass treatment for keyboard focus', () => {
  const shuffleFocus = cssBlock('.shuffle-btn:focus-visible:not(:disabled)')
  const tabFocus = cssBlock('.tab-btn:focus-visible')
  const bubbleFocus = cssBlock('.bubble:focus-visible')

  for (const [block, label] of [
    [shuffleFocus, 'shuffle button'],
    [tabFocus, 'tab button'],
    [bubbleFocus, 'bubble button'],
  ]) {
    assert.match(block, /outline:\s*none/, `${label} should remove default outline after replacing it`)
    assert.ok(backgroundIncludes(block, '--material-glass-control-hover'), `${label} should use hover glass material`)
    assert.match(block, /border-color:\s*var\(--glass-control-border-hover\)/, `${label} should use hover border`)
    assert.match(block, /box-shadow:\s*var\(--glass-control-shadow-hover\),\s*0 0 0 (?:3|4)px rgba\(var\(--accent-rgb\),\s*0\.12\)/, `${label} should expose an Apple glass focus ring`)
  }

  assert.match(shuffleFocus, /color:\s*var\(--text-primary\)/)
  assert.match(tabFocus, /color:\s*var\(--text-primary\)/)
  assert.match(bubbleFocus, /transform:\s*translateY\(-2px\)/)
})

test('genres loading and actress skeletons use shared Apple glass materials', () => {
  const spinner = cssBlock('.spinner-large')
  const skeleton = cssBlock('.actress-skeleton-avatar,\n.actress-skeleton-line')
  const shimmer = cssBlock('.actress-skeleton-avatar::after,\n.actress-skeleton-line::after')

  assert.match(spinner, /border:\s*3px solid var\(--glass-control-border\)/)
  assert.match(spinner, /border-top-color:\s*var\(--glass-active-border\)/)
  assert.match(spinner, /box-shadow:\s*var\(--glass-control-shadow\)/)
  assert.doesNotMatch(spinner, /var\(--border-light\)|var\(--accent\)/)

  assert.ok(backgroundIncludes(skeleton, '--material-glass-subtle'))
  assert.match(skeleton, /var\(--surface-specular-edge/)
  assert.match(skeleton, /var\(--surface-noise\)/)
  assert.match(skeleton, /border:\s*1px solid var\(--glass-control-border\)/)
  assert.match(skeleton, /box-shadow:\s*var\(--glass-inner-shadow\)/)
  assert.match(skeleton, /backdrop-filter:\s*blur\(var\(--glass-blur-control\)\)\s*saturate\(var\(--glass-saturate-control\)\)/)
  assert.doesNotMatch(skeleton, /var\(--surface-control\)|var\(--border-light\)|rgba\(255,\s*255,\s*255/)

  assert.match(shimmer, /background:\s*linear-gradient\(100deg,\s*transparent 0%,\s*var\(--material-glass-control-hover\) 46%,\s*transparent 72%\)/)
  assert.doesNotMatch(shimmer, /rgba\(255,\s*255,\s*255|rgba\(255,255,255/)
})

test('genres glass backgrounds are layered with specular and noise surfaces', () => {
  const singleLayerGlass = /^background:\s*var\(--(?:material-glass-control|material-glass-control-hover|material-glass-sheet|material-glass-subtle|glass-active-material)\);$/gm
  assert.doesNotMatch(source, singleLayerGlass)

  const layeredBlocks = [
    cssBlock('.shuffle-btn'),
    cssBlock('.shuffle-btn:hover:not(:disabled)'),
    cssBlock('.tab-bar'),
    cssBlock('.tab-btn'),
    cssBlock('.tab-btn:hover'),
    cssBlock('.tab-btn.active'),
    cssBlock('.actress-card'),
    cssBlock('.actress-card:hover'),
    cssBlock('.actress-avatar'),
    cssBlock('.actress-skeleton-avatar,\n.actress-skeleton-line'),
    cssBlock('.tag-cloud'),
    cssBlock('.bubble'),
    cssBlock('.bubble:hover'),
    cssBlock('.bubble.active'),
  ]

  for (const block of layeredBlocks) {
    assert.match(block, /var\(--surface-specular-edge/)
    assert.match(block, /var\(--surface-noise\)/)
  }
})
