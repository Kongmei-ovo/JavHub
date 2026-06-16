import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

const source = readFileSync(new URL('./SourcesHealthTab.vue', import.meta.url), 'utf8')
const apiSource = readFileSync(new URL('./useSupplementApi.js', import.meta.url), 'utf8')

test('SourcesHealthTab owns source health and provider smoke fetching', () => {
  assert.match(source, /name:\s*'SourcesHealthTab'/)
  assert.match(source, /useSupplementApi\(/)
  assert.match(source, /SourceHealthPanel/)
  assert.match(source, /loadSourceHealth\(/)
  assert.match(source, /runProviderSmoke/)
  assert.match(source, /loadProviderSmokeRuns/)
  assert.match(source, /pauseSource/)
  assert.match(source, /resumeSource/)
  assert.match(source, /sourceHealthRows/)
  assert.match(source, /providerSourceOptions/)
})

test('SourcesHealthTab no longer hosts gfriends avatar sync (moved to Jobs tab)', () => {
  // Work-first restructure: avatar override is a global maintenance job and now
  // lives in the Jobs tab, not under source health.
  assert.doesNotMatch(source, /confirmGfriendsAvatarSync/)
  assert.doesNotMatch(source, /view-avatar-jobs/)
  assert.doesNotMatch(source, /gfriends-avatar-job=/)
  // the underlying API still exists for the Jobs tab to use
  assert.match(apiSource, /startGfriendsAvatarSyncJob/)
})
