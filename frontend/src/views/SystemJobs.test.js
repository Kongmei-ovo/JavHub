import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

const source = readFileSync(new URL('./SystemJobs.vue', import.meta.url), 'utf8')

test('system jobs has a dedicated AVDB full-sync area', () => {
  assert.match(source, /ref="avdbSection"/)
  assert.match(source, /AVDB 全量同步/)
  assert.match(source, /api\.getAvdbStatus\(\)/)
  assert.match(source, /api\.runAvdbSync\(\)/)
  assert.match(source, /sync_enabled:\s*true/)
  assert.match(source, /avdb_sync:\s*'avdbSection'/)
})

test('AVDB job supports status polling and a safe return to source management', () => {
  assert.match(source, /if \(this\.avdbShouldPoll\)/)
  assert.match(source, /this\.refreshAvdb\(\{ silent: true \}\)/)
  assert.match(source, /return_to/)
  assert.match(source, /target\.startsWith\('\/'\) && !target\.startsWith\('\/\/'\)/)
  assert.match(source, /返回下载源/)
  assert.match(source, /job\.id !== 'avdb_sync'/)
})

test('AVDB run is disabled for unknown status and preserves the enabled source flag', () => {
  assert.match(source, /:disabled="avdbRunDisabled"/)
  assert.match(source, /return this\.avdbBusy \|\| this\.avdbStatusLoading \|\| !this\.avdbStatusKnown/)
  assert.match(source, /if \(this\.avdbRunDisabled\) return/)
  assert.match(source, /enabled:\s*this\.normalizedAvdb\.enabled/)
  assert.match(source, /sync_enabled:\s*true/)
})

test('AVDB job polling prevents overlapping status and schedule refreshes', () => {
  assert.match(source, /if \(this\.avdbPollPending\) return/)
  assert.match(source, /this\.avdbPollPending = true/)
  assert.match(source, /this\.avdbPollPending = false/)
  assert.match(source, /if \(this\.schedulerLoading\) return/)
})

test('AVDB job keeps polling after transient status failures with a bounded retry budget', () => {
  assert.match(source, /const AVDB_POLL_RETRY_LIMIT = 5/)
  assert.match(source, /this\.normalizedAvdb\.status === 'running'/)
  assert.match(source, /this\.avdbPollFailures < AVDB_POLL_RETRY_LIMIT/)
  assert.match(source, /if \(this\.avdbShouldPoll\) this\.refreshAvdb\(\{ silent: true \}\)/)
  assert.match(source, /this\.avdbPollFailures = Math\.min\(/)
  assert.match(source, /this\.avdbPollFailures = 0/)
})
