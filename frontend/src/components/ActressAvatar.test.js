import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, join } from 'node:path'

const source = readFileSync(join(dirname(fileURLToPath(import.meta.url)), 'ActressAvatar.vue'), 'utf8')

test('ActressAvatar uses shared material and badge tokens instead of hardcoded legacy colors', () => {
  assert.match(source, /background:\s*var\(--material-glass-control/)
  assert.match(source, /color:\s*var\(--text-muted/)
  assert.match(source, /background:\s*var\(--badge-error-bg/)
  assert.match(source, /color:\s*var\(--badge-error-text/)
  assert.doesNotMatch(source, /#(?:ddd|999|ff4d4f|fff)\b/i)
})
