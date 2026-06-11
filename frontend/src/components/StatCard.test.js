import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

const source = readFileSync(new URL('./StatCard.vue', import.meta.url), 'utf8')
const style = source.match(/<style scoped>([\s\S]*)<\/style>/)?.[1] || ''

function sourceBlock(selector) {
  return [...style.matchAll(/([^{}]+)\{([^{}]*)\}/g)]
    .filter(([, selectors]) => selectors
      .split(',')
      .map(part => part.trim())
      .includes(selector))
    .map(([, selectors, block]) => `${selectors.trim()} {${block}}`)
    .join('\n')
}

test('StatCard uses a solid content surface and a single props binding', () => {
  const card = sourceBlock('.stat-card')
  const hover = sourceBlock('.stat-card:hover')
  const arrow = sourceBlock('.stat-arrow')

  assert.match(source, /const props = defineProps\(/)
  assert.equal((source.match(/defineProps\(/g) || []).length, 1)
  assert.match(source, /if \(props\.link\)/)

  assert.match(card, /background:\s*var\(--card\)/)
  assert.match(card, /border:\s*1px solid var\(--hairline\)/)
  assert.match(card, /box-shadow:\s*var\(--shadow-card\)/)
  assert.match(card, /transition:\s*transform var\(--motion-standard\)/)
  assert.doesNotMatch(card, /transition:[^;]*(?:background|border-color|box-shadow|filter|backdrop-filter)/)
  assert.doesNotMatch(card, /material-glass|surface-specular-edge|surface-noise|backdrop-filter/)
  assert.doesNotMatch(card, /var\(--surface-card\)|var\(--border-light\)|var\(--shadow-hover\)|var\(--transition-pro\)/)

  assert.match(hover, /background:\s*var\(--card-hover\)/)
  assert.match(hover, /border-color:\s*var\(--hairline-strong\)/)
  assert.match(hover, /box-shadow:\s*var\(--shadow-card\)/)
  assert.doesNotMatch(hover, /material-glass|surface-specular-edge|surface-noise|backdrop-filter/)
  assert.doesNotMatch(hover, /var\(--shadow-hover\)|var\(--border-light\)/)

  assert.match(arrow, /transition:\s*transform var\(--motion-standard\)/)
  assert.doesNotMatch(arrow, /transition:[^;]*color/)
  assert.doesNotMatch(arrow, /var\(--transition-pro\)/)
})
