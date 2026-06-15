import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

const source = readFileSync(new URL('./RepairLaneTab.vue', import.meta.url), 'utf8')
const apiSource = readFileSync(new URL('./useSupplementApi.js', import.meta.url), 'utf8')

test('RepairLaneTab owns diagnostics launchpad state and opens movie sources', () => {
  assert.match(source, /name:\s*'RepairLaneTab'/)
  assert.match(source, /useSupplementApi\(/)
  assert.match(source, /diagnosticsLaunchpadRows/)
  assert.match(source, /diagnosticsFocusMovie/)
  assert.match(source, /diagnosticsFocusMovieBadges/)
  assert.match(source, /openDiagnosticsFocusMovie/)
  assert.match(source, /openMovieSources/)
  assert.match(source, /sourceDiagnosticsOpen/)
  assert.match(source, /SupplementSourceDiagnosticsDialog/)
})

test('RepairLaneTab handles manual match operations through the shared composable', () => {
  assert.match(source, /manualMatchMovie/)
  assert.match(source, /manualIgnoreMovie/)
  assert.match(source, /manualUnmatchMovie/)
  assert.match(source, /manualContentId/)
  assert.match(source, /manualActionLoading/)
  assert.match(apiSource, /reloadCurrentDiagnostics/)
  assert.match(source, /emit\('movies-requested'/)
})
