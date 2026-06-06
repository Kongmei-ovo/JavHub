import test from 'node:test'
import assert from 'node:assert/strict'
import { existsSync, readFileSync } from 'node:fs'

const componentUrl = new URL('./CandidateOverview.vue', import.meta.url)
const source = existsSync(componentUrl) ? readFileSync(componentUrl, 'utf8') : ''

test('candidate overview exposes the six download candidate presets', () => {
  assert.ok(existsSync(componentUrl), 'CandidateOverview.vue should exist')
  assert.match(source, /name:\s*'CandidateOverview'/)
  assert.match(source, /candidateStats:\s*\{ type: Object/)
  assert.match(source, /emits:\s*\[[^\]]*'open-preset'[^\]]*\]/)
  assert.match(source, /readyCandidateCount\(\)/)
  for (const label of ['待确认候选', '待补磁力', '可批准', '订阅发现', '库存发现', '补全发现']) {
    assert.match(source, new RegExp(label))
  }
  assert.match(source, /\$emit\('open-preset', \{ status: 'candidate', needs_magnet: true, source: '' \}\)/)
  assert.match(source, /\$emit\('open-preset', \{ status: 'candidate', source: 'subscription' \}\)/)
})
