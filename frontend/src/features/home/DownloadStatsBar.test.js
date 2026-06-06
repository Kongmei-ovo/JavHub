import test from 'node:test'
import assert from 'node:assert/strict'
import { existsSync, readFileSync } from 'node:fs'

const componentUrl = new URL('./DownloadStatsBar.vue', import.meta.url)
const source = existsSync(componentUrl) ? readFileSync(componentUrl, 'utf8') : ''

test('download stats bar owns status cards and delegates candidate metrics', () => {
  assert.ok(existsSync(componentUrl), 'DownloadStatsBar.vue should exist')
  assert.match(source, /name:\s*'DownloadStatsBar'/)
  assert.match(source, /import CandidateOverview from '\.\/CandidateOverview\.vue'/)
  assert.match(source, /props:\s*\{[\s\S]*stats:[\s\S]*candidateStats:/)
  assert.match(source, /emits:\s*\[[^\]]*'select-status'[^\]]*'open-preset'[^\]]*\]/)
  assert.match(source, /class="stats-bar"/)
  assert.match(source, /v-for="item in statusCards"/)
  assert.match(source, /\$emit\('select-status', item\.status\)/)
  assert.match(source, /<CandidateOverview[\s\S]*:candidate-stats="candidateStats"[\s\S]*@open-preset="\$emit\('open-preset', \$event\)"/)
})
