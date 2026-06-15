import test from 'node:test'
import assert from 'node:assert/strict'
import { existsSync, readFileSync } from 'node:fs'

const componentUrl = new URL('./DownloadStatsBar.vue', import.meta.url)
const source = existsSync(componentUrl) ? readFileSync(componentUrl, 'utf8') : ''

test('download stats bar owns download status cards without candidate metrics', () => {
  assert.ok(existsSync(componentUrl), 'DownloadStatsBar.vue should exist')
  assert.match(source, /name:\s*'DownloadStatsBar'/)
  assert.doesNotMatch(source, /CandidateOverview|candidateStats|open-preset/)
  assert.match(source, /props:\s*\{[\s\S]*stats:[\s\S]*statsLoaded:/)
  assert.match(source, /emits:\s*\[[^\]]*'select-status'[^\]]*\]/)
  assert.match(source, /class="stats-bar"/)
  assert.match(source, /v-for="item in statusCards"/)
  assert.match(source, /\$emit\('select-status', item\.status\)/)
  assert.match(source, /<style scoped src="\.\/downloads\.css"><\/style>/)
})
