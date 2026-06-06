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

test('SourcesHealthTab keeps gfriends avatar sync controls inside the tab', () => {
  assert.match(source, /syncGfriendsAvatars/)
  assert.match(source, /requestConfirm/)
  assert.match(apiSource, /startGfriendsAvatarSyncJob/)
  assert.match(source, /gfriendsAvatarJob/)
  assert.match(source, /gfriendsAvatarSyncing/)
  assert.match(source, /emit\('view-avatar-jobs'/)
  assert.match(source, /同步演员头像/)
})
