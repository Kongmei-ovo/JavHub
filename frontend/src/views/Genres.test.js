import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

const source = readFileSync(new URL('./Genres.vue', import.meta.url), 'utf8')

function cssBlock(selector) {
  const escaped = selector.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  return source.match(new RegExp(`${escaped}\\s*\\{[^}]*\\}`))?.[0] || ''
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
  assert.match(card, /background:\s*var\(--material-glass-subtle\)/)
  assert.match(card, /border:\s*1px solid var\(--glass-control-border\)/)
  assert.match(card, /box-shadow:\s*var\(--glass-control-shadow\)/)
  assert.match(card, /backdrop-filter:\s*blur\(var\(--glass-blur-control\)\)\s*saturate\(var\(--glass-saturate-control\)\)/)
  assert.match(card, /transition:\s*background var\(--motion-fast\)/)
  assert.doesNotMatch(card, /background:\s*transparent|border:\s*0|transition:\s*all/)

  const hover = cssBlock('.actress-card:hover')
  assert.match(hover, /background:\s*var\(--material-glass-control-hover\)/)
  assert.match(hover, /border-color:\s*var\(--glass-control-border-hover\)/)
  assert.match(hover, /box-shadow:\s*var\(--glass-control-shadow-hover\)/)

  const avatar = cssBlock('.actress-avatar')
  assert.match(avatar, /background:\s*var\(--material-glass-control\)/)
  assert.match(avatar, /border:\s*1px solid var\(--glass-control-border\)/)
  assert.match(avatar, /box-shadow:\s*var\(--glass-inner-shadow\)/)
})

test('genres loading and actress skeletons use shared Apple glass materials', () => {
  const spinner = cssBlock('.spinner-large')
  const skeleton = cssBlock('.actress-skeleton-avatar,\n.actress-skeleton-line')
  const shimmer = cssBlock('.actress-skeleton-avatar::after,\n.actress-skeleton-line::after')

  assert.match(spinner, /border:\s*3px solid var\(--glass-control-border\)/)
  assert.match(spinner, /border-top-color:\s*var\(--glass-active-border\)/)
  assert.match(spinner, /box-shadow:\s*var\(--glass-control-shadow\)/)
  assert.doesNotMatch(spinner, /var\(--border-light\)|var\(--accent\)/)

  assert.match(skeleton, /background:\s*var\(--material-glass-subtle\)/)
  assert.match(skeleton, /border:\s*1px solid var\(--glass-control-border\)/)
  assert.match(skeleton, /box-shadow:\s*var\(--glass-inner-shadow\)/)
  assert.match(skeleton, /backdrop-filter:\s*blur\(var\(--glass-blur-control\)\)\s*saturate\(var\(--glass-saturate-control\)\)/)
  assert.doesNotMatch(skeleton, /var\(--surface-control\)|var\(--border-light\)|rgba\(255,\s*255,\s*255/)

  assert.match(shimmer, /background:\s*linear-gradient\(100deg,\s*transparent 0%,\s*var\(--material-glass-control-hover\) 46%,\s*transparent 72%\)/)
  assert.doesNotMatch(shimmer, /rgba\(255,\s*255,\s*255|rgba\(255,255,255/)
})
