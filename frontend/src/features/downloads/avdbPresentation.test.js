import test from 'node:test'
import assert from 'node:assert/strict'

import {
  avdbSourceCountText,
  avdbState,
  formatAvdbCount,
  normalizeAvdbStatus,
  shouldPollAvdb,
} from './avdbPresentation.js'

test('normalizes the AVDB status contract', () => {
  assert.deepEqual(normalizeAvdbStatus({
    enabled: 1,
    sync_enabled: true,
    status: 'success',
    available: true,
    current_release: '2026.07.13',
    current_generation: 'gen-7',
    record_count: '406193',
    source_counts: { x1080x: 104909, sehuatang: 301284 },
    last_completed_at: '2026-07-13T09:00:00Z',
  }), {
    enabled: true,
    syncEnabled: true,
    status: 'success',
    available: true,
    release: '2026.07.13',
    generation: 'gen-7',
    recordCount: 406193,
    sourceCounts: { x1080x: 104909, sehuatang: 301284 },
    lastCheckedAt: '',
    lastStartedAt: '',
    lastCompletedAt: '2026-07-13T09:00:00Z',
    lastError: '',
  })
})

test('maps AVDB lifecycle states for source and job views', () => {
  assert.equal(avdbState({ sync_enabled: false }).code, 'unconfigured')
  assert.equal(avdbState({ sync_enabled: true, status: 'never' }).code, 'unsynced')
  assert.equal(avdbState({ status: 'running' }).code, 'syncing')
  assert.equal(avdbState({ status: 'success', available: true }).code, 'available')
  assert.equal(avdbState({ status: 'failed', available: true }).code, 'failed')
  assert.equal(avdbState({}, { loading: true }).code, 'loading')
  assert.equal(avdbState({}, { known: false }).code, 'unavailable')
})

test('polls AVDB only while the backend reports a running sync', () => {
  assert.equal(shouldPollAvdb({ status: 'running' }), true)
  assert.equal(shouldPollAvdb({ status: 'success' }), false)
  assert.equal(shouldPollAvdb({ status: 'failed' }), false)
  assert.equal(shouldPollAvdb({ status: 'never' }), false)
})

test('formats AVDB aggregate and per-source counts', () => {
  assert.equal(formatAvdbCount(406193), '406,193')
  assert.equal(formatAvdbCount('invalid'), '0')
  assert.equal(avdbSourceCountText({ x1080x: 104909, sehuatang: 301284 }), 'x1080x 104,909 · sehuatang 301,284')
})
