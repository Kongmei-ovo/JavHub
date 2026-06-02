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

test('StatCard uses shared Apple glass materials and a single props binding', () => {
  const card = sourceBlock('.stat-card')
  const hover = sourceBlock('.stat-card:hover')
  const arrow = sourceBlock('.stat-arrow')

  assert.match(source, /const props = defineProps\(/)
  assert.equal((source.match(/defineProps\(/g) || []).length, 1)
  assert.match(source, /if \(props\.link\)/)

  assert.match(card, /background:\s*var\(--surface-specular-edge\),\s*var\(--surface-noise\),\s*var\(--material-glass-control\)/)
  assert.match(card, /border:\s*1px solid var\(--glass-control-border\)/)
  assert.match(card, /box-shadow:\s*var\(--glass-control-shadow\)/)
  assert.match(card, /transition:\s*background var\(--motion-fast\)/)
  assert.match(card, /backdrop-filter:\s*blur\(var\(--glass-blur-control\)\)\s*saturate\(var\(--glass-saturate-control\)\)/)
  assert.doesNotMatch(card, /var\(--surface-card\)|var\(--border-light\)|var\(--shadow-hover\)|var\(--transition-pro\)/)

  assert.match(hover, /background:\s*var\(--surface-specular-edge-strong\),\s*var\(--surface-noise\),\s*var\(--material-glass-control-hover\)/)
  assert.match(hover, /border-color:\s*var\(--glass-control-border-hover\)/)
  assert.match(hover, /box-shadow:\s*var\(--glass-control-shadow-hover\)/)
  assert.doesNotMatch(hover, /var\(--shadow-hover\)|var\(--border-light\)/)

  assert.match(arrow, /transition:\s*color var\(--motion-fast\),\s*transform var\(--motion-fast\)/)
  assert.doesNotMatch(arrow, /var\(--transition-pro\)/)
})
