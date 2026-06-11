import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

const source = readFileSync(new URL('./AppleSkeleton.vue', import.meta.url), 'utf8')
const style = source.match(/<style scoped>([\s\S]*)<\/style>/)?.[1] || ''

function cssBlock(selector) {
  const blocks = [...style.matchAll(/([^{}]+)\{([^{}]*)\}/g)]
    .filter(([, selectors]) => selectors
      .split(',')
      .map(part => part.trim())
      .includes(selector))
    .map(([, , block]) => block)
  assert.ok(blocks.length, `${selector} should exist in AppleSkeleton.vue`)
  return blocks.join('\n')
}

test('AppleSkeleton card loading state uses layered subtle glass material', () => {
  const card = cssBlock('.apple-skeleton--card')

  assert.match(card, /background:\s*var\(--card\)/)
  assert.match(card, /border:\s*1px solid var\(--hairline\)/)
  assert.match(card, /box-shadow:\s*(?:none|var\(--shadow-card\))/)
  assert.doesNotMatch(card, /backdrop-filter/)
  assert.doesNotMatch(card, /background:\s*var\(--material-glass-subtle\);/)
  assert.doesNotMatch(card, /var\(--surface-card\)|var\(--border\)|var\(--glass-surface-shadow\)|var\(--glass-blur-surface\)/)
})

test('AppleSkeleton supports reusable page and list loading layouts', () => {
  assert.match(source, /variant === 'gallery'/)
  assert.match(source, /variant === 'list'/)
  assert.match(source, /:style="\[styleVars, gridVars\]"/)
  assert.match(source, /items:\s*\{\s*type:\s*Number,\s*default:\s*6\s*\}/)
  assert.match(source, /columns:\s*\{\s*type:\s*String,\s*default:\s*'repeat\(auto-fill, minmax\(180px, 1fr\)\)'\s*\}/)
  assert.match(source, /class="apple-skeleton-grid"/)
  assert.match(source, /class="apple-skeleton-list"/)
  assert.match(source, /--skeleton-grid-columns/)
})
