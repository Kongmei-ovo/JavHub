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

test('AppleSkeleton card loading state uses shared subtle glass material', () => {
  const card = cssBlock('.apple-skeleton--card')

  assert.match(card, /background:\s*var\(--material-glass-subtle\)/)
  assert.match(card, /border:\s*1px solid var\(--glass-control-border\)/)
  assert.match(card, /box-shadow:\s*var\(--glass-control-shadow\)/)
  assert.match(card, /backdrop-filter:\s*blur\(var\(--glass-blur-control\)\)\s*saturate\(var\(--glass-saturate-control\)\)/)
  assert.doesNotMatch(card, /var\(--surface-card\)|var\(--border\)|var\(--glass-surface-shadow\)|var\(--glass-blur-surface\)/)
})
